"""SQLite schema (single file DB). Candles are stored for every symbol/timeframe; everything else is small."""
from __future__ import annotations
import json
import sqlite3
import threading
from datetime import datetime
import pandas as pd
from .lifecycle import Signal
from .gates import Protections

SCHEMA = """
PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS instruments(
  symbol TEXT PRIMARY KEY, name TEXT, exchange TEXT, token TEXT, segment TEXT, asset_class TEXT,
  lot_size INTEGER, tick_size REAL, expiry TEXT, tier INTEGER DEFAULT 3, paper INTEGER DEFAULT 0, updated_at TEXT);
CREATE TABLE IF NOT EXISTS candles(
  symbol TEXT NOT NULL, tf TEXT NOT NULL, ts TEXT NOT NULL,
  open REAL, high REAL, low REAL, close REAL, volume REAL, oi REAL,
  PRIMARY KEY(symbol, tf, ts));
CREATE TABLE IF NOT EXISTS signals(
  id TEXT PRIMARY KEY, symbol TEXT, asset_class TEXT, direction TEXT, kind TEXT, state TEXT, grade TEXT,
  confidence REAL, paper INTEGER, entry_lo REAL, entry_hi REAL, sl REAL, t1 REAL, t2 REAL, chase_price REAL,
  valid_till TEXT, exit_by TEXT, created_at TEXT, entry_price REAL, exit_price REAL, closed_at TEXT,
  r_multiple REAL, close_reason TEXT, reasons_json TEXT, extra_json TEXT);
CREATE INDEX IF NOT EXISTS ix_signals_state ON signals(state);
CREATE TABLE IF NOT EXISTS news_items(
  id INTEGER PRIMARY KEY AUTOINCREMENT, url_hash TEXT UNIQUE, title TEXT, source TEXT, official INTEGER,
  ts TEXT, story_id INTEGER, tags_json TEXT);
CREATE TABLE IF NOT EXISTS events(
  id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, when_ts TEXT, impact TEXT, assets_json TEXT,
  forecast REAL, previous REAL, actual REAL, source TEXT, UNIQUE(name, when_ts));
CREATE TABLE IF NOT EXISTS setup_stats(
  setup_key TEXT PRIMARY KEY, trades INTEGER, expectancy_r REAL, win_rate REAL, benched INTEGER DEFAULT 0, updated_at TEXT);
CREATE TABLE IF NOT EXISTS protections_state(
  k TEXT PRIMARY KEY, v TEXT);
CREATE TABLE IF NOT EXISTS decisions(
  symbol TEXT PRIMARY KEY, ts TEXT, action TEXT, json TEXT);
CREATE TABLE IF NOT EXISTS settings(
  k TEXT PRIMARY KEY, v TEXT);
CREATE TABLE IF NOT EXISTS health_log(
  id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT, component TEXT, status TEXT, detail TEXT);
"""


class _Rows:
    """Rows are read inside the lock, so no other thread can touch the cursor."""
    def __init__(self, rows):
        self._r = rows

    def fetchone(self):
        return self._r[0] if self._r else None

    def fetchall(self):
        return list(self._r)

    def __iter__(self):
        return iter(self._r)


class LockedConnection:
    """One SQLite connection shared by scheduler / API / Telegram threads, serialized by an RLock (a bare shared
    connection raised thousands of InterfaceError in a stress test)."""
    def __init__(self, con: sqlite3.Connection):
        self._con, self._lock = con, threading.RLock()

    def execute(self, sql, params=()):
        with self._lock:
            cur = self._con.execute(sql, params)
            return _Rows(cur.fetchall() if cur.description else [])

    def executemany(self, sql, seq):
        with self._lock:
            self._con.executemany(sql, seq)

    def executescript(self, sql):
        with self._lock:
            self._con.executescript(sql)

    def commit(self):
        with self._lock:
            self._con.commit()

    def close(self):
        with self._lock:
            self._con.close()


def connect(path: str = "rtw.db") -> LockedConnection:
    con = sqlite3.connect(path, check_same_thread=False, timeout=30)
    con.row_factory = sqlite3.Row
    con.executescript(SCHEMA)
    return LockedConnection(con)


def save_signal(con: sqlite3.Connection, s: Signal, extra: dict | None = None):
    d = s.to_dict()
    con.execute(
        """INSERT INTO signals(id,symbol,asset_class,direction,kind,state,grade,confidence,paper,entry_lo,entry_hi,sl,t1,t2,
           chase_price,valid_till,exit_by,created_at,entry_price,exit_price,closed_at,r_multiple,close_reason,reasons_json,extra_json)
           VALUES(:id,:symbol,:asset_class,:direction,:kind,:state,:grade,:confidence,:paper,:entry_lo,:entry_hi,:sl,:t1,:t2,
           :chase_price,:valid_till,:exit_by,:created_at,:entry_price,:exit_price,:closed_at,:r_multiple,:close_reason,:reasons_json,:extra_json)
           ON CONFLICT(id) DO UPDATE SET state=excluded.state, kind=excluded.kind, entry_price=excluded.entry_price,
           exit_price=excluded.exit_price, closed_at=excluded.closed_at, r_multiple=excluded.r_multiple,
           close_reason=excluded.close_reason, exit_by=excluded.exit_by, extra_json=excluded.extra_json""",
        {**d, "paper": int(s.paper), "reasons_json": json.dumps(s.reasons, ensure_ascii=False),
         "extra_json": json.dumps(extra or {}, ensure_ascii=False)})
    con.commit()


def upsert_candles(con: sqlite3.Connection, symbol: str, tf: str, rows: list[tuple]):
    """rows: (ts_iso, open, high, low, close, volume[, oi])"""
    norm = [(symbol, tf, r[0], r[1], r[2], r[3], r[4], r[5], (r[6] if len(r) > 6 else None)) for r in rows]
    con.executemany("INSERT OR REPLACE INTO candles(symbol,tf,ts,open,high,low,close,volume,oi) VALUES(?,?,?,?,?,?,?,?,?)", norm)
    con.commit()


def track_record(con: sqlite3.Connection, paper: bool | None = None) -> dict:
    q = "SELECT r_multiple FROM signals WHERE state IN ('TARGET','SL','EXPIRED') AND r_multiple IS NOT NULL AND kind='TRADE'"
    args: list = []
    if paper is not None:
        q += " AND paper=?"
        args.append(int(paper))
    rs = [r[0] for r in con.execute(q, args).fetchall()]
    n = len(rs)
    wins = sum(1 for r in rs if r > 0)
    return {"trades": n, "win_rate": (wins / n) if n else 0.0, "total_r": sum(rs), "avg_r": (sum(rs) / n) if n else 0.0}


# ------------------------------------------------------------------ small helpers used by the pipeline / API
def get_setting(con, k: str, default=None):
    r = con.execute("SELECT v FROM settings WHERE k=?", (k,)).fetchone()
    return json.loads(r[0]) if r else default


def set_setting(con, k: str, v) -> None:
    con.execute("INSERT INTO settings(k,v) VALUES(?,?) ON CONFLICT(k) DO UPDATE SET v=excluded.v", (k, json.dumps(v, ensure_ascii=False, default=str)))
    con.commit()


def load_df(con, symbol: str, tf: str = "5m", n: int = 400) -> pd.DataFrame | None:
    rows = con.execute("SELECT ts,open,high,low,close,volume FROM candles WHERE symbol=? AND tf=? ORDER BY ts DESC LIMIT ?", (symbol, tf, n)).fetchall()
    if not rows:
        return None
    df = pd.DataFrame([tuple(r) for r in rows][::-1], columns=["ts", "open", "high", "low", "close", "volume"])
    df["ts"] = pd.to_datetime(df["ts"], utc=True).dt.tz_convert("Asia/Kolkata")
    return df.set_index("ts")


def signal_from_row(r) -> Signal:
    d = dict(r)
    f = lambda k: datetime.fromisoformat(d[k]) if d.get(k) else None
    return Signal(id=d["id"], symbol=d["symbol"], asset_class=d["asset_class"], direction=d["direction"], entry_lo=d["entry_lo"],
                  entry_hi=d["entry_hi"], sl=d["sl"], t1=d["t1"], t2=d["t2"], chase_price=d["chase_price"], valid_till=f("valid_till"),
                  exit_by=f("exit_by"), created_at=f("created_at"), grade=d["grade"] or "C", confidence=d["confidence"] or 0.0,
                  paper=bool(d["paper"]), kind=d["kind"], state=d["state"], entry_price=d["entry_price"], exit_price=d["exit_price"],
                  closed_at=f("closed_at"), r_multiple=d["r_multiple"], close_reason=d["close_reason"] or "",
                  sl_dist=abs((d["entry_lo"] + d["entry_hi"]) / 2.0 - d["sl"]), reasons=json.loads(d["reasons_json"] or "[]"))


def open_trade(con):
    """The single open TRADE signal (state NEW/ACTIVE) or None. Returns (Signal, extra_dict)."""
    r = con.execute("SELECT * FROM signals WHERE kind='TRADE' AND state IN ('NEW','ACTIVE') ORDER BY created_at DESC LIMIT 1").fetchone()
    if not r:
        return None, {}
    return signal_from_row(r), json.loads(r["extra_json"] or "{}")


def open_trades(con) -> list:
    """All open TRADE signals (NEW/ACTIVE), oldest first. Returns [(Signal, extra_dict)]."""
    rows = con.execute("SELECT * FROM signals WHERE kind='TRADE' AND state IN ('NEW','ACTIVE') ORDER BY created_at ASC").fetchall()
    return [(signal_from_row(r), json.loads(r["extra_json"] or "{}")) for r in rows]


def load_protections(con) -> Protections:
    raw = get_setting(con, "protections")
    p = Protections()
    if raw:
        p.results_r = [(datetime.fromisoformat(t), float(x)) for t, x in raw.get("results_r", [])]
        p.paused_until = datetime.fromisoformat(raw["paused_until"]) if raw.get("paused_until") else None
        p.halted = bool(raw.get("halted"))
    return p


def save_protections(con, p: Protections) -> None:
    set_setting(con, "protections", {"results_r": [(t.isoformat(), x) for t, x in p.results_r[-500:]],
                                     "paused_until": p.paused_until.isoformat() if p.paused_until else None, "halted": p.halted})


def save_decision(con, symbol: str, now: datetime, d: dict) -> None:
    con.execute("INSERT INTO decisions(symbol,ts,action,json) VALUES(?,?,?,?) ON CONFLICT(symbol) DO UPDATE SET ts=excluded.ts, action=excluded.action, json=excluded.json",
                (symbol, now.isoformat(), d.get("action", "WAIT"), json.dumps(d, ensure_ascii=False, default=str)))
    con.commit()


def load_decisions(con) -> dict:
    return {r["symbol"]: json.loads(r["json"]) for r in con.execute("SELECT symbol,json FROM decisions")}


def get_setup_stats(con) -> dict:
    return {r["setup_key"]: dict(r) for r in con.execute("SELECT * FROM setup_stats")}


def put_setup_stats(con, key: str, stats: dict, now: datetime) -> None:
    con.execute("INSERT INTO setup_stats(setup_key,trades,expectancy_r,win_rate,benched,updated_at) VALUES(?,?,?,?,?,?) "
                "ON CONFLICT(setup_key) DO UPDATE SET trades=excluded.trades, expectancy_r=excluded.expectancy_r, win_rate=excluded.win_rate, "
                "benched=excluded.benched, updated_at=excluded.updated_at",
                (key, stats["trades"], stats["expectancy_r"], stats["win_rate"], int(stats.get("benched", 0)), now.isoformat()))
    con.commit()


def log_health(con, now: datetime, component: str, status: str, detail: str = "") -> None:
    con.execute("INSERT INTO health_log(ts,component,status,detail) VALUES(?,?,?,?)", (now.isoformat(), component, status, detail[:300]))
    con.commit()


def patch_decision(con, symbol: str, d: dict) -> None:
    """Update the stored JSON of a decision WITHOUT touching its timestamp (freshness must stay honest)."""
    con.execute("UPDATE decisions SET json=? WHERE symbol=?", (json.dumps(d, ensure_ascii=False, default=str), symbol))
    con.commit()


def forward_stats(con, setup_key: str) -> dict:
    """Closed paper/live trades of one setup (from the signals table, setup_key stored in extra_json)."""
    rs = []
    for r in con.execute("SELECT r_multiple, extra_json FROM signals WHERE kind='TRADE' AND r_multiple IS NOT NULL AND state IN ('TARGET','SL','EXPIRED')"):
        try:
            if json.loads(r["extra_json"] or "{}").get("setup_key") == setup_key:
                rs.append(float(r["r_multiple"]))
        except Exception:
            continue
    n = len(rs)
    return {"trades": n, "expectancy_r": (sum(rs) / n) if n else 0.0}

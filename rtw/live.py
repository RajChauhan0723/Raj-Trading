"""LiveProvider: composes the adapters with fallbacks + small caches. Implements the Provider contract (never raises)."""
from __future__ import annotations
import threading
import time
from datetime import datetime, timedelta
import pandas as pd
from .adapters import angel as A, yf as Y, crypto as C, nse as N, newsfeeds as NF, calendar as CAL
from .config import Settings, Spec, stock_spec, DEFAULT_STOCKS
from .db import get_setting, set_setting, log_health
from .news import Tag, tag_headline, cluster_stories, story_confirmed
from .options import iv_percentile
from .provider import Provider
from .sessions import IST, is_open

HOLIDAY_FILE_KEY = "holidays"        # settings key: list of ISO dates (maintained by `update_holidays` job / by hand)


class _Cache:
    def __init__(self):
        self.d: dict = {}

    def get(self, k, ttl, fn, max_stale=None):
        """Fresh value if younger than ttl; else call fn. If fn fails, a stale value is served only while younger than max_stale
        (default 6 x ttl) - older data is worse than no data."""
        v = self.d.get(k)
        if v and time.time() - v[0] < ttl:
            return v[1]
        val = fn()
        if val not in (None, {}, []):
            self.d[k] = (time.time(), val)
            return val
        if v and time.time() - v[0] < (max_stale if max_stale is not None else ttl * 6):
            return v[1]
        return val


class LiveProvider(Provider):
    name = "live"

    def __init__(self, settings: Settings, con):
        self.st, self.con = settings, con
        self.angel = A.AngelClient(settings) if settings.angel_ready else None
        self.cache = _Cache()
        self._tok: dict = {}
        self._news: list[dict] = []
        self._news_seen: set = set()
        self._lock = threading.Lock()

    # ------------------------------------------------------------ startup
    def start(self, now: datetime) -> list[tuple]:
        """Login + master. Returns health tuples (component, status, detail)."""
        out = []
        if self.angel:
            ok = self.angel.login()
            out.append(("angel_login", "OK" if ok else "FAIL", self.angel.last_error))
            if ok:
                okm = self.angel.load_master()
                out.append(("angel_master", "OK" if okm else "FAIL", self.angel.last_error))
        else:
            out.append(("angel_login", "SKIP", "Angel keys .env me nahi hain -> yfinance/Binance fallback"))
        return out

    # ------------------------------------------------------------ token resolution
    def _angel_target(self, spec: Spec, now: datetime) -> dict | None:
        if not (self.angel and self.angel.master):
            return None
        key = (spec.symbol, now.date())
        if key in self._tok:
            return self._tok[key]
        m, today = self.angel.master, now.date()
        row = None
        if spec.asset_class == "INDEX":
            row = A.index_row(m, spec.angel_name) or ({"token": A.INDEX_TOKENS.get(spec.angel_name), "symbol": spec.angel_name} if A.INDEX_TOKENS.get(spec.angel_name) else None)
            exch = "NSE"
        elif spec.asset_class == "STOCK":
            row, exch = A.equity_row(m, spec.angel_name), "NSE"
        elif spec.asset_class == "COMMODITY":
            if spec.segment == "GLOBAL" or spec.exch == "GLOBAL":
                return None
            row, exch = A.front_future(m, spec.angel_name, "MCX", today, 3, "FUTCOM"), "MCX"
        elif spec.asset_class == "FOREX":
            row, exch = A.front_future(m, spec.angel_name, "CDS", today, 2, "FUTCUR"), "CDS"
        else:
            return None
        t = {"exch": exch, "token": row["token"], "symbol": row.get("symbol", spec.angel_name), "row": row} if row else None
        self._tok[key] = t
        return t

    # ------------------------------------------------------------ candles
    def candles(self, spec, now, tf="5m", n=400):
        try:
            if spec.exch == "BINANCE":
                df = C.klines(spec.symbol, now, "5m", min(n, 1000))
                return df if df is not None else Y.candles(spec.yf, now)
            if spec.segment == "GLOBAL" or spec.exch == "GLOBAL":
                df = Y.candles(spec.yf or "GC=F", now)
                return df.tail(n) if df is not None else None
            t = self._angel_target(spec, now)
            if t:
                days = 6 if spec.segment == "NSE" else 4
                df = self.angel.candles(t["exch"], t["token"], tf, now - timedelta(days=days), now)
                if df is not None and len(df):
                    df = Y.drop_open_bar(df, now, 5).tail(n)
                    df.attrs["contract"] = t.get("symbol")            # pipeline resets state when the front contract rolls
                    return df
            # MCX has NO fallback (COMEX units differ). FOREX falls back only when Angel is not configured at all
            # (yfinance spot and CDS futures differ slightly - mixing them mid-trade would corrupt levels).
            if spec.asset_class in ("INDEX", "STOCK") and spec.yf or (spec.asset_class == "FOREX" and spec.yf and not self.angel):
                df = Y.candles(spec.yf, now)
                return df.tail(n) if df is not None else None
        except Exception:
            return None
        return None

    def history(self, spec, now, days=60):
        try:
            if spec.exch == "BINANCE":
                return C.klines(spec.symbol, now, "5m", 1000)
            if spec.segment == "GLOBAL" or spec.exch == "GLOBAL":
                return Y.candles(spec.yf or "GC=F", now, "5m", "60d")
            t = self._angel_target(spec, now)
            if t:
                df = self.angel.candles(t["exch"], t["token"], "5m", now - timedelta(days=days), now)
                return Y.drop_open_bar(df, now, 5) if df is not None else None
            return Y.candles(spec.yf, now, "5m", "60d") if spec.yf and spec.asset_class != "COMMODITY" else None
        except Exception:
            return None

    def ltp(self, spec, now):
        try:
            if spec.segment == "GLOBAL" or spec.exch == "GLOBAL":
                df = Y.candles(spec.yf or "GC=F", now)
                return float(df["close"].iloc[-1]) if df is not None and len(df) else None
            t = self._angel_target(spec, now)
            if t:
                return self.angel.ltp(t["exch"], t["symbol"], t["token"])
        except Exception:
            pass
        return None

    # ------------------------------------------------------------ context
    def global_changes(self, now):
        return self.cache.get("global", 600, Y.daily_changes) or {}

    def vix_z(self, now):
        return self.cache.get("vixz", 900, Y.vix_zscore)

    def usdinr(self, now):
        def lvl():
            df = Y.candles("USDINR=X", now, "5m", "1d")
            return float(df["close"].iloc[-1]) if df is not None and len(df) else None
        return self.cache.get("usdinr", 900, lvl) or 88.0

    def smart_inputs(self, spec, now):
        try:
            if spec.asset_class == "INDEX":
                d = self.cache.get("fiidii", 1800, N.fii_dii) or {}
                return {"kind": "index", **d} if d else {}
            if spec.asset_class == "CRYPTO":
                return self.cache.get("cryptosmart", 300, C.smart_inputs) or {}
        except Exception:
            pass
        return {}

    def lot(self, spec):
        try:
            if self.angel and self.angel.master and spec.asset_class in ("INDEX", "STOCK"):
                it = "OPTIDX" if spec.asset_class == "INDEX" else "OPTSTK"
                v = A.lot_from_master(self.angel.master, spec.angel_name, "NFO", it)
                if v:
                    return v
        except Exception:
            pass
        return spec.lot

    def holidays(self):
        try:
            from datetime import date
            return {date.fromisoformat(x) for x in (get_setting(self.con, HOLIDAY_FILE_KEY, []) or [])}
        except Exception:
            return set()

    # ------------------------------------------------------------ options
    def _pick_expiry(self, spec: Spec, now: datetime):
        if not (self.angel and self.angel.master):
            return None
        it = "OPTIDX" if spec.asset_class == "INDEX" else "OPTSTK"
        exps = A.option_expiries(self.angel.master, spec.angel_name, now.date(), it)
        for e in exps:                                   # nearest expiry that still has >= 1 day
            if (e - now.date()).days >= 1:
                return e
        return exps[0] if exps else None

    def option_chain(self, spec, now):
        try:
            exp = self._pick_expiry(spec, now)
            if exp is None:
                return None
            df = self.cache.get(f"chain:{spec.symbol}", 45, lambda: N.option_chain(spec.angel_name))
            rows = N.chain_from_df(df, exp) if df is not None else []
            if not rows and df is not None:
                rows = N.chain_from_df(df)                # frame has a single expiry already
            spot = self.ltp(spec, now)
            if not rows:
                return None
            if spot is None:
                from .db import load_df
                d = load_df(self.con, spec.symbol, "5m", 2)
                spot = float(d["close"].iloc[-1]) if d is not None else None
            if spot is None:
                return None
            dte = max(0.0, (datetime.combine(exp, datetime.min.time(), tzinfo=IST) + timedelta(hours=15, minutes=30) - now).total_seconds() / 86400.0)
            iv = N.atm_iv(rows, spot, dte) or 0.15
            hist = get_setting(self.con, f"ivhist:{spec.symbol}", []) or []
            return {"expiry": exp.isoformat(), "dte": dte, "rows": rows, "iv": iv, "iv_pct": iv_percentile(hist, iv), "spot": spot, "lot": self.lot(spec)}
        except Exception:
            return None

    def option_ltp(self, spec, strike, cp, expiry, now):
        try:
            if not (self.angel and self.angel.master):
                return None
            from datetime import date
            it = "OPTIDX" if spec.asset_class == "INDEX" else "OPTSTK"
            r = A.option_token(self.angel.master, spec.angel_name, date.fromisoformat(expiry), strike, cp, it)
            return self.angel.ltp("NFO", r["symbol"], r["token"]) if r else None
        except Exception:
            return None

    def option_candles(self, spec, strike, cp, expiry, now):
        """Real 5m bars of one option contract from Angel (NFO token). None if unavailable. Not tested live."""
        try:
            if not (self.angel and self.angel.master):
                return None
            from datetime import date
            it = "OPTIDX" if spec.asset_class == "INDEX" else "OPTSTK"
            r = A.option_token(self.angel.master, spec.angel_name, date.fromisoformat(expiry), strike, cp, it)
            if not r:
                return None
            df = self.angel.candles("NFO", r["token"], "5m", now - timedelta(days=4), now)
            return Y.drop_open_bar(df, now, 5).tail(400) if df is not None and len(df) else None
        except Exception:
            return None

    def record_iv(self, spec: Spec, now: datetime) -> None:
        """Daily job: append today's ATM IV to history (needed for IV percentile)."""
        ch = self.option_chain(spec, now)
        if ch:
            h = (get_setting(self.con, f"ivhist:{spec.symbol}", []) or [])[-250:]
            h.append(ch["iv"])
            set_setting(self.con, f"ivhist:{spec.symbol}", h)

    # ------------------------------------------------------------ news
    def collect_news(self, now: datetime, gdelt: bool = False) -> int:
        items = NF.fetch_rss(now) + (NF.fetch_gdelt(now) if gdelt else [])
        new = 0
        with self._lock:
            for it in items:
                h = NF.url_hash(it["url"], it["title"])
                if h in self._news_seen:
                    continue
                self._news_seen.add(h)
                self._news.append(it)
                new += 1
                try:
                    self.con.execute("INSERT OR IGNORE INTO news_items(url_hash,title,source,official,ts,tags_json) VALUES(?,?,?,?,?,?)",
                                     (h, it["title"], it["source"], int(it["official"]), it["ts"].isoformat(), "[]"))
                except Exception:
                    pass
            self.con.commit()
            cut = now - timedelta(hours=8)
            self._news = [x for x in self._news if x["ts"] >= cut]
            if len(self._news_seen) > 20000:
                self._news_seen = {NF.url_hash(x["url"], x["title"]) for x in self._news}
        return new

    def news_tags(self, now):
        with self._lock:
            items = list(self._news)
        tags: list[Tag] = []
        for st in cluster_stories([x for x in items if x["ts"] >= now - timedelta(hours=6)]):
            best = max(st["items"], key=lambda x: x.get("trust", 0.5))
            ts = tag_headline(best["title"], st["first_ts"], best["source"], st["official"], best.get("trust", 0.6))
            if not story_confirmed(st):               # single unofficial source: weak vote only
                for t in ts:
                    t.magnitude *= 0.4
            tags += ts
        return tags

    def headlines(self, now):
        with self._lock:
            items = sorted(self._news, key=lambda x: x["ts"], reverse=True)[:40]
        out = []
        for it in items:
            tg = tag_headline(it["title"], it["ts"], it["source"], it["official"], it.get("trust", 0.6))
            out.append({"title": it["title"], "source": it["source"], "ts": it["ts"].isoformat(),
                        "tags": [f"{t.asset} {'+' if t.direction > 0 else '-'}" for t in tg][:4]})
        return out

    def events(self, now):
        ff = self.cache.get("ff", 3600, CAL.fetch_ff) or []
        return CAL.all_events(now, ff=ff)

    # ------------------------------------------------------------ stocks
    def stock_universe(self, now, n=50):
        rows = get_setting(self.con, "stock_universe", []) or [{"symbol": x} for x in DEFAULT_STOCKS]
        return [stock_spec(r["symbol"]) for r in rows[:n]]

    def refresh_stock_universe(self, now: datetime, n: int = 100) -> int:
        rows = N.fno_universe(n)
        if rows:
            set_setting(self.con, "stock_universe", rows)
        return len(rows)

    def stock_lot(self, symbol: str) -> int:
        for r in get_setting(self.con, "stock_universe", []) or []:
            if r["symbol"] == symbol:
                return int(r.get("lot", 1))
        return 1

    # ------------------------------------------------------------ health
    def health(self, now):
        out = []
        if self.angel:
            ok = bool(self.angel.api and self.angel.logged_at)
            out.append(("angel_login", "OK" if ok else "FAIL", self.angel.last_error or "logged in"))
            out.append(("angel_master", "OK" if self.angel.master else "FAIL", f"{len(self.angel.master)} rows"))
        g = self.global_changes(now)
        out.append(("global_yfinance", "OK" if len(g) >= 8 else "FAIL", f"{len(g)} tickers"))
        out.append(("news_items", "OK" if self._news else "FAIL", f"{len(self._news)} items in memory"))
        out.append(("stock_universe", "OK" if get_setting(self.con, "stock_universe", []) else "FAIL",
                    f"{len(get_setting(self.con, 'stock_universe', []) or [])} stocks (default list used if 0)"))
        ev = self.events(now)
        out.append(("calendar", "OK" if ev else "FAIL", f"{len(ev)} events"))
        return out

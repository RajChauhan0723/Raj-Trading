"""Angel One SmartAPI adapter. Login with TOTP, instrument master, candles, LTP, Greeks.
LIVE CALLS ARE VERIFIED BY SIGNATURE ONLY (sandbox had no broker access) -> run `python check_setup.py` first."""
from __future__ import annotations
import json
import os
import threading
import time
from datetime import date, datetime, timedelta
import pandas as pd
import requests
from ..sessions import IST

MASTER_URL = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"
INDEX_TOKENS = {"NIFTY": "99926000", "BANKNIFTY": "99926009", "MIDCPNIFTY": "99926074", "INDIAVIX": "99926017"}   # verified at runtime
INTERVALS = {"1m": "ONE_MINUTE", "3m": "THREE_MINUTE", "5m": "FIVE_MINUTE", "10m": "TEN_MINUTE", "15m": "FIFTEEN_MINUTE",
             "30m": "THIRTY_MINUTE", "1h": "ONE_HOUR", "1d": "ONE_DAY"}
MAX_DAYS = {"1m": 25, "3m": 90, "5m": 90, "10m": 90, "15m": 190, "30m": 190, "1h": 390, "1d": 1900}   # per-request window (safe)


# ---------------------------------------------------------------- pure helpers (offline-testable)
def parse_expiry(s: str) -> date | None:
    try:
        return datetime.strptime(s.title(), "%d%b%Y").date()
    except Exception:
        return None


def parse_candles(resp: dict) -> pd.DataFrame | None:
    """getCandleData response -> DataFrame(open,high,low,close,volume) indexed by IST bar START time."""
    rows = (resp or {}).get("data")
    if not rows:
        return None
    df = pd.DataFrame(rows, columns=["ts", "open", "high", "low", "close", "volume"])
    df["ts"] = pd.to_datetime(df["ts"], utc=True).dt.tz_convert(IST)
    df = df.set_index("ts").sort_index()
    df = df[~df.index.duplicated(keep="last")].astype(float)
    return df


def front_future(master: list, name: str, exch: str, today: date, roll_days: int = 3, itype: str | None = None) -> dict | None:
    """Nearest future of `name` whose expiry is >= today+roll_days (so we roll BEFORE the last days: thin volume, expiry noise)."""
    types = {itype} if itype else {"FUTCOM", "FUTIDX", "FUTSTK", "FUTCUR"}
    c = []
    for r in master:
        if r.get("name") == name and r.get("exch_seg") == exch and r.get("instrumenttype") in types:
            e = parse_expiry(r.get("expiry", ""))
            if e and e >= today + timedelta(days=roll_days):
                c.append((e, r))
    if not c:
        c = [(parse_expiry(r["expiry"]), r) for r in master if r.get("name") == name and r.get("exch_seg") == exch
             and r.get("instrumenttype") in types and parse_expiry(r.get("expiry", "")) and parse_expiry(r["expiry"]) >= today]
    return min(c, key=lambda x: x[0])[1] if c else None


def equity_row(master: list, symbol: str) -> dict | None:
    for r in master:
        if r.get("exch_seg") == "NSE" and r.get("symbol") == f"{symbol}-EQ":
            return r
    return None


def index_row(master: list, name: str) -> dict | None:
    want = {"NIFTY": ["nifty 50", "nifty"], "BANKNIFTY": ["nifty bank", "banknifty"], "MIDCPNIFTY": ["nifty midcap select", "nifty mid select", "midcpnifty"],
            "INDIAVIX": ["india vix"]}.get(name, [name.lower()])
    for r in master:
        if r.get("exch_seg") == "NSE" and r.get("instrumenttype") == "AMXIDX" and (r.get("symbol", "").lower() in want or r.get("name", "").lower() in want):
            return r
    return None


def lot_from_master(master: list, name: str, exch: str, itype: str) -> int | None:
    for r in master:
        if r.get("name") == name and r.get("exch_seg") == exch and r.get("instrumenttype") == itype:
            try:
                return int(float(r["lotsize"]))
            except Exception:
                return None
    return None


def option_expiries(master: list, name: str, today: date, itype: str = "OPTIDX") -> list[date]:
    ex = {parse_expiry(r["expiry"]) for r in master if r.get("name") == name and r.get("exch_seg") in ("NFO",) and r.get("instrumenttype") == itype}
    return sorted(e for e in ex if e and e >= today)


def option_token(master: list, name: str, expiry: date, strike: float, cp: str, itype: str = "OPTIDX") -> dict | None:
    """Master stores strike x100 (e.g. '2450000.000000')."""
    for r in master:
        if (r.get("name") == name and r.get("exch_seg") == "NFO" and r.get("instrumenttype") == itype and parse_expiry(r.get("expiry", "")) == expiry
                and abs(float(r.get("strike", 0)) / 100.0 - strike) < 1e-6 and r.get("symbol", "").endswith(cp)):
            return r
    return None


# ---------------------------------------------------------------- client
class AngelClient:
    MIN_GAP = 0.40       # seconds between REST calls (limit is 3/sec for candles)

    def __init__(self, settings, cache_dir: str = "data"):
        self.st = settings
        self.cache_dir = cache_dir
        self.api = None
        self.master: list = []
        self.logged_at: datetime | None = None
        self.last_error = ""
        self._lock = threading.Lock()
        self._last = 0.0
        self._login_fail_at = 0.0          # login cooldown: repeated bad logins can lock the Angel account

    # ---- session
    LOGIN_COOLDOWN = 90.0

    def login(self) -> bool:
        with self._lock:
            if time.time() - self._login_fail_at < self.LOGIN_COOLDOWN:
                return False
            try:
                import pyotp
                from SmartApi import SmartConnect
                api = SmartConnect(api_key=self.st.angel_api_key)
                totp = pyotp.TOTP(self.st.angel_totp_secret).now()
                d = api.generateSession(self.st.angel_client_code, self.st.angel_pin, totp)
                if not d or not d.get("status"):
                    self.last_error = f"login fail: {(d or {}).get('message', 'no response')}"
                    self._login_fail_at = time.time()
                    return False
                self.api, self.logged_at, self.last_error = api, datetime.now(IST), ""
                return True
            except Exception as e:
                self.last_error = f"login error: {e}"
                self._login_fail_at = time.time()
                return False

    def ensure(self) -> bool:
        if self.api and self.logged_at and datetime.now(IST) - self.logged_at < timedelta(hours=5):
            return True
        return self.login()

    def _throttle(self):
        gap = time.time() - self._last
        if gap < self.MIN_GAP:
            time.sleep(self.MIN_GAP - gap)
        self._last = time.time()

    def _call(self, fn, *a):
        """One retry after re-login (token expiry). Returns response dict or None."""
        for attempt in (0, 1):
            if not self.ensure():
                return None
            with self._lock:
                self._throttle()
            try:
                r = fn(*a)
                if r and r.get("status"):
                    return r
                msg = str((r or {}).get("message", ""))
                self.last_error = msg
                if attempt == 0 and any(k in msg.lower() for k in ("invalid token", "token expired", "session", "unauthor", "login")):
                    self.api = None
                    continue
                return None
            except Exception as e:                      # network blips must NOT force a re-login (that burns login attempts)
                self.last_error = str(e)
                if attempt == 0 and any(k in str(e).lower() for k in ("token", "session", "unauthor")):
                    self.api = None
                    continue
                return None
        return None

    # ---- master
    def load_master(self, force: bool = False) -> bool:
        os.makedirs(self.cache_dir, exist_ok=True)
        path = os.path.join(self.cache_dir, f"master_{datetime.now(IST):%Y%m%d}.json")
        try:
            if not force and os.path.exists(path):
                self.master = json.load(open(path, encoding="utf-8"))
            else:
                r = requests.get(MASTER_URL, timeout=90)
                r.raise_for_status()
                self.master = r.json()
                json.dump(self.master, open(path, "w", encoding="utf-8"))
                for old in os.listdir(self.cache_dir):
                    if old.startswith("master_") and old != os.path.basename(path):
                        os.remove(os.path.join(self.cache_dir, old))
            return len(self.master) > 1000
        except Exception as e:
            self.last_error = f"master: {e}"
            return False

    # ---- data
    def candles(self, exch: str, token: str, tf: str, start: datetime, end: datetime) -> pd.DataFrame | None:
        """Loops over windows (API limits days per request)."""
        step = timedelta(days=MAX_DAYS[tf])
        frames, cur = [], start
        while cur < end:
            nxt = min(cur + step, end)
            p = {"exchange": exch, "symboltoken": token, "interval": INTERVALS[tf],
                 "fromdate": cur.strftime("%Y-%m-%d %H:%M"), "todate": nxt.strftime("%Y-%m-%d %H:%M")}
            r = self._call(lambda: self.api.getCandleData(dict(p)))
            df = parse_candles(r) if r else None
            if df is not None:
                frames.append(df)
            cur = nxt
        if not frames:
            return None
        return pd.concat(frames).sort_index().loc[lambda d: ~d.index.duplicated(keep="last")]

    def ltp(self, exch: str, tradingsymbol: str, token: str) -> float | None:
        if not self.ensure():
            return None
        r = self._call(lambda: self.api.ltpData(exch, tradingsymbol, token))
        try:
            return float(r["data"]["ltp"])
        except Exception:
            return None

    def greeks(self, name: str, expiry_ddmmmyyyy: str) -> list:
        if not self.ensure():
            return []
        r = self._call(lambda: self.api.optionGreek({"name": name, "expirydate": expiry_ddmmmyyyy}))
        return (r or {}).get("data") or []

"""Data-provider contract + FakeProvider (DEMO mode / tests).
RULE for every provider method: NEVER raise. On failure return None / [] / {} and let the caller log health."""
from __future__ import annotations
import hashlib
import math
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
from .config import Spec, CORE_SPECS, stock_spec
from .news import Tag, Event, tag_headline
from .options import bs_price
from .sessions import IST

START_PRICE = {"NIFTY": 22317, "BANKNIFTY": 54643, "MIDCPNIFTY": 13593, "SENSEX": 81388, "GOLD": 149834, "GOLDM": 148570, "XAUUSD": 4197.0, "SILVER": 225950, "CRUDEOIL": 8911,
               "NATURALGAS": 302.1, "USDINR": 88.5, "EURINR": 103.0, "GBPINR": 118.0, "JPYINR": 0.59, "EURUSD": 1.16,
               "GBPUSD": 1.34, "USDJPY": 148.0, "BTCUSDT": 83000}


class Provider:
    name = "base"

    def candles(self, spec: Spec, now: datetime, tf: str = "5m", n: int = 400) -> pd.DataFrame | None: return None
    def history(self, spec: Spec, now: datetime, days: int = 60) -> pd.DataFrame | None: return self.candles(spec, now, "5m", 4000)
    def ltp(self, spec: Spec, now: datetime) -> float | None: return None
    def global_changes(self, now: datetime) -> dict: return {}
    def smart_inputs(self, spec: Spec, now: datetime) -> dict: return {}
    def option_chain(self, spec: Spec, now: datetime) -> dict | None: return None
    def option_ltp(self, spec: Spec, strike: float, cp: str, expiry: str, now: datetime) -> float | None: return None
    def option_candles(self, spec: Spec, strike: float, cp: str, expiry: str, now: datetime) -> pd.DataFrame | None: return None
    def news_tags(self, now: datetime) -> list: return []
    def headlines(self, now: datetime) -> list: return []
    def events(self, now: datetime) -> list: return []
    def usdinr(self, now: datetime) -> float: return 88.0
    def lot(self, spec: Spec) -> float: return spec.lot
    def holidays(self) -> set: return set()
    def vix_z(self, now: datetime) -> float | None: return None
    def stock_universe(self, now: datetime, n: int = 50) -> list: return []
    def health(self, now: datetime) -> list: return [("provider", "OK", self.name)]


def _seed(*parts) -> int:
    return int(hashlib.md5("|".join(map(str, parts)).encode()).hexdigest()[:8], 16)


class FakeProvider(Provider):
    """Synthetic but realistic-looking data so the whole app can be seen working with ZERO setup."""
    name = "demo"
    TREND = {"GOLD": 0.0011, "GOLDM": 0.0011, "XAUUSD": 0.0012, "USDINR": -0.0009, "BTCUSDT": 0.0004}      # symbols that trend in the demo

    def __init__(self, seed: int = 7):
        self.seed = seed

    def candles(self, spec, now, tf="5m", n=400):
        end = pd.Timestamp(now).tz_convert(IST).floor("5min") - pd.Timedelta(minutes=5)   # last CLOSED bar start
        idx = pd.date_range(end=end, periods=n, freq="5min", tz=IST)
        rng = np.random.default_rng(_seed(self.seed, spec.symbol, end.date()))
        drift = self.TREND.get(spec.symbol, 0.0)
        vol = 0.0007 if spec.asset_class != "CRYPTO" else 0.0012
        rets = rng.normal(drift, vol, n)
        start = START_PRICE.get(spec.symbol, 500.0)
        cum = np.cumsum(rets)
        close = start * np.exp(cum - cum[-1])
        open_ = np.r_[close[0], close[:-1]]
        sp = np.abs(rng.normal(0, vol * 0.6, n)) * close
        return pd.DataFrame({"open": open_, "high": np.maximum(open_, close) + sp, "low": np.minimum(open_, close) - sp,
                             "close": close, "volume": 1000 * (1 + np.abs(rng.normal(0, 0.5, n)))}, index=idx)

    def history(self, spec, now, days=60):
        return self.candles(spec, now, "5m", 1500)

    def ltp(self, spec, now):
        df = self.candles(spec, now, n=5)
        return float(df["close"].iloc[-1])

    def global_changes(self, now):
        r = np.random.default_rng(_seed(self.seed, "global", now.date()))
        keys = ["^GSPC", "ES=F", "^IXIC", "^N225", "^HSI", "DX-Y.NYB", "CL=F", "^VIX", "^TNX", "USDINR=X", "GC=F", "SI=F", "NG=F", "BTC-USD"]
        return {k: float(r.normal(0.1, 0.8)) for k in keys}

    def smart_inputs(self, spec, now):
        if spec.asset_class == "INDEX":
            return {"kind": "index", "fii_cash_net_cr": 1200.0, "dii_cash_net_cr": 800.0, "fii_idx_fut_long_ratio": 0.55}
        return {}

    def option_chain(self, spec, now):
        if not (spec.has_options or spec.asset_class == "STOCK"):
            return None
        spot = self.ltp(spec, now)
        step = 50 if spec.symbol == "NIFTY" else (100 if spec.symbol == "BANKNIFTY" else (25 if spec.asset_class == "INDEX" else max(1, round(spot * 0.01))))
        atm = round(spot / step) * step
        dte = 5.0 if spec.symbol == "NIFTY" else 20.0
        iv = 0.14
        rows = []
        for i in range(-10, 11):
            k = atm + i * step
            rows.append({"strike": float(k), "ce_oi": 100000 * (1 + max(0, i)) , "pe_oi": 100000 * (1 + max(0, -i)),
                         "ce_ltp": bs_price(spot, k, dte / 365, iv, "CE"), "pe_ltp": bs_price(spot, k, dte / 365, iv, "PE"),
                         "ce_iv": iv, "pe_iv": iv})
        exp = (now + timedelta(days=dte)).date().isoformat()
        return {"expiry": exp, "dte": dte, "rows": rows, "iv": iv, "iv_pct": 0.4, "spot": spot, "lot": self.lot(spec)}

    def option_ltp(self, spec, strike, cp, expiry, now):
        ch = self.option_chain(spec, now)
        if not ch:
            return None
        for r in ch["rows"]:
            if r["strike"] == strike:
                return r["ce_ltp" if cp == "CE" else "pe_ltp"]
        return None

    def option_candles(self, spec, strike, cp, expiry, now):
        """DEMO only: SYNTHETIC option premium bars priced from the demo underlying with Black-Scholes (no real option history exists here)."""
        from datetime import date
        from .options import bs_price
        df = self.candles(spec, now, "5m", 400)
        if df is None or df.empty:
            return None
        exp_dt = pd.Timestamp(date.fromisoformat(expiry), tz=IST) + pd.Timedelta(hours=15, minutes=30)
        out = df.copy()
        for c in ("open", "high", "low", "close"):
            out[c] = [bs_price(float(u), float(strike), max((exp_dt - ts).total_seconds() / 86400.0, 0.02) / 365.0, 0.15, cp) for u, ts in zip(df[c], df.index)]
        hi, lo = out[["open", "high", "low", "close"]].max(axis=1), out[["open", "high", "low", "close"]].min(axis=1)
        out["high"], out["low"], out["volume"] = hi, lo, 0.0
        return out

    def events(self, now):
        d = now.astimezone(IST)
        return [Event("US CPI", (d + timedelta(days=3)).replace(hour=18, minute=0, second=0, microsecond=0), "HIGH", ("ALL",)),
                Event("RBI policy", (d + timedelta(days=1)).replace(hour=10, minute=0, second=0, microsecond=0), "HIGH", ("INDEX", "USDINR"))]

    def headlines(self, now):
        return [{"title": "Demo: Gold firm as dollar slips", "source": "demo", "ts": now.isoformat(), "tags": ["GOLD +"]},
                {"title": "Demo: Crude steady ahead of OPEC meet", "source": "demo", "ts": now.isoformat(), "tags": []}]

    def news_tags(self, now):
        return tag_headline("Dollar slips, weak dollar helps gold", now, "demo", False, 0.6)

    def stock_universe(self, now, n=50):
        return [stock_spec(s) for s in ("RELIANCE", "HDFCBANK", "TCS", "INFY", "ICICIBANK", "SBIN")][:n]

    def usdinr(self, now): return 88.5

    def lot(self, spec):
        return 500 if spec.asset_class == "STOCK" else spec.lot

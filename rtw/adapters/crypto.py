"""Binance public REST (no key) + Fear&Greed. Never raises. If Binance is geo-blocked the caller falls back to yfinance BTC-USD."""
from __future__ import annotations
from datetime import datetime
import pandas as pd
import requests
from ..sessions import IST

SPOT = "https://api.binance.com"
FUT = "https://fapi.binance.com"


def parse_klines(rows: list, now: datetime | None = None, tf_min: int = 5) -> pd.DataFrame | None:
    """Binance kline row: [openTime ms, o, h, l, c, volume, closeTime ms, ...]."""
    if not rows:
        return None
    df = pd.DataFrame([[r[0], r[1], r[2], r[3], r[4], r[5]] for r in rows], columns=["ts", "open", "high", "low", "close", "volume"])
    df["ts"] = pd.to_datetime(df["ts"], unit="ms", utc=True).dt.tz_convert(IST)
    df = df.set_index("ts").astype(float)
    if now is not None:
        df = df[df.index + pd.Timedelta(minutes=tf_min) <= pd.Timestamp(now)]
    return df


def klines(symbol: str, now: datetime, interval: str = "5m", limit: int = 500) -> pd.DataFrame | None:
    try:
        r = requests.get(f"{SPOT}/api/v3/klines", params={"symbol": symbol, "interval": interval, "limit": limit}, timeout=15)
        return parse_klines(r.json(), now) if r.ok else None
    except Exception:
        return None


def _get(url: str, params: dict):
    try:
        r = requests.get(url, params=params, timeout=15)
        return r.json() if r.ok else None
    except Exception:
        return None


def smart_inputs(symbol: str = "BTCUSDT") -> dict:
    out: dict = {"kind": "crypto"}
    j = _get(f"{FUT}/fapi/v1/premiumIndex", {"symbol": symbol})
    if isinstance(j, dict) and "lastFundingRate" in j:
        out["funding_rate"] = float(j["lastFundingRate"])
    j = _get(f"{FUT}/futures/data/globalLongShortAccountRatio", {"symbol": symbol, "period": "1h", "limit": 1})
    if isinstance(j, list) and j:
        out["ls_ratio"] = float(j[-1]["longShortRatio"])
    j = _get(f"{FUT}/futures/data/openInterestHist", {"symbol": symbol, "period": "1h", "limit": 5})
    if isinstance(j, list) and len(j) >= 2:
        a, b = float(j[0]["sumOpenInterest"]), float(j[-1]["sumOpenInterest"])
        if a > 0:
            out["oi_chg_pct"] = (b / a - 1.0) * 100.0
    j = _get("https://api.alternative.me/fng/", {"limit": 1})
    try:
        out["fear_greed"] = float(j["data"][0]["value"])
    except Exception:
        pass
    return out

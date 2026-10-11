"""Chart data for the PWA (pure functions). Candles come from stored CLOSED 5m bars; 15m/1h are resampled from them."""
from __future__ import annotations
import urllib.parse
import pandas as pd

TFS = {"5m": "5min", "15m": "15min", "1h": "60min"}
IST_OFFSET_S = 19800          # the canvas chart shows IST by shifting the UTC timestamps

_TV_FIXED = {"NIFTY": "NSE:NIFTY", "BANKNIFTY": "NSE:BANKNIFTY", "MIDCPNIFTY": "NSE:NIFTY_MID_SELECT",
             "GOLD": "MCX:GOLD1!", "SILVER": "MCX:SILVER1!", "CRUDEOIL": "MCX:CRUDEOIL1!", "NATURALGAS": "MCX:NATURALGAS1!",
             "USDINR": "NSE:USDINR1!", "EURINR": "NSE:EURINR1!", "GBPINR": "NSE:GBPINR1!", "JPYINR": "NSE:JPYINR1!",
             "EURUSD": "FX:EURUSD", "GBPUSD": "FX:GBPUSD", "USDJPY": "FX:USDJPY", "BTCUSDT": "BINANCE:BTCUSDT"}


def tv_symbol(symbol: str, asset_class: str = "STOCK") -> str:
    """TradingView symbol for the 'open in TradingView' link. Unknown names are treated as NSE stocks."""
    s = symbol.upper()
    if s in _TV_FIXED:
        return _TV_FIXED[s]
    return "NSE:" + urllib.parse.quote(s.replace("&", "_"), safe="_-")


def tv_url(symbol: str, asset_class: str = "STOCK") -> str:
    return "https://www.tradingview.com/chart/?symbol=" + urllib.parse.quote(tv_symbol(symbol, asset_class), safe="")


def resample(df: pd.DataFrame, tf: str) -> pd.DataFrame:
    if tf not in TFS:
        raise ValueError("tf 5m / 15m / 1h me se ek ho")
    if tf == "5m" or df is None or df.empty:
        return df
    o = df.resample(TFS[tf], label="left", closed="left").agg({"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"})
    return o.dropna(subset=["open", "close"])


def _ema(vals: list[float], n: int) -> list[float | None]:
    out, k, e = [], 2.0 / (n + 1), None
    for i, v in enumerate(vals):
        e = v if e is None else e + k * (v - e)
        out.append(e if i >= n - 1 else None)
    return out


def chart_payload(df: pd.DataFrame, tf: str = "5m", n: int = 120, levels: list | None = None) -> dict:
    """Last `n` candles + EMA20 + price levels (entry / SL / targets). Times are unix seconds shifted to IST."""
    d = resample(df, tf)
    ema = _ema([float(x) for x in d["close"]], 20)
    d = d.tail(n)
    ema = ema[-len(d):]
    candles = [{"t": int(ts.timestamp()) + IST_OFFSET_S, "o": float(r.open), "h": float(r.high), "l": float(r.low), "c": float(r.close)}
               for ts, r in d.iterrows()]
    return {"tf": tf, "candles": candles, "ema20": [None if e is None else round(float(e), 4) for e in ema], "levels": levels or []}


def levels_from_plan(plan: dict | None, tag: str = "") -> list[dict]:
    if not plan:
        return []
    out = []
    for key, label, kind in (("entry_lo", "Entry", "entry"), ("entry_hi", "Entry", "entry"), ("sl", "SL", "sl"), ("t1", "T1", "target"), ("t2", "T2", "target")):
        v = plan.get(key)
        if v is not None:
            out.append({"label": label + tag if key != "entry_hi" else "", "price": float(v), "kind": kind})
    return out

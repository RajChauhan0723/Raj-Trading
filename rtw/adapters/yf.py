"""yfinance adapter: global context, India VIX, fallback candles. Never raises."""
from __future__ import annotations
import math
import threading
from datetime import datetime
import pandas as pd
from ..sessions import IST

_YF_LOCK = threading.Lock()      # yfinance shares global state -> one download at a time

GLOBAL_TICKERS = ["^GSPC", "ES=F", "NQ=F", "^IXIC", "^N225", "^HSI", "DX-Y.NYB", "CL=F", "BZ=F", "^VIX", "^TNX", "USDINR=X", "GC=F", "SI=F",
                  "NG=F", "BTC-USD", "EURUSD=X", "GBPUSD=X", "JPY=X"]


def _dl(tickers, **kw):
    import yfinance as yf
    with _YF_LOCK:
        return yf.download(tickers, progress=False, auto_adjust=False, **kw)


def normalize(df: pd.DataFrame) -> pd.DataFrame | None:
    """yfinance frame (possibly MultiIndex columns) -> open/high/low/close/volume, IST index."""
    if df is None or len(df) == 0:
        return None
    if isinstance(df.columns, pd.MultiIndex):
        df = df.copy()
        df.columns = [c[0] for c in df.columns]
    df = df.rename(columns=str.lower)
    need = ["open", "high", "low", "close"]
    if not all(c in df.columns for c in need):
        return None
    if "volume" not in df.columns:
        df["volume"] = 0.0
    df = df[need + ["volume"]].dropna(subset=need)
    idx = pd.to_datetime(df.index)
    df.index = idx.tz_localize("UTC").tz_convert(IST) if idx.tz is None else idx.tz_convert(IST)
    return df.astype(float)


def drop_open_bar(df: pd.DataFrame, now: datetime, tf_min: int = 5) -> pd.DataFrame:
    """Keep only CLOSED bars (bar start + tf <= now)."""
    if df is None or df.empty:
        return df
    return df[df.index + pd.Timedelta(minutes=tf_min) <= pd.Timestamp(now)]


def candles(ticker: str, now: datetime, interval: str = "5m", period: str = "5d") -> pd.DataFrame | None:
    try:
        import yfinance as yf
        df = normalize(_dl(ticker, period=period, interval=interval, threads=False))
        return drop_open_bar(df, now, 5) if df is not None else None
    except Exception:
        return None


def daily_changes(tickers: list[str] = GLOBAL_TICKERS) -> dict:
    """% change of last close vs previous close for each ticker. Missing -> absent."""
    out: dict = {}
    try:
        import yfinance as yf
        data = _dl(tickers, period="7d", interval="1d", threads=False)
        close = data["Close"] if isinstance(data.columns, pd.MultiIndex) else data
        for t in tickers:
            if t in close.columns:
                s = close[t].dropna()
                if len(s) >= 2 and s.iloc[-2] != 0:
                    out[t] = float((s.iloc[-1] / s.iloc[-2] - 1.0) * 100.0)
    except Exception:
        pass
    return out


def vix_zscore(ticker: str = "^INDIAVIX", window: int = 60) -> float | None:
    """z-score of TODAY'S % CHANGE in India VIX vs its own last `window` daily % changes (a spike detector, not a level z-score)."""
    try:
        s = normalize_daily(_dl(ticker, period="6mo", interval="1d"))
        if s is None or len(s) < 30:
            return None
        ch = s.pct_change().dropna() * 100.0
        h = ch.tail(window)
        sd = float(h.std())
        return (float(ch.iloc[-1]) - float(h.mean())) / sd if sd > 0 else 0.0
    except Exception:
        return None


def normalize_daily(df) -> pd.Series | None:
    if df is None or len(df) == 0:
        return None
    if isinstance(df.columns, pd.MultiIndex):
        df = df.copy()
        df.columns = [c[0] for c in df.columns]
    c = df["Close"].dropna() if "Close" in df.columns else None
    return c

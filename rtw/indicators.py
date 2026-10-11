"""Pure indicator functions. Input: pandas Series/DataFrame with columns open, high, low, close, volume.
Rule: every function uses ONLY past+current bars (no lookahead). Callers must pass CLOSED bars only."""
from __future__ import annotations
import numpy as np
import pandas as pd


def ema(s: pd.Series, n: int) -> pd.Series:
    return s.ewm(span=n, adjust=False, min_periods=n).mean()


def sma(s: pd.Series, n: int) -> pd.Series:
    return s.rolling(n, min_periods=n).mean()


def rsi(close: pd.Series, n: int = 14) -> pd.Series:
    d = close.diff()
    up = d.clip(lower=0.0)
    dn = (-d).clip(lower=0.0)
    ru = up.ewm(alpha=1.0 / n, adjust=False, min_periods=n).mean()
    rd = dn.ewm(alpha=1.0 / n, adjust=False, min_periods=n).mean()
    rs = ru / rd.replace(0.0, np.nan)
    out = 100.0 - 100.0 / (1.0 + rs)
    out = out.where(~((rd == 0) & (ru > 0)), 100.0)
    out = out.where(~((rd == 0) & (ru == 0)), 50.0)
    return out


def macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
    line = ema(close, fast) - ema(close, slow)
    sig = line.ewm(span=signal, adjust=False, min_periods=signal).mean()
    return pd.DataFrame({"macd": line, "signal": sig, "hist": line - sig})


def true_range(df: pd.DataFrame) -> pd.Series:
    pc = df["close"].shift(1)
    return pd.concat([df["high"] - df["low"], (df["high"] - pc).abs(), (df["low"] - pc).abs()], axis=1).max(axis=1)


def atr(df: pd.DataFrame, n: int = 14) -> pd.Series:
    return true_range(df).ewm(alpha=1.0 / n, adjust=False, min_periods=n).mean()


def adx(df: pd.DataFrame, n: int = 14) -> pd.DataFrame:
    up = df["high"].diff()
    dn = -df["low"].diff()
    plus_dm = pd.Series(np.where((up > dn) & (up > 0), up, 0.0), index=df.index)
    minus_dm = pd.Series(np.where((dn > up) & (dn > 0), dn, 0.0), index=df.index)
    tr = true_range(df)
    a = 1.0 / n
    atr_ = tr.ewm(alpha=a, adjust=False, min_periods=n).mean()
    pdi = 100.0 * plus_dm.ewm(alpha=a, adjust=False, min_periods=n).mean() / atr_
    mdi = 100.0 * minus_dm.ewm(alpha=a, adjust=False, min_periods=n).mean() / atr_
    dx = 100.0 * (pdi - mdi).abs() / (pdi + mdi).replace(0.0, np.nan)
    adx_ = dx.ewm(alpha=a, adjust=False, min_periods=n).mean()
    return pd.DataFrame({"adx": adx_, "pdi": pdi, "mdi": mdi})


def supertrend(df: pd.DataFrame, n: int = 10, mult: float = 3.0) -> pd.DataFrame:
    """direction: +1 up-trend, -1 down-trend. line: the supertrend value."""
    a = atr(df, n).to_numpy()
    hl2 = ((df["high"] + df["low"]) / 2.0).to_numpy()
    close = df["close"].to_numpy()
    m = len(df)
    ub = hl2 + mult * a
    lb = hl2 - mult * a
    fub = ub.copy()
    flb = lb.copy()
    direction = np.zeros(m)
    line = np.full(m, np.nan)
    start = int(np.argmax(~np.isnan(a))) if np.any(~np.isnan(a)) else m
    for i in range(start, m):
        if i == start:
            direction[i] = 1.0 if close[i] >= hl2[i] else -1.0
            line[i] = flb[i] if direction[i] > 0 else fub[i]
            continue
        fub[i] = ub[i] if (ub[i] < fub[i - 1] or close[i - 1] > fub[i - 1]) else fub[i - 1]
        flb[i] = lb[i] if (lb[i] > flb[i - 1] or close[i - 1] < flb[i - 1]) else flb[i - 1]
        if direction[i - 1] > 0:
            direction[i] = -1.0 if close[i] < flb[i] else 1.0
        else:
            direction[i] = 1.0 if close[i] > fub[i] else -1.0
        line[i] = flb[i] if direction[i] > 0 else fub[i]
    return pd.DataFrame({"direction": direction, "line": line}, index=df.index)


def bollinger(close: pd.Series, n: int = 20, k: float = 2.0) -> pd.DataFrame:
    mid = sma(close, n)
    sd = close.rolling(n, min_periods=n).std(ddof=0)
    up, lo = mid + k * sd, mid - k * sd
    return pd.DataFrame({"mid": mid, "upper": up, "lower": lo, "bw": (up - lo) / mid})


def vwap(df: pd.DataFrame) -> pd.Series:
    """Intraday VWAP, resets each calendar date of the index (DatetimeIndex required)."""
    tp = (df["high"] + df["low"] + df["close"]) / 3.0
    day = df.index.normalize() if hasattr(df.index, "normalize") else pd.Series(df.index).dt.normalize()
    pv = (tp * df["volume"]).groupby(day).cumsum()
    vv = df["volume"].groupby(day).cumsum()
    return pv / vv.replace(0.0, np.nan)


def obv(df: pd.DataFrame) -> pd.Series:
    return (np.sign(df["close"].diff().fillna(0.0)) * df["volume"]).cumsum()


def stoch_rsi(close: pd.Series, n: int = 14, k: int = 3, d: int = 3) -> pd.DataFrame:
    r = rsi(close, n)
    lo, hi = r.rolling(n, min_periods=n).min(), r.rolling(n, min_periods=n).max()
    raw = 100.0 * (r - lo) / (hi - lo).replace(0.0, np.nan)
    kk = raw.rolling(k, min_periods=k).mean()
    return pd.DataFrame({"k": kk, "d": kk.rolling(d, min_periods=d).mean()})


def zscore(s: pd.Series, n: int = 20) -> pd.Series:
    m = s.rolling(n, min_periods=n).mean()
    sd = s.rolling(n, min_periods=n).std(ddof=0).replace(0.0, np.nan)
    return (s - m) / sd


def percentile_rank(s: pd.Series, n: int = 100) -> pd.Series:
    """Rank of the latest value within the trailing n values, 0..1."""
    return s.rolling(n, min_periods=max(10, n // 4)).apply(lambda w: float((w <= w[-1]).mean()), raw=True)


def swing_levels(df: pd.DataFrame, left: int = 3, right: int = 3, lookback: int = 120) -> dict:
    """Last CONFIRMED swing high/low (a swing at bar i is only known after `right` more bars)."""
    d = df.iloc[-lookback:]
    h, l = d["high"].to_numpy(), d["low"].to_numpy()
    sh, sl_ = [], []
    for i in range(left, len(d) - right):
        if h[i] == h[i - left:i + right + 1].max() and h[i] > h[i - left:i].max():
            sh.append(float(h[i]))
        if l[i] == l[i - left:i + right + 1].min() and l[i] < l[i - left:i].min():
            sl_.append(float(l[i]))
    return {"swing_highs": sh, "swing_lows": sl_,
            "last_high": sh[-1] if sh else float(h.max()), "last_low": sl_[-1] if sl_ else float(l.min())}


def classic_pivots(prev_high: float, prev_low: float, prev_close: float) -> dict:
    p = (prev_high + prev_low + prev_close) / 3.0
    return {"P": p, "R1": 2 * p - prev_low, "S1": 2 * p - prev_high,
            "R2": p + (prev_high - prev_low), "S2": p - (prev_high - prev_low)}


def candle_patterns(df: pd.DataFrame) -> dict:
    """Pattern flags for the LAST closed bar. Needs >= 3 bars."""
    if len(df) < 3:
        return {}
    o, h, l, c = (df[x].to_numpy() for x in ("open", "high", "low", "close"))
    i = len(df) - 1
    body = abs(c[i] - o[i])
    rng = max(h[i] - l[i], 1e-12)
    upper = h[i] - max(c[i], o[i])
    lower = min(c[i], o[i]) - l[i]
    prev_body_dir = np.sign(c[i - 1] - o[i - 1])
    prior_trend = c[i - 1] - c[max(0, i - 6)]
    out = {
        "bull_engulf": bool(prev_body_dir < 0 and c[i] > o[i] and c[i] >= o[i - 1] and o[i] <= c[i - 1]),
        "bear_engulf": bool(prev_body_dir > 0 and c[i] < o[i] and c[i] <= o[i - 1] and o[i] >= c[i - 1]),
        "hammer": bool(lower >= 2 * max(body, 1e-12) and upper <= 0.5 * max(body, 1e-12) + 0.1 * rng and prior_trend < 0),
        "shooting_star": bool(upper >= 2 * max(body, 1e-12) and lower <= 0.5 * max(body, 1e-12) + 0.1 * rng and prior_trend > 0),
        "doji": bool(body <= 0.1 * rng),
    }
    m1 = c[i - 2] < o[i - 2] and abs(c[i - 1] - o[i - 1]) <= 0.3 * (h[i - 1] - l[i - 1] + 1e-12) and c[i] > o[i] and c[i] > (o[i - 2] + c[i - 2]) / 2
    e1 = c[i - 2] > o[i - 2] and abs(c[i - 1] - o[i - 1]) <= 0.3 * (h[i - 1] - l[i - 1] + 1e-12) and c[i] < o[i] and c[i] < (o[i - 2] + c[i - 2]) / 2
    out["morning_star"], out["evening_star"] = bool(m1), bool(e1)
    return out

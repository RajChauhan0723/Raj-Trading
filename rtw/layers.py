"""Chart-based layers. Every layer returns LayerResult(score in [-1,1], conf in [0,1], reasons[Hinglish short]).
score>0 = bullish, score<0 = bearish. Input df = CLOSED bars only (index = DatetimeIndex)."""
from __future__ import annotations
from dataclasses import dataclass, field
import numpy as np
import pandas as pd
from . import indicators as ta


@dataclass
class LayerResult:
    name: str
    score: float = 0.0
    conf: float = 0.0
    reasons: list = field(default_factory=list)

    def clipped(self) -> "LayerResult":
        self.score = float(max(-1.0, min(1.0, self.score)))
        self.conf = float(max(0.0, min(1.0, self.conf)))
        return self


def _last(s: pd.Series, default=np.nan):
    v = s.iloc[-1] if len(s) else default
    return default if pd.isna(v) else float(v)


def regime(df: pd.DataFrame) -> dict:
    """TREND / RANGE / VOLATILE + numbers. Needs >= 60 bars."""
    a = ta.adx(df, 14)
    atr_pct = ta.atr(df, 14) / df["close"]
    atr_rank = _last(ta.percentile_rank(atr_pct, 100), 0.5)
    bw_rank = _last(ta.percentile_rank(ta.bollinger(df["close"])["bw"], 100), 0.5)
    adx_v = _last(a["adx"], 0.0)
    if atr_rank >= 0.85 and bw_rank >= 0.85:
        name = "VOLATILE"
    elif adx_v >= 25:
        name = "TREND"
    else:
        name = "RANGE"
    return {"name": name, "adx": adx_v, "atr_rank": atr_rank, "bw_rank": bw_rank}


def trend_layer(df: pd.DataFrame, intraday: bool = False) -> LayerResult:
    r = LayerResult("trend")
    if len(df) < 60:
        return r
    c = df["close"]
    e20, e50 = ta.ema(c, 20), ta.ema(c, 50)
    e200 = ta.ema(c, 200) if len(df) >= 200 else None
    parts = [np.sign(_last(c) - _last(e50, _last(c))), np.sign(_last(e20, 0) - _last(e50, 0))]
    if e200 is not None and not pd.isna(e200.iloc[-1]):
        parts.append(np.sign(_last(e50, 0) - _last(e200, 0)))
    align = float(np.mean(parts))
    st = ta.supertrend(df, 10, 3.0)
    st_dir = float(st["direction"].iloc[-1])
    score = 0.55 * align + 0.45 * st_dir
    if intraday:
        vw = ta.vwap(df)
        if not pd.isna(vw.iloc[-1]):
            score += 0.2 * np.sign(_last(c) - _last(vw))
            r.reasons.append("VWAP ke upar" if _last(c) > _last(vw) else "VWAP ke neeche")
    adx_v = _last(ta.adx(df, 14)["adx"], 0.0)
    r.score = score
    r.conf = min(1.0, max(0.2, adx_v / 35.0))
    r.reasons.append("EMA trend upar" if align > 0.3 else "EMA trend neeche" if align < -0.3 else "EMA mixed")
    r.reasons.append("Supertrend BUY" if st_dir > 0 else "Supertrend SELL")
    r.reasons.append(f"ADX {adx_v:.0f}")
    return r.clipped()


def momentum_layer(df: pd.DataFrame) -> LayerResult:
    r = LayerResult("momentum")
    if len(df) < 40:
        return r
    c = df["close"]
    rs = _last(ta.rsi(c, 14), 50.0)
    m = ta.macd(c)
    hist, hist_prev = _last(m["hist"], 0.0), float(m["hist"].iloc[-2]) if len(m) > 1 and not pd.isna(m["hist"].iloc[-2]) else 0.0
    rsi_score = max(-1.0, min(1.0, (rs - 50.0) / 25.0))
    if rs > 75 or rs < 25:
        rsi_score *= 0.5
        r.reasons.append("RSI extreme, ulta palatne ka risk")
    macd_score = 0.5 * np.sign(hist) + 0.5 * np.sign(hist - hist_prev)
    r.score = 0.5 * rsi_score + 0.5 * macd_score
    r.conf = 0.7
    r.reasons.append(f"RSI {rs:.0f}")
    r.reasons.append("MACD upar" if hist > 0 else "MACD neeche")
    return r.clipped()


def levels_layer(df: pd.DataFrame, n: int = 20) -> LayerResult:
    """Range-breakout + Bollinger. Uses prior n bars (excluding the last) for the channel."""
    r = LayerResult("levels")
    if len(df) < n + 5:
        return r
    prior = df.iloc[-(n + 1):-1]
    hi, lo, c = float(prior["high"].max()), float(prior["low"].min()), float(df["close"].iloc[-1])
    bb = ta.bollinger(df["close"])
    if c > hi:
        r.score, r.conf = 1.0, 0.8
        r.reasons.append(f"{n}-bar high breakout")
    elif c < lo:
        r.score, r.conf = -1.0, 0.8
        r.reasons.append(f"{n}-bar low breakdown")
    else:
        pos = (c - lo) / max(hi - lo, 1e-12)
        r.score = (pos - 0.5) * 0.6
        r.conf = 0.4
        r.reasons.append("range ke andar")
    if not pd.isna(bb["bw"].iloc[-1]) and ta.percentile_rank(bb["bw"], 100).iloc[-1] <= 0.15:
        r.reasons.append("Bollinger squeeze, badi move aa sakti hai")
    return r.clipped()


def volume_layer(df: pd.DataFrame) -> LayerResult:
    r = LayerResult("volume")
    if len(df) < 30 or float(df["volume"].tail(20).sum()) <= 0:
        return r
    z = _last(ta.zscore(df["volume"], 20), 0.0)
    direction = np.sign(float(df["close"].iloc[-1] - df["open"].iloc[-1]))
    obv = ta.obv(df)
    obv_slope = np.sign(float(obv.iloc[-1] - obv.iloc[-10]))
    spike = max(0.0, min(1.0, z / 3.0))
    r.score = direction * spike * 0.7 + 0.3 * obv_slope
    r.conf = max(0.3, min(1.0, abs(z) / 3.0))
    if z >= 2:
        r.reasons.append(f"volume spike z={z:.1f}")
    r.reasons.append("OBV upar" if obv_slope > 0 else "OBV neeche")
    return r.clipped()


def pattern_layer(df: pd.DataFrame) -> LayerResult:
    r = LayerResult("patterns")
    p = ta.candle_patterns(df)
    if not p:
        return r
    s = 0.0
    names = []
    for k, w in (("bull_engulf", 0.6), ("morning_star", 0.7), ("hammer", 0.4),
                 ("bear_engulf", -0.6), ("evening_star", -0.7), ("shooting_star", -0.4)):
        if p.get(k):
            s += w
            names.append(k)
    r.score = s
    r.conf = 0.55 if names else 0.25
    r.reasons = names or (["doji, confusion"] if p.get("doji") else ["koi clear pattern nahi"])
    return r.clipped()


def chart_layers(df: pd.DataFrame, intraday: bool = False) -> dict:
    return {l.name: l for l in (trend_layer(df, intraday), momentum_layer(df), levels_layer(df),
                                volume_layer(df), pattern_layer(df))}

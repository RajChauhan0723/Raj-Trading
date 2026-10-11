"""Cheap funnel scan for Tier 2/3: rank many symbols quickly, send only the best to the full engine."""
from __future__ import annotations
import numpy as np
import pandas as pd
from . import indicators as ta


def liquid_universe(rows: list[dict], min_turnover_cr: float = 50.0, min_price: float = 20.0) -> list[dict]:
    """rows: dicts with symbol, price, turnover_cr (traded value, crore). Returns liquid ones sorted by turnover desc."""
    ok = [r for r in rows if r.get("price", 0) >= min_price and r.get("turnover_cr", 0) >= min_turnover_cr]
    return sorted(ok, key=lambda r: -r["turnover_cr"])


def cheap_scan_score(df: pd.DataFrame, n: int = 20) -> dict:
    """Fast 0..1 'something is happening' score + direction (+1/-1/0). Closed bars only. Needs >= n+30 bars."""
    if len(df) < n + 30:
        return {"score": 0.0, "direction": 0, "reasons": []}
    c = df["close"]
    prior = df.iloc[-(n + 1):-1]
    hi, lo, last = float(prior["high"].max()), float(prior["low"].min()), float(c.iloc[-1])
    atr_v = float(ta.atr(df, 14).iloc[-1])
    breakout = 0.0
    if atr_v > 0:
        if last > hi:
            breakout = min(1.0, (last - hi) / atr_v + 0.5)
        elif last < lo:
            breakout = -min(1.0, (lo - last) / atr_v + 0.5)
    z = float(ta.zscore(df["volume"], 20).iloc[-1]) if float(df["volume"].tail(20).sum()) > 0 else 0.0
    z = 0.0 if np.isnan(z) else z
    roc = float(c.iloc[-1] / c.iloc[-11] - 1.0) if len(c) > 11 else 0.0
    roc_n = min(1.0, abs(roc) / (3.0 * atr_v / last)) if atr_v > 0 else 0.0
    a = ta.adx(df, 14)["adx"].iloc[-1]
    adx_n = 0.0 if np.isnan(a) else min(1.0, float(a) / 40.0)
    direction = int(np.sign(0.6 * breakout + 0.4 * np.sign(roc)))
    score = 0.35 * abs(breakout) + 0.25 * max(0.0, min(1.0, z / 3.0)) + 0.2 * roc_n + 0.2 * adx_n
    reasons = []
    if breakout:
        reasons.append("20-bar breakout" if breakout > 0 else "20-bar breakdown")
    if z >= 2:
        reasons.append(f"volume z={z:.1f}")
    return {"score": float(score), "direction": direction, "reasons": reasons}


def shortlist(scored: list[dict], top_n: int = 40, min_score: float = 0.25) -> list[dict]:
    """scored: dicts with symbol, score. Keep best top_n above min_score."""
    return sorted([s for s in scored if s["score"] >= min_score], key=lambda s: -s["score"])[:top_n]

"""Support / resistance levels and demand / supply zones. Pure functions on CLOSED bars only (no lookahead).

* S/R levels: confirmed swing highs/lows + previous-day high / low / close / classic pivots, clustered when closer than
  `tol` x ATR (more touches = stronger level).
* Demand / supply zones: a small 'base' (1-3 small-bodied candles) followed by an impulse candle (big range, big body) that
  closes out of the base. Demand = impulse up (price rose from there), supply = impulse down. A zone dies when price CLOSES
  through its far edge; it is 'fresh' while price has not come back into it."""
from __future__ import annotations
import numpy as np
import pandas as pd
from . import indicators as ta
from .layers import LayerResult

IMPULSE_ATR, IMPULSE_BODY, BASE_BODY_ATR = 1.6, 0.6, 0.5


def _prev_day_levels(df: pd.DataFrame) -> list[dict]:
    days = pd.Series(df.index.date, index=df.index)
    last_day = days.iloc[-1]
    prev = df[days < last_day]
    if prev.empty:
        return []
    pday = prev[days[prev.index] == days[prev.index].iloc[-1]]
    h, l, c = float(pday["high"].max()), float(pday["low"].min()), float(pday["close"].iloc[-1])
    pv = ta.classic_pivots(h, l, c)
    out = [{"price": h, "src": "PDH"}, {"price": l, "src": "PDL"}, {"price": c, "src": "PDC"}]
    out += [{"price": pv[k], "src": k} for k in ("P", "R1", "S1", "R2", "S2")]
    return out


def sr_levels(df: pd.DataFrame, atr: float, lookback: int = 300, tol: float = 0.3, keep: int = 3) -> dict:
    """{'supports': [...], 'resistances': [...]} nearest first; each {price, touches, src}."""
    if df is None or len(df) < 30 or not atr or atr <= 0:
        return {"supports": [], "resistances": []}
    price = float(df["close"].iloc[-1])
    sw = ta.swing_levels(df, 3, 3, min(lookback, len(df)))
    pts = [{"price": p, "src": "swing"} for p in sw["swing_highs"] + sw["swing_lows"]] + _prev_day_levels(df)
    pts.sort(key=lambda x: x["price"])
    clusters: list[list[dict]] = []
    for p in pts:
        if clusters and p["price"] - np.mean([q["price"] for q in clusters[-1]]) <= tol * atr:
            clusters[-1].append(p)
        else:
            clusters.append([p])
    lv = []
    for c in clusters:
        srcs = sorted({q["src"] for q in c})
        lv.append({"price": float(np.mean([q["price"] for q in c])), "touches": len(c), "src": "+".join(srcs)})
    sup = sorted([x for x in lv if x["price"] < price - 0.05 * atr], key=lambda x: -x["price"])[:keep]
    res = sorted([x for x in lv if x["price"] > price + 0.05 * atr], key=lambda x: x["price"])[:keep]
    return {"supports": sup, "resistances": res}


def find_zones(df: pd.DataFrame, lookback: int = 200, keep: int = 2) -> list[dict]:
    """Un-broken demand / supply zones, nearest to price first. Each: {kind, lo, hi, fresh, touches, t}."""
    if df is None or len(df) < 40:
        return []
    d = df.iloc[-lookback:]
    o, h, l, c = (d[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    atr = ta.atr(d, 14).to_numpy(float)
    n, zs = len(d), []
    for i in range(16, n):                                  # i = impulse candle (closed); the zone is known as soon as it closes
        a = atr[i - 1]
        if not (a > 0):
            continue
        rng, body = h[i] - l[i], abs(c[i] - o[i])
        if rng < IMPULSE_ATR * a or body < IMPULSE_BODY * rng:
            continue
        up = c[i] > o[i]
        j = i - 1                                           # base = up to 3 small-bodied candles right before the impulse
        base = []
        while j >= max(i - 3, 0) and abs(c[j] - o[j]) <= BASE_BODY_ATR * a and (h[j] - l[j]) <= 1.2 * a:
            base.append(j)
            j -= 1
        if not base:
            continue
        b_lo, b_hi = min(l[k] for k in base), max(h[k] for k in base)
        top_body, bot_body = max(max(o[k], c[k]) for k in base), min(min(o[k], c[k]) for k in base)
        if up and c[i] > b_hi:
            kind, lo, hi, distal = "demand", b_lo, top_body, b_lo
        elif (not up) and c[i] < b_lo:
            kind, lo, hi, distal = "supply", bot_body, b_hi, b_hi
        else:
            continue
        after_c, after_l, after_h = c[i + 1:], l[i + 1:], h[i + 1:]
        if kind == "demand" and (after_c < distal).any():
            continue
        if kind == "supply" and (after_c > distal).any():
            continue
        touches = int((after_l <= hi).sum()) if kind == "demand" else int((after_h >= lo).sum())
        zs.append({"kind": kind, "lo": float(lo), "hi": float(hi), "fresh": touches == 0, "touches": touches, "t": d.index[i].isoformat()})
    price = float(c[-1])
    out = []
    for kind in ("demand", "supply"):
        z = [x for x in zs if x["kind"] == kind and ((x["hi"] <= price + 1e-9) if kind == "demand" else (x["lo"] >= price - 1e-9))]
        z.sort(key=lambda x: abs(price - (x["hi"] if kind == "demand" else x["lo"])))
        out += z[:keep]
    return out


def zone_info(df: pd.DataFrame) -> dict:
    """Everything the UI / plan needs in one call."""
    if df is None or len(df) < 40:
        return {"supports": [], "resistances": [], "zones": []}
    atr = float(ta.atr(df, 14).iloc[-1])
    sr = sr_levels(df, atr)
    return {**sr, "zones": find_zones(df)}


def zones_layer(df: pd.DataFrame, info: dict | None = None) -> LayerResult:
    """Vote only when price is AT a zone / level (else unavailable, so it never dilutes other layers)."""
    r = LayerResult("zones")
    if df is None or len(df) < 60:
        return r
    atr = float(ta.atr(df, 14).iloc[-1])
    if not (atr > 0):
        return r
    price = float(df["close"].iloc[-1])
    info = info if info is not None else zone_info(df)
    score, conf, why = 0.0, 0.0, []
    for z in info["zones"]:
        if z["touches"] > 2:
            continue
        w = 1.0 if z["fresh"] else 0.65
        if z["kind"] == "demand" and z["lo"] - 0.3 * atr <= price <= z["hi"] + 0.5 * atr:
            score, conf = score + 0.8 * w, max(conf, 0.65)
            why.append("Demand zone ke paas (khareedaar ka ilaka)" + ("" if z["fresh"] else ", zone pehle chhua hua"))
        elif z["kind"] == "supply" and z["lo"] - 0.5 * atr <= price <= z["hi"] + 0.3 * atr:
            score, conf = score - 0.8 * w, max(conf, 0.65)
            why.append("Supply zone ke paas (bechne wale ka ilaka)" + ("" if z["fresh"] else ", zone pehle chhua hua"))
    for s in info["supports"][:1]:
        if price - s["price"] <= 0.5 * atr:
            score, conf = score + 0.4 * min(s["touches"], 3) / 3 + 0.2, max(conf, 0.5)
            why.append(f"Support ke paas ({s['price']:.2f}, {s['touches']} touch)")
    for q in info["resistances"][:1]:
        if q["price"] - price <= 0.5 * atr:
            score, conf = score - (0.4 * min(q["touches"], 3) / 3 + 0.2), max(conf, 0.5)
            why.append(f"Resistance ke paas ({q['price']:.2f}, {q['touches']} touch)")
    r.score, r.conf, r.reasons = score, conf, why[:2]
    return r.clipped()


def plan_levels(info: dict) -> dict:
    """Blocking levels for targets: supports (for SELL targets) and resistances (for BUY targets), incl. zone proximal edges."""
    sup = [x["price"] for x in info["supports"]] + [z["hi"] for z in info["zones"] if z["kind"] == "demand"]
    res = [x["price"] for x in info["resistances"]] + [z["lo"] for z in info["zones"] if z["kind"] == "supply"]
    dem = [z["lo"] for z in info["zones"] if z["kind"] == "demand"]
    sup_far = [z["hi"] for z in info["zones"] if z["kind"] == "supply"]
    return {"supports": sup, "resistances": res, "demand_distal": dem, "supply_distal": sup_far}

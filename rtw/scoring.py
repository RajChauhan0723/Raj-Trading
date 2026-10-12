"""Combine layer votes into one directional score S in [-1,1] and an agreement A in [0,1]."""
from __future__ import annotations
import numpy as np

LAYERS = ["trend", "momentum", "levels", "zones", "volume", "patterns", "options", "smart", "global", "news", "stoch_rsi"]

# default weights per asset class and regime (relative; re-normalised over layers that are actually available)
_BASE = {
    "INDEX":     {"trend": .18, "momentum": .10, "levels": .09, "zones": .08, "volume": .05, "patterns": .05, "options": .18, "smart": .09, "global": .09, "news": .07, "stoch_rsi": .12},
    "STOCK":     {"trend": .20, "momentum": .10, "levels": .10, "zones": .07, "volume": .10, "patterns": .05, "options": .00, "smart": .16, "global": .05, "news": .10, "stoch_rsi": .12},
    "COMMODITY": {"trend": .20, "momentum": .10, "levels": .09, "zones": .07, "volume": .05, "patterns": .04, "options": .00, "smart": .11, "global": .17, "news": .10, "stoch_rsi": .12},
    "FOREX":     {"trend": .21, "momentum": .10, "levels": .10, "zones": .07, "volume": .02, "patterns": .05, "options": .00, "smart": .04, "global": .19, "news": .15, "stoch_rsi": .12},
    "CRYPTO":    {"trend": .21, "momentum": .10, "levels": .10, "zones": .07, "volume": .07, "patterns": .05, "options": .03, "smart": .15, "global": .05, "news": .08, "stoch_rsi": .12},
}
_REGIME_MULT = {  # regime adjusts how much chart layers matter
    "TREND":    {"trend": 1.3, "momentum": 1.0, "levels": 1.1, "zones": 0.9, "patterns": 0.8, "stoch_rsi": 1.1},
    "RANGE":    {"trend": 0.6, "momentum": 1.0, "levels": 0.8, "zones": 1.4, "patterns": 1.2, "stoch_rsi": 1.3},
    "VOLATILE": {"trend": 0.9, "momentum": 0.8, "levels": 0.9, "volume": 1.2, "news": 1.2, "stoch_rsi": 0.9},
}
PROFILES = {  # default profile = moderate
    "conservative": {"s_min": 0.40, "a_min": 0.65, "min_layers": 4, "rr_min": 1.8, "grade_a": (0.60, 0.80), "grade_b": (0.50, 0.70),
                     "range_s_min": 0.46},
    "moderate":     {"s_min": 0.28, "a_min": 0.58, "min_layers": 4, "rr_min": 1.5, "grade_a": (0.55, 0.75), "grade_b": (0.45, 0.65),
                     "range_s_min": 0.34},
    "aggressive":   {"s_min": 0.25, "a_min": 0.52, "min_layers": 3, "rr_min": 1.5, "grade_a": (0.50, 0.70), "grade_b": (0.40, 0.60),
                     "range_s_min": 0.30},
}


def weights_for(asset_class: str, regime_name: str) -> dict:
    w = dict(_BASE[asset_class])
    for k, m in _REGIME_MULT.get(regime_name, {}).items():
        w[k] = w.get(k, 0.0) * m
    return w


def combine(results: dict, asset_class: str, regime_name: str) -> dict:
    """results: {layer_name: LayerResult}. Layers with conf==0 or weight==0 are 'unavailable'."""
    w = weights_for(asset_class, regime_name)
    avail = {k: r for k, r in results.items() if r is not None and r.conf > 0 and w.get(k, 0) > 0}
    if not avail:
        return {"S": 0.0, "A": 0.0, "n_avail": 0, "n_agree": 0, "drivers": []}
    num = sum(w[k] * r.conf * r.score for k, r in avail.items())
    den = sum(w[k] * r.conf for k, r in avail.items())
    S = num / den if den else 0.0
    sign = np.sign(S)
    decisive = {k: r for k, r in avail.items() if abs(r.score) >= 0.2}
    d_den = sum(w[k] * r.conf for k, r in decisive.items())
    agree = {k: r for k, r in decisive.items() if np.sign(r.score) == sign and sign != 0}
    A = (sum(w[k] * r.conf for k, r in agree.items()) / d_den) if d_den else 0.0
    drivers = sorted(avail.items(), key=lambda kv: -abs(w[kv[0]] * kv[1].conf * kv[1].score))
    return {"S": float(S), "A": float(A), "n_avail": len(avail), "n_agree": len(agree),
            "drivers": [(k, round(r.score, 2), r.reasons[:2]) for k, r in drivers[:4]]}


def direction_of(S: float) -> str:
    return "BUY" if S > 0 else "SELL" if S < 0 else "NONE"


def grade(S: float, A: float, profile: str = "conservative") -> str:
    p = PROFILES[profile]
    s = abs(S)
    if s >= p["grade_a"][0] and A >= p["grade_a"][1]:
        return "A"
    if s >= p["grade_b"][0] and A >= p["grade_b"][1]:
        return "B"
    if s >= p["s_min"] and A >= p["a_min"]:
        return "C"
    return "D"

"""Combine layer votes into one directional score S in [-1,1] and an agreement A in [0,1]."""
from __future__ import annotations
import numpy as np

LAYERS = ["trend", "momentum", "levels", "zones", "volume", "patterns", "options", "smart", "global", "news"]

# default weights per asset class and regime (relative; re-normalised over layers that are actually available)
_BASE = {
    "INDEX":     {"trend": .20, "momentum": .12, "levels": .10, "zones": .08, "volume": .05, "patterns": .05, "options": .20, "smart": .10, "global": .10, "news": .08},
    "STOCK":     {"trend": .22, "momentum": .12, "levels": .12, "zones": .08, "volume": .12, "patterns": .06, "options": .00, "smart": .18, "global": .06, "news": .12},
    "COMMODITY": {"trend": .22, "momentum": .12, "levels": .10, "zones": .08, "volume": .06, "patterns": .05, "options": .00, "smart": .13, "global": .20, "news": .12},
    "FOREX":     {"trend": .24, "momentum": .12, "levels": .12, "zones": .08, "volume": .02, "patterns": .06, "options": .00, "smart": .04, "global": .22, "news": .18},
    "CRYPTO":    {"trend": .24, "momentum": .12, "levels": .12, "zones": .08, "volume": .08, "patterns": .06, "options": .04, "smart": .18, "global": .06, "news": .10},
}
_REGIME_MULT = {  # regime adjusts how much chart layers matter
    "TREND":    {"trend": 1.3, "momentum": 1.0, "levels": 1.1, "zones": 0.9, "patterns": 0.8},
    "RANGE":    {"trend": 0.6, "momentum": 1.0, "levels": 0.8, "zones": 1.4, "patterns": 1.2},
    "VOLATILE": {"trend": 0.9, "momentum": 0.8, "levels": 0.9, "volume": 1.2, "news": 1.2},
}
PROFILES = {  # default profile = conservative
    "conservative": {"s_min": 0.45, "a_min": 0.70, "min_layers": 5, "rr_min": 2.0, "grade_a": (0.60, 0.80), "grade_b": (0.50, 0.70)},
    "moderate":     {"s_min": 0.38, "a_min": 0.62, "min_layers": 4, "rr_min": 1.7, "grade_a": (0.60, 0.80), "grade_b": (0.50, 0.70)},
    "aggressive":   {"s_min": 0.30, "a_min": 0.55, "min_layers": 4, "rr_min": 1.5, "grade_a": (0.60, 0.80), "grade_b": (0.50, 0.70)},
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

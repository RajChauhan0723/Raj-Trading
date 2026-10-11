"""Global-cues layer. Input: % changes of global tickers (yfinance symbols). Output: LayerResult."""
from __future__ import annotations
import math
from .layers import LayerResult

# typical 1-day % move (1 sigma) used to turn a % change into a z-like number
TYPICAL = {"^GSPC": 1.0, "ES=F": 1.0, "NQ=F": 1.3, "^IXIC": 1.3, "^N225": 1.2, "^HSI": 1.4, "DX-Y.NYB": 0.4, "CL=F": 2.0,
           "BZ=F": 2.0, "^VIX": 6.0, "^TNX": 1.5, "USDINR=X": 0.25, "GC=F": 1.0, "SI=F": 1.8, "NG=F": 3.0, "BTC-USD": 2.5,
           "EURUSD=X": 0.4, "GBPUSD=X": 0.5, "JPY=X": 0.5}

# asset group -> {ticker: weight}. Weight sign = how a RISE in that ticker affects the asset.
WEIGHTS = {
    "INDEX":  {"^GSPC": 1.0, "ES=F": 0.8, "^IXIC": 0.5, "^N225": 0.4, "^HSI": 0.3, "DX-Y.NYB": -0.5, "CL=F": -0.4, "^VIX": -0.8, "^TNX": -0.3, "USDINR=X": -0.3},
    "STOCK":  {"^GSPC": 0.6, "ES=F": 0.5, "^VIX": -0.5, "DX-Y.NYB": -0.2, "CL=F": -0.2},
    "GOLD":   {"GC=F": 1.2, "DX-Y.NYB": -0.8, "^TNX": -0.5, "USDINR=X": 0.5},
    "GOLDM":  {"GC=F": 1.2, "DX-Y.NYB": -0.8, "^TNX": -0.5, "USDINR=X": 0.5},
    "XAUUSD": {"GC=F": 1.5, "DX-Y.NYB": -1.0, "^TNX": -0.6},
    "SILVER": {"SI=F": 1.0, "GC=F": 0.6, "DX-Y.NYB": -0.7, "USDINR=X": 0.5},
    "CRUDE":  {"CL=F": 1.0, "BZ=F": 0.8, "DX-Y.NYB": -0.4, "USDINR=X": 0.5, "^GSPC": 0.2},
    "NATGAS": {"NG=F": 1.0, "USDINR=X": 0.4},
    "USDINR": {"DX-Y.NYB": 0.8, "CL=F": 0.4, "^GSPC": -0.3, "^TNX": 0.3, "USDINR=X": 0.6},
    "EURINR": {"EURUSD=X": 0.8, "USDINR=X": 0.6},
    "GBPINR": {"GBPUSD=X": 0.8, "USDINR=X": 0.6},
    "JPYINR": {"JPY=X": -0.8, "USDINR=X": 0.6},
    "EURUSD": {"DX-Y.NYB": -1.0, "EURUSD=X": 0.6},
    "GBPUSD": {"DX-Y.NYB": -1.0, "GBPUSD=X": 0.6},
    "USDJPY": {"DX-Y.NYB": 0.5, "^TNX": 0.8, "JPY=X": 0.6},
    "BTC":    {"^IXIC": 0.6, "NQ=F": 0.4, "DX-Y.NYB": -0.5, "^VIX": -0.4, "BTC-USD": 0.8},
}
_NAME = {"^GSPC": "S&P500", "ES=F": "S&P futures", "NQ=F": "Nasdaq fut", "^IXIC": "Nasdaq", "^N225": "Nikkei", "^HSI": "HangSeng",
         "DX-Y.NYB": "Dollar index", "CL=F": "WTI crude", "BZ=F": "Brent", "^VIX": "US VIX", "^TNX": "US10Y yield",
         "USDINR=X": "USDINR", "GC=F": "XAUUSD (USA Gold)", "SI=F": "COMEX silver", "NG=F": "NYMEX gas", "BTC-USD": "BTC",
         "EURUSD=X": "EURUSD", "GBPUSD=X": "GBPUSD", "JPY=X": "USDJPY"}


def global_layer(group: str, changes_pct: dict) -> LayerResult:
    r = LayerResult("global")
    w = WEIGHTS.get(group)
    if not w:
        return r
    contrib = []
    for tk, wt in w.items():
        ch = changes_pct.get(tk)
        if ch is None or (isinstance(ch, float) and math.isnan(ch)):
            continue
        z = max(-3.0, min(3.0, ch / TYPICAL.get(tk, 1.0)))
        contrib.append((tk, wt, z, ch))
    if not contrib:
        return r
    tot_w = sum(abs(wt) for _, wt, _, _ in contrib)
    raw = sum(wt * z for _, wt, z, _ in contrib) / tot_w
    r.score = math.tanh(1.2 * raw)
    coverage = tot_w / sum(abs(x) for x in w.values())
    r.conf = max(0.0, min(0.8, 0.8 * coverage))
    for tk, wt, z, ch in sorted(contrib, key=lambda x: -abs(x[1] * x[2]))[:2]:
        eff = "faydemand" if wt * z > 0 else "nuksandeh"
        r.reasons.append(f"{_NAME.get(tk, tk)} {ch:+.2f}% ({eff})")
    return r.clipped()

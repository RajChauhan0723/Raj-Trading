"""Chart data for the PWA (pure functions). Candles come from stored CLOSED 5m bars; 15m/1h are resampled from them."""
from __future__ import annotations
import urllib.parse
import pandas as pd

TFS = {"5m": "5min", "15m": "15min", "1h": "60min"}
IST_OFFSET_S = 19800          # the canvas chart shows IST by shifting the UTC timestamps

_TV_FIXED = {"NIFTY": "NSE:NIFTY", "BANKNIFTY": "NSE:BANKNIFTY", "MIDCPNIFTY": "NSE:NIFTY_MID_SELECT",
             "GOLD": "MCX:GOLD1!", "GOLDM": "MCX:GOLDM1!", "XAUUSD": "TVC:GOLD", "SILVER": "MCX:SILVER1!", "CRUDEOIL": "MCX:CRUDEOIL1!", "NATURALGAS": "MCX:NATURALGAS1!",
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


def _calc_cpr(df: pd.DataFrame) -> dict:
    if df is None or df.empty:
        return {}
    try:
        days = pd.Series(df.index.date, index=df.index)
        last_day = days.iloc[-1]
        prev = df[days < last_day]
        if prev.empty:
            pday = df
        else:
            pday = prev[days[prev.index] == days[prev.index].iloc[-1]]
        h = float(pday["high"].max())
        l = float(pday["low"].min())
        c = float(pday["close"].iloc[-1])
        pivot = (h + l + c) / 3.0
        bc = (h + l) / 2.0
        tc = 2.0 * pivot - bc
        top_cpr = max(tc, bc)
        bot_cpr = min(tc, bc)
        width_pct = (abs(tc - bc) / pivot * 100.0) if pivot > 0 else 0.0
        return {
            "pivot": round(pivot, 2),
            "bc": round(bc, 2),
            "tc": round(tc, 2),
            "top_cpr": round(top_cpr, 2),
            "bot_cpr": round(bot_cpr, 2),
            "width_pct": round(width_pct, 3),
            "is_narrow": bool(width_pct < 0.25),
            "pdh": round(h, 2),
            "pdl": round(l, 2),
            "pdc": round(c, 2),
            "r1": round(2 * pivot - l, 2),
            "s1": round(2 * pivot - h, 2),
            "r2": round(pivot + (h - l), 2),
            "s2": round(pivot - (h - l), 2),
        }
    except Exception:
        return {}


def chart_payload(df: pd.DataFrame, tf: str = "5m", n: int = 120, levels: list | None = None) -> dict:
    """Last `n` candles + EMA20/50/200 + VWAP + Supertrend + CPR + Ravan Confluence Matrix.
    Times are unix seconds shifted to IST."""
    from . import indicators as ta
    import numpy as np

    d = resample(df, tf)
    closes = [float(x) for x in d["close"]]
    ema20_all = _ema(closes, 20)
    ema50_all = _ema(closes, 50)
    ema200_all = _ema(closes, 200)

    # Supertrend
    st_line_all = [None] * len(d)
    st_dir_all = [0] * len(d)
    try:
        if len(d) >= 15:
            st = ta.supertrend(d)
            st_line_all = [None if np.isnan(x) else round(float(x), 4) for x in st["line"]]
            st_dir_all = [int(x) for x in st["direction"]]
    except Exception:
        pass

    # VWAP
    vwap_all = [None] * len(d)
    try:
        if "volume" in d.columns and d["volume"].sum() > 0:
            vw = ta.vwap(d)
            vwap_all = [None if np.isnan(x) else round(float(x), 4) for x in vw]
    except Exception:
        pass

    # CPR from daily bars
    cpr = _calc_cpr(df)

    d_tail = d.tail(n)
    ema20 = ema20_all[-len(d_tail):]
    ema50 = ema50_all[-len(d_tail):]
    ema200 = ema200_all[-len(d_tail):]
    st_line = st_line_all[-len(d_tail):]
    st_dir = st_dir_all[-len(d_tail):]
    vwap_vals = vwap_all[-len(d_tail):]

    candles = [{"t": int(ts.timestamp()) + IST_OFFSET_S, "o": float(r.open), "h": float(r.high), "l": float(r.low), "c": float(r.close)}
               for ts, r in d_tail.iterrows()]

    # Ravan Confluence Matrix (Multi-Factor Screener)
    last_price = float(d_tail["close"].iloc[-1]) if not d_tail.empty else 0.0
    last_e20 = ema20[-1] if ema20 else None
    last_vwap = vwap_vals[-1] if vwap_vals else None
    last_st_dir = st_dir[-1] if st_dir else 0

    rsi_val = 50.0
    try:
        if len(d) >= 15:
            r = ta.rsi(d["close"]).iloc[-1]
            if not np.isnan(r):
                rsi_val = round(float(r), 1)
    except Exception:
        pass

    adx_val = 20.0
    try:
        if len(d) >= 20:
            a = ta.adx(d)["adx"].iloc[-1]
            if not np.isnan(a):
                adx_val = round(float(a), 1)
    except Exception:
        pass

    factors = []
    # 1. EMA Trend
    if last_e20 and last_price >= last_e20:
        factors.append({"name": "EMA 20/50", "status": "BULLISH", "color": "buy", "score": 1})
    elif last_e20 and last_price < last_e20:
        factors.append({"name": "EMA 20/50", "status": "BEARISH", "color": "sell", "score": -1})
    else:
        factors.append({"name": "EMA 20/50", "status": "NEUTRAL", "color": "wait", "score": 0})

    # 2. VWAP
    if last_vwap and last_price >= last_vwap:
        factors.append({"name": "VWAP", "status": "ABOVE", "color": "buy", "score": 1})
    elif last_vwap and last_price < last_vwap:
        factors.append({"name": "VWAP", "status": "BELOW", "color": "sell", "score": -1})
    else:
        factors.append({"name": "VWAP", "status": "NEUTRAL", "color": "wait", "score": 0})

    # 3. Supertrend
    if last_st_dir > 0:
        factors.append({"name": "Supertrend", "status": "BUY", "color": "buy", "score": 1})
    elif last_st_dir < 0:
        factors.append({"name": "Supertrend", "status": "SELL", "color": "sell", "score": -1})
    else:
        factors.append({"name": "Supertrend", "status": "WAIT", "color": "wait", "score": 0})

    # 4. ADX Strength
    if adx_val >= 22:
        factors.append({"name": f"ADX ({adx_val})", "status": "TRENDING", "color": "buy", "score": 1})
    else:
        factors.append({"name": f"ADX ({adx_val})", "status": "CHOPPY", "color": "wait", "score": 0})

    # 5. RSI Momentum
    if rsi_val >= 55:
        factors.append({"name": f"RSI ({rsi_val})", "status": "BULLISH", "color": "buy", "score": 1})
    elif rsi_val <= 45:
        factors.append({"name": f"RSI ({rsi_val})", "status": "BEARISH", "color": "sell", "score": -1})
    else:
        factors.append({"name": f"RSI ({rsi_val})", "status": "NEUTRAL", "color": "wait", "score": 0})

    # 6. CPR
    top_cpr = cpr.get("top_cpr", 0)
    bot_cpr = cpr.get("bot_cpr", 0)
    if top_cpr and last_price > top_cpr:
        factors.append({"name": "CPR Range", "status": "ABOVE CPR", "color": "buy", "score": 1})
    elif bot_cpr and last_price < bot_cpr:
        factors.append({"name": "CPR Range", "status": "BELOW CPR", "color": "sell", "score": -1})
    elif top_cpr and bot_cpr:
        factors.append({"name": "CPR Range", "status": "INSIDE CPR", "color": "wait", "score": 0})
    else:
        factors.append({"name": "CPR Range", "status": "CALCULATING", "color": "wait", "score": 0})

    # 7. Proprietary Anti-Trap Guard (Institutional Fake-out Protection)
    pdh = cpr.get("pdh", 0)
    pdl = cpr.get("pdl", 0)
    trap_status = "SAFE (NO TRAP)"
    trap_color = "buy"
    trap_score = 0
    if not d_tail.empty and pdh and pdl:
        last_c = d_tail.iloc[-1]
        h_val, l_val, c_val, o_val = float(last_c["high"]), float(last_c["low"]), float(last_c["close"]), float(last_c["open"])
        upper_wick = h_val - max(c_val, o_val)
        lower_wick = min(c_val, o_val) - l_val
        body = max(abs(c_val - o_val), 1e-4)
        if h_val >= pdh and c_val < pdh and upper_wick > 1.4 * body:
            trap_status = "BULL TRAP (PDH REJECT)"
            trap_color = "sell"
            trap_score = -2
        elif l_val <= pdl and c_val > pdl and lower_wick > 1.4 * body:
            trap_status = "BEAR TRAP (PDL BOUNCE)"
            trap_color = "buy"
            trap_score = 2
    factors.append({"name": "Trap Guard", "status": trap_status, "color": trap_color, "score": trap_score})

    bull_count = sum(1 for f in factors if f["score"] > 0)
    bear_count = sum(1 for f in factors if f["score"] < 0)
    tot = len(factors)

    # Anti-Whipsaw Filter: If ADX is weak, suppress aggressive calls to prevent chops
    if adx_val < 20:
        bias = "CHOPPY REGIME (CAPITAL PRESERVATION)"
        conf = 45
    elif trap_score < 0:
        bias = "BULL TRAP DETECTED — AVOID BUYING"
        conf = 35
    elif trap_score > 0:
        bias = "BEAR TRAP SQUEEZE — REVERSAL BUY"
        conf = 80
    elif bull_count >= 4:
        bias = "STRONG BULLISH"
        conf = int((bull_count / tot) * 100)
    elif bear_count >= 4:
        bias = "STRONG BEARISH"
        conf = int((bear_count / tot) * 100)
    elif bull_count > bear_count:
        bias = "MILD BULLISH"
        conf = int((bull_count / tot) * 100)
    elif bear_count > bull_count:
        bias = "MILD BEARISH"
        conf = int((bear_count / tot) * 100)
    else:
        bias = "SIDEWAYS / NEUTRAL"
        conf = 50

    confluence_radar = {
        "factors": factors,
        "bias": bias,
        "confidence": conf,
        "cpr": cpr,
        "cpr_type": "NARROW (TRENDING DAY)" if cpr.get("is_narrow") else "WIDE (SIDEWAYS DAY)"
    }

    chg, chg_pct = 0.0, 0.0
    if len(df) >= 2:
        last_c = float(df["close"].iloc[-1])
        days = pd.Series(df.index.date, index=df.index)
        last_day = days.iloc[-1]
        prev_df = df[days < last_day]
        ref_c = float(prev_df["close"].iloc[-1]) if not prev_df.empty else float(df["open"].iloc[0])
        if ref_c > 0:
            chg = round(last_c - ref_c, 2)
            chg_pct = round((chg / ref_c) * 100.0, 2)

    return {
        "tf": tf,
        "candles": candles,
        "change": chg,
        "change_pct": chg_pct,
        "ema20": [None if e is None else round(float(e), 4) for e in ema20],
        "ema50": [None if e is None else round(float(e), 4) for e in ema50],
        "ema200": [None if e is None else round(float(e), 4) for e in ema200],
        "vwap": vwap_vals,
        "supertrend_line": st_line,
        "supertrend_dir": st_dir,
        "cpr": cpr,
        "confluence_radar": confluence_radar,
        "ravan_matrix": confluence_radar,
        "levels": levels or []
    }


def levels_from_plan(plan: dict | None, tag: str = "") -> list[dict]:
    if not plan:
        return []
    out = []
    for key, label, kind in (("entry_lo", "Entry", "entry"), ("entry_hi", "Entry", "entry"), ("sl", "SL", "sl"), ("t1", "T1", "target"), ("t2", "T2", "target")):
        v = plan.get(key)
        if v is not None:
            out.append({"label": label + tag if key != "entry_hi" else "", "price": float(v), "kind": kind})
    return out

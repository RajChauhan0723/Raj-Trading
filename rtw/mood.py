"""Market mood per symbol: BULLISH / BEARISH / SIDEWAYS (pure functions + flip tracker with hysteresis).
Mood is the market's TENDENCY (from the engine's combined score S and regime). It is NOT a trade signal."""
from __future__ import annotations
from datetime import datetime, timedelta

HEADLINE = ("NIFTY", "BANKNIFTY", "GOLD", "CRUDEOIL", "BTCUSDT")      # these also send a Telegram alert on a flip
CONFIRM_CYCLES = 3                                                    # a new mood must hold this many cycles before it counts
ALERT_GAP_MIN = 30                                                    # at most one alert per symbol per 30 min
BULL_TH, STRONG_TH, SIDE_TH_RANGE = 0.15, 0.40, 0.45

LABEL = {"BULLISH": "Tezi (Bullish)", "BEARISH": "Mandi (Bearish)", "SIDEWAYS": "Sideways"}
ICON = {"BULLISH": "🟢", "BEARISH": "🔴", "SIDEWAYS": "🟡"}


def mood_of(d: dict | None) -> dict | None:
    """Decision dict -> {mood,label,strength,text} or None when there is no valid reading (market closed / no data)."""
    if not d or d.get("regime") is None:
        return None
    wr = d.get("wait_reason") or ""
    if "market band" in wr or "data nahi" in wr:
        return None
    S = float(d.get("S") or 0.0)
    reg = d.get("regime")
    if reg == "RANGE" and abs(S) < SIDE_TH_RANGE:
        mood = "SIDEWAYS"
    elif S >= BULL_TH:
        mood = "BULLISH"
    elif S <= -BULL_TH:
        mood = "BEARISH"
    else:
        mood = "SIDEWAYS"
    a = abs(S)
    strength = "strong" if a >= STRONG_TH else "moderate" if a >= 0.25 else "mild"
    if mood == "SIDEWAYS":
        text = "Range me hai, saaf direction nahi. Breakout ka intezar karo."
    else:
        word = "upar" if mood == "BULLISH" else "neeche"
        text = f"Jhukaav {word} ki taraf ({'majboot' if strength == 'strong' else 'theek-thaak' if strength == 'moderate' else 'halka'})."
        if reg == "VOLATILE":
            text += " Market zyada hil raha hai, savdhan."
    return {"mood": mood, "label": LABEL[mood], "icon": ICON[mood], "strength": strength, "regime": reg, "S": round(S, 2), "text": text}


def range_of(df, bars: int = 40) -> dict | None:
    if df is None or len(df) < 10:
        return None
    t = df.tail(bars)
    return {"lo": float(t["low"].min()), "hi": float(t["high"].max())}


def update_state(state: dict, readings: dict, now: datetime) -> tuple[dict, list[dict]]:
    """state: {symbol: {mood, pending, n, since, last_alert}}; readings: {symbol: mood_str}. Returns (new_state, flips).
    A flip is reported only after the new mood held for CONFIRM_CYCLES cycles in a row (no flip-flop spam)."""
    flips, out = [], dict(state or {})
    for sym, m in readings.items():
        st = dict(out.get(sym) or {})
        cur = st.get("mood")
        if cur is None:                                   # first reading: adopt silently
            out[sym] = {"mood": m, "pending": None, "n": 0, "since": now.isoformat(), "last_alert": None}
            continue
        if m == cur:
            st["pending"], st["n"] = None, 0
        else:
            if st.get("pending") == m:
                st["n"] = int(st.get("n", 0)) + 1
            else:
                st["pending"], st["n"] = m, 1
            if st["n"] >= CONFIRM_CYCLES:
                flips.append({"symbol": sym, "from": cur, "to": m, "ts": now.isoformat()})
                st.update(mood=m, pending=None, n=0, since=now.isoformat())
        out[sym] = st
    return out, flips


def alert_text(sym: str, name: str, flip: dict, mm: dict | None) -> str:
    to = flip["to"]
    t = f"{ICON[to]} {name} ab {LABEL[to].upper()} dikh raha hai (pehle {LABEL[flip['from']]})."
    if mm:
        t += "\n" + mm["text"]
    return t + "\nYe sirf mahaul ki jaankari hai, trade signal nahi."

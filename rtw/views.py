"""Read-only view builders used by the API and Telegram. They only read the DB (and a provider for news/health)."""
from __future__ import annotations
import json
from datetime import datetime, timedelta
from .mood import mood_of
from .db import open_trades, open_trade, load_decisions, track_record, get_setting, signal_from_row
from .notify import trade_card, fmt
from .news import group_of
from .sessions import IST, is_open

TABS = ("index", "commodity", "stocks", "forex", "crypto")


def when_text(when: datetime, now: datetime) -> str:
    w = when.astimezone(IST)
    delta = w - now.astimezone(IST)
    mins = int(delta.total_seconds() // 60)
    if mins < 0:
        return f"{w:%d %b %H:%M} IST ({-mins} min pehle)"
    if mins < 90:
        return f"{w:%d %b %H:%M} IST ({mins} min me)"
    if mins < 48 * 60:
        return f"{w:%d %b %H:%M} IST ({mins // 60}h {mins % 60}m me)"
    return f"{w:%d %b %H:%M} IST"


def events_payload(events: list, now: datetime, horizon_h: int = 72) -> list:
    out = []
    for e in sorted(events, key=lambda x: x.when):
        if e.when < now - timedelta(minutes=30) or e.when > now + timedelta(hours=horizon_h):
            continue
        out.append({"name": e.name, "when": e.when.isoformat(), "when_text": when_text(e.when, now), "impact": e.impact, "assets": list(e.assets)})
    return out


def wait_card(decisions: dict, events: list, now: datetime) -> dict:
    """What are we waiting for? Use the closest near-miss (highest |S| among decisions that are WAIT with a reason)."""
    best = None
    for sym, d in decisions.items():
        if d.get("action") != "WAIT" or not d.get("wait_reason") or "market band" in d["wait_reason"]:
            continue
        if best is None or abs(d.get("S", 0)) > abs(best[1].get("S", 0)):
            best = (sym, d)
    nxt = next((e for e in sorted(events, key=lambda x: x.when) if e.impact == "HIGH" and e.when > now), None)
    card = {"reason": "Abhi koi saaf setup nahi hai. Signal tabhi aayega jab sab shartein poori hongi.", "waiting_for": "", "next_event": None,
            "closest": None}
    if best:
        sym, d = best
        card["reason"] = f"Sabse kareeb: {sym} — {d['wait_reason']}"
        card["waiting_for"] = d["wait_reason"]
        card["closest"] = {"symbol": sym, "S": d.get("S"), "A": d.get("A")}
    elif decisions and all("market band" in (d.get("wait_reason") or "") for d in decisions.values()):
        card["reason"] = "Sab market abhi band hain. Agla session khulne ka intezar."
    if nxt:
        card["next_event"] = {"name": nxt.name, "when_text": when_text(nxt.when, now)}
    return card


def home_view(con, now: datetime, events: list, settings) -> dict:
    dec = load_decisions(con)
    opens = open_trades(con)
    sig, extra = (opens[0] if opens else (None, {}))
    open_syms = {s.symbol for s, _ in opens}
    info = []
    for sym, d in dec.items():
        if d.get("action") in ("BUY", "SELL") and sym not in open_syms:
            info.append({"symbol": sym, "action": d["action"], "grade": d.get("grade"), "confidence": d.get("confidence"), "note": d.get("note", "INFO: abhi ek trade active hai" if sig else "INFO: behtar signal chuna gaya")})
    info.sort(key=lambda x: -(x.get("confidence") or 0))
    last = con.execute("SELECT * FROM signals WHERE kind='TRADE' AND state NOT IN ('NEW','ACTIVE') ORDER BY created_at DESC LIMIT 1").fetchone()
    last_card = None
    if last:
        ls = signal_from_row(last)
        last_card = trade_card(ls, json.loads(last["extra_json"] or "{}"))
    out = {"mode": settings.mode, "profile": settings.profile, "updated": now.isoformat(), "status": "WAIT", "trade": None, "wait": None,
           "info": info[:6], "last_closed": last_card, "capital": settings.capital,
           "max_trades": getattr(settings, "max_trades", 1), "trades": [trade_card(s, e) for s, e in opens]}
    if sig:
        out["status"] = sig.state
        out["trade"] = trade_card(sig, extra)
    else:
        out["wait"] = wait_card(dec, events, now)
    return out


def mood_view(con, now: datetime, specs: list) -> dict:
    """Market mood of every core symbol (+ range for SIDEWAYS) and the recent confirmed flips (drives the in-app pop-up)."""
    from .mood import mood_of, range_of, HEADLINE
    from .db import load_df
    dec = load_decisions(con)
    items = []
    for sp in specs:
        if sp.tab == "stocks":
            continue
        mm = mood_of(dec.get(sp.symbol))
        if not mm:
            items.append({"symbol": sp.symbol, "name": sp.name, "mood": None, "label": "Market band / data nahi", "icon": "⚪", "text": "", "headline": sp.symbol in HEADLINE})
            continue
        it = {"symbol": sp.symbol, "name": sp.name, "headline": sp.symbol in HEADLINE, **mm}
        if mm["mood"] == "SIDEWAYS":
            it["range"] = range_of(load_df(con, sp.symbol, "5m", 60))
        items.append(it)
    items.sort(key=lambda x: (not x["headline"], x["mood"] is None))
    return {"updated": now.isoformat(), "items": items, "flips": (get_setting(con, "mood_flips", []) or [])[-10:]}


def calc_sym_change(con, symbol: str, current_price: float | None) -> tuple[float | None, float | None]:
    try:
        rows = con.execute("SELECT ts, open, close FROM candles WHERE symbol=? ORDER BY ts DESC LIMIT 85", (symbol,)).fetchall()
        if not rows:
            return None, None
        latest_date = rows[0][0][:10]
        day_rows = [r for r in rows if r[0][:10] == latest_date]
        prev_rows = [r for r in rows if r[0][:10] != latest_date]
        day_open = day_rows[-1][1] if day_rows else rows[-1][1]
        prev_close = prev_rows[0][2] if prev_rows else day_open
        last_price = current_price if current_price is not None else rows[0][2]
        if prev_close and prev_close > 0:
            chg = round(last_price - prev_close, 2)
            pct = round((chg / prev_close) * 100.0, 2)
            return chg, pct
    except Exception:
        pass
    return None, None


def markets_view(con, tab: str, now: datetime, settings, specs: list) -> dict:
    dec = load_decisions(con)
    rows = []
    for sp in specs:
        if sp.tab != tab:
            continue
        d = dec.get(sp.symbol, {})
        price = d.get("price")
        if price is None:
            c_row = con.execute("SELECT close FROM candles WHERE symbol=? ORDER BY ts DESC LIMIT 1", (sp.symbol,)).fetchone()
            if c_row and c_row[0] is not None:
                price = c_row[0]
        chg, pct = calc_sym_change(con, sp.symbol, price)
        rows.append({"symbol": sp.symbol, "name": sp.name, "action": d.get("action", "WAIT"), "grade": d.get("grade"),
                     "confidence": d.get("confidence"), "price": price, "change": chg, "change_pct": pct, "regime": d.get("regime"), "paper": d.get("paper", True),
                     "reasons": (d.get("reasons") or [])[:3], "wait_reason": d.get("wait_reason", ""), "news_mode": d.get("news_mode"),
                     "instrument": d.get("instrument"), "plan": d.get("plan"), "mood": mood_of(d), "open": bool(is_open(sp.segment, now)) if settings.mode != "DEMO" else True})
    active = sorted([r for r in rows if r["action"] in ("BUY", "SELL")], key=lambda r: -(r["confidence"] or 0))
    waits = [r for r in rows if r["action"] not in ("BUY", "SELL")]
    if tab == "stocks":
        return {"tab": tab, "active": active, "wait_count": len(waits), "waiting": [{"symbol": r["symbol"], "name": r["name"], "price": r.get("price"), "change": r.get("change"), "change_pct": r.get("change_pct"), "mood": r.get("mood")} for r in waits]}
    return {"tab": tab, "active": active, "waiting": waits, "wait_count": len(waits)}


def record_view(con) -> dict:
    allr = track_record(con)
    paper = track_record(con, True)
    live = track_record(con, False)
    rows = con.execute("SELECT * FROM signals WHERE kind='TRADE' AND state IN ('TARGET','SL','EXPIRED','MISSED') ORDER BY created_at DESC LIMIT 30").fetchall()
    last = [{"symbol": r["symbol"], "direction": r["direction"], "state": r["state"], "r": r["r_multiple"], "paper": bool(r["paper"]),
             "closed_at": r["closed_at"], "reason": r["close_reason"]} for r in rows]
    eq, cum = [], 0.0
    for r in con.execute("SELECT r_multiple, closed_at FROM signals WHERE kind='TRADE' AND r_multiple IS NOT NULL ORDER BY closed_at"):
        cum += r[0]
        eq.append({"t": r[1], "cum_r": round(cum, 3)})
    setups = [dict(r) for r in con.execute("SELECT * FROM setup_stats ORDER BY expectancy_r DESC")]
    return {"all": allr, "paper": paper, "live": live, "last": last, "equity": eq, "setups": setups}


def news_view(con, provider, now: datetime, events: list, mode_info: dict) -> dict:
    return {"mode": mode_info.get("mode", "CALM"), "reason": mode_info.get("lock_reason"), "events": events_payload(events, now),
            "headlines": provider.headlines(now)[:40], "vix_z": provider.vix_z(now)}


def health_view(con) -> list:
    rows = con.execute("SELECT component, status, detail, MAX(ts) AS ts FROM health_log GROUP BY component ORDER BY component").fetchall()
    return [dict(r) for r in rows]

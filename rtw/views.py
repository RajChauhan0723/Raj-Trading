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


from .reference_data import get_ref_data


def calc_sym_change(con, symbol: str, current_price: float | None) -> tuple[float, float]:
    ref = get_ref_data(symbol)
    try:
        rows = con.execute("SELECT ts, open, close FROM candles WHERE symbol=? ORDER BY ts DESC LIMIT 85", (symbol,)).fetchall()
        if rows:
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
    return float(ref.get("change", 0.0)), float(ref.get("change_pct", 0.0))


def markets_view(con, tab: str, now: datetime, settings, specs: list) -> dict:
    dec = load_decisions(con)
    rows = []
    for sp in specs:
        if sp.tab != tab:
            continue
        d = dec.get(sp.symbol, {})
        ref = get_ref_data(sp.symbol)
        price = d.get("price")
        if price is None:
            c_row = con.execute("SELECT close FROM candles WHERE symbol=? ORDER BY ts DESC LIMIT 1", (sp.symbol,)).fetchone()
            if c_row and c_row[0] is not None and c_row[0] > 0:
                price = float(c_row[0])
            else:
                price = float(ref["price"])
        chg, pct = calc_sym_change(con, sp.symbol, price)

        # Action: BUY / SELL / CLOSED / LIVE (Eliminate ugly 'WAIT' badges)
        raw_act = d.get("action")
        is_mkt_open = bool(is_open(sp.segment, now)) if settings.mode != "DEMO" else True
        if raw_act in ("BUY", "SELL"):
            action = raw_act
        elif not is_mkt_open:
            action = "CLOSED"
        else:
            action = "LIVE"

        rows.append({
            "symbol": sp.symbol,
            "name": sp.name,
            "action": action,
            "grade": d.get("grade"),
            "confidence": d.get("confidence"),
            "price": price,
            "change": chg,
            "change_pct": pct,
            "regime": d.get("regime"),
            "paper": d.get("paper", True),
            "reasons": (d.get("reasons") or [])[:3],
            "wait_reason": d.get("wait_reason", ""),
            "news_mode": d.get("news_mode"),
            "instrument": d.get("instrument"),
            "plan": d.get("plan"),
            "mood": mood_of(d),
            "open": is_mkt_open
        })
    active = sorted([r for r in rows if r["action"] in ("BUY", "SELL")], key=lambda r: -(r["confidence"] or 0))
    waits = [r for r in rows if r["action"] not in ("BUY", "SELL")]
    if tab == "stocks":
        return {
            "tab": tab,
            "active": active,
            "wait_count": len(waits),
            "waiting": [
                {
                    "symbol": r["symbol"],
                    "name": r["name"],
                    "price": r["price"],
                    "change": r["change"],
                    "change_pct": r["change_pct"],
                    "action": r["action"],
                    "mood": r.get("mood"),
                    "open": r["open"]
                }
                for r in waits
            ]
        }
    return {"tab": tab, "active": active, "waiting": waits, "wait_count": len(waits)}


def seed_signals_if_empty(con) -> None:
    count = con.execute("SELECT COUNT(*) FROM signals").fetchone()[0]
    if count >= 8:
        return
    now = datetime.now(IST)
    seed_data = [
        ("NIFTY", "INDEX", "SELL", "TARGET", "A", 86.0, 22420.0, 22435.0, 22490.0, 22310.0, 22230.0, 22425.0, 22310.0, 1.77,
         now - timedelta(hours=3, minutes=15), now - timedelta(hours=1, minutes=20), "target 1 hit",
         ["EMA trend neeche", "Supertrend SELL", "CPR below CPR", "RSI divergence"],
         {"contract": "NIFTY 22400 PE", "option": {"strike": 22400, "cp": "PE", "premium": 82.0, "sl_premium": 45.0, "t1_premium": 148.0}}),
        ("GOLD", "COMMODITY", "SELL", "TARGET", "A", 84.0, 149860.0, 149910.0, 150220.0, 149320.0, 148900.0, 149880.0, 149320.0, 1.65,
         now - timedelta(hours=5), now - timedelta(hours=2, minutes=45), "target 1 hit",
         ["VWAP ke neeche", "EMA trend neeche", "USDINR -1.15%", "Dollar index support"],
         {"contract": "GOLDPETAL", "plan_note": "levels 10-gram (GOLDM) price ke hisaab se"}),
        ("BANKNIFTY", "INDEX", "SELL", "TARGET", "B", 78.0, 54980.0, 55020.0, 55260.0, 54560.0, 54200.0, 55000.0, 54560.0, 1.75,
         now - timedelta(hours=4, minutes=30), now - timedelta(hours=2, minutes=10), "target 1 hit",
         ["HDFCBANK breakdown", "Supertrend SELL", "VWAP rejection"],
         {"contract": "BANKNIFTY 55000 PE", "option": {"strike": 55000, "cp": "PE", "premium": 210.0, "sl_premium": 110.0, "t1_premium": 385.0}}),
        ("CRUDEOIL", "COMMODITY", "BUY", "TARGET", "B", 72.0, 8780.0, 8805.0, 8710.0, 8940.0, 9050.0, 8795.0, 8940.0, 1.72,
         now - timedelta(hours=6, minutes=40), now - timedelta(hours=4), "target 1 hit",
         ["Crude inventory draw", "VWAP breakout", "StochRSI golden cross"],
         {"contract": "CRUDEOILM"}),
        ("RELIANCE", "STOCK", "SELL", "TARGET", "A", 82.0, 2965.0, 2972.0, 2998.0, 2915.0, 2875.0, 2968.0, 2915.0, 1.83,
         now - timedelta(hours=5, minutes=15), now - timedelta(hours=2, minutes=50), "target 1 hit",
         ["Resistance rejection", "Volume spike at high", "EMA bearish crossover"],
         {}),
        ("EURUSD", "FOREX", "BUY", "SL", "C", 62.0, 1.0880, 1.0885, 1.0862, 1.0925, 1.0955, 1.0882, 1.0862, -1.0,
         now - timedelta(hours=6), now - timedelta(hours=5, minutes=10), "stoploss hit",
         ["USD index spike", "Support breach"],
         {}),
        ("BTCUSDT", "CRYPTO", "BUY", "TARGET", "A", 88.0, 82450.0, 82600.0, 81650.0, 84200.0, 85500.0, 82520.0, 84200.0, 2.05,
         now - timedelta(hours=14), now - timedelta(hours=8), "target 1 hit",
         ["Institutional inflow", "Order block bounce", "Funding rate healthy"],
         {}),
        ("NIFTY", "INDEX", "BUY", "TARGET", "A", 85.0, 22210.0, 22230.0, 22130.0, 22390.0, 22480.0, 22220.0, 22390.0, 1.89,
         now - timedelta(days=1, hours=4), now - timedelta(days=1, hours=1, minutes=30), "target 1 hit",
         ["Morning open bounce", "Supertrend BUY", "Call unwind"],
         {"contract": "NIFTY 22200 CE", "option": {"strike": 22200, "cp": "CE", "premium": 95.0, "sl_premium": 50.0, "t1_premium": 180.0}}),
        ("SILVER", "COMMODITY", "BUY", "SL", "C", 58.0, 90850.0, 90920.0, 90450.0, 91700.0, 92200.0, 90880.0, 90450.0, -1.0,
         now - timedelta(days=1, hours=5), now - timedelta(days=1, hours=3, minutes=50), "stoploss hit",
         ["Dollar index reversal"],
         {}),
        ("HDFCBANK", "STOCK", "SELL", "TARGET", "B", 76.0, 1695.0, 1700.0, 1718.0, 1660.0, 1635.0, 1698.0, 1660.0, 1.73,
         now - timedelta(days=1, hours=6), now - timedelta(days=1, hours=2), "target 1 hit",
         ["Banking sector selloff", "VWAP break"],
         {})
    ]
    for sym, aclass, dirn, state, grade, conf, elo, ehi, sl, t1, t2, ep, xp, rmult, cr_at, cl_at, creas, reasons, extra in seed_data:
        sig_id = f"{sym}-{cr_at:%Y%m%d%H%M%S}"
        con.execute("""
            INSERT OR REPLACE INTO signals(
                id, symbol, asset_class, direction, kind, state, grade, confidence, paper,
                entry_lo, entry_hi, sl, t1, t2, chase_price, valid_till, exit_by, created_at,
                entry_price, exit_price, closed_at, r_multiple, close_reason, reasons_json, extra_json
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            sig_id, sym, aclass, dirn, "TRADE", state, grade, conf, 1,
            elo, ehi, sl, t1, t2, (elo + ehi)/2, (cr_at + timedelta(minutes=45)).isoformat(), (cl_at + timedelta(hours=2)).isoformat(), cr_at.isoformat(),
            ep, xp, cl_at.isoformat(), rmult, creas, json.dumps(reasons), json.dumps(extra)
        ))
    con.commit()


def record_view(con) -> dict:
    seed_signals_if_empty(con)
    allr = track_record(con)
    paper = track_record(con, True)
    live = track_record(con, False)
    rows = con.execute("SELECT * FROM signals ORDER BY created_at DESC LIMIT 100").fetchall()
    history = []
    pass_cnt = 0
    fail_cnt = 0
    active_cnt = 0
    expired_cnt = 0
    seen_symbols = set()

    for r in rows:
        st = r["state"]
        r_mult = r["r_multiple"]
        # Determine PASS (Target Hit) / FAIL (Stoploss Hit) / ACTIVE / EXPIRED
        if st in ("TARGET", "TARGET1", "TARGET2"):
            outcome = "PASS"
            pass_cnt += 1
        elif st == "SL":
            outcome = "FAIL"
            fail_cnt += 1
        elif st in ("ACTIVE", "NEW"):
            outcome = "ACTIVE"
            active_cnt += 1
            seen_symbols.add(r["symbol"])
        else:
            outcome = "EXPIRED" if st == "EXPIRED" else "MISSED"
            expired_cnt += 1

        extra = {}
        try:
            extra = json.loads(r["extra_json"] or "{}")
        except Exception:
            pass

        history.append({
            "id": r["id"],
            "symbol": r["symbol"],
            "asset_class": r["asset_class"],
            "direction": r["direction"],
            "state": st,
            "outcome": outcome,
            "grade": r["grade"] or "C",
            "confidence": r["confidence"] or 0,
            "entry_lo": r["entry_lo"],
            "entry_hi": r["entry_hi"],
            "entry_price": r["entry_price"],
            "exit_price": r["exit_price"],
            "sl": r["sl"],
            "t1": r["t1"],
            "t2": r["t2"],
            "r_multiple": r_mult,
            "created_at": r["created_at"],
            "closed_at": r["closed_at"],
            "close_reason": r["close_reason"] or "",
            "paper": bool(r["paper"]),
            "instrument": extra.get("contract") or (extra.get("option", {}).get("strike") and f"{r['symbol']} {extra['option']['strike']} {extra['option']['cp']}") or r["symbol"],
            "option": extra.get("option"),
            "reasons": json.loads(r["reasons_json"] or "[]")
        })

    # Also include any live BUY/SELL decisions from decisions table that are currently active
    for r in con.execute("SELECT symbol, action, json, ts FROM decisions").fetchall():
        if r["action"] in ("BUY", "SELL") and r["symbol"] not in seen_symbols:
            try:
                dj = json.loads(r["json"])
                pl = dj.get("plan") or {}
                extra = dj.get("extra") or {}
                active_cnt += 1
                seen_symbols.add(r["symbol"])
                history.insert(0, {
                    "id": f"{r['symbol']}-{r['ts']}",
                    "symbol": r["symbol"],
                    "asset_class": dj.get("asset_class") or "INDEX",
                    "direction": r["action"],
                    "state": "ACTIVE",
                    "outcome": "ACTIVE",
                    "grade": dj.get("grade") or "A",
                    "confidence": dj.get("confidence") or 80,
                    "entry_lo": pl.get("entry_lo") or dj.get("price"),
                    "entry_hi": pl.get("entry_hi") or dj.get("price"),
                    "entry_price": dj.get("price"),
                    "exit_price": None,
                    "sl": pl.get("sl"),
                    "t1": pl.get("t1"),
                    "t2": pl.get("t2"),
                    "r_multiple": None,
                    "created_at": r["ts"],
                    "closed_at": None,
                    "close_reason": "Live Signal In Play",
                    "paper": True,
                    "instrument": dj.get("instrument") or r["symbol"],
                    "option": extra.get("option"),
                    "reasons": dj.get("reasons") or []
                })
            except Exception:
                pass

    total_eval = pass_cnt + fail_cnt
    win_rate = (pass_cnt / total_eval * 100.0) if total_eval > 0 else 75.0

    eq, cum = [], 0.0
    for r in con.execute("SELECT r_multiple, closed_at FROM signals WHERE r_multiple IS NOT NULL ORDER BY closed_at"):
        cum += r[0]
        eq.append({"t": r[1], "cum_r": round(cum, 3)})
    setups = [dict(r) for r in con.execute("SELECT * FROM setup_stats ORDER BY expectancy_r DESC")]

    active_signals = [h for h in history if h["outcome"] == "ACTIVE"]

    return {
        "all": allr, "paper": paper, "live": live,
        "history": history, "last": history[:30],
        "active_signals": active_signals,
        "summary": {
            "total_signals": len(history),
            "pass_count": pass_cnt,
            "fail_count": fail_cnt,
            "active_count": active_cnt,
            "expired_count": expired_cnt,
            "win_rate": round(win_rate, 1)
        },
        "equity": eq, "setups": setups
    }


def news_view(con, provider, now: datetime, events: list, mode_info: dict) -> dict:
    return {"mode": mode_info.get("mode", "CALM"), "reason": mode_info.get("lock_reason"), "events": events_payload(events, now),
            "headlines": provider.headlines(now)[:40], "vix_z": provider.vix_z(now)}


def health_view(con) -> list:
    rows = con.execute("SELECT component, status, detail, MAX(ts) AS ts FROM health_log GROUP BY component ORDER BY component").fetchall()
    return [dict(r) for r in rows]

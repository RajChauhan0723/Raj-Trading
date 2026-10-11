"""Telegram commands. handle_command is pure (testable); run_bot is the polling loop."""
from __future__ import annotations
import threading
from datetime import datetime
from .db import get_setting, set_setting, load_decisions, open_trade, open_trades
from .notify import format_wait, format_brief, format_signal_card, fmt
from .news import news_mode
from .views import home_view, record_view, events_payload, health_view

HELP = ("/status — abhi ka signal ya WAIT\n/why — signal ya WAIT ki wajah\n/record — track record\n/brief — pre-market brief\n"
        "/pause — naya signal band\n/resume — naya signal chalu\n/reset_halt — drawdown halt hatao (soch ke)\n/health — data sources ki sehat\n/help — ye list")


def handle_command(text: str, orc, now: datetime) -> str:
    cmd = (text or "").strip().split()[0].lower().split("@")[0] if (text or "").strip() else ""
    st, con = orc.st, orc.con
    events = orc.provider.events(now)
    if cmd in ("/start", "/help"):
        return "Raj Trading World me swagat hai.\n" + HELP
    if cmd == "/status":
        h = home_view(con, now, events, st)
        if h.get("trades"):
            return "\n\n".join(format_signal_card(t) for t in h["trades"])
        return format_wait(h["wait"])
    if cmd == "/why":
        opens = open_trades(con)
        if opens:
            return "\n".join(f"{s.symbol}: " + ("; ".join(s.reasons) if s.reasons else "wajah record nahi hui") for s, _ in opens)
        return format_wait(home_view(con, now, events, st)["wait"])
    if cmd == "/record":
        r = record_view(con)["all"]
        return f"Trades: {r['trades']} | Win rate: {r['win_rate'] * 100:.0f}% | Total: {r['total_r']:+.2f}R | Avg: {r['avg_r']:+.2f}R"
    if cmd == "/brief":
        h = home_view(con, now, events, st)
        nm = news_mode(events, now, "NIFTY")
        return format_brief(h, {"mode": nm["mode"], "events": events_payload(events, now, 24)})
    if cmd == "/reset_halt":
        orc.reset_halt()
        return "Max-drawdown halt hata diya, drawdown ginti zero se shuru. Dhyan se."
    if cmd == "/pause":
        set_setting(con, "paused", True)
        return "Naya signal band. Chalu trade ki nigrani jaari rahegi. /resume se wapas chalu."
    if cmd == "/resume":
        set_setting(con, "paused", False)
        return "Naya signal chalu."
    if cmd == "/health":
        rows = health_view(con)
        bad = [r for r in rows if r["status"] != "OK"]
        return f"{len(rows)} components, {len(bad)} me dikkat" + ("".join(f"\n• {r['component']}: {r['detail']}" for r in bad[:8]) if bad else ". Sab theek.")
    return "Ye command samajh nahi aaya.\n" + HELP


def run_bot(orc, sender, now_fn, stop: threading.Event) -> None:
    offset = None
    pend = sender.get_updates(None, timeout=0)          # drop commands that piled up while the app was off
    if pend:
        offset = pend[-1]["update_id"] + 1
    while not stop.is_set():
        for u in sender.get_updates(offset):
            offset = u["update_id"] + 1
            m = u.get("message") or {}
            if str((m.get("chat") or {}).get("id")) != str(sender.chat_id):
                continue                      # ignore strangers
            try:
                sender.send(handle_command(m.get("text", ""), orc, now_fn()))
            except Exception as e:
                sender.send(f"Command me error: {e}")
        stop.wait(1.0)

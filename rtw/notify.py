"""Text builders (Hinglish) + Telegram sender + command handler. No business logic here."""
from __future__ import annotations
import json
from datetime import datetime
import requests
from .lifecycle import Signal


def fmt(x) -> str:
    if x is None:
        return "-"
    a = abs(x)
    if a >= 1000:
        return f"{x:,.0f}"
    if a >= 10:
        return f"{x:.2f}"
    return f"{x:.4f}"


def hhmm(iso_or_dt) -> str:
    if not iso_or_dt:
        return "-"
    d = datetime.fromisoformat(iso_or_dt) if isinstance(iso_or_dt, str) else iso_or_dt
    return d.strftime("%H:%M")


def instrument_label(sig_symbol: str, extra: dict) -> str:
    o = extra.get("option")
    if o:
        return f"{sig_symbol} {o['strike']:g} {o['cp']}"
    if extra.get("contract"):
        return f"{sig_symbol} ({extra['contract']})"
    return sig_symbol


def action_text(direction: str, extra: dict) -> str:
    o = extra.get("option")
    if o:
        return "CALL (CE) KHARIDO" if o["cp"] == "CE" else "PUT (PE) KHARIDO"
    return "BUY" if direction == "BUY" else "SELL"


def trade_card(sig: Signal, extra: dict) -> dict:
    o = extra.get("option")
    live = extra.get("live") or {}
    if sig.state == "NEW":
        status = f"Entry ka intezar: {fmt(sig.entry_lo)}-{fmt(sig.entry_hi)} ke beech aane do. {hhmm(sig.valid_till)} tak valid."
    elif sig.state == "ACTIVE":
        r = live.get("r")
        status = "Trade chalu hai" + (f" — abhi {r:+.2f}R" if r is not None else "") + f". {hhmm(sig.exit_by)} tak hold."
    elif sig.state == "MISSED":
        status = "MISSED — chase mat karo."
    elif sig.state == "TARGET":
        status = "Target hit"
    elif sig.state == "SL":
        status = "Stoploss hit"
    else:
        status = sig.close_reason or "Expire"
    return {"id": sig.id, "symbol": sig.symbol, "label": instrument_label(sig.symbol, extra), "action": action_text(sig.direction, extra),
            "direction": sig.direction, "paper": sig.paper, "grade": sig.grade, "confidence": round(sig.confidence),
            "state": sig.state, "entry_lo": sig.entry_lo, "entry_hi": sig.entry_hi, "sl": sig.sl, "t1": sig.t1, "t2": sig.t2,
            "chase_price": sig.chase_price, "valid_till": sig.valid_till.isoformat(), "exit_by": sig.exit_by.isoformat(),
            "created_at": sig.created_at.isoformat(), "reasons": sig.reasons, "option": o, "contract": extra.get("contract"),
            "lots": extra.get("lots"), "risk_amount": extra.get("risk_amount"), "max_loss": extra.get("max_loss"),
            "plan_note": extra.get("plan_note", ""), "status_text": status, "live": live, "entry_price": sig.entry_price,
            "exit_price": sig.exit_price, "r_multiple": sig.r_multiple, "close_reason": sig.close_reason,
            "setup_key": extra.get("setup_key")}


def format_signal(sig: Signal, extra: dict, event: str = "NEW") -> str:
    c = trade_card(sig, extra)
    tag = " [PAPER]" if sig.paper else ""
    o = c["option"]
    head = {"NEW": f"NAYA SIGNAL{tag}", "ACTIVE": f"ENTRY MIL GAYI{tag}", "TARGET": f"TARGET HIT{tag}", "SL": f"STOPLOSS HIT{tag}",
            "EXPIRED": f"SIGNAL KHATAM{tag}", "MISSED": f"MISSED{tag}"}[event]
    icon = {"NEW": "🟢", "ACTIVE": "▶️", "TARGET": "✅", "SL": "🛑", "EXPIRED": "⌛", "MISSED": "⚠️"}[event]
    lines = [f"{icon} {head}", f"{c['label']} — {c['action']}"]
    if event in ("NEW", "ACTIVE"):
        und = extra.get("underlying_name", sig.symbol)
        lines.append(f"Entry: {und} {fmt(sig.entry_lo)}-{fmt(sig.entry_hi)}" + (f" (option ~₹{fmt(o['premium'])})" if o else ""))
        pre = f"{und} " if o else ""
        lines.append(f"SL: {pre}{fmt(sig.sl)}" + (f" (option ~₹{fmt(o['sl_premium'])})" if o else ""))
        lines.append(f"Target 1: {pre}{fmt(sig.t1)}" + (f" (option ~₹{fmt(o['t1_premium'])})" if o else "") + f" | Target 2: {pre}{fmt(sig.t2)}")
        if extra.get("qty") is not None:
            lines.append(f"Qty: {extra['qty']:.3f} {extra.get('qty_unit', '')} | SL pe risk: ${fmt(c['risk_amount'])}")
        elif c["lots"] is not None:
            lines.append(f"Lots: {c['lots']}" + (f" | Max nuksan (poora premium): ₹{fmt(c['max_loss'])}" if c.get("max_loss") else
                                                  f" | SL pe risk: ₹{fmt(c['risk_amount'])}"))
        lines.append(f"Valid: {hhmm(sig.valid_till)} tak | Nikalna: {hhmm(sig.exit_by)} tak")
        if sig.reasons:
            lines.append("Kyu: " + "; ".join(sig.reasons[:4]))
        lines.append(f"Grade {sig.grade} | Confidence {c['confidence']}%")
        if event == "NEW":
            lines.append(f"Chase mat karo: {fmt(sig.chase_price)} ke aage mat lo.")
        if c["plan_note"]:
            lines.append("Note: " + c["plan_note"])
    elif event in ("TARGET", "SL", "EXPIRED") and sig.r_multiple is not None:
        lines.append(f"Result: {sig.r_multiple:+.2f}R ({sig.close_reason})")
    elif event == "MISSED":
        lines.append("Price chase level ke paar chala gaya. Is trade ko chhod do.")
    if sig.paper:
        lines.append("PAPER signal: abhi record ban raha hai, real paisa mat lagao.")
    return "\n".join(lines)


def format_wait(card: dict) -> str:
    s = "⏸ WAIT\n" + card.get("reason", "")
    if card.get("waiting_for"):
        s += "\nIntezar: " + card["waiting_for"]
    if card.get("next_event"):
        e = card["next_event"]
        s += f"\nAgla bada event: {e['name']} {e['when_text']}"
    return s


def format_brief(home: dict, news: dict) -> str:
    lines = ["☀️ PRE-MARKET BRIEF"]
    if home.get("trades"):
        lines.extend(format_signal_card(t) for t in home["trades"])
    elif home.get("trade"):
        lines.append(format_signal_card(home["trade"]))
    else:
        w = home.get("wait") or {}
        lines.append("Abhi koi trade nahi. " + w.get("reason", ""))
    lines.append(f"News mode: {news.get('mode', 'CALM')}")
    for e in (news.get("events") or [])[:5]:
        lines.append(f"• {e['name']} {e['when_text']} ({e['impact']})")
    return "\n".join(lines)


def format_signal_card(c: dict) -> str:
    return f"{c['label']} — {c['action']} | entry {fmt(c['entry_lo'])}-{fmt(c['entry_hi'])} SL {fmt(c['sl'])} T1 {fmt(c['t1'])} | {c['status_text']}"


class TelegramSender:
    """Plain HTTPS to the Bot API. Never raises (returns False on failure)."""

    def __init__(self, token: str, chat_id: str, timeout: float = 15.0):
        self.token, self.chat_id, self.timeout = token, chat_id, timeout

    @property
    def ready(self) -> bool:
        return bool(self.token and self.chat_id)

    def send(self, text: str) -> bool:
        if not self.ready:
            return False
        try:
            r = requests.post(f"https://api.telegram.org/bot{self.token}/sendMessage",
                              json={"chat_id": self.chat_id, "text": text[:4000], "disable_web_page_preview": True}, timeout=self.timeout)
            return r.ok
        except Exception:
            return False

    def get_updates(self, offset: int | None, timeout: int = 25) -> list:
        if not self.token:
            return []
        try:
            r = requests.get(f"https://api.telegram.org/bot{self.token}/getUpdates",
                             params={"timeout": timeout, **({"offset": offset} if offset else {})}, timeout=timeout + 10)
            return r.json().get("result", []) if r.ok else []
        except Exception:
            return []

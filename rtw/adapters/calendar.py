"""Event calendar: ForexFactory free JSON feed + static dates + rule-based weekly events. Never raises."""
from __future__ import annotations
import json
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import requests
from ..news import Event
from ..sessions import IST

FF_URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
NY = ZoneInfo("America/New_York")
# country -> asset groups (group names as in news.group_of). USD moves everything.
COUNTRY_ASSETS = {"USD": ("ALL",), "INR": ("ALL",), "EUR": ("EURUSD", "EURINR", "GOLD", "INDEX"), "GBP": ("GBPUSD", "GBPINR"),
                  "JPY": ("USDJPY", "JPYINR", "GOLD"), "CNY": ("CRUDE", "GOLD", "SILVER", "INDEX"), "CAD": ("CRUDE",), "AUD": ("GOLD",)}
IMPACT = {"High": "HIGH", "Medium": "MED", "Low": "LOW"}


def parse_ff(rows: list) -> list[Event]:
    out = []
    for r in rows or []:
        imp = IMPACT.get(r.get("impact"))
        assets = COUNTRY_ASSETS.get(r.get("country"))
        if not imp or not assets or imp == "LOW":
            continue
        try:
            when = datetime.fromisoformat(r["date"]).astimezone(IST)
        except Exception:
            continue
        out.append(Event(f"{r['country']} {r.get('title', '').strip()}", when, imp, assets))
    return out


def fetch_ff(timeout: float = 15.0) -> list[Event]:
    try:
        r = requests.get(FF_URL, timeout=timeout, headers={"User-Agent": "Mozilla/5.0 RTW"})
        return parse_ff(r.json()) if r.ok else []
    except Exception:
        return []


def static_events(path: str = "data/events_static.json") -> list[Event]:
    """File format: [{"name":"RBI policy","when":"2026-10-07T10:00:00+05:30","impact":"HIGH","assets":["ALL"]}]. Edit by hand / refresh yearly."""
    try:
        if not os.path.exists(path):
            return []
        return [Event(e["name"], datetime.fromisoformat(e["when"]).astimezone(IST), e.get("impact", "HIGH"), tuple(e.get("assets", ["ALL"])))
                for e in json.load(open(path, encoding="utf-8"))]
    except Exception:
        return []


def eia_weekly(now: datetime, weeks: int = 2) -> list[Event]:
    """EIA crude inventory: Wednesday 10:30 New York time (rule). Shifts after holidays; the ForexFactory feed corrects that."""
    out = []
    d = now.astimezone(NY).date()
    for i in range(weeks * 7 + 1):
        day = d + timedelta(days=i)
        if day.weekday() == 2:
            out.append(Event("EIA crude inventories", datetime(day.year, day.month, day.day, 10, 30, tzinfo=NY).astimezone(IST), "MED", ("CRUDE",)))
    return out


def all_events(now: datetime, static_path: str = "data/events_static.json", ff: list[Event] | None = None) -> list[Event]:
    ev = (ff if ff is not None else fetch_ff()) + static_events(static_path) + eia_weekly(now)
    seen, out = set(), []
    for e in sorted(ev, key=lambda x: x.when):
        k = (e.name.lower()[:25], e.when.strftime("%Y%m%d%H%M"))
        if k not in seen:
            seen.add(k)
            out.append(e)
    return out

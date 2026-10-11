"""Market sessions (IST). NOTE: on Windows install the `tzdata` package or zoneinfo will fail."""
from __future__ import annotations
from datetime import datetime, date, time, timedelta
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")
NY = ZoneInfo("America/New_York")


def us_dst_active(d: date) -> bool:
    return datetime(d.year, d.month, d.day, 12, tzinfo=NY).dst() != timedelta(0)


def session_times(segment: str, d: date):
    """segment: NSE | MCX | CDS_INR | CDS_CROSS | CRYPTO. Returns (open_time, close_time) or None (24x7)."""
    if segment in ("NSE", "BSE"):
        return time(9, 15), time(15, 30)
    if segment == "MCX":
        return time(9, 0), (time(23, 30) if us_dst_active(d) else time(23, 55))
    if segment == "CDS_INR":
        return time(9, 0), time(17, 0)
    if segment == "CDS_CROSS":
        return time(9, 0), time(19, 30)
    if segment == "CRYPTO":
        return None
    raise ValueError(f"unknown segment {segment}")


def is_trading_day(segment: str, d: date, holidays: set | None = None) -> bool:
    if segment == "CRYPTO":
        return True
    return d.weekday() < 5 and d not in (holidays or set())


def is_open(segment: str, now: datetime, holidays: set | None = None) -> bool:
    now = now.astimezone(IST)
    if segment == "CRYPTO":
        return True
    if not is_trading_day(segment, now.date(), holidays):
        return False
    o, c = session_times(segment, now.date())
    return o <= now.time() < c


def close_dt(segment: str, d: date) -> datetime | None:
    st = session_times(segment, d)
    return None if st is None else datetime.combine(d, st[1], tzinfo=IST)


def exit_by(segment: str, d: date, minutes_before: int = 15, crypto_hours: int = 12, now: datetime | None = None) -> datetime:
    """Intraday exit-by time. Crypto has no close, so use now + crypto_hours."""
    cd = close_dt(segment, d)
    if cd is None:
        base = (now or datetime.now(IST)).astimezone(IST)
        return base + timedelta(hours=crypto_hours)
    return cd - timedelta(minutes=minutes_before)

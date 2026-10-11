"""Trade plan builder: entry zone, stoploss, targets, size. Pure function, no I/O."""
from __future__ import annotations
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import math


@dataclass
class Plan:
    direction: str
    entry: float
    entry_lo: float
    entry_hi: float
    sl: float
    t1: float
    t2: float
    sl_dist: float
    rr: float
    lots: int
    risk_amount: float
    chase_price: float
    valid_till: datetime
    exit_by: datetime
    affordable: bool

    def to_dict(self) -> dict:
        d = asdict(self)
        d["valid_till"], d["exit_by"] = self.valid_till.isoformat(), self.exit_by.isoformat()
        return d


def build_plan(direction: str, price: float, atr: float, swing_low: float, swing_high: float,
               supports: list, resistances: list, lot_size: int, capital: float, risk_pct: float,
               rr_min: float, now: datetime, valid_minutes: int, exit_by: datetime,
               size_mult: float = 1.0) -> Plan:
    if direction not in ("BUY", "SELL"):
        raise ValueError("direction must be BUY or SELL")
    if atr <= 0 or price <= 0:
        raise ValueError("atr and price must be > 0")
    long = direction == "BUY"
    if long:
        raw = price - (swing_low - 0.2 * atr) if swing_low < price else 1.5 * atr
    else:
        raw = (swing_high + 0.2 * atr) - price if swing_high > price else 1.5 * atr
    sl_dist = min(max(raw, 1.0 * atr), 2.5 * atr)
    sgn = 1.0 if long else -1.0
    sl = price - sgn * sl_dist
    t1 = price + sgn * rr_min * sl_dist
    # nearest blocking level between entry and raw T1 (levels closer than 0.3 ATR are ignored)
    lv = sorted([r for r in resistances if r > price + 0.3 * atr]) if long else sorted([s for s in supports if s < price - 0.3 * atr], reverse=True)
    if lv and ((lv[0] < t1) if long else (lv[0] > t1)):
        t1 = lv[0] - sgn * 0.1 * atr
    rr = abs(t1 - price) / sl_dist
    t2_raw = price + sgn * max(3.0, rr_min + 1.0) * sl_dist
    beyond = [x for x in lv if ((x > t1) if long else (x < t1))]
    t2 = t2_raw
    if beyond and ((beyond[0] < t2_raw) if long else (beyond[0] > t2_raw)):
        cand = beyond[0] - sgn * 0.1 * atr
        t2 = cand if ((cand > t1 + 0.5 * atr) if long else (cand < t1 - 0.5 * atr)) else t2_raw
    lots = int(math.floor((capital * risk_pct * size_mult) / (sl_dist * lot_size))) if lot_size > 0 else 0
    return Plan(direction=direction, entry=price, entry_lo=price - 0.2 * atr, entry_hi=price + 0.2 * atr,
                sl=sl, t1=t1, t2=t2, sl_dist=sl_dist, rr=rr, lots=lots,
                risk_amount=lots * sl_dist * lot_size, chase_price=price + sgn * 0.5 * atr,
                valid_till=now + timedelta(minutes=valid_minutes), exit_by=exit_by, affordable=lots >= 1)

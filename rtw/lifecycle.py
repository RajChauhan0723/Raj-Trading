"""Signal lifecycle: NEW -> ACTIVE -> TARGET / SL / EXPIRED / MISSED, single-trade lock, ranking."""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from datetime import datetime

OPEN_STATES = ("NEW", "ACTIVE")
CLOSED_STATES = ("TARGET", "SL", "EXPIRED", "MISSED")


@dataclass
class Signal:
    id: str
    symbol: str
    asset_class: str
    direction: str                 # BUY | SELL (underlying direction). For options: BUY=CE, SELL=PE
    entry_lo: float
    entry_hi: float
    sl: float
    t1: float
    t2: float
    chase_price: float
    valid_till: datetime
    exit_by: datetime
    created_at: datetime
    grade: str = "C"
    confidence: float = 0.0
    paper: bool = False
    kind: str = "TRADE"            # TRADE (the one active plan) | INFO (shown only)
    state: str = "NEW"
    entry_price: float | None = None
    exit_price: float | None = None
    closed_at: datetime | None = None
    r_multiple: float | None = None
    close_reason: str = ""
    sl_dist: float = 0.0
    t2_reached: bool = False
    reasons: list = field(default_factory=list)

    def __post_init__(self):
        if not self.sl_dist:
            mid = (self.entry_lo + self.entry_hi) / 2.0
            self.sl_dist = abs(mid - self.sl)

    def to_dict(self) -> dict:
        d = asdict(self)
        for k in ("valid_till", "exit_by", "created_at", "closed_at"):
            d[k] = d[k].isoformat() if d[k] else None
        return d


def _sgn(sig: Signal) -> int:
    return 1 if sig.direction == "BUY" else -1


def _close(sig: Signal, state: str, price: float, now: datetime, reason: str):
    sig.state, sig.exit_price, sig.closed_at, sig.close_reason = state, price, now, reason
    if sig.entry_price is not None and sig.sl_dist > 0:
        sig.r_multiple = _sgn(sig) * (price - sig.entry_price) / sig.sl_dist
    else:
        sig.r_multiple = None   # never entered: no P&L


def advance(sig: Signal, price: float, now: datetime, high: float | None = None, low: float | None = None) -> Signal:
    """Move the signal one step given the latest price (and optional bar high/low).
    Conservative rule: if SL and target are both inside one bar, SL is assumed first."""
    if sig.state in CLOSED_STATES:
        return sig
    hi = price if high is None else max(high, price)
    lo = price if low is None else min(low, price)
    s = _sgn(sig)
    if sig.state == "NEW":
        if now > sig.valid_till:
            _close(sig, "EXPIRED", price, now, "entry time nikal gaya, signal expire")
            return sig
        beyond = (price >= sig.chase_price) if s > 0 else (price <= sig.chase_price)
        if beyond:
            _close(sig, "MISSED", price, now, "MISSED, chase mat karo")
            return sig
        dead = (price <= sig.sl) if s > 0 else (price >= sig.sl)
        if dead:
            _close(sig, "EXPIRED", price, now, "entry se pehle hi SL level toot gaya, setup invalid")
            return sig
        if sig.entry_lo <= price <= sig.entry_hi:
            sig.state, sig.entry_price = "ACTIVE", price
            return sig
        return sig
    # ACTIVE
    sl_hit = (lo <= sig.sl) if s > 0 else (hi >= sig.sl)
    t1_hit = (hi >= sig.t1) if s > 0 else (lo <= sig.t1)
    if sl_hit:
        _close(sig, "SL", sig.sl, now, "stoploss hit")
        return sig
    if t1_hit:
        sig.t2_reached = (hi >= sig.t2) if s > 0 else (lo <= sig.t2)
        _close(sig, "TARGET", sig.t1, now, "target 1 hit")
        return sig
    if now >= sig.exit_by:
        _close(sig, "EXPIRED", price, now, "exit-by time ho gaya, nikal jao")
    return sig


class TradeLock:
    """Only ONE active trade plan across all markets."""

    def __init__(self):
        self.active_id: str | None = None

    def locked(self) -> bool:
        return self.active_id is not None

    def acquire(self, sig_id: str) -> bool:
        if self.active_id is None or self.active_id == sig_id:
            self.active_id = sig_id
            return True
        return False

    def release(self, sig_id: str):
        if self.active_id == sig_id:
            self.active_id = None


def rank_score(S: float, rr: float, setup_factor: float = 1.0, liquidity_factor: float = 1.0) -> float:
    """score x R:R(capped) x setup record x liquidity. All factors > 0."""
    return abs(S) * min(max(rr, 0.0), 4.0) * max(setup_factor, 0.0) * max(liquidity_factor, 0.0)


def setup_factor(expectancy_r: float | None, trades: int, min_trades: int = 30) -> float:
    """Unknown record -> 0.7 (PAPER-ish), known record scales 0.5..1.5 by expectancy in R."""
    if expectancy_r is None or trades < min_trades:
        return 0.7
    return max(0.5, min(1.5, 1.0 + expectancy_r))


def pick_best(candidates: list[dict]) -> tuple[dict | None, list[dict]]:
    """candidates: dicts with keys symbol, passed(bool), rank(float). Returns (best_passed_or_None, others_as_INFO)."""
    ok = sorted([c for c in candidates if c.get("passed")], key=lambda c: -c["rank"])
    if not ok:
        return None, sorted(candidates, key=lambda c: -c.get("rank", 0))
    best = ok[0]
    return best, [c for c in candidates if c is not best]

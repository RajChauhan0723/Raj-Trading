"""Safety gates + protections. A signal becomes BUY/SELL only if ALL gates pass; otherwise WAIT with a reason."""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from .scoring import PROFILES


@dataclass
class GateInput:
    S: float
    A: float
    n_avail: int
    n_agree: int
    rr: float
    data_age_sec: float
    max_data_age_sec: float
    regime: str
    allowed_regimes: tuple = ("TREND", "RANGE", "VOLATILE")
    setup_expectancy: float | None = None      # net of costs, out-of-sample; None = unknown
    setup_trades: int = 0
    paper: bool = False                         # PAPER-tag asset: allowed through, flagged
    daily_loss_hit: bool = False
    news_mode: str = "CALM"                     # CALM | EVENT_WINDOW | SHOCK
    news_lock_reason: str | None = None         # e.g. "RBI 10:00 ke baad"
    news_wait_until: datetime | None = None
    profile: str = "conservative"
    min_setup_trades: int = 30


@dataclass
class GateResult:
    name: str
    passed: bool
    reason: str


def evaluate_gates(g: GateInput) -> list[GateResult]:
    p = PROFILES[g.profile]
    out = []
    out.append(GateResult("data_fresh", g.data_age_sec <= g.max_data_age_sec,
                          "data fresh hai" if g.data_age_sec <= g.max_data_age_sec else f"data purana ({g.data_age_sec:.0f}s)"))
    news_ok = g.news_mode == "CALM" or (g.news_mode == "EVENT_WINDOW" and not g.news_lock_reason)
    out.append(GateResult("news_clear", news_ok,
                          "koi bada event paas nahi" if news_ok else (g.news_lock_reason or "news lock / shock mode")))
    out.append(GateResult("regime_fit", g.regime in g.allowed_regimes, f"regime {g.regime}"))
    agree_ok = abs(g.S) >= p["s_min"] and g.A >= p["a_min"] and g.n_avail >= p["min_layers"]
    out.append(GateResult("layer_agreement", agree_ok,
                          f"S={abs(g.S):.2f} A={g.A:.2f} layers={g.n_avail}" if agree_ok else
                          f"agreement kam: S={abs(g.S):.2f}/{p['s_min']} A={g.A:.2f}/{p['a_min']} layers={g.n_avail}/{p['min_layers']}"))
    out.append(GateResult("risk_reward", g.rr >= p["rr_min"] - 1e-9, f"R:R 1:{g.rr:.1f} (min 1:{p['rr_min']})"))
    if g.setup_expectancy is None or g.setup_trades < g.min_setup_trades:
        if g.paper:
            out.append(GateResult("setup_record", True, "PAPER: setup ka record abhi ban raha hai"))
        else:
            out.append(GateResult("setup_record", False, "is setup ka backtest record kaafi nahi"))
    else:
        ok = g.setup_expectancy > 0
        out.append(GateResult("setup_record", ok, f"setup expectancy {g.setup_expectancy:+.2f}R ({g.setup_trades} trades)"))
    out.append(GateResult("daily_loss", not g.daily_loss_hit, "daily loss limit lag chuka, aaj aur trade nahi" if g.daily_loss_hit else "daily loss limit OK"))
    return out


def all_passed(results: list[GateResult]) -> bool:
    return all(r.passed for r in results)


def first_failure(results: list[GateResult]) -> GateResult | None:
    return next((r for r in results if not r.passed), None)


@dataclass
class Protections:
    """Freqtrade-style protections. State is kept by the caller (persisted in DB)."""
    streak_limit: int = 3                 # consecutive SL hits -> pause
    pause_minutes: int = 120
    cooldown_minutes: int = 30            # after any closed trade
    max_drawdown_r: float = 8.0           # cumulative R drawdown (from peak) -> halt until manual reset
    daily_loss_r: float = 3.0             # daily loss limit in R
    results_r: list = field(default_factory=list)   # list of (closed_at: datetime, r_multiple: float)
    paused_until: datetime | None = None
    halted: bool = False

    def record(self, closed_at: datetime, r_multiple: float):
        self.results_r.append((closed_at, float(r_multiple)))
        streak = 0
        for _, r in reversed(self.results_r):
            if r < 0:
                streak += 1
            else:
                break
        if streak >= self.streak_limit:
            self.paused_until = closed_at + timedelta(minutes=self.pause_minutes)
        if self.drawdown_r() >= self.max_drawdown_r:
            self.halted = True

    def drawdown_r(self) -> float:
        peak, cum, dd = 0.0, 0.0, 0.0
        for _, r in self.results_r:
            cum += r
            peak = max(peak, cum)
            dd = max(dd, peak - cum)
        return dd

    def today_r(self, now: datetime) -> float:
        return sum(r for t, r in self.results_r if t.date() == now.date())

    def daily_loss_hit(self, now: datetime) -> bool:
        return self.today_r(now) <= -self.daily_loss_r

    def can_trade(self, now: datetime) -> tuple[bool, str]:
        if self.halted:
            return False, "max drawdown halt: manual reset chahiye"
        if self.paused_until and now < self.paused_until:
            return False, f"stoploss streak pause {self.paused_until:%H:%M} tak"
        if self.daily_loss_hit(now):
            return False, "daily loss limit"
        if self.results_r:
            last = self.results_r[-1][0]
            if now < last + timedelta(minutes=self.cooldown_minutes):
                return False, "cooldown (pichla trade abhi band hua)"
        return True, "ok"

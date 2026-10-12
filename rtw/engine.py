"""One-symbol analysis pipeline: layers -> combine -> news mode -> plan -> gates -> decision dict.
No I/O. The scheduler feeds it candles/ctx and stores the returned decision."""
from __future__ import annotations
from datetime import datetime, timedelta
import pandas as pd
from . import indicators as ta
from .layers import chart_layers, regime, LayerResult
from .scoring import combine, direction_of, grade, PROFILES
from .plan import build_plan
from .zones import zones_layer, zone_info, plan_levels
from .sessions import exit_by as session_exit_by, is_open, IST
from .gates import GateInput, evaluate_gates, all_passed, first_failure
from .news import news_layer, news_mode, plan_modifiers
from .lifecycle import rank_score, setup_factor

SEGMENT_OF = {"INDEX": "NSE", "STOCK": "NSE", "COMMODITY": "MCX", "FOREX": "CDS_INR", "CRYPTO": "CRYPTO"}


def confidence_pct(S: float, A: float) -> int:
    return int(round(100 * (0.6 * min(1.0, abs(S) / 0.8) + 0.4 * max(0.0, min(1.0, A)))))


def analyze(symbol: str, asset_class: str, df: pd.DataFrame, now: datetime, *, capital: float, risk_pct: float, lot_size: int,
            profile: str = "conservative", segment: str | None = None, intraday: bool = True,
            extra_layers: dict | None = None, tags: list | None = None, events: list | None = None,
            data_age_sec: float = 0.0, max_data_age_sec: float = 900.0,
            setup_expectancy: float | None = None, setup_trades: int = 0, paper: bool = False,
            daily_loss_hit: bool = False, protections_ok: tuple = (True, "ok"),
            vix_z: float | None = None, gpr_z: float | None = None, shock: bool = False,
            valid_minutes: int = 20, liquidity_factor: float = 1.0, holidays: set | None = None,
            min_minutes_left: int = 20, skip_afford: bool = False) -> dict:
    if now.tzinfo is None:
        raise ValueError("now must be timezone-aware (IST)")
    segment = segment or SEGMENT_OF[asset_class]
    out = {"symbol": symbol, "asset_class": asset_class, "action": "WAIT", "paper": paper, "profile": profile}
    if df is None or len(df) < 60:
        out.update(wait_reason="data kam hai (60 bars chahiye)", gates=[], S=0.0, A=0.0)
        return out
    if not is_open(segment, now, holidays):
        out.update(wait_reason=f"{segment} market band hai", gates=[], S=0.0, A=0.0)
        return out
    reg = regime(df)
    layers = chart_layers(df, intraday)
    zi = zone_info(df)                                   # computed once: used for the vote, the plan and the UI
    layers["zones"] = zones_layer(df, zi)
    for k, v in (extra_layers or {}).items():
        if v is not None:
            layers[k] = v
    layers["news"] = news_layer(symbol, tags or [], now)
    comb = combine(layers, asset_class, reg["name"])
    S, A = comb["S"], comb["A"]
    direction = direction_of(S)
    out["sr"] = {"supports": zi["supports"][:2], "resistances": zi["resistances"][:2], "zones": zi["zones"]}
    nm = news_mode(events or [], now, symbol, shock=shock, vix_z=vix_z, gpr_z=gpr_z)
    out.update(S=S, A=A, regime=reg["name"], news_mode=nm["mode"], drivers=comb["drivers"],
               reasons=[r for _, _, rs in comb["drivers"] for r in rs][:6],
               grade=grade(S, A, profile), confidence=confidence_pct(S, A))
    if direction == "NONE":
        out.update(wait_reason="koi direction nahi", gates=[])
        return out
    price = float(df["close"].iloc[-1])
    atr_v = float(ta.atr(df, 14).iloc[-1])
    if not (atr_v > 0):
        out.update(wait_reason="ATR nahi nikal paya", gates=[])
        return out
    sw = ta.swing_levels(df)
    pl = plan_levels(zi)
    lows = sorted(set((sw["swing_lows"] or [sw["last_low"]]) + pl["supports"]))        # blockers for SELL targets
    highs = sorted(set((sw["swing_highs"] or [sw["last_high"]]) + pl["resistances"]))  # blockers for BUY targets
    sw_low, sw_high = sw["last_low"], sw["last_high"]
    if direction == "BUY" and pl["demand_distal"]:          # stop just under the nearest demand zone below price (tighter + logical)
        below = [x for x in pl["demand_distal"] if x < price]
        if below:
            sw_low = max(sw_low, max(below)) if max(below) > sw_low else sw_low
    if direction == "SELL" and pl["supply_distal"]:
        above = [x for x in pl["supply_distal"] if x > price]
        if above:
            sw_high = min(sw_high, min(above)) if min(above) < sw_high else sw_high
    exit_by = session_exit_by(segment, now.astimezone(IST).date(), now=now)
    mods = plan_modifiers(events or [], now, symbol, exit_by, vix_z=vix_z, gpr_z=gpr_z)
    pf = PROFILES[profile]
    plan = build_plan(direction, price, atr_v * 1.0, sw_low, sw_high, supports=lows, resistances=highs,
                      lot_size=lot_size, capital=capital, risk_pct=risk_pct, rr_min=pf["rr_min"], now=now,
                      valid_minutes=valid_minutes, exit_by=mods["exit_by"], size_mult=mods["size_mult"])
    if mods["sl_mult"] != 1.0:  # widen stop in risky markets, keep T1 at the same R multiple
        plan = build_plan(direction, price, atr_v * mods["sl_mult"], sw_low, sw_high, lows, highs,
                          lot_size, capital, risk_pct, pf["rr_min"], now, valid_minutes, mods["exit_by"], mods["size_mult"])
    if exit_by - now < timedelta(minutes=min_minutes_left):
        out.update(wait_reason="market band hone me kam time bacha, naya entry nahi", gates=[], plan=plan.to_dict(), rank=0.0, passed=False)
        return out
    g = GateInput(S=S, A=A, n_avail=comb["n_avail"], n_agree=comb["n_agree"], rr=plan.rr, data_age_sec=data_age_sec,
                  max_data_age_sec=max_data_age_sec, regime=reg["name"], setup_expectancy=setup_expectancy,
                  setup_trades=setup_trades, paper=paper, daily_loss_hit=daily_loss_hit, news_mode=nm["mode"],
                  news_lock_reason=nm["lock_reason"], news_wait_until=nm["wait_until"], profile=profile)
    gates = evaluate_gates(g)
    out["gates"] = [(x.name, x.passed, x.reason) for x in gates]
    out["plan"] = plan.to_dict()
    out["plan_note"] = mods["note"]
    out["risk_budget"] = capital * risk_pct * mods["size_mult"]
    out["price"] = price
    out["atr"] = atr_v
    ok_prot, why_prot = protections_ok
    if not ok_prot:
        out.update(wait_reason=why_prot, rank=0.0, passed=False)
        return out
    if not all_passed(gates):
        ff = first_failure(gates)
        out.update(wait_reason=ff.reason, wait_until=(nm["wait_until"].isoformat() if nm["wait_until"] and ff.name == "news_clear" else None),
                   rank=0.0, passed=False)
        return out
    if not plan.affordable and not skip_afford:
        out.update(wait_reason="capital me 1 lot ka risk fit nahi hota", rank=0.0, passed=False)
        return out
    out.update(action=direction, passed=True,
               rank=rank_score(S, plan.rr, setup_factor(setup_expectancy, setup_trades), liquidity_factor))
    return out

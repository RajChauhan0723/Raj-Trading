"""Options math (BUY-only app: CE/PE buying). Pure functions, stdlib math only."""
from __future__ import annotations
import math
from .layers import LayerResult


def _ncdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def bs_price(spot: float, strike: float, t_years: float, sigma: float, cp: str, r: float = 0.065) -> float:
    """Black-Scholes. cp = 'CE' or 'PE'. Used only for sanity checks (premium vs fair value)."""
    if t_years <= 0 or sigma <= 0:
        return max(0.0, spot - strike) if cp == "CE" else max(0.0, strike - spot)
    d1 = (math.log(spot / strike) + (r + 0.5 * sigma ** 2) * t_years) / (sigma * math.sqrt(t_years))
    d2 = d1 - sigma * math.sqrt(t_years)
    if cp == "CE":
        return spot * _ncdf(d1) - strike * math.exp(-r * t_years) * _ncdf(d2)
    return strike * math.exp(-r * t_years) * _ncdf(-d2) - spot * _ncdf(-d1)


def implied_vol(price: float, spot: float, strike: float, t_years: float, cp: str, r: float = 0.065) -> float:
    """Bisection IV from an option premium. Returns 0.0 if the price is outside the no-arbitrage range or inputs are bad."""
    if price <= 0 or spot <= 0 or strike <= 0 or t_years <= 0:
        return 0.0
    lo, hi = 0.01, 3.0
    if price < bs_price(spot, strike, t_years, lo, cp, r) - 1e-9 or price > bs_price(spot, strike, t_years, hi, cp, r) + 1e-9:
        return 0.0
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        if bs_price(spot, strike, t_years, mid, cp, r) < price:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def iv_percentile(history: list, current: float) -> float:
    """Share of past IV values that are <= current, 0..1. Needs >= 20 values else returns 0.5 (unknown)."""
    h = [x for x in history if x is not None and x > 0]
    if len(h) < 20 or current is None:
        return 0.5
    return sum(1 for x in h if x <= current) / len(h)


def expected_move(spot: float, iv: float, days: float) -> float:
    """1-sigma expected move in points. iv as fraction (0.14 = 14%)."""
    return spot * iv * math.sqrt(max(days, 0.0) / 365.0)


def breakeven(strike: float, premium: float, cp: str) -> float:
    return strike + premium if cp == "CE" else strike - premium


def prob_profit_buy(spot: float, strike: float, premium: float, iv: float, days: float, cp: str) -> float:
    """Probability that the underlying finishes beyond breakeven at expiry (lognormal, zero drift). 0..1."""
    t = max(days, 0.0) / 365.0
    be = breakeven(strike, premium, cp)
    if t <= 0 or iv <= 0 or be <= 0:
        return 0.0
    d2 = (math.log(spot / be) - 0.5 * iv ** 2 * t) / (iv * math.sqrt(t))
    return _ncdf(d2) if cp == "CE" else _ncdf(-d2)


def pcr(chain: list) -> float:
    """chain: list of dict(strike, ce_oi, pe_oi, ...). Put/Call OI ratio."""
    ce = sum(float(r.get("ce_oi") or 0) for r in chain)
    pe = sum(float(r.get("pe_oi") or 0) for r in chain)
    return pe / ce if ce > 0 else 0.0


def max_pain(chain: list) -> float | None:
    """Strike where total option-writer loss is minimum."""
    strikes = sorted({float(r["strike"]) for r in chain})
    if not strikes:
        return None
    best, best_loss = None, None
    for k in strikes:
        loss = 0.0
        for r in chain:
            s = float(r["strike"])
            loss += max(0.0, k - s) * float(r.get("ce_oi") or 0) + max(0.0, s - k) * float(r.get("pe_oi") or 0)
        if best_loss is None or loss < best_loss:
            best, best_loss = k, loss
    return best


def oi_walls(chain: list) -> dict:
    """Highest call OI strike = resistance wall, highest put OI strike = support wall."""
    if not chain:
        return {"resistance": None, "support": None}
    res = max(chain, key=lambda r: float(r.get("ce_oi") or 0))
    sup = max(chain, key=lambda r: float(r.get("pe_oi") or 0))
    return {"resistance": float(res["strike"]), "support": float(sup["strike"])}


def atm_strike(spot: float, strikes: list) -> float:
    return min(strikes, key=lambda k: abs(k - spot))


def pick_option(direction: str, spot: float, strikes: list, chain_by_strike: dict, days_to_expiry: float,
                iv: float, max_premium_pct: float = 0.012) -> dict | None:
    """BUY-only. BUY signal -> CE, SELL signal -> PE. Picks ATM; steps to 1 strike OTM if premium is
    larger than max_premium_pct of spot (cheap enough). Returns None if nothing sensible.
    chain_by_strike: {strike: {"CE": ltp, "PE": ltp}}"""
    if direction not in ("BUY", "SELL") or not strikes:
        return None
    cp = "CE" if direction == "BUY" else "PE"
    ss = sorted(strikes)
    i = ss.index(atm_strike(spot, ss))
    step = 1 if cp == "CE" else -1
    for j in (i, i + step):
        if j < 0 or j >= len(ss):
            continue
        k = ss[j]
        prem = (chain_by_strike.get(k) or {}).get(cp)
        if not prem or prem <= 0:
            continue
        if j == i and prem > max_premium_pct * spot and (i + step) in range(len(ss)):
            continue
        em = expected_move(spot, iv, days_to_expiry)
        pop = prob_profit_buy(spot, k, prem, iv, days_to_expiry, cp)
        be = breakeven(k, prem, cp)
        need = abs(be - spot)
        return {"cp": cp, "strike": k, "premium": float(prem), "breakeven": be, "expected_move": em,
                "pop": pop, "need_move": need, "move_ratio": (need / em) if em > 0 else 9.9}
    return None


def option_ok(opt: dict | None, iv_pct: float, days_to_expiry: float,
              max_move_ratio: float = 0.8, max_iv_pct: float = 0.85, min_days: float = 0.5) -> tuple[bool, str]:
    """Buy-only sanity: do not buy when needed move is too big vs expected move, IV expensive, or expiry too near."""
    if opt is None:
        return False, "option premium nahi mila"
    if days_to_expiry < min_days:
        return False, "expiry bahut paas, theta kha jayega"
    if opt["move_ratio"] > max_move_ratio:
        return False, "option ko paisa banane ke liye expected move se zyada chalna padega"
    if iv_pct > max_iv_pct:
        return False, "IV bahut mehengi, option overpriced"
    return True, "option theek hai"


def options_layer(spot: float, chain: list, iv_pct: float | None = None, prev_oi_chain: list | None = None) -> LayerResult:
    """Vote from option chain: PCR, OI walls, max pain. Index/BTC use only."""
    r = LayerResult("options")
    if not chain or spot <= 0 or sum(float(x.get("ce_oi") or 0) + float(x.get("pe_oi") or 0) for x in chain) <= 0:
        return r        # no OI data (e.g. broker-only fallback chain) -> no vote
    p = pcr(chain)
    mp = max_pain(chain)
    walls = oi_walls(chain)
    s = 0.0
    # PCR: >1.2 supportive (put writers confident), <0.7 bearish; extremes treated mildly (contrarian risk)
    if p >= 1.2:
        s += 0.4
        r.reasons.append(f"PCR {p:.2f} (put writing, support)")
    elif p <= 0.7:
        s -= 0.4
        r.reasons.append(f"PCR {p:.2f} (call writing, dabav)")
    else:
        r.reasons.append(f"PCR {p:.2f} neutral")
    if mp:
        d = (mp - spot) / spot
        s += max(-0.3, min(0.3, d * 30.0))
        r.reasons.append(f"max pain {mp:.0f}")
    if walls["resistance"] and walls["support"]:
        up, dn = walls["resistance"] - spot, spot - walls["support"]
        tot = up + dn
        if tot > 0:
            s += 0.3 * ((up - dn) / tot)
            r.reasons.append(f"OI wall: support {walls['support']:.0f}, resistance {walls['resistance']:.0f}")
    r.score = s
    r.conf = 0.6
    if iv_pct is not None and iv_pct > 0.85:
        r.conf *= 0.7
        r.reasons.append("IV bahut high")
    return r.clipped()


def bs_delta(spot: float, strike: float, t_years: float, sigma: float, cp: str, r: float = 0.065) -> float:
    """Black-Scholes delta (CE positive, PE negative). Used when the broker Greeks are missing."""
    if t_years <= 0 or sigma <= 0:
        itm = spot > strike if cp == "CE" else spot < strike
        return (1.0 if cp == "CE" else -1.0) if itm else 0.0
    d1 = (math.log(spot / strike) + (r + 0.5 * sigma ** 2) * t_years) / (sigma * math.sqrt(t_years))
    return _ncdf(d1) if cp == "CE" else _ncdf(d1) - 1.0


def option_plan(premium: float, delta: float, sl_dist: float, t1_dist: float, t2_dist: float, lot: float,
                risk_budget: float, risk_pct: float = 0.01, max_sl_frac: float = 0.45) -> dict:
    """Premium-level plan from underlying levels (delta approximation; gamma/theta ignored -> conservative on gains).
    SL never risks more than max_sl_frac of the premium. max_loss = whole premium (BUY-only app)."""
    d = abs(delta)
    sl_p = max(premium - d * sl_dist, premium * (1.0 - max_sl_frac))
    t1_p = premium + d * t1_dist
    t2_p = premium + d * t2_dist
    risk_per_lot = (premium - sl_p) * lot
    lots = int(math.floor(risk_budget / risk_per_lot)) if risk_per_lot > 0 else 0
    return {"premium": premium, "sl_premium": sl_p, "t1_premium": t1_p, "t2_premium": t2_p, "delta": d, "lot": lot,
            "lots": lots, "affordable": lots >= 1, "risk_per_lot": risk_per_lot, "max_loss_per_lot": premium * lot,
            "min_capital": (risk_per_lot / risk_pct) if risk_pct > 0 else None,
            "rr_premium": ((t1_p - premium) / (premium - sl_p)) if premium > sl_p else 0.0}


def liquidity_ok(rows: list, strike: float, cp: str, strict: bool = False, premium: float | None = None,
                 min_premium: float = 2.0) -> tuple[bool, str]:
    """Open-interest liquidity proxy (the free chain has no bid/ask). OI at the strike must be >= 40% of the median OI of the
    11 nearest strikes (100% when strict, used for Midcap Nifty). Unknown OI: pass, except strict -> fail."""
    key = "ce_oi" if cp == "CE" else "pe_oi"
    near = sorted(rows, key=lambda r: abs(float(r["strike"]) - strike))[:11]
    ois = sorted(float(r.get(key) or 0) for r in near)
    if not ois or sum(ois) == 0:
        return (False, "OI data nahi, Midcap ke liye liquidity pakki nahi") if strict else (True, "OI data nahi, liquidity check chhoda")
    me = next((float(r.get(key) or 0) for r in rows if float(r["strike"]) == strike), 0.0)
    if me <= 0:
        return False, "is strike par OI zero hai"
    med = ois[len(ois) // 2]
    if me < (1.0 if strict else 0.4) * med:
        return False, "is strike par OI/liquidity kam hai"
    if premium is not None and premium < min_premium:
        return False, "premium bahut chhota, illiquid"
    return True, "liquidity theek hai"

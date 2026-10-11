"""Smart-money layers: FII/DII + participant OI (index), delivery/bulk/insider (stocks), funding/F&G/OI (crypto), COT (commodity)."""
from __future__ import annotations
import math
from .layers import LayerResult


def oi_buildup(price_chg_pct: float, oi_chg_pct: float, thr_p: float = 0.1, thr_oi: float = 1.0) -> str:
    if abs(price_chg_pct) < thr_p or abs(oi_chg_pct) < thr_oi:
        return "NEUTRAL"
    if price_chg_pct > 0 and oi_chg_pct > 0:
        return "LONG_BUILDUP"
    if price_chg_pct < 0 and oi_chg_pct > 0:
        return "SHORT_BUILDUP"
    if price_chg_pct > 0 and oi_chg_pct < 0:
        return "SHORT_COVERING"
    return "LONG_UNWINDING"


_BUILD_SCORE = {"LONG_BUILDUP": 0.5, "SHORT_COVERING": 0.25, "SHORT_BUILDUP": -0.5, "LONG_UNWINDING": -0.25, "NEUTRAL": 0.0}
_BUILD_TXT = {"LONG_BUILDUP": "long buildup", "SHORT_COVERING": "short covering", "SHORT_BUILDUP": "short buildup",
              "LONG_UNWINDING": "long unwinding", "NEUTRAL": "OI neutral"}


def fii_layer(fii_cash_net_cr: float | None, dii_cash_net_cr: float | None = None, fii_idx_fut_long_ratio: float | None = None,
              index_buildup: str | None = None) -> LayerResult:
    """fii_idx_fut_long_ratio = FII index-futures long / (long+short) from participant-wise OI (0..1)."""
    r = LayerResult("smart")
    parts, w = [], []
    if fii_cash_net_cr is not None:
        parts.append(math.tanh(fii_cash_net_cr / 3000.0))
        w.append(0.4)
        r.reasons.append(f"FII cash {fii_cash_net_cr:+.0f} cr")
    if dii_cash_net_cr is not None:
        parts.append(0.5 * math.tanh(dii_cash_net_cr / 3000.0))
        w.append(0.15)
    if fii_idx_fut_long_ratio is not None:
        parts.append(max(-1.0, min(1.0, (fii_idx_fut_long_ratio - 0.5) * 4.0)))
        w.append(0.3)
        r.reasons.append(f"FII index fut long {fii_idx_fut_long_ratio * 100:.0f}%")
    if index_buildup:
        parts.append(_BUILD_SCORE[index_buildup] * 2.0)
        w.append(0.15)
        r.reasons.append(_BUILD_TXT[index_buildup])
    if not parts:
        return r
    r.score = sum(p * x for p, x in zip(parts, w)) / sum(w)
    r.conf = min(0.9, 0.3 + 0.6 * sum(w))
    return r.clipped()


def stock_smart_layer(delivery_pct: float | None, delivery_avg_pct: float | None, price_chg_pct: float | None,
                      buildup: str | None = None, bulk_net: int = 0, insider_net: int = 0) -> LayerResult:
    """bulk_net / insider_net: +1 net buying, -1 net selling, 0 none (last few days)."""
    r = LayerResult("smart")
    s, w = 0.0, 0.0
    if delivery_pct is not None and delivery_avg_pct and price_chg_pct is not None and abs(price_chg_pct) >= 0.3:
        ratio = delivery_pct / delivery_avg_pct
        if ratio >= 1.3:
            s += (1 if price_chg_pct > 0 else -1) * min(1.0, (ratio - 1.0)) * 0.6
            r.reasons.append("delivery zyada (" + ("accumulation" if price_chg_pct > 0 else "distribution") + ")")
        w += 0.4
    if buildup:
        s += _BUILD_SCORE[buildup] * 0.8
        w += 0.3
        r.reasons.append(_BUILD_TXT[buildup])
    if bulk_net:
        s += 0.3 * bulk_net
        w += 0.15
        r.reasons.append("bulk deal " + ("buy" if bulk_net > 0 else "sell"))
    if insider_net:
        s += 0.3 * insider_net
        w += 0.15
        r.reasons.append("insider " + ("buying" if insider_net > 0 else "selling"))
    if w == 0:
        return r
    r.score = s / max(w, 0.5)
    r.conf = min(0.85, 0.25 + w)
    return r.clipped()


def crypto_smart_layer(funding_rate: float | None, ls_ratio: float | None, fear_greed: float | None,
                       oi_chg_pct: float | None, price_chg_pct: float | None) -> LayerResult:
    """funding_rate per 8h as fraction (0.0001 = 0.01%). Extremes are CONTRARIAN."""
    r = LayerResult("smart")
    s, n = 0.0, 0
    if funding_rate is not None:
        n += 1
        if funding_rate > 0.0005:
            s -= 0.4
            r.reasons.append("funding bahut high (longs crowded)")
        elif funding_rate < -0.0002:
            s += 0.4
            r.reasons.append("funding negative (shorts crowded)")
    if ls_ratio is not None:
        n += 1
        if ls_ratio > 2.0:
            s -= 0.2
        elif ls_ratio < 0.8:
            s += 0.2
    if fear_greed is not None:
        n += 1
        if fear_greed <= 20:
            s += 0.3
            r.reasons.append(f"extreme fear {fear_greed:.0f} (bounce chance)")
        elif fear_greed >= 80:
            s -= 0.3
            r.reasons.append(f"extreme greed {fear_greed:.0f} (garmi, risk)")
    if oi_chg_pct is not None and price_chg_pct is not None:
        n += 1
        b = oi_buildup(price_chg_pct, oi_chg_pct)
        s += _BUILD_SCORE[b] * 0.8
        r.reasons.append(_BUILD_TXT[b])
    if n == 0:
        return r
    r.score = s
    r.conf = min(0.7, 0.2 + 0.12 * n)
    return r.clipped()


def cot_layer(net_spec_pct_oi: float | None, change_4w_pct_oi: float | None) -> LayerResult:
    """CFTC managed-money net position as % of open interest (weekly, lagging) -> mild trend-follow, fade extremes."""
    r = LayerResult("smart")
    if net_spec_pct_oi is None or change_4w_pct_oi is None:
        return r
    s = math.tanh(change_4w_pct_oi / 8.0) * 0.6
    if abs(net_spec_pct_oi) > 35:
        s *= 0.4
        r.reasons.append("COT extreme, ulta palatne ka risk")
    r.score = s
    r.conf = 0.35
    r.reasons.append(f"COT 4-hafte badlav {change_4w_pct_oi:+.1f}% OI")
    return r.clipped()

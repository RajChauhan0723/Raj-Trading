"""Bar-by-bar walk-forward backtester using the SAME analyze() + advance() as live. Closed bars only, no lookahead.
Gate 6 (setup record) is bypassed here via paper=True, because this module PRODUCES that record."""
from __future__ import annotations
from datetime import timedelta
import pandas as pd
from .engine import analyze
from .lifecycle import Signal, advance

COST_BPS = {"INDEX": 3.0, "STOCK": 6.0, "COMMODITY": 5.0, "FOREX": 2.0, "CRYPTO": 8.0}  # round-trip, underlying-level proxy


def backtest(df: pd.DataFrame, symbol: str, asset_class: str, *, lot_size: int = 1, capital: float = 1_000_000.0,
             risk_pct: float = 0.01, profile: str = "conservative", tf_minutes: int = 5, window: int = 300, warmup: int = 100,
             step: int = 1, max_hold_bars: int = 200, segment: str | None = None, holidays: set | None = None,
             extra_layers_fn=None, **analyze_kw) -> list[dict]:
    """extra_layers_fn(i, ts) -> dict of extra LayerResults (optional, must itself be point-in-time)."""
    trades: list[dict] = []
    n = len(df)
    tf = timedelta(minutes=tf_minutes)
    i = max(warmup, 60)
    cost_bps = COST_BPS[asset_class]
    while i < n - 1:
        now = df.index[i] + tf                       # bar i just closed
        win = df.iloc[max(0, i - window + 1): i + 1]
        extra = extra_layers_fn(i, now) if extra_layers_fn else None
        d = analyze(symbol, asset_class, win, now, capital=capital, risk_pct=risk_pct, lot_size=lot_size, profile=profile,
                    segment=segment, intraday=True, extra_layers=extra, paper=True, holidays=holidays, **analyze_kw)
        if d["action"] not in ("BUY", "SELL"):
            i += step
            continue
        pl = d["plan"]
        sig = Signal(f"bt{i}", symbol, asset_class, d["action"], pl["entry_lo"], pl["entry_hi"], pl["sl"], pl["t1"], pl["t2"],
                     pl["chase_price"], now + timedelta(minutes=20), pd.Timestamp(pl["exit_by"]).to_pydatetime(), now,
                     sl_dist=pl["sl_dist"])
        j = i + 1
        last_j = min(n - 1, i + max_hold_bars)
        while j <= last_j and sig.state in ("NEW", "ACTIVE"):
            ts = df.index[j]
            row = df.iloc[j]
            advance(sig, float(row["open"]), ts, None, None)
            if sig.state in ("NEW", "ACTIVE"):
                advance(sig, float(row["close"]), ts + tf, float(row["high"]), float(row["low"]))
            j += 1
        if sig.state in ("NEW", "ACTIVE"):
            advance(sig, float(df.iloc[last_j]["close"]), df.index[last_j] + 10 * tf, None, None)
            if sig.state == "NEW":
                sig.state = "EXPIRED"
        if sig.entry_price is not None and sig.r_multiple is not None:
            cost_r = (cost_bps / 1e4 * sig.entry_price) / sig.sl_dist if sig.sl_dist > 0 else 0.0
            trades.append({"ts": now, "symbol": symbol, "asset_class": asset_class, "direction": sig.direction,
                           "regime": d["regime"], "grade": d["grade"], "state": sig.state, "r_gross": sig.r_multiple,
                           "cost_r": cost_r, "r_net": sig.r_multiple - cost_r})
        else:
            trades.append({"ts": now, "symbol": symbol, "asset_class": asset_class, "direction": sig.direction,
                           "regime": d["regime"], "grade": d["grade"], "state": sig.state, "r_gross": None,
                           "cost_r": 0.0, "r_net": None})
        i = max(j, i + step)
    return trades


def _rs(trades: list[dict], cost_mult: float = 1.0) -> list[float]:
    return [t["r_gross"] - cost_mult * t["cost_r"] for t in trades if t.get("r_gross") is not None]


def expectancy(trades: list[dict], cost_mult: float = 1.0) -> float:
    rs = _rs(trades, cost_mult)
    return sum(rs) / len(rs) if rs else 0.0


def setup_stats(trades: list[dict]) -> dict:
    rs = _rs(trades)
    n = len(rs)
    if n == 0:
        return {"trades": 0, "win_rate": 0.0, "expectancy_r": 0.0, "profit_factor": 0.0, "max_dd_r": 0.0,
                "is_expectancy_r": 0.0, "oos_expectancy_r": 0.0, "stress_expectancy_r": 0.0}
    done = [t for t in trades if t.get("r_gross") is not None]
    cut = int(n * 0.7)
    gp = sum(r for r in rs if r > 0)
    gl = -sum(r for r in rs if r < 0)
    peak = cum = dd = 0.0
    for r in rs:
        cum += r
        peak = max(peak, cum)
        dd = max(dd, peak - cum)
    return {"trades": n, "win_rate": sum(1 for r in rs if r > 0) / n, "expectancy_r": sum(rs) / n,
            "profit_factor": (gp / gl) if gl > 0 else float("inf"), "max_dd_r": dd,
            "is_expectancy_r": expectancy(done[:cut]) if cut else 0.0,
            "oos_expectancy_r": expectancy(done[cut:]) if n - cut else 0.0,
            "stress_expectancy_r": expectancy(done, 2.0)}


def passes_record(stats: dict, min_trades: int = 30) -> bool:
    """Net-of-costs expectancy > 0, out-of-sample (last 30%) > 0, and still > 0 with doubled costs."""
    return (stats["trades"] >= min_trades and stats["expectancy_r"] > 0 and stats["oos_expectancy_r"] > 0
            and stats["stress_expectancy_r"] > 0)


def group_setups(trades: list[dict]) -> dict:
    """setup_key = ASSETCLASS|DIRECTION|REGIME -> stats."""
    g: dict = {}
    for t in trades:
        g.setdefault(f"{t['asset_class']}|{t['direction']}|{t['regime']}", []).append(t)
    return {k: setup_stats(v) for k, v in g.items()}

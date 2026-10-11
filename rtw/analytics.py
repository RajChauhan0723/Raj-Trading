"""Analytics view — read-only. Aggregates data from existing DB tables.
Produces:
  1. walk-forward: signal accuracy for last 30 / 60 / 90 days (from signals table)
  2. sector_heatmap: per-sector strength from live decisions
  3. setups: setup-wise expectancy / win-rate from setup_stats table
  4. equity_curve: cumulative R over time
No writes; no conflict with the pipeline.
"""
from __future__ import annotations
from datetime import datetime, timedelta
from .sessions import IST

# ---------------------------------------------------------------------------
SECTOR_MAP: dict[str, str] = {
    # Indices
    "NIFTY": "Index", "BANKNIFTY": "Index", "MIDCPNIFTY": "Index", "SENSEX": "Index",
    # IT
    "INFY": "IT", "TCS": "IT", "WIPRO": "IT", "HCLTECH": "IT", "TECHM": "IT",
    # Banking / Finance
    "HDFCBANK": "Banking", "ICICIBANK": "Banking", "SBIN": "Banking", "AXISBANK": "Banking",
    "KOTAKBANK": "Banking", "INDUSINDBK": "Banking", "BAJFINANCE": "Finance",
    "BAJAJFINSV": "Finance", "SBILIFE": "Finance", "HDFCLIFE": "Finance",
    # Energy / Oil
    "RELIANCE": "Energy", "ONGC": "Energy", "BPCL": "Energy", "IOC": "Energy",
    "CRUDEOIL": "Energy", "NATURALGAS": "Energy",
    # Metals
    "TATASTEEL": "Metals", "JSWSTEEL": "Metals", "HINDALCO": "Metals",
    "COALINDIA": "Metals", "GOLD": "Precious Metals", "GOLDM": "Precious Metals", "XAUUSD": "Precious Metals", "SILVER": "Precious Metals",
    # Auto
    "MARUTI": "Auto", "M&M": "Auto", "EICHERMOT": "Auto", "HEROMOTOCO": "Auto",
    # Pharma
    "SUNPHARMA": "Pharma", "DRREDDY": "Pharma", "CIPLA": "Pharma", "DIVISLAB": "Pharma",
    # FMCG / Consumer
    "HINDUNILVR": "FMCG", "ITC": "FMCG", "NESTLEIND": "FMCG",
    "ASIANPAINT": "Consumer", "TITAN": "Consumer",
    # Infra / Capital
    "LT": "Infra", "NTPC": "Power", "POWERGRID": "Power", "BEL": "Defence", "HAL": "Defence",
    "ADANIENT": "Conglomerate", "ADANIPORTS": "Infra",
    # Cement
    "ULTRACEMCO": "Cement", "GRASIM": "Cement",
    # Telecom
    "BHARTIARTL": "Telecom",
    # Pharma/Hosp
    "APOLLOHOSP": "Hospitals", "TRENT": "Retail",
    # Crypto
    "BTCUSDT": "Crypto",
}


def _walk_forward_stats(con, days: int, now: datetime) -> dict:
    """Closed trades within last N days from the signals table."""
    cutoff = (now - timedelta(days=days)).isoformat()
    rows = con.execute(
        "SELECT r_multiple, state, direction FROM signals "
        "WHERE kind='TRADE' AND state IN ('TARGET','SL','EXPIRED') "
        "AND closed_at >= ? AND r_multiple IS NOT NULL",
        (cutoff,)
    ).fetchall()
    rs = [float(r[0]) for r in rows]
    n = len(rs)
    if n == 0:
        return {"days": days, "trades": 0, "win_rate": 0.0, "expectancy_r": 0.0,
                "total_r": 0.0, "avg_win": 0.0, "avg_loss": 0.0, "profit_factor": 0.0}
    wins = [r for r in rs if r > 0]
    losses = [r for r in rs if r < 0]
    gp = sum(wins)
    gl = -sum(losses)
    return {
        "days": days,
        "trades": n,
        "win_rate": round(len(wins) / n, 4),
        "expectancy_r": round(sum(rs) / n, 4),
        "total_r": round(sum(rs), 3),
        "avg_win": round(sum(wins) / len(wins), 3) if wins else 0.0,
        "avg_loss": round(sum(losses) / len(losses), 3) if losses else 0.0,
        "profit_factor": round(gp / gl, 3) if gl > 0 else (float("inf") if gp > 0 else 0.0),
    }


def _sector_heatmap(con) -> list[dict]:
    """Per-sector strength score from latest decisions in DB."""
    decisions = {r["symbol"]: r["action"] for r in con.execute(
        "SELECT symbol, action FROM decisions"
    )}
    sector_data: dict[str, dict] = {}
    for sym, action in decisions.items():
        sector = SECTOR_MAP.get(sym.upper(), "Other")
        if sector not in sector_data:
            sector_data[sector] = {"buy": 0, "sell": 0, "wait": 0, "total": 0}
        sd = sector_data[sector]
        sd["total"] += 1
        if action == "BUY":
            sd["buy"] += 1
        elif action == "SELL":
            sd["sell"] += 1
        else:
            sd["wait"] += 1

    result = []
    for sector, sd in sorted(sector_data.items()):
        n = sd["total"] or 1
        # Strength score: +1 per BUY, -1 per SELL, normalized -100 to +100
        score = round(((sd["buy"] - sd["sell"]) / n) * 100)
        if sd["buy"] > sd["sell"]:
            bias = "BULLISH"
            color = "buy"
        elif sd["sell"] > sd["buy"]:
            bias = "BEARISH"
            color = "sell"
        else:
            bias = "NEUTRAL"
            color = "wait"
        result.append({
            "sector": sector,
            "score": score,
            "bias": bias,
            "color": color,
            "buy": sd["buy"],
            "sell": sd["sell"],
            "wait": sd["wait"],
            "total": sd["total"],
        })
    # Sort: most bullish first, most bearish last
    result.sort(key=lambda x: -x["score"])
    return result


def _setup_breakdown(con) -> list[dict]:
    """Setup-wise expectancy from the setup_stats table (already maintained by pipeline)."""
    rows = con.execute(
        "SELECT setup_key, trades, expectancy_r, win_rate, benched, updated_at "
        "FROM setup_stats ORDER BY expectancy_r DESC"
    ).fetchall()
    out = []
    for r in rows:
        parts = (r["setup_key"] or "").split("|")
        out.append({
            "setup_key": r["setup_key"],
            "asset_class": parts[0] if len(parts) > 0 else "-",
            "direction": parts[1] if len(parts) > 1 else "-",
            "regime": parts[2] if len(parts) > 2 else "-",
            "trades": r["trades"],
            "expectancy_r": round(float(r["expectancy_r"] or 0), 3),
            "win_rate": round(float(r["win_rate"] or 0), 4),
            "benched": bool(r["benched"]),
            "updated_at": r["updated_at"],
        })
    return out


def _equity_curve(con) -> list[dict]:
    """Cumulative R curve from all closed trades (for mini sparkline chart)."""
    rows = con.execute(
        "SELECT r_multiple, closed_at FROM signals "
        "WHERE kind='TRADE' AND r_multiple IS NOT NULL "
        "ORDER BY closed_at"
    ).fetchall()
    curve = []
    cum = 0.0
    for r in rows:
        cum += float(r[0])
        curve.append({"t": r[1], "cum_r": round(cum, 3)})
    return curve


def _oi_summary(con) -> dict:
    """Latest OI wall data from decisions extra_json (if available from index symbols)."""
    index_syms = ("NIFTY", "BANKNIFTY", "MIDCPNIFTY")
    result = {}
    for sym in index_syms:
        row = con.execute("SELECT json FROM decisions WHERE symbol=?", (sym,)).fetchone()
        if not row:
            continue
        try:
            import json
            d = json.loads(row["json"] or "{}")
            oi_walls = d.get("oi_walls") or {}
            pcr = d.get("pcr")
            if oi_walls or pcr is not None:
                result[sym] = {
                    "pcr": round(float(pcr), 3) if pcr is not None else None,
                    "support_wall": oi_walls.get("support"),
                    "resistance_wall": oi_walls.get("resistance"),
                }
        except Exception:
            continue
    return result


def analytics_view(con, now: datetime) -> dict:
    """Aggregated analytics: walk-forward accuracy, sector heatmap, setup breakdown, equity curve."""
    wf_30 = _walk_forward_stats(con, 30, now)
    wf_60 = _walk_forward_stats(con, 60, now)
    wf_90 = _walk_forward_stats(con, 90, now)

    return {
        "updated": now.isoformat(),
        "walk_forward": [wf_30, wf_60, wf_90],
        "sector_heatmap": _sector_heatmap(con),
        "setups": _setup_breakdown(con),
        "equity_curve": _equity_curve(con),
        "oi_summary": _oi_summary(con),
    }

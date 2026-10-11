"""Scheduled jobs (plain functions, each safe to call alone and fully testable with FakeProvider)."""
from __future__ import annotations
import json
import os
from datetime import datetime, timedelta
from .backtest import backtest, group_setups, passes_record
from .config import CORE_SPECS
from .db import upsert_candles, put_setup_stats, log_health, set_setting, get_setting
from .notify import format_brief
from .news import news_mode
from .sessions import IST
from .views import home_view, events_payload


def bootstrap_history(orc, now: datetime, days: int = 60) -> int:
    """First start: fill the candle table with history so indicators/backtests have data."""
    n = 0
    for sp in list(CORE_SPECS) + list(orc.provider.stock_universe(now, orc.st.stocks_top_n)):
        try:
            df = orc.provider.history(sp, now, days)
        except Exception as e:
            log_health(orc.con, now, f"history:{sp.symbol}", "FAIL", repr(e))
            continue
        if df is None or df.empty:
            log_health(orc.con, now, f"history:{sp.symbol}", "FAIL", "no history")
            continue
        rows = [(ts.tz_convert(IST).isoformat(), float(r.open), float(r.high), float(r.low), float(r.close), float(r.volume)) for ts, r in df.iterrows()]
        upsert_candles(orc.con, sp.symbol, "5m", rows)
        log_health(orc.con, now, f"history:{sp.symbol}", "OK", f"{len(rows)} bars")
        n += 1
    return n


def nightly_backtest(orc, now: datetime, step: int = 3, min_bars: int = 1200) -> dict:
    """Walk-forward test per setup (asset class | direction | regime) on stored history. Writes setup_stats.
    Rules that stop working get benched (benched=1) -> their signals are blocked by the setup_record gate."""
    from .db import load_df
    ctx = orc.context(now)
    by_class: dict = {}
    for sp in CORE_SPECS:
        df = load_df(orc.con, sp.symbol, "5m", 20000)
        if df is None or len(df) < min_bars:
            continue
        lot, cap = orc._engine_lot_and_capital(sp, ctx)
        try:
            tr = backtest(df, sp.symbol, sp.asset_class, lot_size=lot, capital=cap, risk_pct=orc.st.risk_pct, profile=orc.st.profile,
                          step=step, segment="CRYPTO", warmup=120)       # sessions ignored: history already only has market hours
        except Exception as e:
            log_health(orc.con, now, f"backtest:{sp.symbol}", "FAIL", repr(e))
            continue
        by_class.setdefault(sp.asset_class, []).extend(tr)
    written = {}
    for cls, trades in by_class.items():
        for key, st in group_setups(trades).items():
            st["benched"] = int(st["trades"] >= 30 and not passes_record(st))
            put_setup_stats(orc.con, key, st, now)
            written[key] = st
    log_health(orc.con, now, "nightly_backtest", "OK", f"{len(written)} setups")
    return written


def health_check(orc, now: datetime) -> list:
    rows = orc.provider.health(now)
    prev = get_setting(orc.con, "health_prev", {}) or {}
    cur = {}
    for comp, status, detail in rows:
        log_health(orc.con, now, comp, status, detail)
        cur[comp] = status
        if status == "FAIL" and prev.get(comp) != "FAIL":
            orc.send(f"⚠️ Data problem: {comp} — {detail}")
        if status == "OK" and prev.get(comp) == "FAIL":
            orc.send(f"✅ Theek ho gaya: {comp}")
    set_setting(orc.con, "health_prev", cur)
    return rows


def morning_brief(orc, now: datetime) -> str:
    ev = orc.provider.events(now)
    h = home_view(orc.con, now, ev, orc.st)
    nm = news_mode(ev, now, "NIFTY", vix_z=orc.provider.vix_z(now))
    text = format_brief(h, {"mode": nm["mode"], "events": events_payload(ev, now, 24)})
    orc.send(text)
    return text


def update_holidays(orc, now: datetime) -> int:
    from .adapters import nse
    days = nse.fetch_holidays()
    path = os.path.join("data", "holidays.json")
    if os.path.exists(path):                              # manual override/addition file: ["2026-11-10", ...]
        try:
            days = sorted(set(days) | set(json.load(open(path, encoding="utf-8"))))
        except Exception:
            pass
    if days:
        set_setting(orc.con, "holidays", days)
    return len(days)

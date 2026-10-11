"""APScheduler wiring. Every job is wrapped so an exception is logged and never kills the scheduler."""
from __future__ import annotations
import threading
import traceback
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from . import jobs
from .db import log_health, get_setting, open_trade
from .sessions import IST


def _safe(orc, name, fn):
    def run():
        now = datetime.now(IST)
        try:
            fn(now)
        except Exception as e:
            log_health(orc.con, now, f"job:{name}", "FAIL", f"{e!r} {traceback.format_exc()[-200:]}")
    run.__name__ = name
    return run


def build_scheduler(orc, live=None) -> BackgroundScheduler:
    """live = LiveProvider or None (DEMO). Timezone is IST for every cron."""
    sch = BackgroundScheduler(timezone=IST, job_defaults={"max_instances": 1, "coalesce": True, "misfire_grace_time": 60})

    def core(now):
        orc.refresh_all(now, "core")
        orc.cycle(now, "core")

    def stocks(now):
        orc.refresh_all(now, "stocks")
        orc.cycle(now, "stocks")

    sch.add_job(_safe(orc, "core", core), "cron", second=8, id="core")           # 8 s after every minute: the bar has closed
    sch.add_job(_safe(orc, "stocks", stocks), "cron", minute="*/5", second=25, id="stocks")   # just after each 5-min bar closes
    sch.add_job(_safe(orc, "health", lambda n: jobs.health_check(orc, n)), "interval", minutes=10, id="health")
    sch.add_job(_safe(orc, "brief", lambda n: jobs.morning_brief(orc, n)), "cron", day_of_week="mon-fri", hour=8, minute=30, id="brief")
    sch.add_job(_safe(orc, "backtest", lambda n: jobs.nightly_backtest(orc, n)), "cron", hour=23, minute=50, id="backtest")
    if live is not None:
        sch.add_job(_safe(orc, "news", lambda n: live.collect_news(n)), "interval", minutes=2, id="news")
        sch.add_job(_safe(orc, "gdelt", lambda n: live.collect_news(n, gdelt=True)), "interval", minutes=15, id="gdelt")

        def morning(now):
            for c, s, d in live.start(now):
                log_health(orc.con, now, c, s, d)
            live.refresh_stock_universe(now, 100)
            jobs.update_holidays(orc, now)

        sch.add_job(_safe(orc, "morning", morning), "cron", hour=6, minute=0, id="morning")
        sch.add_job(_safe(orc, "iv", lambda n: [live.record_iv(sp, n) for sp in orc.specs(n) if sp.has_options]), "cron",
                    day_of_week="mon-fri", hour=15, minute=45, id="iv")
    return sch

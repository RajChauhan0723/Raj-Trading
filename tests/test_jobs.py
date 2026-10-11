from datetime import datetime
from rtw.config import Settings
from rtw.db import connect, get_setup_stats
from rtw.provider import FakeProvider
from rtw.pipeline import Orchestrator
from rtw.scheduler import build_scheduler
from rtw.sessions import IST
from rtw import jobs

NOW = datetime(2026, 10, 7, 11, 2, tzinfo=IST)


def make():
    st = Settings(mode="DEMO", capital=2_000_000)
    sent = []
    orc = Orchestrator(connect(":memory:"), FakeProvider(), st, send=lambda t: sent.append(t) or True)
    return orc, sent


def test_bootstrap_backtest_health_brief():
    orc, sent = make()
    n = jobs.bootstrap_history(orc, NOW)
    assert n >= 14
    w = jobs.nightly_backtest(orc, NOW, step=6, min_bars=300)
    assert isinstance(w, dict)
    rows = jobs.health_check(orc, NOW)
    assert rows and rows[0][1] == "OK"
    assert "PRE-MARKET" in jobs.morning_brief(orc, NOW)
    assert all("trades" in v for v in get_setup_stats(orc.con).values())


def test_scheduler_builds_and_jobs_registered():
    orc, _ = make()
    sch = build_scheduler(orc, None)
    ids = {j.id for j in sch.get_jobs()}
    assert {"core", "stocks", "health", "brief", "backtest"} <= ids

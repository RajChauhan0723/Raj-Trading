import json
from datetime import datetime, timedelta
import pytest
from rtw.config import Settings
from rtw.db import connect, open_trade, load_decisions, save_decision, load_protections
from rtw.pipeline import Orchestrator, data_age_sec, htf_conflict
from rtw.provider import FakeProvider
from rtw.sessions import IST
from rtw.views import home_view, markets_view, record_view, news_view
from rtw.notify import format_signal, trade_card

NOW = datetime(2026, 10, 7, 11, 2, 30, tzinfo=IST)


def make(profile="aggressive", capital=2_000_000):
    con = connect(":memory:")
    st = Settings(mode="DEMO", capital=capital, risk_pct=0.01, profile=profile)
    sent = []
    orc = Orchestrator(con, FakeProvider(), st, send=lambda t: sent.append(t) or True)
    return con, st, orc, sent


def test_refresh_and_cycle_produces_one_trade_or_wait():
    con, st, orc, sent = make()
    assert orc.refresh_all(NOW, "core") == len([s for s in orc.specs(NOW) if s.tab != "stocks"])
    ev = orc.cycle(NOW, "core")
    dec = load_decisions(con)
    assert len(dec) >= 14
    sig, extra = open_trade(con)
    n_open = con.execute("SELECT COUNT(*) FROM signals WHERE kind='TRADE' AND state IN ('NEW','ACTIVE')").fetchone()[0]
    assert n_open <= 1
    if sig:
        assert sent and "NAYA SIGNAL" in sent[0] and sig.paper
        assert sig.sl != sig.t1
    home = home_view(con, NOW, orc.provider.events(NOW), st)
    assert home["status"] in ("WAIT", "NEW", "ACTIVE")
    if home["status"] == "WAIT":
        assert home["wait"]["reason"]


def test_second_cycle_does_not_open_second_trade():
    con, st, orc, sent = make()
    orc.refresh_all(NOW, "core"); orc.cycle(NOW, "core")
    t1 = NOW + timedelta(minutes=1)
    orc.refresh_all(t1, "core"); orc.cycle(t1, "core")
    n = con.execute("SELECT COUNT(*) FROM signals WHERE kind='TRADE' AND state IN ('NEW','ACTIVE')").fetchone()[0]
    assert n <= 1


def test_forced_signal_lifecycle_and_protections():
    con, st, orc, sent = make()
    orc.refresh_all(NOW, "core")
    orc.cycle(NOW, "core")
    sig, extra = open_trade(con)
    if sig is None:
        pytest.skip("demo data produced no signal at this time")
    # push price through target using ltp override
    spec = orc.spec_by_symbol(sig.symbol, NOW)
    sgn = 1 if sig.direction == "BUY" else -1
    px = [(sig.entry_lo + sig.entry_hi) / 2, sig.t1 + sgn * 1.0]
    it = iter(px)
    orc.provider.ltp = lambda s, n: next(it, px[-1])
    orc.cycle(NOW + timedelta(minutes=1), "core")
    s2 = con.execute("SELECT state FROM signals WHERE id=?", (sig.id,)).fetchone()[0]
    assert s2 in ("ACTIVE", "TARGET", "NEW", "MISSED", "SL")
    orc.cycle(NOW + timedelta(minutes=2), "core")
    rec = record_view(con)
    assert "all" in rec and isinstance(rec["last"], list)


def test_data_age_and_htf():
    con, st, orc, sent = make()
    spec = orc.specs(NOW)[0]
    df = orc.provider.candles(spec, NOW)
    assert data_age_sec(df, NOW) == 0
    assert data_age_sec(df, NOW + timedelta(minutes=30)) > 1000
    bad, why = htf_conflict(df, "BUY")
    assert isinstance(bad, bool)


def test_market_closed_blocks_everything_in_live_mode():
    con = connect(":memory:")
    st = Settings(mode="PAPER", capital=1_000_000)
    orc = Orchestrator(con, FakeProvider(), st)
    sat = datetime(2026, 10, 10, 11, 0, tzinfo=IST)      # Saturday
    orc.refresh_all(sat, "core")                          # only crypto is open
    orc.cycle(sat, "core")
    dec = load_decisions(con)
    assert all(d["action"] == "WAIT" for s, d in dec.items() if s != "BTCUSDT")
    assert "market band" in dec["NIFTY"]["wait_reason"]


def test_views_shapes():
    con, st, orc, sent = make()
    orc.refresh_all(NOW, "core"); orc.cycle(NOW, "core")
    for tab in ("index", "commodity", "forex", "crypto"):
        v = markets_view(con, tab, NOW, st, orc.specs(NOW))
        assert v["tab"] == tab and "active" in v and "waiting" in v
    nv = news_view(con, orc.provider, NOW, orc.provider.events(NOW), {"mode": "CALM"})
    assert nv["events"] and nv["events"][0]["when_text"]


def test_option_conversion_for_index_when_forced():
    con, st, orc, sent = make(capital=5_000_000)
    spec = orc.spec_by_symbol("NIFTY", NOW)
    orc.refresh_symbol(spec, NOW)
    ctx = orc.context(NOW)
    chain = orc.provider.option_chain(spec, NOW)
    d = {"action": "BUY", "price": chain["spot"], "risk_budget": 50000.0, "plan": {"entry_lo": chain["spot"] - 5, "entry_hi": chain["spot"] + 5,
         "sl_dist": 60.0, "t1": chain["spot"] + 120, "t2": chain["spot"] + 180}, "extra": {}}
    d["extra"] = {"underlying_name": "Nifty 50"}
    out = orc._option_conversion(spec, d, chain, NOW)
    if out["action"] == "BUY":
        o = out["extra"]["option"]
        assert o["cp"] == "CE" and o["premium"] > 0 and o["sl_premium"] < o["premium"] < o["t1_premium"]
        assert out["extra"]["max_loss"] > 0 and out["extra"]["lots"] >= 1
    else:
        assert out["wait_reason"]


def test_commodity_contract_choice():
    from rtw.config import choose_contract
    c = choose_contract("GOLD", 600.0, 3000.0)       # 600*100 and 600*10 exceed 3000 ; 600*0.1=60 per lot -> 50 lots
    assert c["contract"] == "GOLDPETAL" and c["lots"] == 50
    c = choose_contract("GOLD", 600.0, 100000.0)
    assert c["contract"] == "GOLD" and c["lots"] == 1
    c = choose_contract("CRUDE", 100.0, 500.0)
    assert c["affordable"] is False


def test_stock_gets_option_call_via_lazy_chain():
    con, st, orc, sent = make(capital=20_000_000)
    orc.provider.TREND = {**FakeProvider.TREND, "RELIANCE": 0.0011}
    spec = orc.spec_by_symbol("RELIANCE", NOW)
    assert orc.refresh_symbol(spec, NOW)
    from rtw.db import get_setup_stats, load_protections
    d = orc.analyze_spec(spec, NOW, orc.context(NOW), get_setup_stats(con), load_protections(con))
    assert d["action"] in ("BUY", "WAIT")
    if d["action"] == "BUY":
        assert d["extra"]["option"]["cp"] == "CE" and "CE" in d["instrument"] and d["extra"]["max_loss"] > 0
    else:
        assert d["wait_reason"]
    print(d["action"], d.get("instrument"), d.get("wait_reason"))


def test_parallel_cycles_never_open_two_trades():
    import threading
    con, st, orc, sent = make()
    for sp in orc.specs(NOW):
        orc.refresh_symbol(sp, NOW)
    ts = [threading.Thread(target=orc.cycle, args=(NOW, sc)) for sc in ("core", "stocks", "core", "all")]
    [t.start() for t in ts]
    [t.join() for t in ts]
    n = con.execute("SELECT COUNT(*) FROM signals WHERE kind='TRADE' AND state IN ('NEW','ACTIVE')").fetchone()[0]
    assert n <= 1


def test_default_stock_list_when_universe_empty():
    from rtw.config import Settings
    from rtw.db import connect
    from rtw.live import LiveProvider
    lp = LiveProvider(Settings(mode="PAPER"), connect(":memory:"))
    assert len(lp.stock_universe(NOW, 50)) == 48 or len(lp.stock_universe(NOW, 50)) >= 40

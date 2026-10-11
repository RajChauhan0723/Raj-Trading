"""Regression tests for audit-2 fixes."""
import json
import threading
from datetime import datetime, timedelta
import pandas as pd
from rtw.db import connect, save_signal, forward_stats, load_protections, save_protections
from rtw.lifecycle import Signal
from rtw.options import bs_price, implied_vol
from rtw.adapters import nse as N
from rtw.adapters import angel as A
from rtw.live import _Cache
from rtw.sessions import IST

NOW = datetime(2026, 10, 7, 11, 2, 30, tzinfo=IST)


def _sig(i, state="SL", r=-1.0):
    return Signal(id=i, symbol="NIFTY", asset_class="INDEX", direction="BUY", entry_lo=100, entry_hi=101, sl=99, t1=103, t2=105,
                  chase_price=102, valid_till=NOW + timedelta(hours=1), exit_by=NOW + timedelta(hours=3), created_at=NOW,
                  state=state, r_multiple=r)


def test_extra_json_roundtrip_and_forward_stats():
    con = connect(":memory:")
    for i, r in enumerate([1.0, 2.0, -1.0]):
        save_signal(con, _sig(f"a{i}", "TARGET" if r > 0 else "SL", r), {"setup_key": "k1"})
    save_signal(con, _sig("b0", "SL", -1.0), {"setup_key": "k2"})
    fs = forward_stats(con, "k1")
    assert fs["trades"] == 3 and abs(fs["expectancy_r"] - 2 / 3) < 1e-9
    # extra_json is updated on re-save
    save_signal(con, _sig("b0", "SL", -1.0), {"setup_key": "k1"})
    assert forward_stats(con, "k1")["trades"] == 4


def test_locked_connection_threads():
    con = connect(":memory:")
    errs = []

    def work(n):
        try:
            for i in range(40):
                save_signal(con, _sig(f"t{n}_{i}"), {"setup_key": "x"})
                con.execute("SELECT COUNT(*) FROM signals").fetchone()
        except Exception as e:
            errs.append(e)
    ts = [threading.Thread(target=work, args=(n,)) for n in range(6)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    assert not errs
    assert con.execute("SELECT COUNT(*) FROM signals").fetchone()[0] == 240


def test_protections_persist():
    con = connect(":memory:")
    p = load_protections(con)
    p.halted = True
    save_protections(con, p)
    assert load_protections(con).halted is True


def test_implied_vol_bisection():
    for cp in ("CE", "PE"):
        px = bs_price(24000, 24100, 5 / 365, 0.18, cp)
        assert abs(implied_vol(px, 24000, 24100, 5 / 365, cp) - 0.18) < 1e-4
    assert implied_vol(0, 24000, 24100, 5 / 365, "CE") == 0.0
    assert implied_vol(1e6, 24000, 24100, 5 / 365, "CE") == 0.0


def test_atm_iv_backs_out_from_premium_when_columns_missing():
    t = 4 / 365
    rows = [{"strike": 24000, "ce_oi": 1, "pe_oi": 1, "ce_ltp": bs_price(24010, 24000, t, 0.16, "CE"),
             "pe_ltp": bs_price(24010, 24000, t, 0.16, "PE"), "ce_iv": 0.0, "pe_iv": 0.0}]
    assert N.atm_iv(rows, 24010) == 0.0                      # no dte -> cannot back out
    assert abs(N.atm_iv(rows, 24010, 4.0) - 0.16) < 0.005
    rows[0]["ce_iv"] = 0.2
    assert abs(N.atm_iv(rows, 24010, 4.0) - 0.2) < 1e-9      # real IV column wins


def test_turnover_ranking_from_bhav():
    df = pd.DataFrame({"SYMBOL": ["AAA", "BBB", "CCC", "AAA"], "SERIES": ["EQ", "EQ", "BE", "BE"], "TOTTRDVAL": [5, 9, 100, 50]})
    m = N.turnover_map(df)
    assert m == {"AAA": 5.0, "BBB": 9.0}
    assert N.turnover_map(None) == {}


def test_cache_stale_limit():
    c = _Cache()
    assert c.get("k", 10, lambda: [1]) == [1]
    c.d["k"] = (c.d["k"][0] - 30, c.d["k"][1])               # 30 s old, ttl 10, default max_stale 60
    assert c.get("k", 10, lambda: None) == [1]
    c.d["k"] = (c.d["k"][0] - 100, c.d["k"][1])              # 130 s old -> too stale
    assert not c.get("k", 10, lambda: None)


def test_angel_login_cooldown_and_error_handling():
    class S:
        angel_api_key = "k"; angel_client_code = "c"; angel_pin = "p"; angel_totp_secret = "JBSWY3DPEHPK3PXP"
    a = A.AngelClient(S())
    import time
    a._login_fail_at = time.time()
    assert a.login() is False                                 # inside cooldown: no attempt made
    calls = []

    class Api:
        def f(self):
            calls.append(1)
            raise ConnectionError("network down")
    a.api, a.logged_at = Api(), datetime.now(IST)
    assert a._call(a.api.f) is None
    assert len(calls) == 1 and a.api is not None              # network blip: no forced re-login, no retry storm


def test_reset_halt_and_contract_roll():
    from tests.test_pipeline import make
    con, st, orc, sent = make()
    p = load_protections(con)
    p.halted = True
    save_protections(con, p)
    orc.reset_halt()
    assert load_protections(con).halted is False


# ---------------------------------------------------------------- multiple signals (max_trades)
def _multi(max_trades):
    from tests.test_pipeline import make
    from rtw.provider import FakeProvider
    con, st, orc, sent = make(capital=20_000_000)
    orc.provider.TREND = {**FakeProvider.TREND, "RELIANCE": 0.0011}
    st.max_trades = max_trades
    orc.refresh_all(NOW, "core")
    orc.refresh_all(NOW, "stocks")
    orc.cycle(NOW, "all")
    return con, st, orc, sent


def test_single_signal_is_default():
    from rtw.config import get_settings, Settings
    assert Settings().max_trades == 1
    con, st, orc, sent = _multi(1)
    from rtw.db import open_trades
    assert len(open_trades(con)) == 1


def test_multiple_signals_open_together_without_duplicates():
    from rtw.db import open_trades
    from rtw.views import home_view
    con, st, orc, sent = _multi(4)
    ot = open_trades(con)
    syms = [s.symbol for s, _ in ot]
    assert 2 <= len(ot) <= 4 and len(set(syms)) == len(syms)
    h = home_view(con, NOW, orc.provider.events(NOW), st)
    assert len(h["trades"]) == len(ot) and h["trade"]["symbol"] == h["trades"][0]["symbol"] and h["max_trades"] == 4
    assert len([m for m in sent if "NAYA SIGNAL" in m]) == len(ot)
    orc.cycle(NOW, "all")                                    # a second cycle must not add duplicates
    assert len(open_trades(con)) == len(ot)


def test_index_same_direction_conflict_rule():
    from rtw.pipeline import Orchestrator
    s = _sig("x")
    s.symbol, s.asset_class, s.direction = "NIFTY", "INDEX", "BUY"
    assert Orchestrator._conflicts([s], {"symbol": "BANKNIFTY", "asset_class": "INDEX", "action": "BUY"})
    assert not Orchestrator._conflicts([s], {"symbol": "BANKNIFTY", "asset_class": "INDEX", "action": "SELL"})
    assert Orchestrator._conflicts([s], {"symbol": "NIFTY", "asset_class": "INDEX", "action": "SELL"})
    assert not Orchestrator._conflicts([s], {"symbol": "GOLD", "asset_class": "COMMODITY", "action": "BUY"})


def test_max_trades_setting_validation_and_api():
    from tests.test_pipeline import make
    con, st, orc, sent = make()
    orc.update_settings(max_trades=3)
    assert st.max_trades == 3
    for bad in (0, 6):
        try:
            orc.update_settings(max_trades=bad)
            assert False
        except ValueError:
            pass
    from fastapi.testclient import TestClient
    from rtw.api import create_app
    c = TestClient(create_app(orc, lambda: NOW))
    assert c.get("/api/settings").json()["max_trades"] == 3
    assert c.post("/api/settings", json={"max_trades": 2}).json()["max_trades"] == 2
    assert c.post("/api/settings", json={"max_trades": 9}).status_code == 400
    assert "trades" in c.get("/api/home").json()


def test_telegram_status_lists_all_open_trades():
    from rtw.telegram_bot import handle_command
    con, st, orc, sent = _multi(4)
    from rtw.db import open_trades
    txt = handle_command("/status", orc, NOW)
    for s, _ in open_trades(con):
        assert s.symbol.replace("&", "") in txt.replace("&", "") or s.symbol in txt


# ---------------------------------------------------------------- charts
def test_chart_payload_and_tv_symbols():
    import numpy as np
    from rtw.charts import chart_payload, tv_symbol, tv_url, resample
    idx = pd.date_range("2026-10-07 09:15", periods=60, freq="5min", tz=IST)
    df = pd.DataFrame({"open": np.arange(60) + 100.0, "high": np.arange(60) + 101.0, "low": np.arange(60) + 99.0, "close": np.arange(60) + 100.5, "volume": 1.0}, index=idx)
    p = chart_payload(df, "5m", 40, [{"label": "SL", "price": 99.0, "kind": "sl"}])
    assert len(p["candles"]) == 40 and len(p["ema20"]) == 40 and p["levels"][0]["label"] == "SL"
    assert p["candles"][-1]["t"] - p["candles"][-2]["t"] == 300
    q = chart_payload(df, "15m", 100)
    assert len(q["candles"]) == 20 and q["candles"][0]["h"] == 103.0 and q["candles"][0]["l"] == 99.0
    assert tv_symbol("NIFTY") == "NSE:NIFTY" and tv_symbol("GOLD") == "MCX:GOLD1!" and tv_symbol("BTCUSDT") == "BINANCE:BTCUSDT"
    assert tv_symbol("M&M") == "NSE:M_M" and tv_symbol("reliance") == "NSE:RELIANCE"
    assert tv_url("EURUSD").startswith("https://www.tradingview.com/chart/?symbol=FX%3AEURUSD")
    try:
        resample(df, "3m")
        assert False
    except ValueError:
        pass


def test_chart_api_symbol_levels_and_option():
    from tests.test_pipeline import make
    from fastapi.testclient import TestClient
    from rtw.api import create_app
    con, st, orc, sent = _multi(4)
    c = TestClient(create_app(orc, lambda: NOW))
    from rtw.db import open_trades
    sym = open_trades(con)[0][0].symbol                                 # a symbol with an open trade -> real levels
    r = c.get("/api/chart", params={"q": sym}).json()
    assert r["found"] and len(r["candles"]) > 30 and {l["kind"] for l in r["levels"]} >= {"entry", "sl", "target"}
    assert set(r["sr"]) == {"supports", "resistances", "zones"}
    r = c.get("/api/chart", params={"q": "tcs", "tf": "15m"}).json()  # any stock: data fetched on demand
    assert r["found"] and r["tf"] == "15m" and r["tv_url"].endswith("NSE%3ATCS")
    assert c.get("/api/chart", params={"q": "tcs", "tf": "7m"}).json()["found"] is False
    r = c.get("/api/chart", params={"q": "nifty", "strike": 24500, "cp": "CE", "expiry": "2026-10-13"}).json()
    assert r["found"] and r["option"]["cp"] == "CE" and all(x["l"] <= x["h"] for x in r["candles"])
    assert c.get("/api/chart", params={"q": "a" * 50}).status_code == 400


# ---------------------------------------------------------------- market mood
def test_mood_of_rules():
    from rtw.mood import mood_of
    assert mood_of({"regime": "TREND", "S": 0.5})["mood"] == "BULLISH"
    assert mood_of({"regime": "TREND", "S": -0.3})["mood"] == "BEARISH"
    assert mood_of({"regime": "TREND", "S": 0.05})["mood"] == "SIDEWAYS"
    assert mood_of({"regime": "RANGE", "S": 0.30})["mood"] == "SIDEWAYS"        # range regime: weak lean = sideways
    assert mood_of({"regime": "RANGE", "S": -0.6})["mood"] == "BEARISH"
    assert mood_of({"regime": "TREND", "S": 0.6})["strength"] == "strong"
    assert "range" not in mood_of({"regime": "TREND", "S": 0.0})
    assert mood_of({"regime": "TREND", "S": 0.5, "wait_reason": "NSE market band hai"}) is None
    assert mood_of({"S": 0.5}) is None and mood_of(None) is None


def test_mood_flip_needs_confirmation():
    from rtw.mood import update_state, CONFIRM_CYCLES
    st, fl = update_state({}, {"NIFTY": "BULLISH"}, NOW)
    assert fl == []                                                   # first reading adopted silently
    for i in range(CONFIRM_CYCLES - 1):
        st, fl = update_state(st, {"NIFTY": "SIDEWAYS"}, NOW + timedelta(minutes=i))
        assert fl == []
    st, fl = update_state(st, {"NIFTY": "SIDEWAYS"}, NOW + timedelta(minutes=9))
    assert len(fl) == 1 and fl[0]["from"] == "BULLISH" and fl[0]["to"] == "SIDEWAYS"
    # a single blip back and forth never flips
    st, _ = update_state(st, {"NIFTY": "BEARISH"}, NOW)
    st, fl = update_state(st, {"NIFTY": "SIDEWAYS"}, NOW)
    st, fl = update_state(st, {"NIFTY": "BEARISH"}, NOW)
    assert fl == []


def test_mood_api_markets_chart_and_telegram_alert():
    from fastapi.testclient import TestClient
    from rtw.api import create_app
    from rtw.db import get_setting, set_setting
    con, st, orc, sent = _multi(1)
    c = TestClient(create_app(orc, lambda: NOW))
    m = c.get("/api/mood").json()
    assert m["items"] and any(i["mood"] in ("BULLISH", "BEARISH", "SIDEWAYS") for i in m["items"])
    assert all("range" in i for i in m["items"] if i["mood"] == "SIDEWAYS")
    assert c.get("/api/markets/index").json()["active"] is not None
    ch = c.get("/api/chart", params={"q": "gold"}).json()
    assert ch["mood"] is None or ch["mood"]["mood"] in ("BULLISH", "BEARISH", "SIDEWAYS")
    # force a confirmed flip for a headline symbol and check the Telegram alert (cooldown respected)
    state = get_setting(con, "moods", {})
    cur = state["GOLD"]["mood"]
    other = "BEARISH" if cur != "BEARISH" else "BULLISH"
    d = orc.provider  # keep provider
    from rtw.db import load_decisions, save_decision
    dec = load_decisions(con)["GOLD"]
    dec["S"], dec["regime"] = (-0.6 if other == "BEARISH" else 0.6), "TREND"
    n0 = len(sent)
    for i in range(3):
        save_decision(con, "GOLD", NOW, dec)
        orc._update_moods(NOW + timedelta(minutes=i))
    assert get_setting(con, "moods")["GOLD"]["mood"] == other
    assert any("GOLD" in x or "Gold" in x for x in sent[n0:]) and any("trade signal nahi" in x for x in sent[n0:])
    assert get_setting(con, "mood_flips")[-1]["symbol"] == "GOLD"
    n1 = len(sent)
    dec["S"] = 0.0
    for i in range(3):                                               # flips back inside the 30-min alert gap: recorded, not re-sent
        save_decision(con, "GOLD", NOW, dec)
        orc._update_moods(NOW + timedelta(minutes=5 + i))
    assert len(sent) == n1 and get_setting(con, "mood_flips")[-1]["to"] == "SIDEWAYS"

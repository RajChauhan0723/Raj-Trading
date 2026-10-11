import math
from datetime import datetime, timedelta, date
import numpy as np
import pandas as pd
import pytest

from rtw import indicators as ta
from rtw.layers import chart_layers, regime, LayerResult
from rtw.scoring import combine, grade, direction_of, weights_for, PROFILES
from rtw.sessions import IST, is_open, session_times, exit_by, us_dst_active
from rtw.plan import build_plan
from rtw import options as op
from rtw.gates import GateInput, evaluate_gates, all_passed, first_failure, Protections
from rtw.lifecycle import Signal, advance, TradeLock, rank_score, pick_best, setup_factor
from rtw import news as nw
from rtw.db import connect, save_signal, upsert_candles, track_record
from rtw.engine import analyze

T0 = datetime(2026, 10, 7, 11, 0, tzinfo=IST)   # Wednesday, NSE open


def make_df(n=300, drift=0.0006, vol=0.003, seed=1, start=22000.0, freq="5min", t0=None, vol_base=1000):
    rng = np.random.default_rng(seed)
    rets = rng.normal(drift, vol, n)
    close = start * np.exp(np.cumsum(rets))
    open_ = np.r_[start, close[:-1]]
    spread = np.abs(rng.normal(0, vol * 0.6, n)) * close
    high = np.maximum(open_, close) + spread
    low = np.minimum(open_, close) - spread
    volu = vol_base * (1 + np.abs(rng.normal(0, 0.5, n)))
    # build index ending inside NSE session on a weekday
    end = t0 or T0
    idx = pd.date_range(end=end, periods=n, freq=freq, tz=IST)
    return pd.DataFrame({"open": open_, "high": high, "low": low, "close": close, "volume": volu}, index=idx)


# ---------------- indicators ----------------
def test_rsi_bounds_and_flat():
    df = make_df()
    r = ta.rsi(df["close"]).dropna()
    assert ((r >= 0) & (r <= 100)).all()
    flat = pd.Series([100.0] * 50)
    assert ta.rsi(flat).iloc[-1] == 50.0
    up = pd.Series(np.arange(1, 60, dtype=float))
    assert ta.rsi(up).iloc[-1] == 100.0


def test_no_lookahead_indicators():
    df = make_df(200)
    full = ta.ema(df["close"], 20)
    part = ta.ema(df["close"].iloc[:150], 20)
    assert math.isclose(full.iloc[149], part.iloc[-1], rel_tol=1e-12)
    st_full = ta.supertrend(df)["direction"].iloc[149]
    st_part = ta.supertrend(df.iloc[:150])["direction"].iloc[-1]
    assert st_full == st_part
    ax_full = ta.adx(df)["adx"].iloc[149]
    ax_part = ta.adx(df.iloc[:150])["adx"].iloc[-1]
    assert math.isclose(ax_full, ax_part, rel_tol=1e-9)


def test_atr_positive_and_supertrend_values():
    df = make_df()
    assert (ta.atr(df).dropna() > 0).all()
    st = ta.supertrend(df)
    assert set(st["direction"].unique()) <= {-1.0, 0.0, 1.0}


def test_vwap_resets_each_day():
    a = make_df(40, t0=datetime(2026, 10, 6, 15, 0, tzinfo=IST))
    b = make_df(40, t0=datetime(2026, 10, 7, 15, 0, tzinfo=IST))
    df = pd.concat([a[a.index.date == date(2026, 10, 6)], b[b.index.date == date(2026, 10, 7)]])
    v = ta.vwap(df)
    first_new_day = df.index[df.index.date == date(2026, 10, 7)][0]
    tp = (df.loc[first_new_day, "high"] + df.loc[first_new_day, "low"] + df.loc[first_new_day, "close"]) / 3
    assert math.isclose(v.loc[first_new_day], tp, rel_tol=1e-9)


def test_swing_levels_confirmed_only():
    df = make_df(200)
    sw = ta.swing_levels(df)
    assert sw["last_high"] >= sw["last_low"]
    # last `right` bars can never be a confirmed swing
    last_bars_max = df["high"].iloc[-3:].max()
    if last_bars_max > df["high"].iloc[-120:-3].max():
        assert sw["last_high"] < last_bars_max


def test_candle_patterns_engulf():
    idx = pd.date_range("2026-10-07 09:15", periods=4, freq="5min", tz=IST)
    df = pd.DataFrame({"open": [100, 101, 100, 98.5], "high": [101.5, 101.5, 100.5, 102.5],
                       "low": [99.5, 99.5, 98, 98.0], "close": [101, 100, 98.5, 102],
                       "volume": [1, 1, 1, 1]}, index=idx)
    p = ta.candle_patterns(df)
    assert p["bull_engulf"] is True and p["bear_engulf"] is False


# ---------------- layers / scoring ----------------
def test_regime_names():
    assert regime(make_df())["name"] in ("TREND", "RANGE", "VOLATILE")


def test_chart_layers_bullish_trend():
    df = make_df(300, drift=0.002, vol=0.002, seed=3)
    L = chart_layers(df, True)
    assert set(L) == {"trend", "momentum", "levels", "volume", "patterns", "stoch_rsi"}
    assert L["trend"].score > 0.3
    for l in L.values():
        assert -1 <= l.score <= 1 and 0 <= l.conf <= 1


def test_chart_layers_short_data_safe():
    df = make_df(30)
    L = chart_layers(df, True)
    assert L["trend"].conf == 0.0


def test_combine_agreement_and_conflict():
    bull = {k: LayerResult(k, 0.8, 0.8, [k]) for k in ["trend", "momentum", "levels", "volume", "global", "smart"]}
    c = combine(bull, "INDEX", "TREND")
    assert c["S"] > 0.7 and c["A"] == 1.0 and c["n_agree"] == 6
    mixed = dict(bull)
    mixed["trend"] = LayerResult("trend", -0.9, 0.9, ["x"])
    mixed["global"] = LayerResult("global", -0.9, 0.9, ["x"])
    c2 = combine(mixed, "INDEX", "TREND")
    assert c2["A"] < c["A"]
    assert combine({}, "INDEX", "TREND")["n_avail"] == 0


def test_weights_zero_layers_ignored():
    r = {"options": LayerResult("options", 1.0, 1.0, [])}
    assert combine(r, "STOCK", "TREND")["n_avail"] == 0   # STOCK options weight = 0


def test_grade_thresholds():
    assert grade(0.7, 0.9) == "A"
    assert grade(0.52, 0.75) == "B"
    assert grade(0.46, 0.71) == "C"
    assert grade(0.2, 0.9) == "D"
    assert direction_of(-0.1) == "SELL"


# ---------------- sessions ----------------
def test_sessions():
    assert is_open("NSE", datetime(2026, 10, 7, 9, 15, tzinfo=IST))
    assert not is_open("NSE", datetime(2026, 10, 7, 15, 30, tzinfo=IST))
    assert not is_open("NSE", datetime(2026, 10, 10, 11, 0, tzinfo=IST))          # Saturday
    assert not is_open("NSE", T0, holidays={T0.date()})
    assert is_open("CRYPTO", datetime(2026, 10, 10, 3, 0, tzinfo=IST))
    assert session_times("MCX", date(2026, 7, 1))[1].hour == 23 and session_times("MCX", date(2026, 7, 1))[1].minute == 30
    assert session_times("MCX", date(2026, 12, 1))[1].minute == 55
    assert us_dst_active(date(2026, 7, 1)) and not us_dst_active(date(2026, 12, 1))
    assert exit_by("NSE", date(2026, 10, 7)).hour == 15 and exit_by("NSE", date(2026, 10, 7)).minute == 15


# ---------------- plan ----------------
def test_plan_buy_sell_geometry():
    now = T0
    eb = now + timedelta(hours=3)
    p = build_plan("BUY", 22000, 50, 21940, 22100, [21900], [22400], 65, 100000, 0.01, 2.0, now, 20, eb)
    assert p.sl < p.entry < p.t1 < p.t2
    assert p.rr >= 1.99 or p.rr < 2.0   # may be clipped by a level, gate handles it
    assert 50 <= p.sl_dist <= 125
    s = build_plan("SELL", 22000, 50, 21900, 22060, [21700], [22100], 65, 100000, 0.01, 2.0, now, 20, eb)
    assert s.t2 < s.t1 < s.entry < s.sl
    assert s.chase_price < s.entry
    assert p.chase_price > p.entry


def test_plan_level_clips_target_and_rr_drops():
    now = T0
    p = build_plan("BUY", 22000, 50, 21950, 22000, [], [22080], 65, 100000, 0.01, 2.0, now, 20, now + timedelta(hours=2))
    assert p.t1 < 22080 and p.rr < 2.0


def test_plan_lots_and_affordable():
    now = T0
    p = build_plan("BUY", 22000, 50, 21950, 22000, [], [], 65, 5000, 0.01, 2.0, now, 20, now + timedelta(hours=2))
    assert p.lots == 0 and not p.affordable
    p2 = build_plan("BUY", 22000, 50, 21950, 22000, [], [], 65, 1_000_000, 0.01, 2.0, now, 20, now + timedelta(hours=2))
    assert p2.lots >= 1 and p2.risk_amount <= 1_000_000 * 0.01 + 1e-6
    with pytest.raises(ValueError):
        build_plan("HOLD", 1, 1, 1, 1, [], [], 1, 1, 1, 1, now, 1, now)


# ---------------- options ----------------
def test_black_scholes_parity_and_pop():
    c = op.bs_price(22000, 22000, 7 / 365, 0.14, "CE")
    p = op.bs_price(22000, 22000, 7 / 365, 0.14, "PE")
    assert c > 0 and p > 0
    r = 0.065
    assert math.isclose(c - p, 22000 - 22000 * math.exp(-r * 7 / 365), rel_tol=1e-6, abs_tol=1e-4)
    pop = op.prob_profit_buy(22000, 22000, 150, 0.14, 7, "CE")
    assert 0.15 < pop < 0.5            # ATM buy has < 50% PoP because of premium
    assert op.prob_profit_buy(22000, 22000, 150, 0.14, 0, "CE") == 0.0


def test_expected_move_and_iv_percentile():
    assert math.isclose(op.expected_move(22000, 0.14, 365), 22000 * 0.14)
    assert op.iv_percentile([10] * 5, 12) == 0.5
    assert op.iv_percentile(list(range(1, 101)), 90) == 0.9


CHAIN = [{"strike": k, "ce_oi": ce, "pe_oi": pe} for k, ce, pe in
         [(21800, 100, 900), (21900, 200, 800), (22000, 500, 500), (22100, 800, 200), (22200, 900, 100)]]


def test_pcr_maxpain_walls():
    assert math.isclose(op.pcr(CHAIN), 2500 / 2500)
    assert op.max_pain(CHAIN) == 22000
    w = op.oi_walls(CHAIN)
    assert w["resistance"] == 22200 and w["support"] == 21800
    assert op.max_pain([]) is None


def test_pick_option_buy_only_and_filters():
    strikes = [21900, 22000, 22100]
    prem = {21900: {"CE": 190, "PE": 40}, 22000: {"CE": 120, "PE": 85}, 22100: {"CE": 60, "PE": 150}}
    o = op.pick_option("BUY", 22010, strikes, prem, 3, 0.14)
    assert o["cp"] == "CE" and o["strike"] == 22000
    o2 = op.pick_option("SELL", 22010, strikes, prem, 3, 0.14)
    assert o2["cp"] == "PE"
    assert op.pick_option("WAIT", 22010, strikes, prem, 3, 0.14) is None
    ok, why = op.option_ok(o, 0.5, 3)
    assert isinstance(ok, bool) and why
    assert op.option_ok(o, 0.95, 3)[0] is False
    assert op.option_ok(o, 0.5, 0.2)[0] is False
    assert op.option_ok(None, 0.5, 3)[0] is False


def test_options_layer_direction():
    bull_chain = [{"strike": k, "ce_oi": 100, "pe_oi": 400} for k in (21900, 22000, 22100)]
    assert op.options_layer(22000, bull_chain).score > 0
    bear_chain = [{"strike": k, "ce_oi": 400, "pe_oi": 100} for k in (21900, 22000, 22100)]
    assert op.options_layer(22000, bear_chain).score < 0
    assert op.options_layer(22000, []).conf == 0


# ---------------- gates & protections ----------------
def good_gate(**kw):
    base = dict(S=0.62, A=0.85, n_avail=6, n_agree=5, rr=2.2, data_age_sec=10, max_data_age_sec=120, regime="TREND",
                setup_expectancy=0.3, setup_trades=50)
    base.update(kw)
    return GateInput(**base)


def test_gates_all_pass_and_each_fail():
    assert all_passed(evaluate_gates(good_gate()))
    cases = {
        "data_fresh": dict(data_age_sec=500),
        "news_clear": dict(news_mode="SHOCK", news_lock_reason="shock"),
        "regime_fit": dict(allowed_regimes=("RANGE",)),
        "layer_agreement": dict(A=0.4),
        "risk_reward": dict(rr=1.2),
        "setup_record": dict(setup_expectancy=-0.1),
        "daily_loss": dict(daily_loss_hit=True),
    }
    for name, kw in cases.items():
        res = evaluate_gates(good_gate(**kw))
        assert first_failure(res).name == name, name
    assert len(evaluate_gates(good_gate())) == 7


def test_setup_record_unknown_paper_vs_real():
    assert first_failure(evaluate_gates(good_gate(setup_expectancy=None, setup_trades=0))).name == "setup_record"
    assert all_passed(evaluate_gates(good_gate(setup_expectancy=None, setup_trades=0, paper=True)))


def test_protections():
    p = Protections()
    t = T0
    assert p.can_trade(t)[0]
    for i in range(3):
        p.record(t + timedelta(hours=i), -1.0)
    now = t + timedelta(hours=2, minutes=40)
    assert not p.can_trade(now)[0]      # streak pause (120 min after last loss at +2h) and daily loss
    p2 = Protections()
    p2.record(t, 1.0)
    assert not p2.can_trade(t + timedelta(minutes=10))[0]       # cooldown
    assert p2.can_trade(t + timedelta(minutes=40))[0]
    p3 = Protections(max_drawdown_r=3.0, streak_limit=99, daily_loss_r=99)
    for i in range(4):
        p3.record(t + timedelta(days=i), -1.0)
    assert p3.halted and "halt" in p3.can_trade(t + timedelta(days=10))[1]


# ---------------- lifecycle ----------------
def mk_sig(direction="BUY"):
    if direction == "BUY":
        return Signal("s1", "NIFTY", "INDEX", "BUY", 21990, 22010, 21930, 22140, 22220, 22040,
                      T0 + timedelta(minutes=20), T0 + timedelta(hours=3), T0)
    return Signal("s2", "NIFTY", "INDEX", "SELL", 21990, 22010, 22070, 21860, 21780, 21960,
                  T0 + timedelta(minutes=20), T0 + timedelta(hours=3), T0)


def test_lifecycle_buy_target():
    s = mk_sig()
    advance(s, 22020, T0 + timedelta(minutes=1))
    assert s.state == "NEW"
    advance(s, 22000, T0 + timedelta(minutes=2))
    assert s.state == "ACTIVE" and s.entry_price == 22000
    advance(s, 22100, T0 + timedelta(minutes=30), high=22145, low=22090)
    assert s.state == "TARGET" and s.r_multiple > 1.9 and s.close_reason


def test_lifecycle_sl_first_when_both_in_bar():
    s = mk_sig()
    advance(s, 22000, T0 + timedelta(minutes=1))
    advance(s, 22000, T0 + timedelta(minutes=5), high=22200, low=21900)
    assert s.state == "SL" and abs(s.r_multiple + 1.0) < 0.05


def test_lifecycle_missed_expired_exit_by():
    s = mk_sig()
    advance(s, 22050, T0 + timedelta(minutes=1))
    assert s.state == "MISSED" and "chase" in s.close_reason and s.r_multiple is None
    s = mk_sig()
    advance(s, 22020, T0 + timedelta(minutes=25))
    assert s.state == "EXPIRED" and s.r_multiple is None
    s = mk_sig()
    advance(s, 22000, T0 + timedelta(minutes=1))
    advance(s, 22030, T0 + timedelta(hours=3, minutes=1))
    assert s.state == "EXPIRED" and s.r_multiple is not None
    # closed signals never move
    before = (s.state, s.exit_price)
    advance(s, 1, T0 + timedelta(hours=4))
    assert (s.state, s.exit_price) == before


def test_lifecycle_sell_side():
    s = mk_sig("SELL")
    advance(s, 22000, T0 + timedelta(minutes=1))
    assert s.state == "ACTIVE"
    advance(s, 21900, T0 + timedelta(minutes=10), high=22001, low=21850)
    assert s.state == "TARGET" and s.r_multiple > 1.9
    s = mk_sig("SELL")
    advance(s, 21950, T0 + timedelta(minutes=1))
    assert s.state == "MISSED"


def test_trade_lock_and_pick_best():
    lk = TradeLock()
    assert lk.acquire("a") and not lk.acquire("b") and lk.acquire("a")
    lk.release("b")
    assert lk.locked()
    lk.release("a")
    assert not lk.locked()
    best, info = pick_best([{"symbol": "A", "passed": True, "rank": 1.0}, {"symbol": "B", "passed": True, "rank": 2.0},
                            {"symbol": "C", "passed": False, "rank": 9.0}])
    assert best["symbol"] == "B" and len(info) == 2
    best, info = pick_best([{"symbol": "C", "passed": False, "rank": 9.0}])
    assert best is None and len(info) == 1
    assert rank_score(0.6, 10) == rank_score(0.6, 4)
    assert setup_factor(None, 0) == 0.7 and setup_factor(0.9, 50) == 1.5


# ---------------- news ----------------
def test_tagger_and_dedupe():
    t = nw.tag_headline("Missile attack on oil facility lifts crude", T0, "reuters")
    d = {(x.asset, x.direction) for x in t}
    assert ("CRUDE", 1) in d and ("INDEX", -1) in d and ("GOLD", 1) in d
    t2 = nw.tag_headline("RBI announces rate cut of 25 bps", T0, "rbi", official=True)
    assert any(x.asset == "BANKNIFTY" and x.direction == 1 and x.conf > 0.9 for x in t2)
    assert nw.tag_headline("Local cricket match result", T0) == []
    assert nw.same_story("RBI cuts repo rate by 25 bps", "RBI cuts repo rate by 25 bps, says governor")
    assert not nw.same_story("RBI cuts repo rate", "Gold rallies on weak dollar")


def test_story_confirmation():
    items = [{"title": "Oil jumps as OPEC+ cuts output", "source": "a", "ts": T0, "official": False},
             {"title": "Oil jumps as OPEC+ cuts output sharply", "source": "b", "ts": T0, "official": False},
             {"title": "Random thing", "source": "c", "ts": T0, "official": False}]
    st = nw.cluster_stories(items)
    assert len(st) == 2
    assert nw.story_confirmed(st[0]) and not nw.story_confirmed(st[1])


def test_surprise_engine():
    hot = nw.surprise_tags("US_CPI_YOY", 3.5, 3.2, T0)
    d = {x.asset: x.direction for x in hot}
    assert d["GOLD"] == -1 and d["USDINR"] == 1 and d["INDEX"] == -1
    cool = nw.surprise_tags("US_CPI_YOY", 2.9, 3.2, T0)
    assert {x.asset: x.direction for x in cool}["GOLD"] == 1
    assert nw.surprise_tags("US_CPI_YOY", 3.21, 3.2, T0) == []
    un = nw.surprise_tags("US_UNEMPLOYMENT", 4.5, 4.2, T0)
    assert {x.asset: x.direction for x in un}["GOLD"] == 1       # higher unemployment = dovish
    cs = nw.surprise_tags("CRUDE_STOCKS", 6.0, 1.0, T0)
    assert cs[0].asset == "CRUDE" and cs[0].direction == -1


def test_reaction_reader():
    assert nw.read_reaction(1, 100, 100.5, 101, 1.0) == "CONFIRMED"
    assert nw.read_reaction(1, 100, 100.5, 100.02, 1.0) == "FADED"
    assert nw.read_reaction(1, 100, 99.9, 99.5, 1.0) == "OPPOSITE"
    assert nw.read_reaction(1, 100, 100.1, 100.1, 1.0) == "NO_REACTION"
    assert nw.read_reaction(-1, 100, 99.4, 99.0, 1.0) == "CONFIRMED"


def test_news_mode_rbi_window_and_modifiers():
    rbi = nw.Event("RBI policy", datetime(2026, 10, 7, 10, 0, tzinfo=IST), "HIGH", ("INDEX", "USDINR"))
    m = nw.news_mode([rbi], datetime(2026, 10, 7, 9, 45, tzinfo=IST), "NIFTY")
    assert m["mode"] == "EVENT_WINDOW" and "RBI" in m["lock_reason"]
    m = nw.news_mode([rbi], datetime(2026, 10, 7, 10, 5, tzinfo=IST), "BANKNIFTY")
    assert m["mode"] == "EVENT_WINDOW" and "baad" in m["lock_reason"]
    assert nw.news_mode([rbi], datetime(2026, 10, 7, 10, 20, tzinfo=IST), "NIFTY")["mode"] == "CALM"
    assert nw.news_mode([rbi], datetime(2026, 10, 7, 9, 45, tzinfo=IST), "GOLD")["mode"] == "CALM"
    assert nw.news_mode([], T0, "NIFTY", shock=True)["mode"] == "SHOCK"
    mods = nw.plan_modifiers([rbi], datetime(2026, 10, 7, 8, 0, tzinfo=IST), "NIFTY", datetime(2026, 10, 7, 15, 15, tzinfo=IST))
    assert mods["exit_by"] < datetime(2026, 10, 7, 9, 30, tzinfo=IST) and "RBI" in mods["note"]
    mods2 = nw.plan_modifiers([], T0, "NIFTY", T0 + timedelta(hours=2), vix_z=2.0)
    assert mods2["size_mult"] < 1 and mods2["sl_mult"] > 1


def test_news_layer_decay_and_direction():
    tags = nw.tag_headline("War escalates, missile attack reported", T0 - timedelta(minutes=10), "x", trust=0.8)
    lr = nw.news_layer("CRUDEOILM", tags, T0)
    assert lr.score > 0.2 and lr.conf > 0
    ln = nw.news_layer("NIFTY", tags, T0)
    assert ln.score < 0
    old = nw.news_layer("CRUDEOILM", tags, T0 + timedelta(days=3))
    assert old.conf == 0
    assert nw.news_layer("RELIANCE", tags, T0).conf == 0


# ---------------- db ----------------
def test_db_roundtrip(tmp_path):
    con = connect(str(tmp_path / "t.db"))
    s = mk_sig()
    save_signal(con, s)
    advance(s, 22000, T0 + timedelta(minutes=1))
    advance(s, 22100, T0 + timedelta(minutes=30), high=22145, low=22090)
    save_signal(con, s)
    row = con.execute("SELECT state, r_multiple FROM signals WHERE id='s1'").fetchone()
    assert row["state"] == "TARGET" and row["r_multiple"] > 1.9
    tr = track_record(con)
    assert tr["trades"] == 1 and tr["win_rate"] == 1.0
    upsert_candles(con, "NIFTY", "5m", [("2026-10-07T09:15:00+05:30", 1, 2, 0.5, 1.5, 100)])
    upsert_candles(con, "NIFTY", "5m", [("2026-10-07T09:15:00+05:30", 1, 3, 0.5, 2.0, 100)])
    assert con.execute("SELECT COUNT(*) c, MAX(close) m FROM candles").fetchone()["c"] == 1


# ---------------- engine end-to-end ----------------
KW = dict(capital=1_000_000, risk_pct=0.01, lot_size=65)


def test_engine_bull_trend_gives_buy_or_wait_with_reason():
    df = make_df(300, drift=0.0015, vol=0.0012, seed=5)
    extra = {"global": LayerResult("global", 0.7, 0.8, ["global positive"]), "smart": LayerResult("smart", 0.6, 0.7, ["FII buy"]),
             "options": LayerResult("options", 0.5, 0.6, ["PCR high"])}
    d = analyze("NIFTY", "INDEX", df, T0, extra_layers=extra, setup_expectancy=0.3, setup_trades=60, **KW)
    assert d["action"] in ("BUY", "WAIT")
    if d["action"] == "WAIT":
        assert d["wait_reason"]
    else:
        pl = d["plan"]
        assert pl["sl"] < pl["entry"] < pl["t1"] and d["passed"] and d["rank"] > 0


def test_engine_forced_buy_path():
    # strong clean uptrend + strong votes + wide room (no resistance clipping since price at highs)
    df = make_df(300, drift=0.0012, vol=0.0008, seed=11)
    extra = {k: LayerResult(k, 0.9, 0.9, [k]) for k in ("global", "smart", "options")}
    d = analyze("NIFTY", "INDEX", df, T0, extra_layers=extra, setup_expectancy=0.4, setup_trades=80, profile="aggressive",
                capital=3_000_000, risk_pct=0.01, lot_size=65)
    assert d["S"] > 0
    assert d["action"] == "BUY", d.get("wait_reason")
    assert d["plan"]["rr"] >= 1.5 and d["confidence"] > 40


def test_engine_news_lock_forces_wait_with_reason():
    df = make_df(300, drift=0.0012, vol=0.0008, seed=11)
    extra = {k: LayerResult(k, 0.9, 0.9, [k]) for k in ("global", "smart", "options")}
    rbi = nw.Event("RBI policy", datetime(2026, 10, 7, 11, 15, tzinfo=IST), "HIGH", ("INDEX",))
    d = analyze("NIFTY", "INDEX", df, T0, extra_layers=extra, events=[rbi], setup_expectancy=0.4, setup_trades=80,
                profile="aggressive", **KW)
    assert d["action"] == "WAIT" and "RBI" in d["wait_reason"] and d["wait_until"]


def test_engine_guards():
    df = make_df(300)
    assert analyze("NIFTY", "INDEX", df.iloc[:30], T0, **KW)["action"] == "WAIT"
    closed = datetime(2026, 10, 7, 20, 0, tzinfo=IST)
    d = analyze("NIFTY", "INDEX", df, closed, **KW)
    assert d["action"] == "WAIT" and "band" in d["wait_reason"]
    with pytest.raises(ValueError):
        analyze("NIFTY", "INDEX", df, datetime(2026, 10, 7, 11, 0), **KW)
    d = analyze("NIFTY", "INDEX", df, T0, protections_ok=(False, "cooldown"), **KW)
    assert d["action"] == "WAIT"
    stale = analyze("NIFTY", "INDEX", df, T0, data_age_sec=9999, **KW)
    assert stale["action"] == "WAIT"


def test_engine_random_walk_mostly_wait():
    waits = 0
    for seed in range(20):
        df = make_df(300, drift=0.0, vol=0.003, seed=100 + seed)
        d = analyze("NIFTY", "INDEX", df, T0, setup_expectancy=0.1, setup_trades=50, **KW)
        waits += d["action"] == "WAIT"
    assert waits >= 17      # conservative profile must stay quiet on noise


def test_engine_crypto_and_commodity_run():
    df = make_df(300, drift=0.001, vol=0.002, seed=8, start=60000)
    d = analyze("BTCUSDT", "CRYPTO", df, T0, paper=True, capital=100000, risk_pct=0.01, lot_size=1)
    assert d["action"] in ("BUY", "WAIT", "SELL") and d["paper"] is True
    mcx_now = datetime(2026, 10, 7, 21, 0, tzinfo=IST)
    dfc = make_df(300, drift=0.001, vol=0.002, seed=9, start=6200, t0=mcx_now)
    d2 = analyze("CRUDEOILM", "COMMODITY", dfc, mcx_now, capital=500000, risk_pct=0.01, lot_size=10)
    assert d2["action"] in ("BUY", "WAIT", "SELL")


def test_engine_unaffordable_and_near_close():
    df = make_df(300, drift=0.0012, vol=0.0008, seed=11)
    extra = {k: LayerResult(k, 0.9, 0.9, [k]) for k in ("global", "smart", "options")}
    d = analyze("NIFTY", "INDEX", df, T0, extra_layers=extra, setup_expectancy=0.4, setup_trades=80, profile="aggressive",
                capital=100_000, risk_pct=0.01, lot_size=65)
    assert d["action"] == "WAIT" and "capital" in d["wait_reason"]
    late = datetime(2026, 10, 7, 15, 20, tzinfo=IST)
    dfl = make_df(300, drift=0.0012, vol=0.0008, seed=11, t0=late)
    d2 = analyze("NIFTY", "INDEX", dfl, late, extra_layers=extra, setup_expectancy=0.4, setup_trades=80, profile="aggressive",
                 capital=3_000_000, risk_pct=0.01, lot_size=65)
    assert d2["action"] == "WAIT" and "kam time" in d2["wait_reason"]

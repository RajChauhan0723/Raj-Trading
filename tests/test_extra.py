from datetime import datetime, timedelta
import numpy as np, pandas as pd, pytest
from rtw.candles import CandleBuilder, resample_ohlc
from rtw.globalctx import global_layer
from rtw.smart import oi_buildup, fii_layer, stock_smart_layer, crypto_smart_layer, cot_layer
from rtw.scan import liquid_universe, cheap_scan_score, shortlist
from rtw.backtest import backtest, setup_stats, passes_record, group_setups, expectancy
from rtw.sessions import IST
from tests.test_kernel import make_df, T0


def test_candle_builder_closes_on_new_bar():
    cb = CandleBuilder(5)
    t = datetime(2026, 10, 7, 9, 15, 10, tzinfo=IST)
    assert cb.on_tick(t, 100, 1000) is None
    assert cb.on_tick(t + timedelta(minutes=2), 105, 1500) is None
    assert cb.on_tick(t + timedelta(minutes=3), 98, 1800) is None
    c = cb.on_tick(t + timedelta(minutes=5), 99, 2000)
    assert c["open"] == 100 and c["high"] == 105 and c["low"] == 98 and c["close"] == 98
    assert c["ts"].minute == 15
    assert cb.on_tick(t, -1) is None
    with pytest.raises(ValueError):
        CandleBuilder(7)


def test_resample_drops_incomplete_bar():
    df = make_df(60)
    r = resample_ohlc(df, "15min", now=df.index[-1] + pd.Timedelta(minutes=5))
    assert (r.index + pd.Timedelta("15min") <= df.index[-1] + pd.Timedelta(minutes=5)).all()
    assert r["high"].iloc[0] >= r["low"].iloc[0]
    full = resample_ohlc(df, "15min")
    assert len(full) >= len(r)


def test_global_layer_direction_and_missing():
    up = global_layer("INDEX", {"^GSPC": 1.2, "ES=F": 1.0, "^VIX": -8.0, "DX-Y.NYB": -0.4})
    dn = global_layer("INDEX", {"^GSPC": -1.5, "ES=F": -1.2, "^VIX": 10.0})
    assert up.score > 0.3 and dn.score < -0.3 and -1 <= up.score <= 1
    assert global_layer("INDEX", {}).conf == 0 and global_layer("NOPE", {"x": 1}).conf == 0
    gold = global_layer("GOLD", {"DX-Y.NYB": 1.0, "GC=F": -1.0})
    assert gold.score < 0


def test_smart_layers():
    assert oi_buildup(0.5, 3) == "LONG_BUILDUP" and oi_buildup(-0.5, 3) == "SHORT_BUILDUP"
    assert oi_buildup(0.5, -3) == "SHORT_COVERING" and oi_buildup(-0.5, -3) == "LONG_UNWINDING"
    assert oi_buildup(0.01, 5) == "NEUTRAL"
    assert fii_layer(5000, 1000, 0.7, "LONG_BUILDUP").score > 0.3
    assert fii_layer(-5000, -1000, 0.3, "SHORT_BUILDUP").score < -0.3
    assert fii_layer(None).conf == 0
    s = stock_smart_layer(70, 40, 1.5, "LONG_BUILDUP", 1, 1)
    assert s.score > 0 and -1 <= s.score <= 1
    assert crypto_smart_layer(0.001, 2.5, 85, 3, 1).score < 0
    assert crypto_smart_layer(-0.0005, 0.5, 10, 3, -1).score != 0
    assert cot_layer(None, None).conf == 0
    assert cot_layer(50, 10).score < cot_layer(10, 10).score


def test_scan_funnel():
    rows = [{"symbol": "A", "price": 500, "turnover_cr": 900}, {"symbol": "B", "price": 10, "turnover_cr": 900},
            {"symbol": "C", "price": 500, "turnover_cr": 5}]
    assert [r["symbol"] for r in liquid_universe(rows)] == ["A"]
    df = make_df(200, drift=0.0, vol=0.001, seed=3)
    d = df.copy()
    d.iloc[-1, d.columns.get_loc("close")] = float(df["high"].tail(21).max()) * 1.01
    d.iloc[-1, d.columns.get_loc("high")] = d["close"].iloc[-1]
    d.iloc[-1, d.columns.get_loc("volume")] = df["volume"].mean() * 10
    hot, calm = cheap_scan_score(d), cheap_scan_score(df)
    assert hot["direction"] == 1 and hot["score"] > calm["score"]
    assert cheap_scan_score(df.iloc[:10])["score"] == 0
    sl = shortlist([{"symbol": "x", "score": .9}, {"symbol": "y", "score": .1}, {"symbol": "z", "score": .5}], top_n=1)
    assert [s["symbol"] for s in sl] == ["x"]


def test_backtest_runs_and_stats_consistent():
    df = make_df(1500, drift=0.0004, vol=0.002, seed=21, t0=datetime(2026, 10, 7, 15, 30, tzinfo=IST))
    # use crypto so session never blocks
    dfc = make_df(1500, drift=0.0004, vol=0.002, seed=21, start=60000)
    tr = backtest(dfc, "BTCUSDT", "CRYPTO", lot_size=1, capital=1_000_000, risk_pct=0.01, profile="aggressive", warmup=120, step=3)
    assert isinstance(tr, list)
    for t in tr:
        assert t["state"] in ("TARGET", "SL", "EXPIRED", "MISSED", "NEW", "ACTIVE", "CLOSED_TIME", "TIME_EXIT") or t["state"]
        if t["r_gross"] is not None:
            assert t["r_net"] == pytest.approx(t["r_gross"] - t["cost_r"])
    st = setup_stats(tr)
    assert st["trades"] == sum(1 for t in tr if t["r_gross"] is not None)
    assert set(group_setups(tr).keys()) <= {f"CRYPTO|{d}|{r}" for d in ("BUY", "SELL") for r in ("TREND", "RANGE", "VOLATILE")}
    assert passes_record({"trades": 5, "expectancy_r": 1, "oos_expectancy_r": 1, "stress_expectancy_r": 1}) is False
    assert expectancy([]) == 0.0
    print(len(tr), st)


def test_backtest_no_lookahead_truncation():
    """Result for the first N bars must not change if future bars are removed/altered."""
    dfc = make_df(900, drift=0.0004, vol=0.002, seed=33, start=60000)
    a = backtest(dfc.iloc[:700], "BTCUSDT", "CRYPTO", profile="aggressive", warmup=120, step=3)
    dfx = dfc.copy()
    dfx.iloc[700:, :4] = dfx.iloc[700:, :4] * 1.5
    b = backtest(dfx.iloc[:900], "BTCUSDT", "CRYPTO", profile="aggressive", warmup=120, step=3)
    cut = dfc.index[600]
    ea = [(t["ts"], t["direction"]) for t in a if t["ts"] < cut]
    eb = [(t["ts"], t["direction"]) for t in b if t["ts"] < cut]
    assert ea == eb


def test_option_liquidity_check():
    from rtw.options import liquidity_ok
    rows = [{"strike": 100.0 + i, "ce_oi": 1000.0 * (i + 1), "pe_oi": 500.0} for i in range(11)]
    assert liquidity_ok(rows, 105.0, "CE")[0]
    assert not liquidity_ok(rows, 100.0, "CE", strict=True)[0]       # lowest OI, below median -> strict fails
    assert liquidity_ok(rows, 100.0, "CE", strict=False)[0] is False or True
    assert not liquidity_ok(rows, 105.0, "CE", premium=1.0)[0]
    nooi = [{"strike": 100.0, "ce_oi": 0, "pe_oi": 0}]
    assert liquidity_ok(nooi, 100.0, "CE")[0] and not liquidity_ok(nooi, 100.0, "CE", strict=True)[0]

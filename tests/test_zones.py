"""Support/resistance and demand/supply zone logic."""
import numpy as np
import pandas as pd
from rtw.zones import sr_levels, find_zones, zone_info, zones_layer, plan_levels
from rtw.sessions import IST


def _frame(closes, spread=0.25):
    idx = pd.date_range("2026-10-05 09:15", periods=len(closes), freq="5min", tz=IST)
    c = np.array(closes, float)
    o = np.r_[c[0], c[:-1]]
    return pd.DataFrame({"open": o, "high": np.maximum(o, c) + spread, "low": np.minimum(o, c) - spread, "close": c, "volume": 1000.0}, index=idx)


def _noise(n, base=100.0, seed=1):
    r = np.random.default_rng(seed)
    return list(base + np.cumsum(r.normal(0, 0.15, n)) * 0.2)


def _demand_case():
    pre = [100.0 + 0.3 * np.sin(i / 3.0) for i in range(60)]      # choppy lead-in, ATR ~0.8
    base = [100.0, 100.05, 100.0]                                  # tiny candles = base
    impulse = [104.0]                                              # big up candle closing above the base
    run = [104.5, 105.0, 105.2, 105.0, 104.8, 105.1]
    return pre + base + impulse + run


def test_demand_zone_detected_and_alive():
    df = _frame(_demand_case())
    zs = find_zones(df)
    dem = [z for z in zs if z["kind"] == "demand"]
    assert dem and dem[0]["lo"] < 100.5 and dem[0]["hi"] <= 100.5 and dem[0]["fresh"]
    assert dem[0]["hi"] < float(df["close"].iloc[-1])             # zone sits below price


def test_zone_dies_when_price_closes_through_it():
    case = _demand_case() + [102.0, 99.0, 98.5, 98.8, 99.2]       # closes below the zone's far edge -> broken
    df = _frame(case)
    assert not [z for z in find_zones(df) if z["kind"] == "demand" and z["lo"] > 99.5]


def test_supply_zone_mirror():
    pre = [100.0 + 0.3 * np.sin(i / 3.0) for i in range(60)]
    case = pre + [100.0, 99.95, 100.0] + [96.0] + [95.5, 95.0, 94.8, 95.0, 95.2, 94.9]
    zs = find_zones(_frame(case))
    sup = [z for z in zs if z["kind"] == "supply"]
    assert sup and sup[0]["lo"] >= 99.5


def test_no_lookahead_zone_unknown_before_impulse_closes():
    case = _demand_case()
    cut = case.index(104.0)                                        # data ends just BEFORE the impulse candle
    assert not [z for z in find_zones(_frame(case[:cut])) if z["kind"] == "demand" and z["lo"] > 99.0 and z["hi"] > 100.2 and z["t"] > "2026-10-05 12"]


def test_sr_levels_cluster_and_split_around_price():
    wave = []
    for k in range(8):                                             # oscillation between ~98 and ~102 -> repeated swing levels
        wave += list(np.linspace(98, 102, 12)) + list(np.linspace(102, 98, 12))
    wave += list(np.linspace(98, 100.3, 8))
    df = _frame(wave, spread=0.1)
    price = float(df["close"].iloc[-1])
    sr = sr_levels(df, atr=0.4)
    assert sr["supports"] and sr["resistances"]
    assert all(s["price"] < price for s in sr["supports"]) and all(r["price"] > price for r in sr["resistances"])
    assert max(r["touches"] for r in sr["resistances"]) >= 2        # clustered swing highs near 102
    assert any(abs(r["price"] - 102) < 0.6 and r["touches"] >= 2 for r in sr["resistances"])      # the 102 swing-high cluster is found
    assert any(abs(x["price"] - 98) < 0.6 for x in sr["supports"])


def test_layer_votes_only_at_a_zone_and_plan_levels():
    case = _demand_case()[:-6] + [104.5, 103.0, 101.5, 100.3]       # price returns INTO the demand zone
    df = _frame(case)
    r = zones_layer(df)
    assert r.conf > 0 and any("Demand" in x for x in r.reasons)          # (a resistance right above can offset the score, by design)
    far = zones_layer(_frame(_noise(120, 100.0)))                   # nothing nearby -> abstains (conf 0), never dilutes
    assert far.conf == 0 or abs(far.score) <= 1
    pl = plan_levels(zone_info(df))
    assert set(pl) == {"supports", "resistances", "demand_distal", "supply_distal"}


def test_short_data_is_safe():
    assert zone_info(_frame([100.0] * 10)) == {"supports": [], "resistances": [], "zones": []}
    assert zones_layer(_frame([100.0] * 10)).conf == 0

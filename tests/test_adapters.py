from datetime import date, datetime, timedelta
import pandas as pd
from rtw.adapters import angel as A, nse as N, crypto as C, newsfeeds as NF, calendar as CAL, yf as Y
from rtw.news import tag_headline
from rtw.options import options_layer
from rtw.sessions import IST

NOW = datetime(2026, 10, 7, 11, 2, tzinfo=IST)


def test_angel_candles_and_master_helpers():
    resp = {"status": True, "data": [["2026-10-07T09:15:00+05:30", 100, 101, 99, 100.5, 1000], ["2026-10-07T09:20:00+05:30", 100.5, 102, 100, 101, 800]]}
    df = A.parse_candles(resp)
    assert list(df.columns) == ["open", "high", "low", "close", "volume"] and len(df) == 2 and str(df.index.tz) == "Asia/Kolkata"
    assert A.parse_candles({"data": None}) is None
    master = [
        {"token": "1", "symbol": "GOLDM05NOV26FUT", "name": "GOLDM", "expiry": "05NOV2026", "lotsize": "1", "instrumenttype": "FUTCOM", "exch_seg": "MCX", "strike": "-1"},
        {"token": "2", "symbol": "GOLDM05OCT26FUT", "name": "GOLDM", "expiry": "05OCT2026", "lotsize": "1", "instrumenttype": "FUTCOM", "exch_seg": "MCX", "strike": "-1"},
        {"token": "3", "symbol": "GOLDM05DEC26FUT", "name": "GOLDM", "expiry": "05DEC2026", "lotsize": "1", "instrumenttype": "FUTCOM", "exch_seg": "MCX", "strike": "-1"},
        {"token": "9", "symbol": "Nifty 50", "name": "NIFTY", "expiry": "", "lotsize": "1", "instrumenttype": "AMXIDX", "exch_seg": "NSE", "strike": "-1"},
        {"token": "5", "symbol": "RELIANCE-EQ", "name": "RELIANCE", "expiry": "", "lotsize": "1", "instrumenttype": "", "exch_seg": "NSE", "strike": "-1"},
        {"token": "7", "symbol": "NIFTY14OCT2624500CE", "name": "NIFTY", "expiry": "14OCT2026", "lotsize": "65", "instrumenttype": "OPTIDX", "exch_seg": "NFO", "strike": "2450000.000000"},
        {"token": "8", "symbol": "NIFTY14OCT2624500PE", "name": "NIFTY", "expiry": "14OCT2026", "lotsize": "65", "instrumenttype": "OPTIDX", "exch_seg": "NFO", "strike": "2450000.000000"},
    ]
    assert A.front_future(master, "GOLDM", "MCX", date(2026, 10, 3), 3)["token"] == "1"      # 05OCT is within roll window -> next
    assert A.front_future(master, "GOLDM", "MCX", date(2026, 9, 20), 3)["token"] == "2"
    assert A.equity_row(master, "RELIANCE")["token"] == "5" and A.index_row(master, "NIFTY")["token"] == "9"
    assert A.lot_from_master(master, "NIFTY", "NFO", "OPTIDX") == 65
    assert A.option_expiries(master, "NIFTY", date(2026, 10, 7)) == [date(2026, 10, 14)]
    assert A.option_token(master, "NIFTY", date(2026, 10, 14), 24500.0, "PE")["token"] == "8"
    assert A.parse_expiry("14OCT2026") == date(2026, 10, 14) and A.parse_expiry("x") is None


def test_nse_chain_parsers():
    df = pd.DataFrame({"Strike Price": [24400, 24500, 24600], "CE OI": [100, 500, 900], "PE OI": [900, 600, 100], "CE LTP": [150, 90, 50],
                       "PE LTP": [40, 80, 140], "CE IV": [14, 13.5, 13], "PE IV": [14.5, 14, 13.8], "CE Chng in OI": [1, 2, 3], "Expiry Date": ["14-Oct-2026"] * 3})
    rows = N.chain_from_df(df, date(2026, 10, 14))
    assert len(rows) == 3 and rows[1]["ce_oi"] == 500 and rows[1]["pe_ltp"] == 80 and abs(rows[1]["ce_iv"] - 0.135) < 1e-9
    assert N.chain_from_df(df, date(2026, 10, 21)) == []
    assert N.chain_from_df(pd.DataFrame({"x": [1]})) == []
    j = {"records": {"expiryDates": ["14-Oct-2026"], "underlyingValue": 24510.0, "data": [
        {"strikePrice": 24500, "expiryDate": "14-Oct-2026", "CE": {"openInterest": 10, "lastPrice": 90, "impliedVolatility": 13.5}, "PE": {"openInterest": 20, "lastPrice": 80, "impliedVolatility": 14}}]}}
    rows, exp, und = N.chain_from_json(j)
    assert exp == "14-Oct-2026" and und == 24510.0 and rows[0]["pe_oi"] == 20
    assert 0.13 < N.atm_iv(rows, 24510) < 0.15
    # chain with no OI must give no vote
    assert options_layer(24500, [{"strike": 24500, "ce_oi": 0, "pe_oi": 0}], 0.4).conf == 0


def test_crypto_yf_parsers():
    k = [[1760000000000 + i * 300000, "100", "101", "99", "100.5", "10", 0] for i in range(5)]
    df = C.parse_klines(k, pd.Timestamp(1760000000000 + 4 * 300000, unit="ms", tz="UTC").to_pydatetime())
    assert len(df) == 4 and df["close"].iloc[0] == 100.5            # last bar not finished -> dropped
    assert C.parse_klines([]) is None
    raw = pd.DataFrame({"Open": [1.0, 2.0], "High": [2, 3], "Low": [0.5, 1], "Close": [1.5, 2.5], "Volume": [10, 20]},
                       index=pd.to_datetime(["2026-10-07 04:00", "2026-10-07 04:05"], utc=True))
    n = Y.normalize(raw)
    assert str(n.index.tz) == "Asia/Kolkata" and list(n.columns)[:4] == ["open", "high", "low", "close"]
    mi = raw.copy(); mi.columns = pd.MultiIndex.from_product([raw.columns, ["^NSEI"]])
    assert Y.normalize(mi) is not None
    assert len(Y.drop_open_bar(n, datetime(2026, 10, 7, 9, 36, tzinfo=IST))) == 1


RSS = """<?xml version="1.0"?><rss version="2.0"><channel><title>t</title>
<item><title>Crude surges as OPEC+ announces production cuts</title><link>http://a/1</link><pubDate>Wed, 07 Oct 2026 05:00:00 GMT</pubDate></item>
<item><title>OPEC+ production cuts push crude higher - Reuters</title><link>http://b/2</link><pubDate>Wed, 07 Oct 2026 05:02:00 GMT</pubDate></item>
</channel></rss>"""


def test_rss_gdelt_and_story_confirmation():
    items = NF.parse_rss(RSS, "feed", 0.6, False, NOW)
    assert len(items) == 2 and items[0]["ts"].tzinfo is not None
    assert NF.url_hash("u", "t") == NF.url_hash("U", "x")
    g = NF.parse_gdelt({"articles": [{"title": "War escalates", "url": "u", "domain": "d.com", "seendate": "20261007T050000Z"}]}, NOW)
    assert g[0]["ts"].hour == 10 and g[0]["source"].startswith("GDELT")
    assert any(t.asset == "CRUDE" and t.direction == 1 for t in tag_headline(items[0]["title"], NOW))


def test_calendar():
    ff = CAL.parse_ff([{"title": "CPI y/y", "country": "USD", "date": "2026-10-14T08:30:00-04:00", "impact": "High"},
                       {"title": "Minor", "country": "USD", "date": "2026-10-14T08:30:00-04:00", "impact": "Low"},
                       {"title": "Bank Holiday", "country": "USD", "date": "2026-10-14T00:00:00-04:00", "impact": "Holiday"}])
    assert len(ff) == 1 and ff[0].when.hour == 18 and ff[0].when.minute == 0 and ff[0].impact == "HIGH"
    st = CAL.static_events("data/events_static.json")
    assert any("RBI" in e.name for e in st)
    eia = CAL.eia_weekly(NOW)
    assert eia and all(e.when.astimezone(CAL.NY).weekday() == 2 for e in eia)
    allv = CAL.all_events(NOW, ff=ff)
    assert allv == sorted(allv, key=lambda e: e.when) and len(allv) >= 3

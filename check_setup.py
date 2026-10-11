"""Run this FIRST:  python check_setup.py   (add --telegram to send a test message). Prints OK / FAIL / SKIP with the fix for every part."""
import importlib
import os
import sys
from datetime import datetime

from rtw.config import get_settings
from rtw.db import connect
from rtw.sessions import IST

OK, FAIL, SKIP = "OK  ", "FAIL", "SKIP"
rows = []


def rec(name, status, detail="", fix=""):
    rows.append((name, status, detail, fix))
    print(f"[{status}] {name}: {detail}" + (f"\n        -> FIX: {fix}" if fix and status != OK else ""))


def main():
    now = datetime.now(IST)
    st = get_settings()
    rec("python", OK if sys.version_info >= (3, 10) else FAIL, sys.version.split()[0], "Python 3.10+ install karo")
    for mod in ("pandas", "numpy", "fastapi", "uvicorn", "apscheduler", "requests", "feedparser", "yfinance", "pyotp", "SmartApi", "nsefin", "tzdata"):
        try:
            importlib.import_module(mod)
            rec(f"package {mod}", OK)
        except Exception as e:
            rec(f"package {mod}", FAIL, str(e), "pip install -r requirements.txt")
    rec(".env file", OK if os.path.exists(".env") else SKIP, f"mode={st.mode}", ".env.example ko .env naam se copy karke keys bharo (DEMO me zaroorat nahi)")
    con = connect(st.db_path)
    rec("database", OK, st.db_path)
    if st.mode == "DEMO":
        rec("mode", OK, "DEMO: synthetic data. Live data ke liye .env me RTW_MODE=PAPER karo")
        return summary()
    from rtw.live import LiveProvider
    from rtw.config import CORE_SPECS
    lp = LiveProvider(st, con)
    for c, s, d in lp.start(now):
        rec(c, OK if s == "OK" else (SKIP if s == "SKIP" else FAIL), d,
            "Angel API key / client code / PIN / TOTP secret check karo (TOTP secret = QR ke neeche wala text, 6 digit code nahi)")
    for sym in ("NIFTY", "GOLD", "USDINR", "BTCUSDT"):
        sp = next(x for x in CORE_SPECS if x.symbol == sym)
        df = lp.candles(sp, now, "5m", 100)
        rec(f"candles {sym}", OK if df is not None and len(df) > 20 else FAIL, f"{0 if df is None else len(df)} bars",
            "market band ho to normal hai; warna Angel login/master ya internet check karo")
    ltp = lp.ltp(CORE_SPECS[0], now)
    rec("angel ltp NIFTY", OK if ltp else SKIP, str(ltp))
    g = lp.global_changes(now)
    rec("global (yfinance)", OK if len(g) >= 8 else FAIL, f"{len(g)} tickers", "internet check; kuch ghante baad dobara")
    rec("India VIX z", OK if lp.vix_z(now) is not None else SKIP, str(lp.vix_z(now)))
    ch = lp.option_chain(CORE_SPECS[0], now)
    rec("option chain NIFTY", OK if ch and ch["rows"] else SKIP, f"{len(ch['rows']) if ch else 0} strikes, expiry {ch['expiry'] if ch else '-'}",
        "NSE kabhi block karta hai; market hours me dobara try karo. Columns print karne ke liye rtw/adapters/nse.py::chain_from_df dekho")
    n = lp.collect_news(now, gdelt=True)
    rec("news feeds", OK if n > 10 else FAIL, f"{n} items", "internet/firewall check")
    ev = lp.events(now)
    rec("event calendar", OK if ev else FAIL, f"{len(ev)} events")
    fii = lp.smart_inputs(CORE_SPECS[0], now)
    rec("FII/DII (NSE)", OK if fii else SKIP, str(fii))
    cs = lp.smart_inputs(CORE_SPECS[-1], now)
    rec("crypto funding/F&G", OK if cs and len(cs) > 1 else SKIP, str(cs))
    if "--telegram" in sys.argv:
        from rtw.notify import TelegramSender
        s = TelegramSender(st.telegram_token, st.telegram_chat_id)
        rec("telegram", OK if s.send("Raj Trading World test message ✅") else FAIL, "test message", "BOT TOKEN aur CHAT ID check karo; bot ko pehle /start bhejo")
    summary()


def summary():
    bad = [r for r in rows if r[1] == FAIL]
    print(f"\n{len(rows)} checks | {len(bad)} FAIL")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()

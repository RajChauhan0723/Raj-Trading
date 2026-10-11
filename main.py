"""Raj Trading World — start everything:  python main.py"""
import threading
from datetime import datetime
import uvicorn
from rtw.api import create_app
from rtw.config import get_settings
from rtw.db import connect, log_health
from rtw.notify import TelegramSender
from rtw.pipeline import Orchestrator
from rtw.scheduler import build_scheduler
from rtw.sessions import IST
from rtw import jobs
from rtw.telegram_bot import run_bot
from rtw.icons import ensure_icons
from rtw.api import WEB_DIR


def build(st):
    con = connect(st.db_path)
    live = None
    if st.mode == "DEMO":
        from rtw.provider import FakeProvider
        provider = FakeProvider()
    else:
        from rtw.live import LiveProvider
        provider = live = LiveProvider(st, con)
    sender = TelegramSender(st.telegram_token, st.telegram_chat_id)
    orc = Orchestrator(con, provider, st, send=sender.send if sender.ready else None)
    orc.apply_saved_settings()
    return orc, live, sender


def startup(orc, live, now):
    if live is not None:
        for c, s, d in live.start(now):
            log_health(orc.con, now, c, s, d)
        live.refresh_stock_universe(now, 100)
        jobs.update_holidays(orc, now)
        live.collect_news(now, gdelt=True)
    has = orc.con.execute("SELECT COUNT(*) FROM candles").fetchone()[0]
    if has < 500:
        jobs.bootstrap_history(orc, now, 60)
        jobs.nightly_backtest(orc, now)
    now = datetime.now(IST)                      # bootstrap/backtest may have taken minutes
    orc.refresh_all(now, "core")
    orc.cycle(now, "core")


def main():
    st = get_settings()
    ensure_icons(WEB_DIR)
    orc, live, sender = build(st)
    now = datetime.now(IST)
    print(f"Raj Trading World | mode={st.mode} | capital={st.capital:.0f} | profile={st.profile}")
    threading.Thread(target=startup, args=(orc, live, now), daemon=True).start()   # UI opens immediately, data fills in
    sch = build_scheduler(orc, live)
    sch.start()
    stop = threading.Event()
    if sender.ready:
        threading.Thread(target=run_bot, args=(orc, sender, lambda: datetime.now(IST), stop), daemon=True).start()
        sender.send("Raj Trading World chalu ho gaya. /help likho.")
    print(f"App kholo: http://localhost:{st.port}   (phone: same WiFi par http://<PC-IP>:{st.port})")
    uvicorn.run(create_app(orc), host=st.host, port=st.port, log_level="warning")


if __name__ == "__main__":
    main()

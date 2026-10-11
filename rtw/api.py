"""FastAPI app: JSON API + serves the PWA from ./web. Optional access key (header x-key or ?key=)."""
from __future__ import annotations
import os
from datetime import datetime
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from .db import get_setting
from .news import news_mode
from .sessions import IST
from .views import home_view, mood_view, markets_view, record_view, news_view, health_view, TABS
from .analytics import analytics_view

WEB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web")


class SettingsIn(BaseModel):
    capital: float | None = None
    risk_pct: float | None = None
    profile: str | None = None
    max_trades: int | None = None


class TVAlertIn(BaseModel):
    symbol: str
    action: str
    price: float | None = None
    sl: float | None = None
    t1: float | None = None
    t2: float | None = None
    indicator: str | None = "RAVAN 2.0"
    message: str | None = None
    secret: str | None = None


def create_app(orc, now_fn=lambda: datetime.now(IST)) -> FastAPI:
    app = FastAPI(title="Raj Trading World", docs_url=None, redoc_url=None)
    st = orc.st

    @app.middleware("http")
    async def guard(request: Request, call_next):
        if st.access_key and request.url.path.startswith("/api/"):
            key = request.headers.get("x-key") or request.query_params.get("key")
            if key != st.access_key:
                return JSONResponse({"error": "access key galat ya missing"}, status_code=401)
        return await call_next(request)

    @app.get("/api/home")
    def home():
        now = now_fn()
        return home_view(orc.con, now, orc.provider.events(now), st)

    @app.get("/api/markets/{tab}")
    def markets(tab: str):
        if tab not in TABS:
            raise HTTPException(404, "tab nahi mila")
        now = now_fn()
        return markets_view(orc.con, tab, now, st, orc.specs(now))

    @app.get("/api/search")
    def search(q: str):
        if len(q) > 40:
            raise HTTPException(400, "query bahut lambi")
        return orc.search(q, now_fn())

    @app.get("/api/chart")
    def chart(q: str, tf: str = "5m", strike: float | None = None, cp: str | None = None, expiry: str | None = None):
        if len(q) > 40:
            raise HTTPException(400, "query bahut lambi")
        return orc.chart(q, now_fn(), tf, strike, cp, expiry)

    @app.get("/api/mood")
    def mood():
        now = now_fn()
        return mood_view(orc.con, now, orc.specs(now))

    @app.get("/api/news")
    def news():
        now = now_fn()
        ev = orc.provider.events(now)
        return news_view(orc.con, orc.provider, now, ev, news_mode(ev, now, "NIFTY", vix_z=orc.provider.vix_z(now)))

    @app.get("/api/record")
    def record():
        return record_view(orc.con)

    @app.get("/api/analytics")
    def analytics():
        now = now_fn()
        return analytics_view(orc.con, now)

    @app.post("/api/reset_halt")
    def reset_halt():
        orc.reset_halt()
        return {"ok": True}

    @app.get("/api/health")
    def health():
        return {"mode": st.mode, "last_cycle": get_setting(orc.con, "last_cycle"), "paused": get_setting(orc.con, "paused", False),
                "components": health_view(orc.con)}

    @app.get("/api/settings")
    def get_settings_():
        return {"capital": st.capital, "risk_pct": st.risk_pct, "profile": st.profile, "mode": st.mode, "max_trades": st.max_trades}

    @app.post("/api/settings")
    def set_settings(body: SettingsIn):
        try:
            orc.update_settings(body.capital, body.risk_pct, body.profile, body.max_trades)
        except ValueError as e:
            raise HTTPException(400, str(e))
        return {"capital": st.capital, "risk_pct": st.risk_pct, "profile": st.profile, "max_trades": st.max_trades}

    @app.post("/api/refresh")
    def refresh():
        now = now_fn()
        orc.refresh_all(now, "core")
        return orc.cycle(now, "core")

    @app.post("/api/webhook/tradingview")
    def tv_webhook(alert: TVAlertIn):
        sym = alert.symbol.upper().replace("NSE:", "").replace("MCX:", "").replace("BINANCE:", "")
        action = alert.action.upper()
        if action not in ("BUY", "SELL"):
            raise HTTPException(400, "action must be BUY or SELL")
        now = now_fn()
        txt = (
            f"⚡ <b>RTW VIP TRADE ALERT</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🎯 <b>Symbol:</b> {sym} | <b>Action:</b> {action}\n"
            f"💵 <b>Price:</b> {alert.price or '-'}\n"
            f"🛑 <b>SL:</b> {alert.sl or '-'} | <b>Target:</b> {alert.t1 or '-'}\n"
            f"📊 <b>Engine:</b> {alert.indicator or 'RTW Confluence Radar'}\n"
            f"🕒 <b>Time:</b> {now.strftime('%d-%b-%Y %I:%M %p IST')}"
        )
        if alert.message:
            txt += f"\n📝 <i>{alert.message}</i>"
        try:
            if orc.send:
                orc.send(txt)
        except Exception:
            pass
        return {"ok": True, "symbol": sym, "action": action, "broadcasted": True}

    @app.get("/api/scanner/master")
    def scanner_master():
        now = now_fn()
        specs = orc.specs(now)
        out = {}
        for tab in TABS:
            out[tab] = markets_view(orc.con, tab, now, st, specs)
        return out

    @app.get("/sw.js")
    def sw():
        return FileResponse(
            os.path.join(WEB_DIR, "sw.js"),
            media_type="application/javascript",
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0"
            }
        )

    @app.get("/")
    def index():
        return FileResponse(
            os.path.join(WEB_DIR, "index.html"),
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0"
            }
        )

    if os.path.isdir(WEB_DIR):
        app.mount("/", StaticFiles(directory=WEB_DIR), name="web")
    return app

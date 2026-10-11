from datetime import datetime
from fastapi.testclient import TestClient
from rtw.api import create_app
from rtw.telegram_bot import handle_command
from tests.test_pipeline import make, NOW


def client(key=""):
    con, st, orc, sent = make()
    st.access_key = key
    orc.refresh_all(NOW, "core"); orc.cycle(NOW, "core")
    return TestClient(create_app(orc, lambda: NOW)), orc, st


def test_endpoints_ok():
    c, orc, st = client()
    assert c.get("/api/home").json()["status"] in ("WAIT", "NEW", "ACTIVE")
    for tab in ("index", "commodity", "stocks", "forex", "crypto"):
        assert c.get(f"/api/markets/{tab}").status_code == 200
    assert c.get("/api/markets/nope").status_code == 404
    assert c.get("/api/news").json()["events"]
    assert "all" in c.get("/api/record").json()
    assert c.get("/api/health").json()["mode"] == "DEMO"
    r = c.get("/api/search", params={"q": "reliance"}).json()
    assert r["found"] and r["decision"]["info_only"]
    r = c.get("/api/search", params={"q": "nifty"}).json()
    assert r["symbol"] == "NIFTY"
    assert c.get("/").status_code in (200, 404)


def test_settings_validation_and_key():
    c, orc, st = client("s3cret")
    assert c.get("/api/home").status_code == 401
    h = {"x-key": "s3cret"}
    assert c.get("/api/home", headers=h).status_code == 200
    assert c.post("/api/settings", json={"capital": 50}, headers=h).status_code == 400
    assert c.post("/api/settings", json={"profile": "wild"}, headers=h).status_code == 400
    r = c.post("/api/settings", json={"capital": 250000, "risk_pct": 0.02, "profile": "moderate"}, headers=h)
    assert r.status_code == 200 and st.capital == 250000 and st.profile == "moderate"


def test_telegram_commands():
    c, orc, st = client()
    for cmd in ("/start", "/status", "/why", "/record", "/brief", "/health", "/pause", "/resume", "/xyz"):
        assert isinstance(handle_command(cmd, orc, NOW), str) and handle_command(cmd, orc, NOW)
    handle_command("/pause", orc, NOW)
    from rtw.db import get_setting
    assert get_setting(orc.con, "paused") is True

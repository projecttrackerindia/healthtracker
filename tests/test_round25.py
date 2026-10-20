"""Round 25: doctor summary share links; day-counted insight patterns. Run: python -m pytest -q tests/test_round25.py"""
import os
import uuid
from datetime import date, datetime
from pathlib import Path

os.environ.setdefault("OTP_DEMO", "1")
os.environ.setdefault("PWNED_CHECK", "0")
os.environ["DATABASE_URL"] = "sqlite:///./data/test_round25.db"

from fastapi.testclient import TestClient  # noqa: E402

import server  # noqa: E402
from api import proactive, summary  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
H = {"x-tht": "1"}


def client():
    c = TestClient(server.app)
    c.__enter__()
    return c


def signup(c):
    u = uuid.uuid4().hex[:8]
    r = c.post("/api/v1/auth/signup/start", headers=H, json={"name": "Meera Raghavan", "email": f"{u}@example.com", "phone": "9" + str(uuid.uuid4().int)[-9:], "password": "Zq!8vB#2mLp@9xT", "terms": True})
    assert r.status_code == 200, r.text
    r = c.post("/api/v1/auth/signup/verify", headers=H, json={"flow": r.json()["flow"], "code": r.json()["demo"]})
    assert r.status_code == 200, r.text
    c.headers["X-DoKKo-Key"] = uuid.uuid4().hex          # the app's household key: the account gets its household on the first hello
    assert c.post("/api/v1/hello", json={"name": "T", "members": 1}).status_code == 200


HTML = """<!doctype html><html><head><title>x</title><script>alert(1)</script></head><body><h1>Meera Raghavan</h1><p onclick="x()">Allergies: penicillin</p><table><tr><td>HbA1c</td><td>6.8</td></tr></table><a href="javascript:evil()">x</a><iframe src="https://evil"></iframe><button onclick="print()">Print</button></body></html>"""


def test_share_link_opens_for_anyone_until_it_expires_or_is_ended():
    c = client()
    signup(c)
    r = c.post("/api/v1/summary/share", headers=H, json={"member": "d1", "name": "Meera Raghavan", "html": HTML, "hours": 48})
    assert r.status_code == 200, r.text
    j = r.json()
    assert "/ds/" in j["url"] and j["expires"] > 0
    tok = j["token"]
    # a stranger (new client, no cookies) can read it
    other = client()
    p = other.get("/ds/" + tok)
    assert p.status_code == 200 and "Meera Raghavan" in p.text and "HbA1c" in p.text and "penicillin" in p.text
    assert "<script>alert" not in p.text and "onclick=\"x()\"" not in p.text and "javascript:" not in p.text and "<iframe" not in p.text
    assert "Print / save PDF" in p.text and p.text.count("<button") == 1       # the page's own print button only
    assert p.headers["x-robots-tag"].startswith("noindex") and "default-src 'none'" in p.headers["content-security-policy"]
    # the family sees it listed with one view, then ends it
    mine = c.get("/api/v1/summary/share", headers=H).json()
    assert len(mine) == 1 and mine[0]["token"] == tok and mine[0]["views"] == 1
    assert c.delete("/api/v1/summary/share/" + tok, headers=H).json()["revoked"] is True
    assert other.get("/ds/" + tok).status_code == 404 and c.get("/api/v1/summary/share", headers=H).json() == []
    assert other.get("/ds/nope").status_code == 404


def test_share_needs_a_signed_in_account_and_caps_hours():
    c = client()
    assert c.post("/api/v1/summary/share", headers=H, json={"html": HTML}).status_code == 401
    signup(c)
    j = c.post("/api/v1/summary/share", headers=H, json={"html": HTML, "hours": 99999}).json()
    assert j["expires"] - int(__import__("time").time()) <= 14 * 86400 + 5
    assert c.post("/api/v1/summary/share", headers=H, json={"html": ""}).status_code == 400
    assert c.post("/api/v1/summary/share", headers=H, json={"html": "x" * (summary.MAX_HTML + 1)}).status_code == 400


def test_clean_keeps_content_and_drops_everything_active():
    out = summary._clean(HTML)
    assert out.startswith("<h1>Meera Raghavan</h1>") and "<table>" in out
    assert "script" not in out and "onclick" not in out and "iframe" not in out and "<button" not in out and "javascript:" not in out


def test_patterns_count_days_not_readings():
    t = lambda day, hour: int(datetime(2026, 10, day, hour, tzinfo=proactive.IST).timestamp() * 1000)  # noqa: E731
    week = [  # 4 days with BP readings, high on 3 of them (two readings on the 15th, both high, count once)
        {"t": t(14, 8), "sys": 128, "dia": 82}, {"t": t(15, 8), "sys": 146, "dia": 92}, {"t": t(15, 20), "sys": 150, "dia": 95},
        {"t": t(16, 8), "sys": 142, "dia": 88}, {"t": t(18, 8), "sys": 144, "dia": 90},
        {"t": t(14, 7), "glu": 118, "gt": "fasting"}, {"t": t(16, 7), "glu": 135, "gt": "fasting"},   # sugar: only 2 days → below the minimum
    ]
    out = proactive.patterns(week, "Vikram")
    assert len(out) == 1 and out[0]["field"] == "sys" and out[0]["days"] == 3 and out[0]["of"] == 4
    assert out[0]["title"] == "Vikram: blood pressure high this week" and "on 3 of the 4 days" in out[0]["body"]
    # and the nudge job carries it with a weekly dedupe key
    state = {"members": [{"id": "d2", "name": "Vikram Raghavan"}], "vitals": {"d2": week}}
    n = [x for x in proactive.nudges(state, date(2026, 10, 20)) if x["key"].startswith("pattern:")]
    assert len(n) == 1 and n[0]["key"] == "pattern:d2:sys:43" and n[0]["ref"]["days"] == 3


def test_page_carries_layer_25():
    html = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
    assert "/*live-p25*/" in html and "if(SX.__summaryGrab){SX.__summaryGrab(html);return}" in html and "SX.act.sumshare=" in html
    assert "🖨️ ${P('Doctor summary')}" not in html      # the old card is gone

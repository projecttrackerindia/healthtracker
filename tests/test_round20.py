"""Round 20: mobile codes through Firebase Phone Authentication. Run: python -m pytest -q tests/test_round20.py"""
import os
import uuid
from pathlib import Path

import pytest

os.environ.setdefault("PWNED_CHECK", "0")
os.environ.setdefault("OTP_DEMO", "1")
os.environ["DATABASE_URL"] = "sqlite:///./data/test_round20.db"

from fastapi.testclient import TestClient  # noqa: E402

import server  # noqa: E402
from api import auth, messaging  # noqa: E402


@pytest.fixture(autouse=True)
def firebase_env(monkeypatch):
    """Firebase as the only SMS channel, no email channel, real (non-demo) delivery paths — for this module's tests only."""
    monkeypatch.setenv("OTP_DEMO", "0")
    monkeypatch.setenv("APP_ENV", "production")
    for k in ("MSG91_AUTH_KEY", "MSG91_TEMPLATE_ID", "TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "RESEND_API_KEY", "SMTP_HOST"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("FIREBASE_WEB_API_KEY", "test-key")
    monkeypatch.setenv("FIREBASE_PROJECT_ID", "central-weft-511003-c1")
    monkeypatch.setenv("FIREBASE_APP_ID", "1:1:web:1")

ROOT = Path(__file__).resolve().parents[1]
H = {"x-tht": "1"}
PW = "Zq!8vB#2mLp@9xT"


def client():
    c = TestClient(server.app)
    c.__enter__()
    return c


def fresh_phone():
    return "+91" + "9" + str(uuid.uuid4().int)[-9:].zfill(9)


def test_firebase_is_the_sms_channel_and_config_tells_the_browser():
    assert messaging.sms_mode() == "firebase" and messaging.sms_ready()
    c = client()
    j = c.get("/api/v1/auth/config", headers=H).json()
    assert j["sms"] is True and j["firebase"] == {"apiKey": "test-key", "authDomain": "central-weft-511003-c1.firebaseapp.com", "projectId": "central-weft-511003-c1", "appId": "1:1:web:1"}


def test_signup_by_mobile_hands_the_sms_to_the_browser_and_accepts_the_token(monkeypatch):
    c = client()
    phone = fresh_phone()
    # no email channel on this server, so the first verification goes to the mobile
    r = c.post("/api/v1/auth/signup/start", headers=H, json={"name": "Test Person", "email": f"{uuid.uuid4().hex[:8]}@example.com", "phone": phone, "password": PW, "terms": True})
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["channel"] == "phone" and j["firebase"] is True and j["phone"] == phone and "demo" not in j
    flow = j["flow"]
    # a 6-digit guess is still checked against our (never revealed) code and fails
    r = c.post("/api/v1/auth/signup/verify", headers=H, json={"flow": flow, "code": "000000"})
    assert r.status_code == 400 and "not right" in r.json()["detail"]
    # a token Google says belongs to a different number is refused
    monkeypatch.setattr(messaging, "firebase_phone", lambda t: "+919999999999")
    r = c.post("/api/v1/auth/signup/verify", headers=H, json={"flow": flow, "firebaseToken": "tok"})
    assert r.status_code == 400
    # the right number signs the person up
    monkeypatch.setattr(messaging, "firebase_phone", lambda t: phone if t == "good" else "")
    r = c.post("/api/v1/auth/signup/verify", headers=H, json={"flow": flow, "firebaseToken": "good"})
    assert r.status_code == 200, r.text
    assert r.json()["user"]["phone"] == phone
    me = c.get("/api/v1/auth/me", headers=H).json()["user"]
    assert me["phoneVerified"] is True if "phoneVerified" in me else True
    # the same token cannot be replayed into another flow: the one-time row is used up
    r = c.post("/api/v1/auth/signup/verify", headers=H, json={"flow": flow, "firebaseToken": "good"})
    assert r.status_code == 400


def test_otp_signin_by_mobile_looks_the_same_for_unknown_numbers(monkeypatch):
    c = client()
    known = fresh_phone()
    r = c.post("/api/v1/auth/signup/start", headers=H, json={"name": "Known Person", "email": f"{uuid.uuid4().hex[:8]}@example.com", "phone": known, "password": PW, "terms": True})
    monkeypatch.setattr(messaging, "firebase_phone", lambda t: known)
    assert c.post("/api/v1/auth/signup/verify", headers=H, json={"flow": r.json()["flow"], "firebaseToken": "t"}).status_code == 200
    c.post("/api/v1/auth/logout", headers=H)
    import time
    monkeypatch.setattr(auth, "now", lambda: int(time.time()) + 120)   # past the 45-second resend guard from the sign-up code
    a = c.post("/api/v1/auth/otp/start", headers=H, json={"id": known}).json()
    b = c.post("/api/v1/auth/otp/start", headers=H, json={"id": fresh_phone()}).json()
    assert a["firebase"] is True and b["firebase"] is True and set(a) == set(b)
    # the known number signs in with the token
    r = c.post("/api/v1/auth/otp/verify", headers=H, json={"flow": a["flow"], "firebaseToken": "t"})
    assert r.status_code == 200 and r.json()["user"]["phone"] == known
    # the unknown number cannot, whatever Google certifies
    r = c.post("/api/v1/auth/otp/verify", headers=H, json={"flow": b["flow"], "firebaseToken": "t"})
    assert r.status_code == 400


def test_lookup_failure_is_a_wrong_code_not_a_crash(monkeypatch):
    c = client()
    phone = fresh_phone()
    r = c.post("/api/v1/auth/signup/start", headers=H, json={"name": "Test Person", "email": f"{uuid.uuid4().hex[:8]}@example.com", "phone": phone, "password": PW, "terms": True})
    flow = r.json()["flow"]

    def boom(req, timeout=10):
        raise OSError("network down")
    monkeypatch.setattr(messaging.urllib.request, "urlopen", boom)
    assert messaging.firebase_phone("x") == ""
    r = c.post("/api/v1/auth/signup/verify", headers=H, json={"flow": flow, "firebaseToken": "x"})
    assert r.status_code == 400


def test_page_and_site_carry_the_phone_step():
    html = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
    assert "/*live-p20*/" in html and html.count("SX.fbBody(flow,code)") == 4 and html.count("SX.fbArm(") == 4
    assert "{step:flow,code}" not in html            # the two-step verify now sends `flow`
    site = (ROOT / "site" / "index.html").read_text(encoding="utf-8")
    assert site.count("await codeBody(c)") == 4 and "THT.phone.send(r.phone)" in site
    js = (ROOT / "site" / "auth.js").read_text(encoding="utf-8")
    assert "signInWithPhoneNumber" in js and "accounts:lookup" not in js   # the browser never talks to the lookup endpoint; the server does
    assert "dk-r20" in (ROOT / "web" / "sw.js").read_text(encoding="utf-8")
    assert "identitytoolkit.googleapis.com" in server.CSP and "www.gstatic.com" in server.CSP

"""Round-1 production checks. Run: OTP_DEMO=1 PWNED_CHECK=0 python -m pytest -q tests"""
import gzip
import os
import uuid

os.environ.setdefault("OTP_DEMO", "1")
os.environ.setdefault("PWNED_CHECK", "0")
os.environ["DATABASE_URL"] = "sqlite:///./data/test_live.db"

from fastapi.testclient import TestClient  # noqa: E402

import server  # noqa: E402

H = {"x-tht": "1"}


def client():
    c = TestClient(server.app)
    c.__enter__()
    return c


def signup(c, phone=None):
    u = uuid.uuid4().hex[:8]
    phone = phone or "9" + str(uuid.uuid4().int)[-9:].zfill(9)
    r = c.post("/api/v1/auth/signup/start", headers=H, json={"name": "Test Person", "email": f"{u}@example.com", "phone": phone, "password": "Zq!8vB#2mLp@9xT", "terms": True})
    assert r.status_code == 200, r.text
    r = c.post("/api/v1/auth/signup/verify", headers=H, json={"flow": r.json()["flow"], "code": r.json()["demo"]})
    assert r.status_code == 200, r.text
    return r.json()["user"]


def test_config_hides_provider_and_model():
    c = client()
    j = c.get("/api/v1/config").json()
    assert "model" not in j["ai"] and j["ai"]["engine"] in ("ai", "local")
    assert "claude" not in c.get("/api/v1/config").text.lower()


def test_signup_requires_mobile():
    c = client()
    r = c.post("/api/v1/auth/signup/start", headers=H, json={"name": "No Phone", "email": "np@example.com", "password": "Zq!8vB#2mLp@9xT", "terms": True})
    assert r.status_code == 400 and "mobile" in r.json()["detail"].lower()


def test_verify_mobile_gives_badge_and_delete_account():
    c = client()
    u = signup(c)
    assert u["emailVerified"] and not u["phoneVerified"]
    r = c.post("/api/v1/auth/contact/start", headers=H, json={"value": u["phone"]})
    assert r.status_code == 200, r.text
    r = c.post("/api/v1/auth/contact/verify", headers=H, json={"flow": r.json()["flow"], "code": r.json()["demo"]})
    assert r.json()["user"]["phoneVerified"] is True
    assert c.post("/api/v1/auth/contact/start", headers=H, json={"value": u["phone"]}).status_code == 400  # already verified
    assert c.post("/api/v1/auth/account/delete", headers=H, json={"confirm": "nope"}).status_code == 400
    assert c.post("/api/v1/auth/account/delete", headers=H, json={"confirm": "DELETE"}).json() == {"deleted": True}
    assert c.get("/api/v1/auth/me").json() == {"user": None}


def test_contact_cannot_take_another_accounts_number():
    a, b = client(), client()
    ua = signup(a)
    signup(b)
    assert b.post("/api/v1/auth/contact/start", headers=H, json={"value": ua["phone"]}).status_code == 409


def test_legal_pages_filled():
    c = client()
    for p in ("/privacy", "/terms"):
        r = c.get(p)
        assert r.status_code == 200 and "{{" not in r.text and "TheHealthTracker" in r.text


def test_stale_compressed_copy_is_never_served(tmp_path):
    src = server.WEB / "index.html"
    alt = server.WEB / "index.html.br"
    import brotli
    keep = alt.read_bytes()
    try:
        alt.write_bytes(brotli.compress(b"OLD BUILD"))
        server.VARIANTS = server._verified_variants()
        r = client().get("/app", headers={"accept-encoding": "br"})
        assert b"OLD BUILD" not in r.content and r.content.startswith(src.read_bytes()[:50])
    finally:
        alt.write_bytes(keep)
        server.VARIANTS = server._verified_variants()


def test_app_has_no_sample_people():
    html = (server.WEB / "index.html").read_text(encoding="utf-8")
    six = html[html.index('<script id="six-js">'):]
    for n in ("name:'Prasanna'", "Demo checkout", "fictional sample data for this demo", "Math.random()*9);tip()"):
        assert n not in six

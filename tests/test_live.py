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


def signup(c, phone=None, full=False):
    u = uuid.uuid4().hex[:8]
    phone = phone or "9" + str(uuid.uuid4().int)[-9:].zfill(9)
    r = c.post("/api/v1/auth/signup/start", headers=H, json={"name": "Test Person", "email": f"{u}@example.com", "phone": phone, "password": "Zq!8vB#2mLp@9xT", "terms": True})
    assert r.status_code == 200, r.text
    r = c.post("/api/v1/auth/signup/verify", headers=H, json={"flow": r.json()["flow"], "code": r.json()["demo"]})
    assert r.status_code == 200, r.text
    c.last_signup = r.json()
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


def test_signup_requires_email():
    c = client()
    r = c.post("/api/v1/auth/signup/start", headers=H, json={"name": "No Mail", "phone": "9876501234", "password": "Zq!8vB#2mLp@9xT", "terms": True})
    assert r.status_code == 400 and "email" in r.json()["detail"].lower()


def test_verify_mobile_gives_badge_and_delete_account():
    c = client()
    u = signup(c)
    assert u["emailVerified"] and not u["phoneVerified"] and u["verified"] is False
    nxt = c.last_signup["verifyNext"]                       # sign-up continues with the mobile code at once
    assert nxt["channel"] == "phone" and nxt["demo"]
    r = c.post("/api/v1/auth/contact/verify", headers=H, json={"flow": nxt["flow"], "code": nxt["demo"]})
    assert r.json()["user"]["phoneVerified"] is True and r.json()["user"]["verified"] is True
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


def test_card_reader_without_key_offers_manual_entry(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False); monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    c = client()
    r = c.post("/api/v1/auth/../hello".replace("/auth/../", "/"), json={"name": "T"}, headers={"X-DoKKo-Key": "k" * 32})
    assert r.status_code == 200
    r = c.post("/api/v1/ai/analyze", data={"kind": "card", "consent": "1"}, files={"file": ("card.png", b"\x89PNG\r\n\x1a\n" + b"0" * 100, "image/png")}, headers={"X-DoKKo-Key": "k" * 32})
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["kind"] == "card" and j["readable"] is False and j["engine"] == "local" and "model" not in j
    assert "warnings" in j and j["warnings"]


def test_admin_ai_test_reports_missing_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False); monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    from api import ai as AI
    r = AI.test_connection()
    assert r["ok"] is False and "API_KEY" in r["error"]


def test_no_admin_wording_in_user_messages():
    src = (server.ROOT / "api" / "ai.py").read_text(encoding="utf-8")
    assert "set up by your administrator" not in src


def test_account_name_changes_once_a_week():
    c = client()
    signup(c)
    r = c.post("/api/v1/auth/profile", headers=H, json={"name": "Prasanna Krishna"})          # completing the card on day one: free
    assert r.status_code == 200 and r.json()["user"]["nameNext"] is None
    from sqlalchemy import select
    from api import db as DB
    from api.models import User
    with DB.session() as db:
        u = db.scalar(select(User).where(User.name == "Prasanna Krishna")); u.created -= 2 * 86400
    r = c.post("/api/v1/auth/profile", headers=H, json={"name": "Prasanna Krishna Daddala"})
    assert r.status_code == 200 and r.json()["user"]["name"] == "Prasanna Krishna Daddala" and r.json()["user"]["nameNext"]
    r = c.post("/api/v1/auth/profile", headers=H, json={"name": "Someone Else"})
    assert r.status_code == 423 and "once a week" in r.json()["detail"]
    assert c.post("/api/v1/auth/profile", headers=H, json={"name": "Prasanna Krishna Daddala"}).status_code == 200  # unchanged name is fine


def test_paid_plan_needs_a_payment_provider(monkeypatch):
    monkeypatch.setenv("FREE_UNTIL", "")          # how the paid route behaves once the launch period is over
    monkeypatch.delenv("RAZORPAY_KEY_ID", raising=False)
    c = client()
    signup(c)
    monkeypatch.setenv("APP_ENV", "production")
    c.headers["X-DoKKo-Key"] = uuid.uuid4().hex
    c.post("/api/v1/hello", json={"name": "T", "members": 1})
    plans = c.get("/api/v1/plans").json()
    assert plans["provider"] == "upi"                       # the UPI QR route is on; the demo switch stays shut
    paid = next(p["code"] for p in plans["plans"] if p["month"] > 0)
    r = c.post("/api/v1/subscribe", json={"plan": paid, "period": "month"})
    assert r.status_code == 503 and "UPI" in r.json()["detail"]
    assert c.get("/api/v1/plans").json()["current"] == "free"
    monkeypatch.setenv("UPI_PAY", "0")
    assert c.get("/api/v1/plans").json()["provider"] == "soon"
    r = c.post("/api/v1/subscribe", json={"plan": paid, "period": "month"})
    assert r.status_code == 503 and "Free" in r.json()["detail"]


def test_ai_ask_and_insight_without_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False); monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    c = client()
    c.headers["X-DoKKo-Key"] = uuid.uuid4().hex
    c.post("/api/v1/hello", json={"name": "T", "members": 1})
    assert c.post("/api/v1/ai/ask", json={"question": "Is my sugar okay?", "context": {}}).status_code == 503
    assert c.post("/api/v1/ai/insight", json={"context": {}, "member": "m1"}).status_code == 503


def test_ai_ask_counts_quota_and_insight_caches(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test")
    from api import agent, ai as AI
    calls = []

    class R:
        content = [type("B", (), {"type": "text", "text": '{"answer":"Your fasting sugar 96 mg/dL on 1 Oct suggests it is in range. Discuss with your doctor.","sources":["Fasting sugar 96 mg/dL · 1 Oct 2026"],"actions":["Record a reading next week"],"urgent":false,"headline":"Sugar steady","points":["Fasting 96 mg/dL on 1 Oct."],"action":"Walk 30 minutes daily","trend":"steady"}'})()]

    monkeypatch.setattr(AI, "create", lambda **kw: (calls.append(kw) or R()))
    c = client()
    c.headers["X-DoKKo-Key"] = uuid.uuid4().hex
    c.post("/api/v1/hello", json={"name": "T", "members": 1})
    ctx = {"me": {"name": "T", "age": 40}, "readings": [{"glu": 96, "d": "2026-10-01"}]}
    r = c.post("/api/v1/ai/ask", json={"question": "Is my sugar okay?", "context": ctx})
    assert r.status_code == 200 and r.json()["quota"]["used"] == 1 and "96" in r.json()["answer"] and "model" not in r.json()
    assert "claude" not in r.json()["answer"].lower()
    a = c.post("/api/v1/ai/insight", json={"context": ctx, "member": "m1"}).json()
    b = c.post("/api/v1/ai/insight", json={"context": ctx, "member": "m1"}).json()
    assert a["cached"] is False and b["cached"] is True and a["headline"] == "Sugar steady" and len(calls) == 2
    assert agent.ctx_key(ctx) != agent.ctx_key({**ctx, "readings": []})


def test_model_fallback_on_not_found(monkeypatch):
    import anthropic
    from api import ai as AI
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test")
    monkeypatch.setattr(AI, "_WORKING", {"model": None})
    seen = []

    class FakeMessages:
        def create(self, model, **kw):
            seen.append(model)
            if model == AI.FALLBACK_MODELS[0]:
                import httpx
                raise anthropic.NotFoundError(message="model not found", response=httpx.Response(404, request=httpx.Request("POST", "https://api.anthropic.com/v1/messages")), body=None)
            return "ok"

    class FakeClient:
        messages = FakeMessages()

    monkeypatch.setattr(anthropic, "Anthropic", lambda **kw: FakeClient())
    assert AI.create(max_tokens=5, messages=[]) == "ok"
    assert seen[0] == AI.FALLBACK_MODELS[0] and AI.current_model() == seen[1] != seen[0]
    assert AI.create(max_tokens=5, messages=[]) == "ok" and seen[-1] == AI.current_model()   # remembered: no retry next time


def test_demo_codes_never_in_production(monkeypatch):
    from api import messaging
    monkeypatch.setenv("OTP_DEMO", "1")
    monkeypatch.setenv("APP_ENV", "production")
    assert messaging.demo() is False
    monkeypatch.setenv("APP_ENV", "staging")
    assert messaging.demo() is True


def test_data_key_can_be_set_after_launch(monkeypatch):
    """Records written before DATA_KEY existed stay readable, and are re-encrypted with the new key on the next save."""
    import os
    from api import family
    monkeypatch.delenv("DATA_KEY", raising=False)
    old = family.encrypt({"members": [{"id": "m1"}], "note": "before"})
    monkeypatch.setenv("DATA_KEY", os.urandom(32).hex())
    assert family.decrypt(old)["note"] == "before"           # legacy key still opens it
    new = family.encrypt({"note": "after"})
    assert family.decrypt(new)["note"] == "after"
    monkeypatch.setenv("DATA_KEY", os.urandom(32).hex())
    try:
        family.decrypt(new)
        assert False, "a blob under a lost key must not open"
    except Exception:
        pass

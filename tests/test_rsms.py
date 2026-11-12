"""Reverse SMS: the person texts us a one-use phrase from their own number; that text, not a code we send, proves the
number. Only a text from the typed number counts, only once, only with the right secret, and only before it expires."""
import os
import uuid

os.environ.setdefault("OTP_DEMO", "1")
os.environ.setdefault("PWNED_CHECK", "0")
os.environ["DATABASE_URL"] = "sqlite:///./data/test_rsms.db"
os.environ["REVERSE_SMS_NUMBER"] = "9000012345"
os.environ["REVERSE_SMS_SECRET"] = "s3cret-forwarder"

from fastapi.testclient import TestClient  # noqa: E402

import server  # noqa: E402

H = {"x-tht": "1"}
KEY = {"x-uh-key": "s3cret-forwarder"}


def client():
    c = TestClient(server.app)
    c.__enter__()
    c.headers.update(H)
    return c


def phone():
    return "9" + str(uuid.uuid4().int)[-9:].zfill(9)


def text_in(c, sender, body, key=KEY):
    return c.post("/api/v1/auth/rsms/inbound", headers=key, json={"from": sender, "text": body})


def test_signup_then_sign_in_by_text():
    c, mob = client(), phone()
    assert c.get("/api/v1/auth/config").json()["rsms"] is True
    r = c.post("/api/v1/auth/signup/start", json={"name": "Jyothsna V", "phone": mob, "email": f"{uuid.uuid4().hex[:8]}@example.com", "password": "Zq!8vB#2mLp@9xT", "terms": True, "method": "rsms"}).json()
    # email is confirmed first (code), then the mobile by text
    v = c.post("/api/v1/auth/signup/verify", json={"flow": r["flow"], "code": r["demo"]}).json()
    nxt = v["verifyNext"]
    assert nxt["channel"] == "phone" and nxt.get("rsms") and "demo" not in nxt          # no code sent for the mobile
    t = c.post("/api/v1/auth/rsms/start", json={"flow": nxt["flow"], "kind": "contact"}).json()
    assert t["to"] == "+919000012345" and t["uri"].startswith("sms:+919000012345?&body=") and t["phrase"] in t["text"]
    assert c.get(f"/api/v1/auth/rsms/status?id={t['id']}").json()["state"] == "pending"
    assert c.post("/api/v1/auth/contact/verify", json={"flow": nxt["flow"], "rsms": t["id"]}).status_code == 400   # not arrived yet
    assert text_in(c, "+91 " + mob, t["text"]).json()["ok"] is True
    assert c.get(f"/api/v1/auth/rsms/status?id={t['id']}").json()["state"] == "ok"
    ok = c.post("/api/v1/auth/contact/verify", json={"flow": nxt["flow"], "rsms": t["id"]})
    assert ok.status_code == 200, ok.text
    assert c.get("/api/v1/auth/me").json()["user"]["phoneVerified"] is True
    # sign in again on a new device, by text only
    d = client()
    s = d.post("/api/v1/auth/otp/start", json={"id": mob, "method": "rsms"}).json()
    assert s.get("rsms") and "demo" not in s
    t2 = d.post("/api/v1/auth/rsms/start", json={"flow": s["flow"], "kind": "otp"}).json()
    text_in(d, mob, t2["text"].lower())                                  # case of the phrase does not matter
    r2 = d.post("/api/v1/auth/otp/verify", json={"flow": s["flow"], "rsms": t2["id"]})
    assert r2.status_code == 200 and d.get("/api/v1/auth/me").json()["user"]
    # the same proof cannot be used twice
    assert d.post("/api/v1/auth/otp/verify", json={"flow": s["flow"], "rsms": t2["id"]}).status_code == 400


def test_wrong_sender_wrong_secret_and_expiry():
    c, mob, other = client(), phone(), phone()
    c.post("/api/v1/auth/signup/start", json={"name": "Owner One", "phone": mob, "email": f"{uuid.uuid4().hex[:8]}@example.com", "password": "Zq!8vB#2mLp@9xT", "terms": True})
    s = c.post("/api/v1/auth/otp/start", json={"id": mob, "method": "rsms"}).json()
    t = c.post("/api/v1/auth/rsms/start", json={"flow": s["flow"], "kind": "otp"}).json()
    assert text_in(c, mob, t["text"], key={"x-uh-key": "guess"}).status_code == 401      # forged forwarder
    assert c.post("/api/v1/auth/rsms/inbound", json={"from": mob, "text": t["text"]}).status_code == 401
    text_in(c, other, t["text"])                                                         # sent from another SIM
    st = c.get(f"/api/v1/auth/rsms/status?id={t['id']}").json()
    assert st["state"] == "mismatch" and other[-3:] in st["from"]
    assert c.post("/api/v1/auth/otp/verify", json={"flow": s["flow"], "rsms": t["id"]}).status_code == 400
    assert text_in(c, mob, "UH-ZZZZZZ hello").json()["ok"] is False                       # unknown phrase
    # a new text replaces the old one
    t3 = c.post("/api/v1/auth/rsms/start", json={"flow": s["flow"], "kind": "otp"}).json()
    assert c.get(f"/api/v1/auth/rsms/status?id={t['id']}").json()["state"] == "gone"
    from api.db import SessionLocal
    from api.models import AuthFlow
    with SessionLocal() as db:
        f = db.get(AuthFlow, t3["id"]); f.expires = 1; db.commit()
    assert text_in(c, mob, t3["text"]).json()["ok"] is False
    assert c.get(f"/api/v1/auth/rsms/status?id={t3['id']}").json()["state"] == "expired"


def test_unknown_number_and_code_fallback():
    c, mob = client(), phone()
    s = c.post("/api/v1/auth/otp/start", json={"id": mob, "method": "rsms"}).json()
    assert s.get("rsms")                                                                 # same answer as a known number
    t = c.post("/api/v1/auth/rsms/start", json={"flow": s["flow"], "kind": "otp"}).json()
    text_in(c, mob, t["text"])
    r = c.post("/api/v1/auth/otp/verify", json={"flow": s["flow"], "rsms": t["id"]})
    assert r.status_code == 404 and "Create one" in r.json()["detail"]                   # they proved the number, so say so
    # "Get a code instead" on a known number sends a code; resend respects the 45 s gap
    k = client(); mob2 = phone()
    k.post("/api/v1/auth/signup/start", json={"name": "Code Person", "phone": mob2, "email": f"{uuid.uuid4().hex[:8]}@example.com", "password": "Zq!8vB#2mLp@9xT", "terms": True})
    s2 = k.post("/api/v1/auth/otp/start", json={"id": mob2, "method": "rsms"}).json()
    from api.db import SessionLocal
    from api.models import AuthFlow, User
    from sqlalchemy import select
    with SessionLocal() as db:   # make the account exist for this test
        if not db.scalar(select(User.id).where(User.phone == "+91" + mob2)):
            db.add(User(name="Code Person", phone="+91" + mob2, pw_hash="x", phone_verified=True)); db.commit()
        uid = db.scalar(select(User.id).where(User.phone == "+91" + mob2))
        f = db.get(AuthFlow, s2["flow"]); f.user_id = uid; db.commit()
    sent = k.post("/api/v1/auth/code/send", json={"flow": s2["flow"], "kind": "otp"}).json()
    assert sent.get("demo") and sent["channel"] == "phone"
    assert k.post("/api/v1/auth/code/send", json={"flow": s2["flow"], "kind": "otp"}).status_code == 429
    assert k.post("/api/v1/auth/otp/verify", json={"flow": s2["flow"], "code": sent["demo"]}).status_code == 200

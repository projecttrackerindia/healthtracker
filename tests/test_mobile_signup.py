"""Board u5 "Welcome": the same mobile number creates the account, and a backup mobile can get sign-in codes."""
import os
import random

os.environ.setdefault("PWNED_CHECK", "0")
os.environ.setdefault("OTP_DEMO", "1")
os.environ["DATABASE_URL"] = "sqlite:///./data/test_mobile_signup.db"

from fastapi.testclient import TestClient  # noqa: E402

import server  # noqa: E402

H = {"x-tht": "1"}


def phone():
    return "9" + "".join(random.choice("0123456789") for _ in range(9))


def cool():
    """Skip the 45-second wait between codes to the same number (the rule itself is tested elsewhere)."""
    from api.db import session
    from api.models import OtpCode
    with session() as db:
        db.query(OtpCode).update({"created": OtpCode.created - 120})


def client():
    c = TestClient(server.app)
    c.__enter__()
    return c


def test_new_mobile_creates_account_then_signs_in():
    c, ph = client(), phone()
    s = c.post("/api/v1/auth/otp/start", json={"id": ph}, headers=H).json()
    assert s.get("demo"), s
    v = c.post("/api/v1/auth/otp/verify", json={"flow": s["flow"], "code": s["demo"]}, headers=H)
    assert v.status_code == 200 and v.json().get("newAccount"), v.text
    bad = c.post("/api/v1/auth/otp/create", json={"flow": v.json()["newAccount"], "name": "Priya", "terms": False}, headers=H)
    assert bad.status_code == 400
    ok = c.post("/api/v1/auth/otp/create", json={"flow": v.json()["newAccount"], "name": "Priya Raman", "terms": True}, headers=H)
    assert ok.status_code == 200, ok.text
    me = c.get("/api/v2/me", headers=H).json()
    assert me["user"]["name"] == "Priya Raman" and me["user"]["phone"].endswith(ph) and not me["user"]["hasPassword"]
    # the same number now signs in, it does not make a second account
    cool()
    c2 = client()
    r2 = c2.post("/api/v1/auth/otp/start", json={"id": ph}, headers=H)
    assert r2.status_code == 200, r2.text
    s2 = r2.json()
    v2 = c2.post("/api/v1/auth/otp/verify", json={"flow": s2["flow"], "code": s2["demo"]}, headers=H)
    assert v2.status_code == 200 and "newAccount" not in v2.json()


def test_backup_mobile_gets_codes():
    c, ph, bk = client(), phone(), phone()
    s = c.post("/api/v1/auth/otp/start", json={"id": ph}, headers=H).json()
    v = c.post("/api/v1/auth/otp/verify", json={"flow": s["flow"], "code": s["demo"]}, headers=H).json()
    c.post("/api/v1/auth/otp/create", json={"flow": v["newAccount"], "name": "Ravi Kumar", "terms": True}, headers=H)
    cool()
    b = c.post("/api/v1/auth/contact/backup", json={"value": bk}, headers=H).json()
    assert c.post("/api/v1/auth/contact/verify", json={"flow": b["flow"], "code": b["demo"]}, headers=H).status_code == 200
    assert c.get("/api/v2/me", headers=H).json()["user"]["recoveryPhone"].endswith(bk)
    # a code to the backup signs into the same account
    cool()
    c3 = client()
    s3 = c3.post("/api/v1/auth/otp/start", json={"id": bk}, headers=H).json()
    v3 = c3.post("/api/v1/auth/otp/verify", json={"flow": s3["flow"], "code": s3["demo"]}, headers=H)
    assert v3.status_code == 200 and "newAccount" not in v3.json()
    assert c3.get("/api/v2/me", headers=H).json()["user"]["name"] == "Ravi Kumar"

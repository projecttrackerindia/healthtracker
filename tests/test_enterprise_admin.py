"""Admin roles, authenticator sign-in, set-up links, two-admin approval of doctors and pharmacists, licence expiry."""
import os
import time
import uuid

os.environ.setdefault("DATABASE_URL", "sqlite:///./data/test_enterprise.db")
os.environ.setdefault("OTP_DEMO", "1")

from fastapi.testclient import TestClient  # noqa: E402

import server  # noqa: E402
from api import totp  # noqa: E402

H = {"x-tht": "1"}


def code(sec, shift=0):
    return totp._code(sec, int(time.time() // 30) + shift)


def admin(email, role="owner", pw="Chennai#Rain2026!x"):
    """Create an admin directly and sign in through the authenticator set-up, as a new admin would."""
    from api.db import SessionLocal
    from api.models import Admin
    from api.security import hash_pw
    with SessionLocal() as db:
        if not db.query(Admin).filter(Admin.email == email).first():
            db.add(Admin(email=email, pw_hash=hash_pw(pw), role=role))
            db.commit()
    c = TestClient(server.app)
    c.__enter__()
    c.headers.update(H)
    r = c.post("/api/admin/login", json={"email": email, "password": pw})
    assert r.status_code == 428 and r.json()["detail"]["enrolTotp"], r.text
    d = r.json()["detail"]
    assert "<svg" in d["qr"] and d["uri"].startswith("otpauth://totp/")
    assert c.post("/api/admin/login", json={"email": email, "password": pw, "totp": "123456", "enrol": d["enrol"]}).status_code == 401
    ok = c.post("/api/admin/login", json={"email": email, "password": pw, "totp": code(d["secret"]), "enrol": d["enrol"]})
    assert ok.status_code == 200, ok.text
    c.secret = d["secret"]
    return c


def test_totp_every_sign_in_and_no_replay(monkeypatch):
    monkeypatch.setenv("TOTP_REQUIRED", "1")
    e = f"o{uuid.uuid4().hex[:6]}@urbanhealth.in"
    o = admin(e)
    assert o.get("/api/admin/me").json()["totp"] is True
    c = TestClient(server.app)
    c.__enter__()
    c.headers.update(H)
    assert c.post("/api/admin/login", json={"email": e, "password": "Chennai#Rain2026!x"}).json()["detail"] == {"needTotp": True}
    # the code that enrolled cannot be used again
    assert c.post("/api/admin/login", json={"email": e, "password": "Chennai#Rain2026!x", "totp": code(o.secret)}).status_code == 401
    assert c.post("/api/admin/login", json={"email": e, "password": "Chennai#Rain2026!x", "totp": code(o.secret, 1)}).status_code == 200


def test_roles_are_enforced_everywhere(monkeypatch):
    monkeypatch.setenv("TOTP_REQUIRED", "1")
    tag = uuid.uuid4().hex[:6]
    ops, con = admin(f"ops{tag}@urbanhealth.in", "ops"), admin(f"con{tag}@urbanhealth.in", "content")
    assert con.get("/api/admin/videos").status_code == 200
    for path in ("/api/admin/users", "/api/admin/households", "/api/admin/onboard", "/api/admin/rx", "/api/admin/data-requests"):
        assert con.get(path).status_code == 403, path
    assert ops.get("/api/admin/users").status_code == 200
    assert ops.get("/api/admin/admins").status_code == 403
    assert ops.put("/api/admin/plans/family", json={}).status_code == 403
    assert ops.post("/api/admin/households/x/restore/1").status_code == 403
    assert ops.delete("/api/admin/stores/x").status_code == 403
    from api.admin import allowed
    assert allowed("owner", "DELETE", "/api/admin/admins/3") and not allowed("ops", "GET", "/api/admin/admins")
    assert allowed("content", "PUT", "/api/admin/catalog/meds/x") and not allowed("content", "GET", "/api/admin/users")


def test_lists_are_paged_and_viewing_is_audited(monkeypatch):
    monkeypatch.setenv("TOTP_REQUIRED", "1")
    o = admin(f"p{uuid.uuid4().hex[:6]}@urbanhealth.in")
    d = o.get("/api/admin/users?page=1&size=10").json()
    assert {"total", "page", "pages", "users"} <= set(d) and len(d["users"]) <= 10
    assert any(r["what"] == "view.users" for r in o.get("/api/admin/audit").json()["rows"])


def _hospital(o):
    s = o.post("/api/admin/stores", json={"kind": "hospital", "name": "Test Clinic " + uuid.uuid4().hex[:4], "city": "Chennai",
                                          "address": "1 Main Rd", "phone": "9000000000", "lat": 13.0, "lng": 80.2}).json()
    return s["id"]


def test_doctor_needs_certificate_and_two_admins(monkeypatch):
    monkeypatch.setenv("TOTP_REQUIRED", "1")
    tag = uuid.uuid4().hex[:6]
    a1, a2 = admin(f"a{tag}@urbanhealth.in"), admin(f"b{tag}@urbanhealth.in", "ops")
    sid = _hospital(a1)
    from api.db import SessionLocal
    from api.models import PartnerUser
    with SessionLocal() as db:
        u = PartnerUser(store_id=sid, email=f"dr{tag}@example.com", name="Dr Test", role="doctor", reg_no="TNMC 1234", pw_hash="x", must_change=False)
        db.add(u)
        db.commit()
        uid = u.id
    v = f"/api/admin/stores/{sid}/users/{uid}/verify"
    assert "certificate" in a1.post(v, json={"verified": True}).json()["detail"]
    with SessionLocal() as db:
        u = db.get(PartnerUser, uid)
        u.reg_doc, u.reg_expiry = "f1", "2099-01-01"
        db.commit()
    assert a1.post(v, json={"verified": True}).json()["approvedBy"] == f"a{tag}@urbanhealth.in"
    assert a1.post(v, json={"verified": True}).status_code == 409          # the same admin can't approve twice
    assert a2.post(v, json={"verified": True}).json()["verified"] is True   # a second admin completes it
    assert a2.post(v, json={"verified": False}).json()["verified"] is False  # withdrawal needs only one


def test_setup_link_not_password(monkeypatch):
    monkeypatch.setenv("TOTP_REQUIRED", "1")
    o = admin(f"s{uuid.uuid4().hex[:6]}@urbanhealth.in")
    sid = _hospital(o)
    r = o.post(f"/api/admin/stores/{sid}/users", json={"name": "Asha Staff", "phone": "98765" + str(uuid.uuid4().int)[-5:], "role": "staff"})
    j = r.json()
    assert r.status_code == 200 and j["setupLink"] is True and j["demoLink"].startswith("/partner/join/")
    # (the test helper completes the link and reports the password it chose; the server never made one up)
    from api.db import SessionLocal
    from api.models import Audit
    with SessionLocal() as db:
        assert db.query(Audit).filter(Audit.what.like("partner.join%")).count() >= 1


def test_unapproved_pharmacist_cannot_sign_off(monkeypatch):
    from fastapi import HTTPException
    from api.models import PartnerUser
    from api.partner import _pharmacist
    u = PartnerUser(role="pharmacist", reg_no="TN/1234", must_change=False, verified=False)
    try:
        _pharmacist(u)
        raise AssertionError("should refuse")
    except HTTPException as e:
        assert e.status_code == 403 and "registration" in e.detail
    u.verified = True
    assert _pharmacist(u) is u


def test_licence_expiry_pauses_partner_and_lapses_registration():
    from api.db import SessionLocal
    from api.models import PartnerUser, Store
    from api.onboard import expire_partners
    with SessionLocal() as db:
        s = Store(kind="pharmacy", name="Old Licence Medicals", city="Chennai", lat=13.0, lng=80.2, verified=True, active=True, profile={"licenceExpiry": "2020-01-01"})
        db.add(s)
        db.flush()
        u = PartnerUser(store_id=s.id, email=f"ph{uuid.uuid4().hex[:6]}@example.com", role="pharmacist", verified=True, reg_expiry="2020-01-01")
        db.add(u)
        db.commit()
        sid, uid = s.id, u.id
        out = expire_partners(db)
        assert out["paused"] >= 1 and out["lapsed"] >= 1
        assert db.get(Store, sid).active is False and db.get(PartnerUser, uid).verified is False


def test_totp_maths():
    sec = totp.new_secret()
    t = 1_800_000_000
    c = totp._code(sec, t // 30)
    assert totp.verify(sec, c, 0, at=t) == t // 30
    assert totp.verify(sec, c, t // 30, at=t) == 0          # already used
    assert totp.unseal(totp.seal(sec)) == sec
    # RFC 6238 test vector (SHA-1, 59 s): 94287082 -> last six digits 287082
    import base64
    rfc = base64.b32encode(b"12345678901234567890").decode().rstrip("=")
    assert totp._code(rfc, 59 // 30) == "287082"

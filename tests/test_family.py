"""Household sync and invitations."""
import os
import uuid

os.environ.setdefault("OTP_DEMO", "1")
os.environ.setdefault("PWNED_CHECK", "0")
os.environ["DATABASE_URL"] = "sqlite:///./data/test_family.db"

from fastapi.testclient import TestClient  # noqa: E402

import server  # noqa: E402
from api import family  # noqa: E402

H = {"x-tht": "1"}


def client():
    c = TestClient(server.app)
    c.__enter__()
    return c


def signup(c):
    u = uuid.uuid4().hex[:8]
    r = c.post("/api/v1/auth/signup/start", headers=H, json={"name": "Owner " + u, "email": f"{u}@example.com", "phone": "9" + str(uuid.uuid4().int)[-9:].zfill(9), "password": "Zq!8vB#2mLp@9xT", "terms": True})
    r = c.post("/api/v1/auth/signup/verify", headers=H, json={"flow": r.json()["flow"], "code": r.json()["demo"]})
    assert r.status_code == 200, r.text
    key = uuid.uuid4().hex
    c.headers["X-DoKKo-Key"] = key
    c.owner_tag = u
    assert c.post("/api/v1/hello", json={"name": "T", "members": 1}).status_code == 200   # gives the account a household
    return r.json()["user"]


STATE = {"members": [{"id": "m1", "name": "Owner", "rel": "You", "sex": "male", "age": 30}], "meds": {"m1": [{"id": "x", "n": "A"}]}}


def test_encrypt_roundtrip():
    blob = family.encrypt(STATE)
    assert blob[:2] == b"v1" and b"Owner" not in blob
    assert family.decrypt(blob) == STATE


def test_sync_put_get_and_conflict():
    c = client()
    signup(c)
    assert c.get("/api/v1/sync").json()["version"] == 0
    r = c.put("/api/v1/sync", headers=H, json={"base": 0, "state": STATE, "sect": {"members": 1}})
    assert r.status_code == 200 and r.json()["version"] == 1
    g = c.get("/api/v1/sync").json()
    assert g["version"] == 1 and g["state"]["members"][0]["name"] == "Owner" and g["sect"] == {"members": 1}
    stale = c.put("/api/v1/sync", headers=H, json={"base": 0, "state": STATE})
    assert stale.status_code == 409 and stale.json()["detail"]["version"] == 1 and stale.json()["detail"]["state"]["meds"]["m1"][0]["n"] == "A"
    assert c.put("/api/v1/sync", headers=H, json={"base": 1, "state": {"members": []}}).status_code == 400
    assert c.delete("/api/v1/sync", headers=H).json()["deleted"] is True
    assert c.get("/api/v1/sync").json()["version"] == 0


def test_sync_requires_sign_in():
    c = client()
    assert c.get("/api/v1/sync").status_code == 401


def test_invite_and_join_share_household():
    owner, spouse = client(), client()
    signup(owner)
    owner.put("/api/v1/sync", headers=H, json={"base": 0, "state": {"members": [{"id": "m1", "name": "O", "rel": "You"}, {"id": "m2", "name": "S", "rel": "Spouse"}]}})
    inv = owner.post("/api/v1/family/invite", headers=H, json={"member_id": "m2", "name": "S", "contact": "spouse@example.com"})
    assert inv.status_code == 200, inv.text
    tok = inv.json()["token"]
    assert inv.json()["status"] == "pending" and "/join/" in inv.json()["link"]
    assert spouse.get(f"/api/v1/family/invite/{tok}").json()["name"] == "S"
    assert spouse.get("/api/v1/family/invite/nope").status_code == 404
    signup(spouse)
    j = spouse.post("/api/v1/family/join", headers=H, json={"token": tok})
    assert j.status_code == 200 and j.json()["memberId"] == "m2" and j.json()["householdKey"]
    g = spouse.get("/api/v1/sync").json()
    assert g["version"] == 1 and g["memberId"] == "m2" and [m["id"] for m in g["state"]["members"]] == ["m1", "m2"]
    assert spouse.post("/api/v1/family/join", headers=H, json={"token": tok}).status_code == 404   # single use
    lst = owner.get("/api/v1/family/invites").json()
    assert lst["invites"][0]["status"] == "joined" and any(a["memberId"] == "m2" for a in lst["accounts"])


def test_cannot_join_second_family_with_data():
    a, b, joiner = client(), client(), client()
    signup(a); a.put("/api/v1/sync", headers=H, json={"base": 0, "state": {"members": [{"id": "m1"}, {"id": "m2"}]}})
    signup(b); b.put("/api/v1/sync", headers=H, json={"base": 0, "state": {"members": [{"id": "n1"}, {"id": "n2"}]}})
    ta = a.post("/api/v1/family/invite", headers=H, json={"member_id": "m2"}).json()["token"]
    tb = b.post("/api/v1/family/invite", headers=H, json={"member_id": "n2"}).json()["token"]
    signup(joiner)
    assert joiner.post("/api/v1/family/join", headers=H, json={"token": ta}).status_code == 200
    assert joiner.post("/api/v1/family/join", headers=H, json={"token": tb}).status_code == 409


def test_every_sync_keeps_the_previous_version():
    from api import db as DB
    from api.models import HouseholdStateHistory
    from sqlalchemy import select as sel
    c = client(); signup(c)
    base = {"members": [{"id": "m1", "name": "A", "rel": "You"}]}
    v1 = c.put("/api/v1/sync", headers=H, json={"base": 0, "state": base}).json()["version"]
    c.put("/api/v1/sync", headers=H, json={"base": v1, "state": {**base, "vitals": {"m1": [{"hr": 70}]}}})
    c.put("/api/v1/sync", headers=H, json={"base": v1 + 1, "state": base})          # a device wiped the vitals by mistake
    with DB.session() as db:
        from api.models import User
        hid = db.scalar(sel(User.household_id).where(User.name == "Owner " + c.owner_tag)) if getattr(c, "owner_tag", None) else None
        rows = db.scalars(sel(HouseholdStateHistory).order_by(HouseholdStateHistory.id)).all()
        mine = [r for r in rows if r.household_id == hid] if hid else rows[-2:]
        assert [r.version for r in mine][-2:] == [1, 2] and all(r.blob for r in mine)

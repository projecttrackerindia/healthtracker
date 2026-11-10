"""Invites never duplicate and can be resent or cancelled; identity details change once a week with an emailed code."""
import os
os.environ.setdefault("OTP_DEMO", "1")
from tests.test_people_v2 import person  # noqa: E402
from api import people  # noqa: E402


def test_normalisers():
    assert people.norm_relation("WIFE ") == "Wife" and people.norm_relation("wfie") == "Wife" and people.norm_relation("zzz") == "Other"
    assert people.norm_name("prasana  krishna") == "Prasana Krishna" and people.norm_name("McAdam") == "McAdam"
    assert people.norm_contact("+91 70931-27380")[1] == people.norm_contact("07093127380")[1] == "+917093127380"


def test_invite_dedupe_resend_cancel():
    c = person("Ravi")
    r = c.post("/api/v2/household/invite", json={"contact": "7093127380", "relation": "WIFE", "name": "sravani"}).json()
    assert r["invite"]["name"] == "Sravani" and r["invite"]["relation"] == "Wife"
    again = c.post("/api/v2/household/invite", json={"contact": "+91 70931 27380", "relation": "Wife"}).json()
    assert again["duplicate"] and again["invite"]["ref"] == r["invite"]["ref"]
    assert c.post("/api/v2/household/invite", json={"contact": "9000000001", "relation": "wife"}).status_code == 409
    assert len(c.get("/api/v2/me").json()["invites"]) == 1
    ref = r["invite"]["ref"]
    assert c.post(f"/api/v2/household/invites/{ref}/resend").status_code == 429      # too soon
    assert c.put(f"/api/v2/household/invites/{ref}", json={"name": "Sravani D"}).json()["name"] == "Sravani D"
    tok = r["link"].rsplit("/", 1)[1]
    assert c.get(f"/api/v2/household/invite/{tok}").status_code == 200
    assert c.get("/api/v2/me").json()["invites"][0]["status"] == "opened"
    assert c.delete(f"/api/v2/household/invites/{ref}").status_code == 200
    assert c.get("/api/v2/me").json()["invites"] == []
    assert c.post("/api/v2/household/join", json={"token": tok}).status_code == 400


def _fresh():
    from api.db import SessionLocal
    from api.models import OtpCode
    with SessionLocal() as db:
        db.query(OtpCode).update({"created": OtpCode.created - 100})
        db.commit()


def test_identity_weekly_lock_with_code():
    c = person("Kiran")
    pid = c.pid
    assert c.put(f"/api/v2/people/{pid}", json={"profile": {"weight": "70"}}).status_code == 200      # health data: any time
    assert c.put(f"/api/v2/people/{pid}", json={"profile": {"legalName": "Kiran Kumar"}}).status_code == 428           # needs a code
    _fresh()
    code = c.post(f"/api/v2/people/{pid}/idcode").json()["demo"]
    r = c.put(f"/api/v2/people/{pid}", json={"profile": {"legalName": "Kiran Kumar"}, "code": code})
    assert r.status_code == 200 and r.json()["idLock"]["fix"]
    _fresh()
    code = c.post(f"/api/v2/people/{pid}/idcode").json()["demo"]                                      # one correction in 24 h
    assert c.put(f"/api/v2/people/{pid}", json={"profile": {"legalName": "Kiran Kumaar"}, "code": code}).status_code == 200
    me = c.get(f"/api/v2/people/{pid}").json()
    assert me["idLock"]["locked"] and me["idLock"]["next"] > 0
    assert c.post(f"/api/v2/people/{pid}/idcode").status_code == 423
    assert c.put(f"/api/v2/people/{pid}", json={"profile": {"legalName": "X Y"}}).status_code == 423
    assert c.put(f"/api/v2/people/{pid}", json={"name": "కిరణ్"}).status_code == 200      # display name: any language, any time
    assert [x["fields"] for x in c.get("/api/v2/changes").json()][0] == ["legalName"]


def test_meds_abha_handover_relation_dupes():
    c = person("Lakshmi")
    assert c.post(f"/api/v2/people/{c.pid}/records", json={"kind": "med", "data": {"name": "DOLO-650"}}).json()["name"] == "Dolo 650"
    assert c.post(f"/api/v2/people/{c.pid}/records", json={"kind": "med", "data": {"name": "dolo650"}}).status_code == 409
    assert c.put(f"/api/v2/people/{c.pid}", json={"profile": {"weight": "60", "abha": "12345678901234"}}).status_code == 200
    d = person("Other")
    assert d.put(f"/api/v2/people/{d.pid}", json={"profile": {"abha": "12-3456-7890-1234"}}).status_code == 409
    kid = c.post("/api/v2/people", json={"name": "Anu", "dependent": True, "profile": {"dob": "2005-01-01", "sex": "female"}}).json()
    assert c.post("/api/v2/people", json={"name": "Anu K", "dependent": True, "profile": {"dob": "2005-01-01"}}).status_code == 409
    c.post(f"/api/v2/people/{kid['id']}/records", json={"kind": "vital", "data": {"type": "weight", "value": "50"}, "day": "2026-01-01"})
    h = c.post(f"/api/v2/people/{kid['id']}/handover", json={"contact": "9123456780"}).json()
    tok = h["invite"]["link"].rsplit("/", 1)[1]
    from tests.test_people_v2 import TestClient, server, H
    import uuid
    a = TestClient(server.app); a.__enter__(); a.headers.update(H)
    u = uuid.uuid4().hex[:8]
    r = a.post("/api/v1/auth/signup/start", json={"name": "Anu", "email": f"{u}@example.com", "phone": "9" + str(uuid.uuid4().int)[-9:].zfill(9), "password": "Zq!8vB#2mLp@9xT", "terms": True}).json()
    a.post("/api/v1/auth/signup/verify", json={"flow": r["flow"], "code": r["demo"]})
    assert a.post("/api/v2/household/join", json={"token": tok}).json()["handover"]
    me = a.get("/api/v2/me").json()
    assert me["me"] == kid["id"]
    assert a.get(f"/api/v2/people/{kid['id']}").json()["self"]
    w = c.post("/api/v2/household/invite", json={"contact": "9988776655", "relation": "Wife"}).json()
    assert c.get("/api/v2/household/invites/" + w["invite"]["ref"] + "/qr.svg").headers["content-type"].startswith("image/svg")
    assert c.get("/api/v2/household/duplicates").status_code == 200

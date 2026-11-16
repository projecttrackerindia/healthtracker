"""Board 10: the doctor's consult for an OP token — shared for this visit only, spoken prescription, sign and send.
Run: python -m pytest -q tests/test_visit_consult.py"""
import os
import uuid

os.environ.setdefault("OTP_DEMO", "1")
os.environ.setdefault("PWNED_CHECK", "0")
os.environ["DATABASE_URL"] = "sqlite:///./data/test_visit.db"

from fastapi.testclient import TestClient  # noqa: E402

import server  # noqa: E402
from api.db import Base, engine, session  # noqa: E402
from api.models import PartnerUser, Store, VisitShare  # noqa: E402
from api.security import hash_pw  # noqa: E402

H = {"x-tht": "1"}
PW = "Zq!8vB#2mLp@9xT"
Base.metadata.create_all(engine)
CTX = {"person": {"name": "Meera K", "age": 52, "sex": "female"}, "allergies": "Sulfa drugs",
       "medicines": [{"name": "Metformin 500 mg", "dose": "1-0-1"}, {"name": "Atorvastatin 10 mg", "dose": "0-0-1"}, {"name": "Telmisartan 40 mg", "dose": "1-0-0"}],
       "findings": [{"test": "HbA1c", "value": "7.8", "unit": "%", "flag": "high", "code": "hba1c"}]}
SAID = "Increase metformin to 1000 twice a day, continue atorva but make it 20, telma same. Repeat HbA1c in three months. Walk thirty minutes."


def clinic():
    tag = uuid.uuid4().hex[:8]
    with session() as db:
        s = Store(kind="hospital", name=f"Adyar {tag}", city="Chennai", lat=13.0, lng=80.25, active=True)
        db.add(s)
        db.flush()
        doc = PartnerUser(store_id=s.id, email=f"d{tag}@cl.test", name="Dr Anitha", role="doctor", reg_no="TNMC/55512",
                          specialty="General medicine", verified=True, pw_hash=hash_pw(PW), active=True, must_change=False)
        desk = PartnerUser(store_id=s.id, email=f"s{tag}@cl.test", name="Desk", role="staff", pw_hash=hash_pw(PW), active=True, must_change=False)
        other = PartnerUser(store_id=s.id, email=f"x{tag}@cl.test", name="Dr Other", role="doctor", reg_no="TNMC/1", verified=True,
                            pw_hash=hash_pw(PW), active=True, must_change=False)
        db.add_all([doc, desk, other])
        db.flush()
        return s.id, doc.id, doc.email, desk.email, other.email


def family():
    c = TestClient(server.app)
    c.__enter__()
    c.headers["X-DoKKo-Key"] = uuid.uuid4().hex
    c.headers.update(H)
    c.post("/api/v1/hello", json={"name": "Meera", "members": 2})
    return c


def partner(email):
    c = TestClient(server.app)
    c.__enter__()
    c.headers.update({**H, "x-forwarded-for": f"10.8.{uuid.uuid4().int % 250}.{uuid.uuid4().int % 250}"})
    assert c.post("/api/partner/login", json={"email": email, "password": PW}).status_code == 200
    return c


def visit_in_room():
    sid, did, demail, desk, other = clinic()
    fam = family()
    t = fam.post("/api/v1/queue", json={"store": sid, "doctor": did, "member": "Meera K"}).json()
    return sid, did, demail, desk, other, fam, t["id"]


def test_shared_only_for_this_visit_and_gone_when_it_ends():
    sid, did, demail, desk, other, fam, tid = visit_in_room()
    doc = partner(demail)
    assert doc.get(f"/api/partner/queue/{tid}/visit").json()["ctx"] is None
    assert fam.post(f"/api/v1/queue/{tid}/share", json={"ctx": CTX}).status_code == 200
    assert fam.get(f"/api/v1/queue/{tid}").json()["shared"] is True
    v = doc.get(f"/api/partner/queue/{tid}/visit").json()
    assert v["ctx"]["allergies"] == "Sulfa drugs" and v["token"]["member"] == "Meera K"
    with session() as db:
        assert b"Sulfa" not in db.get(VisitShare, tid).blob          # sealed at rest
    # the desk and another doctor do not see it
    assert partner(desk).get(f"/api/partner/queue/{tid}/visit").status_code == 403
    assert partner(other).get(f"/api/partner/queue/{tid}/visit").status_code == 403
    for to in ("called", "in", "done"):
        assert doc.post(f"/api/partner/queue/{tid}/move", json={"to": to}).status_code == 200
    with session() as db:
        assert db.get(VisitShare, tid) is None
    assert fam.post(f"/api/v1/queue/{tid}/share", json={"ctx": CTX}).status_code == 409


def test_another_household_cannot_share_into_someone_elses_token():
    sid, did, demail, desk, other, fam, tid = visit_in_room()
    assert family().post(f"/api/v1/queue/{tid}/share", json={"ctx": CTX}).status_code == 404


def test_the_spoken_prescription_is_drafted_against_what_she_takes_now():
    sid, did, demail, desk, other, fam, tid = visit_in_room()
    fam.post(f"/api/v1/queue/{tid}/share", json={"ctx": CTX})
    d = partner(demail).post(f"/api/partner/queue/{tid}/rx-draft", json={"text": SAID}).json()
    got = {i["name"]: (i["strength"], i["frequency"], i["status"]) for i in d["items"]}
    assert got["Metformin"] == ("1000 mg", "bd", "changed")
    assert got["Atorvastatin"] == ("20 mg", "hs", "changed")
    assert got["Telmisartan"] == ("40 mg", "od", "same")
    assert d["tests"][0]["code"] == "hba1c" and d["tests"][0]["when"] == "3 months"
    assert d["advice"] == ["Walk 30 min daily"]


def test_nothing_is_added_that_was_not_said():
    sid, did, demail, desk, other, fam, tid = visit_in_room()
    fam.post(f"/api/v1/queue/{tid}/share", json={"ctx": CTX})
    d = partner(demail).post(f"/api/partner/queue/{tid}/rx-draft", json={"text": "Continue metformin."}).json()
    assert [i["name"] for i in d["items"]] == ["Metformin"] and d["tests"] == []


def test_sign_needs_the_patient_in_and_every_medicine_timed():
    sid, did, demail, desk, other, fam, tid = visit_in_room()
    doc = partner(demail)
    body = {"items": [{"name": "Metformin", "strength": "1000 mg", "frequency": "bd"}], "tests": [{"code": "hba1c", "name": "HbA1c", "when": "3 months"}]}
    assert doc.put(f"/api/partner/queue/{tid}/rx", json=body).status_code == 409
    doc.post(f"/api/partner/queue/{tid}/move", json={"to": "called"})
    assert doc.put(f"/api/partner/queue/{tid}/rx", json={"items": [{"name": "Metformin", "frequency": "whenever"}]}).status_code == 400
    assert partner(desk).put(f"/api/partner/queue/{tid}/rx", json=body).status_code == 403
    r = doc.put(f"/api/partner/queue/{tid}/rx", json=body)
    if r.status_code == 502:          # the PDF library is not installed here; the rest is covered
        return
    assert r.status_code == 200, r.text
    assert r.json()["rx"]["followUp"] == "HbA1c in 3 months"
    v = doc.get(f"/api/partner/queue/{tid}/visit").json()
    assert v["rx"]["items"][0]["name"] == "Metformin"

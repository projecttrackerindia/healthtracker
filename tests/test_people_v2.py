"""Phase 0 per-person records: the server, not the app, decides who sees what."""
import os
import uuid

os.environ.setdefault("OTP_DEMO", "1")
os.environ.setdefault("PWNED_CHECK", "0")
os.environ["DATABASE_URL"] = "sqlite:///./data/test_people_v2.db"

from fastapi.testclient import TestClient  # noqa: E402

import server  # noqa: E402

H = {"x-tht": "1"}
PROFILE = {"dob": "1992-03-12", "sex": "male", "blood": "B+", "height": "174", "weight": "72", "allergies": "Penicillin"}


def person(name, profile=None):
    c = TestClient(server.app)
    c.__enter__()
    c.headers.update(H)
    u = uuid.uuid4().hex[:8]
    r = c.post("/api/v1/auth/signup/start", json={"name": name, "email": f"{u}@example.com", "phone": "9" + str(uuid.uuid4().int)[-9:].zfill(9), "password": "Zq!8vB#2mLp@9xT", "terms": True})
    assert r.status_code == 200, r.text
    r = c.post("/api/v1/auth/signup/verify", json={"flow": r.json()["flow"], "code": r.json()["demo"]})
    assert r.status_code == 200, r.text
    me = c.post("/api/v2/people", json={"name": name, "profile": profile or PROFILE}).json()
    c.pid = me["id"]
    c.uid = c.get("/api/v2/me").json()["user"]["id"]
    return c


def family():
    """Prasanna owns the household; Sita joins by invite; Amma is Prasanna's dependent."""
    pr = person("Prasanna")
    si = person("Sita", {**PROFILE, "sex": "female", "dob": "1995-07-04", "blood": "A+", "allergies": "None"})
    link = pr.post("/api/v2/household/invite", json={"contact": "9876543210", "relation": "Wife"}).json()["link"]
    assert si.post("/api/v2/household/join", json={"token": link.rsplit("/", 1)[1]}).status_code == 200
    amma = pr.post("/api/v2/people", json={"name": "Amma", "dependent": True, "profile": {"sex": "female", "dob": "1964-01-01", "blood": "O+"}}).json()
    return pr, si, amma["id"]


def test_requires_sign_in():
    c = TestClient(server.app)
    c.__enter__()
    assert c.get("/api/v2/me").status_code == 401


def test_csrf_header_required():
    c = person("Csrf")
    del c.headers["x-tht"]
    assert c.post("/api/v2/people", json={"name": "X", "dependent": True}).status_code == 403


def test_medical_id_visible_but_profile_private_by_default():
    pr, si, _ = family()
    p = pr.get(f"/api/v2/people/{si.pid}").json()
    assert p["access"] == "medid"
    assert p["medicalId"]["blood"] == "A+"
    assert "profile" not in p
    assert pr.get(f"/api/v2/people/{si.pid}/records?kind=report").status_code == 403


def test_sharing_levels_gate_records():
    pr, si, _ = family()
    si.post(f"/api/v2/people/{si.pid}/records", json={"kind": "report", "data": {"title": "CBC"}})
    si.post(f"/api/v2/people/{si.pid}/records", json={"kind": "med", "data": {"name": "Iron"}})
    assert si.put(f"/api/v2/people/{si.pid}/sharing", json={"user_id": pr.uid, "level": "summary"}).status_code == 200
    kinds = {x["kind"] for x in pr.get(f"/api/v2/people/{si.pid}/records").json()}
    assert kinds == {"report"}                     # summary: reports yes, medicines no
    si.put(f"/api/v2/people/{si.pid}/sharing", json={"user_id": pr.uid, "level": "all"})
    kinds = {x["kind"] for x in pr.get(f"/api/v2/people/{si.pid}/records").json()}
    assert kinds == {"report", "med"}


def test_womens_health_never_leaks_without_its_switch():
    pr, si, _ = family()
    si.post(f"/api/v2/people/{si.pid}/records", json={"kind": "preg", "data": {"stage": "pregnant", "lmp": "2026-05-05"}})
    si.post(f"/api/v2/people/{si.pid}/records", json={"kind": "kick", "data": {"count": 10, "minutes": 38}, "day": "2026-11-09"})
    si.put(f"/api/v2/people/{si.pid}/sharing", json={"user_id": pr.uid, "level": "all", "womens": False})
    p = pr.get(f"/api/v2/people/{si.pid}").json()
    assert "pregnancy" not in p and "pregnancy" not in p["medicalId"]
    assert not [x for x in pr.get(f"/api/v2/people/{si.pid}/records").json() if x["kind"] in ("preg", "kick", "cycle")]
    assert pr.get(f"/api/v2/people/{si.pid}/records?kind=preg").status_code == 403
    # her own view always has it, with the week worked out
    own = si.get(f"/api/v2/people/{si.pid}").json()
    assert own["pregnancy"]["stage"] == "pregnant" and own["pregnancy"]["week"] >= 1
    si.put(f"/api/v2/people/{si.pid}/sharing", json={"user_id": pr.uid, "level": "medid", "womens": True})
    assert pr.get(f"/api/v2/people/{si.pid}").json()["pregnancy"]["stage"] == "pregnant"


def test_only_owner_writes_and_reads_are_logged():
    pr, si, _ = family()
    assert pr.put(f"/api/v2/people/{si.pid}", json={"name": "Changed"}).status_code == 403
    assert pr.post(f"/api/v2/people/{si.pid}/records", json={"kind": "report", "data": {}}).status_code == 403
    assert pr.put(f"/api/v2/people/{si.pid}/sharing", json={"user_id": pr.uid, "level": "all"}).status_code == 403
    pr.get(f"/api/v2/people/{si.pid}")
    log = si.get(f"/api/v2/people/{si.pid}/access-log").json()
    assert log and log[0]["who"] == "Prasanna"


def test_dependent_managed_by_guardian():
    pr, si, amma = family()
    assert pr.post(f"/api/v2/people/{amma}/records", json={"kind": "med", "data": {"name": "Metformin 500 mg"}}).status_code == 200
    assert si.get(f"/api/v2/people/{amma}").json()["access"] == "medid"
    assert si.post(f"/api/v2/people/{amma}/records", json={"kind": "med", "data": {"name": "X"}}).status_code == 403
    assert pr.post(f"/api/v2/people/{amma}/guardians", json={"user_id": si.uid}).status_code == 200
    assert si.get(f"/api/v2/people/{amma}").json()["access"] == "guardian"
    assert si.post(f"/api/v2/people/{amma}/records", json={"kind": "dose", "data": {"med": "m"}, "day": "2026-11-09"}).status_code == 200


def test_other_families_cannot_probe():
    pr, si, amma = family()
    stranger = person("Stranger")
    assert stranger.get(f"/api/v2/people/{si.pid}").status_code == 404
    assert stranger.get(f"/api/v2/people/{amma}").status_code == 404


def test_emergency_contact_validation_and_onboarded_flag():
    c = person("Solo")
    assert c.get("/api/v2/me").json()["onboarded"] is False
    assert c.post(f"/api/v2/people/{c.pid}/records", json={"kind": "contact", "data": {"name": "Ravi"}}).status_code == 400
    assert c.post(f"/api/v2/people/{c.pid}/records", json={"kind": "contact", "data": {"name": "Ravi", "phone": "+91 98765 43210", "relation": "Brother", "order": 1}}).status_code == 200
    me = c.get("/api/v2/me").json()
    assert me["onboarded"] is True and me["people"][0]["medicalId"]["contacts"][0]["name"] == "Ravi"


def test_leave_takes_records_and_ends_sharing():
    pr, si, _ = family()
    si.post(f"/api/v2/people/{si.pid}/records", json={"kind": "report", "data": {"title": "CBC"}})
    si.put(f"/api/v2/people/{si.pid}/sharing", json={"user_id": pr.uid, "level": "all"})
    assert si.post("/api/v2/household/leave").status_code == 200
    assert pr.get(f"/api/v2/people/{si.pid}").status_code == 404
    assert [x["title"] for x in si.get(f"/api/v2/people/{si.pid}/records?kind=report").json()] == ["CBC"]


def test_last_guardian_cannot_leave_or_be_removed():
    pr, si, amma = family()
    assert pr.post("/api/v2/household/leave").status_code == 409
    pr.post(f"/api/v2/people/{amma}/guardians", json={"user_id": si.uid})
    assert pr.post("/api/v2/household/leave").status_code == 200
    assert si.get("/api/v2/me").json()["user"]["role"] == "admin"   # ownership passed on


def test_owner_removes_member():
    pr, si, _ = family()
    assert si.post("/api/v2/household/remove", json={"user_id": pr.uid}).status_code == 403
    assert pr.post("/api/v2/household/remove", json={"user_id": si.uid}).status_code == 200
    assert pr.get(f"/api/v2/people/{si.pid}").status_code == 404
    assert si.get(f"/api/v2/people/{si.pid}").status_code == 200


def test_records_encrypted_at_rest():
    c = person("Enc")
    c.post(f"/api/v2/people/{c.pid}/records", json={"kind": "med", "data": {"name": "Secretmedicine"}})
    from api.db import session
    from api.models import HealthRecord, Person
    with session() as db:
        assert all(b"Secretmedicine" not in x.blob for x in db.query(HealthRecord).all())
        assert all(b"Penicillin" not in x.blob for x in db.query(Person).all())


def test_report_upload_stored_and_downloadable():
    c = person("Up")
    r = c.post(f"/api/v2/people/{c.pid}/reports", files={"file": ("cbc.pdf", b"%PDF-1.4 fake", "application/pdf")}, data={"read": "0"})
    assert r.status_code == 200, r.text
    rid = r.json()["id"]
    f = c.get(f"/api/v2/records/{rid}/file")
    assert f.status_code == 200 and f.content.startswith(b"%PDF")
    assert c.post(f"/api/v2/people/{c.pid}/reports", files={"file": ("x.exe", b"MZ", "application/octet-stream")}).status_code == 415


def test_v2_reminders_go_to_owner_and_guardians_only(monkeypatch):
    from datetime import datetime
    from api import push as PUSH, reminders
    pr, si, amma = family()
    pr.post(f"/api/v2/people/{amma}/records", json={"kind": "med", "data": {"name": "Metformin", "times": ["08:00"], "active": True}})
    si.post(f"/api/v2/people/{si.pid}/records", json={"kind": "med", "data": {"name": "Iron", "times": ["08:00"], "active": True}})
    from api.db import session
    from api.models import PushSub
    with session() as db:
        db.add(PushSub(user_id=pr.uid, household_id="h", endpoint="https://p/" + pr.uid, sub={"endpoint": "https://p/" + pr.uid}))
        db.add(PushSub(user_id=si.uid, household_id="h", endpoint="https://p/" + si.uid, sub={"endpoint": "https://p/" + si.uid}))
    got = []
    monkeypatch.setattr(PUSH, "send", lambda sub, data, ttl=3600: (got.append((sub["endpoint"], data["body"])) or (True, 201, "")))
    with session() as db:
        reminders.tick_people(db, datetime(2026, 11, 10, 8, 5, tzinfo=reminders.IST))
    to_pr = [b for e, b in got if e.endswith(pr.uid)]
    to_si = [b for e, b in got if e.endswith(si.uid)]
    assert "Metformin" in to_pr and "Iron" not in " ".join(to_pr)       # Sita's medicines never reach Prasanna
    assert "Iron" in to_si and "Metformin" not in " ".join(to_si)
    got.clear()
    with session() as db:   # same window again: no repeat
        reminders.tick_people(db, datetime(2026, 11, 10, 8, 10, tzinfo=reminders.IST))
    assert not [g for g in got if "Metformin" in g[1] or "Iron" in g[1]]
    with session() as db:   # leave no test phones subscribed for the tests that run after this one
        db.query(PushSub).filter(PushSub.user_id.in_([pr.uid, si.uid])).delete()


def test_lab_orders_follow_person_privacy():
    pr, si, amma = family()
    key = pr.get("/api/v2/me").json()["hkey"]
    assert key == si.get("/api/v2/me").json()["hkey"]
    from api.db import session
    from api.models import LabTest, Store
    with session() as db:
        lab = Store(kind="lab", name="Test Lab", city="Hyderabad", area="Gachibowli", lat=26.9124, lng=75.7873, home_collection=True, verified=True, active=True)   # its own city, away from other tests' labs
        db.add(lab)
        db.flush()
        db.add(LabTest(store_id=lab.id, code="hba1c", name="HbA1c", price=450, tat_hours=24, fasting=False))
    code = "hba1c"
    q = si.post("/api/v1/labs/quotes", json={"tests": [code], "home": True, "lat": 26.9124, "lng": 75.7873}, headers={"X-DoKKo-Key": key}).json()
    store = next((x for x in q.get("labs", []) if x["lines"] and x["name"] == "Test Lab"), None)
    assert store, "the test database seeds labs; without one this test proves nothing"
    def book(c, who):
        return c.post("/api/v1/orders", json={"store": store["id"], "kind": "lab", "items": [{"code": code}], "memberId": who, "member": "x", "slot": store["slots"][0], "payment": "cod"}, headers={"X-DoKKo-Key": key})
    assert book(pr, si.pid).status_code == 403                # cannot book for an adult who has not shared
    o = book(si, si.pid)
    assert o.status_code == 200, o.text
    assert book(pr, amma).status_code == 200                  # guardian books for a dependent
    mine = [x["id"] for x in pr.get("/api/v1/orders", headers={"X-DoKKo-Key": key}).json()["orders"]]
    assert o.json()["id"] not in mine                         # Sita's booking is hers
    assert pr.get(f"/api/v1/orders/{o.json()['id']}/track", headers={"X-DoKKo-Key": key}).status_code == 404
    assert o.json()["id"] in [x["id"] for x in si.get("/api/v1/orders", headers={"X-DoKKo-Key": key}).json()["orders"]]

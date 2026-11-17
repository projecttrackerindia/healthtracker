"""Eye exams: a verified doctor at the eye hospital writes them, the patient's app reads them, nobody else can."""
import os
import uuid

os.environ.setdefault("OTP_DEMO", "1")
os.environ.setdefault("PWNED_CHECK", "0")
os.environ["DATABASE_URL"] = "sqlite:///./data/test_eye_exam.db"

from fastapi.testclient import TestClient  # noqa: E402

import server  # noqa: E402
from api.db import Base, engine, session  # noqa: E402
from api.models import Appointment, HealthRecord, Notice, PartnerUser, Store  # noqa: E402
from api.security import hash_pw  # noqa: E402

Base.metadata.create_all(engine)
H = {"x-tht": "1"}
PW = "Zq!8vB#2mLp@9xT"
PROFILE = {"dob": "1968-03-12", "sex": "male", "blood": "B+"}


def person(name):
    c = TestClient(server.app)
    c.__enter__()
    c.headers.update(H)
    u = uuid.uuid4().hex[:8]
    r = c.post("/api/v1/auth/signup/start", json={"name": name, "email": f"{u}@example.com", "phone": "9" + str(uuid.uuid4().int)[-9:].zfill(9), "password": PW, "terms": True})
    r = c.post("/api/v1/auth/signup/verify", json={"flow": r.json()["flow"], "code": r.json()["demo"]})
    assert r.status_code == 200, r.text
    c.pid = c.post("/api/v2/people", json={"name": name, "profile": PROFILE}).json()["id"]
    c.hh = c.get("/api/v2/me").json()["user"].get("householdId") or ""
    return c


def hospital(verified=True, role="doctor"):
    tag = uuid.uuid4().hex[:8]
    with session() as db:
        s = Store(kind="hospital", name=f"Drishti {tag}", city="Chennai", lat=13.08, lng=80.27, active=True)
        db.add(s)
        db.flush()
        d = PartnerUser(store_id=s.id, email=f"d{tag}@eye.test", name="Kavitha Rao", role=role, reg_no="TNMC 4411", specialty="Ophthalmology",
                        pw_hash=hash_pw(PW), active=True, must_change=False, verified=verified)
        db.add(d)
        db.flush()
        sid, em = s.id, d.email
    c = TestClient(server.app)
    c.__enter__()
    assert c.post("/api/partner/login", headers=H, json={"email": em, "password": PW}).status_code == 200
    c.headers.update(H)
    c.sid = sid
    return c


def visit(sid, fam, status="confirmed", doctor=""):
    with session() as db:
        from api.models import Person
        hh = db.get(Person, fam.pid).household_id
        a = Appointment(household_id=hh, member_id=fam.pid, member_name="Suresh", store_id=sid, kind="visit", date="2026-11-12", time="10:00", why="Eye check", status=status, doctor=doctor)
        db.add(a)
        db.flush()
        return a.id


EXAM = {"R": {"vision": "6/9", "sph": "-2.25", "cyl": "-0.50", "axis": "180", "iop": 23, "cct": 528, "cd": 0.6, "oct": 268, "angle": "Open, grade 3", "lens": "Clear"},
        "L": {"vision": "6/6", "sph": "-2.00", "iop": 19, "cd": 0.4},
        "findings": [{"part": "disc", "side": "R", "label": "Large cup · glaucoma suspect", "tone": "watch"}],
        "note": "Your eye pressure is a little high and the nerve cup is larger. We will test your side vision.", "dx": "Glaucoma suspect OD"}


def test_doctor_sends_an_exam_and_the_patient_sees_it_on_the_eye():
    fam, doc = person("Suresh"), hospital()
    aid = visit(doc.sid, fam)
    assert any(v["id"] == aid for v in doc.get("/api/partner/eye/visits").json()["visits"])
    r = doc.put(f"/api/partner/eye/visits/{aid}", json=EXAM)
    assert r.status_code == 200, r.text
    ex = r.json()["visit"]["exam"]
    assert ex["R"]["iop"] == 23 and ex["R"]["cd"] == 0.6 and ex["R"]["sph"] == "-2.25" and ex["doctor"] == "Kavitha Rao"
    recs = fam.get(f"/api/v2/people/{fam.pid}/records?kind=eye").json()
    assert len(recs) == 1 and recs[0]["R"]["iop"] == 23 and recs[0]["findings"][0]["part"] == "disc" and recs[0]["note"].startswith("Your eye")
    # sending again updates the same record instead of adding a second one
    assert doc.put(f"/api/partner/eye/visits/{aid}", json={**EXAM, "note": "Updated note."}).status_code == 200
    recs = fam.get(f"/api/v2/people/{fam.pid}/records?kind=eye").json()
    assert len(recs) == 1 and recs[0]["note"] == "Updated note."
    with session() as db:
        n = db.query(Notice).filter(Notice.kind == "eye").order_by(Notice.id.desc()).first()
        assert n and "eye check" in n.title and n.ref["person"] == fam.pid and n.member_id == fam.pid
        x = db.query(HealthRecord).filter(HealthRecord.kind == "eye", HealthRecord.person_id == fam.pid).one()
        assert b"glaucoma" not in x.blob and b"Kavitha" not in x.blob   # encrypted at rest


def test_earlier_exams_at_the_same_hospital_come_back_for_the_trend():
    fam, doc = person("Ravi"), hospital()
    a1, a2 = visit(doc.sid, fam, "done"), visit(doc.sid, fam)
    assert doc.put(f"/api/partner/eye/visits/{a1}", json={"R": {"iop": 21, "cd": 0.55}}).status_code == 200
    h = doc.get(f"/api/partner/eye/visits/{a2}").json()
    assert h["visit"]["exam"] is None and h["history"][0]["R"]["cd"] == 0.55


def test_families_cannot_write_eye_exams_themselves():
    fam = person("Anita")
    r = fam.post(f"/api/v2/people/{fam.pid}/records", json={"kind": "eye", "day": "2026-11-12", "data": {"R": {"iop": 12}, "doctor": "Me"}})
    assert r.status_code == 403


def test_only_verified_doctors_of_that_hospital_and_only_sane_numbers():
    fam = person("Lakshmi")
    doc, other, unverified, staff = hospital(), hospital(), hospital(verified=False), hospital(role="staff")
    aid = visit(doc.sid, fam)
    assert other.put(f"/api/partner/eye/visits/{aid}", json=EXAM).status_code == 404       # another hospital's visit
    for c in (unverified, staff):
        a = visit(c.sid, fam)
        assert c.put(f"/api/partner/eye/visits/{a}", json=EXAM).status_code == 403
    for bad in ({"R": {"iop": 120}}, {"R": {"cd": 1.4}}, {"R": {"sph": "two"}}, {"R": {"axis": "200"}},
                {"findings": [{"part": "<script>", "label": "x", "tone": "watch"}]}, {"findings": [{"part": "lens", "label": " ", "tone": "watch"}]}, {}):
        assert doc.put(f"/api/partner/eye/visits/{aid}", json=bad).status_code in (400, 422), bad
    req = visit(doc.sid, fam, "requested")
    assert doc.put(f"/api/partner/eye/visits/{req}", json=EXAM).status_code == 400
    # a doctor sees visits assigned to them or to nobody, not a colleague's
    mine, theirs = visit(doc.sid, fam, doctor="Dr Kavitha Rao"), visit(doc.sid, fam, doctor="Dr Arun")
    ids = {v["id"] for v in doc.get("/api/partner/eye/visits").json()["visits"]}
    assert mine in ids and theirs not in ids


def test_eye_page_is_served_and_frameable_only_by_the_app():
    c = TestClient(server.app)
    r = c.get("/eye")
    assert r.status_code == 200 and "Urban Health · Eyes" in r.text
    assert "frame-ancestors 'self'" in r.headers["content-security-policy"]
    m = __import__("re").search(r"/a/(eye-orbit\.[0-9a-f]{8}\.bin)", r.text)
    assert m and c.get("/a/" + m.group(1)).status_code == 200


def test_board_11_near_vision_other_checks_and_a_glasses_quote_reach_the_family():
    fam, doc = person("Kavya"), hospital()
    aid = visit(doc.sid, fam)
    body = {"R": {"sph": "-1.25", "cyl": "-0.50", "axis": "180", "vision": "6/6", "add": "+1.00", "near": "N6"},
            "L": {"sph": "-1.50", "near": "N6"}, "colour": "Ishihara 14 of 14", "squint": "None",
            "glasses": {"lens": "Polycarbonate · blue filter", "lensPrice": 1800, "frame": "Kids flexible · navy", "framePrice": 1200,
                        "ready": "Thursday", "delivery": "home", "inStock": True}}
    r = doc.put(f"/api/partner/eye/visits/{aid}", json=body)
    assert r.status_code == 200, r.text
    ex = r.json()["visit"]["exam"]
    assert ex["R"]["near"] == "N6" and ex["colour"] == "Ishihara 14 of 14" and ex["squint"] == "None"
    assert ex["glasses"]["total"] == 3000 and ex["glasses"]["inStock"] is True
    with session() as db:
        n = db.query(Notice).filter(Notice.kind == "eye").order_by(Notice.id.desc()).first()
        assert "₹3,000" in n.body and "Thursday" in n.body and n.ref["glasses"]["total"] == 3000


def test_a_glasses_price_cannot_be_negative():
    fam, doc = person("Kavya"), hospital()
    aid = visit(doc.sid, fam)
    r = doc.put(f"/api/partner/eye/visits/{aid}", json={"R": {"sph": "-1.00"}, "glasses": {"lens": "CR-39", "lensPrice": -5}})
    assert r.status_code == 422


def test_family_orders_glasses_and_the_counter_moves_it_on():
    fam, doc = person("Meena"), hospital()
    aid = visit(doc.sid, fam)
    body = {"R": {"sph": "-1.25"}, "L": {"sph": "-1.00"},
            "glasses": {"lens": "CR-39", "lensPrice": 900, "frame": "Metal · black", "framePrice": 1100, "ready": "Friday", "delivery": "pickup"}}
    assert doc.put(f"/api/partner/eye/visits/{aid}", json=body).status_code == 200
    # the counter cannot mark them ready before the family orders
    assert doc.post(f"/api/partner/eye/{aid}/glasses", json={"status": "ready"}).status_code == 400
    g = fam.get("/api/v2/glasses").json()["glasses"]
    assert g and g[0]["total"] == 2000 and g[0]["status"] == "quoted"
    o = fam.post(f"/api/v2/glasses/{aid}/order", json={"pay": "counter"}).json()
    assert o["status"] == "ordered" and o["pay"] == "counter"
    # an edited exam keeps the order
    assert doc.put(f"/api/partner/eye/visits/{aid}", json=body).json()["visit"]["exam"]["glasses"]["status"] == "ordered"
    r = doc.post(f"/api/partner/eye/{aid}/glasses", json={"status": "ready"})
    assert r.status_code == 200 and r.json()["status"] == "ready"
    with session() as db:
        n = db.query(Notice).filter(Notice.title == "Your glasses are ready").order_by(Notice.id.desc()).first()
        assert n and "₹2,000 to pay" in n.body

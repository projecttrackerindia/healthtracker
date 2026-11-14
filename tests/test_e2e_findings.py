"""Findings from the 14 Nov 2026 end-to-end run (family app, pharmacy, lab, technician, admin), pinned."""
import os
import uuid

os.environ.setdefault("OTP_DEMO", "1")
os.environ.setdefault("PWNED_CHECK", "0")
os.environ["DATABASE_URL"] = "sqlite:///./data/test_e2e_findings.db"

from fastapi.testclient import TestClient  # noqa: E402

import server  # noqa: E402
from api.db import Base, engine, session  # noqa: E402
from api.models import HealthRecord, LabTest, Order, PartnerUser, Store, now  # noqa: E402
from api.security import hash_pw  # noqa: E402
from api.seed import TESTS  # noqa: E402

Base.metadata.create_all(engine)
H = {"x-tht": "1"}
PW = "Zq!8vB#2mLp@9xT"
LL = {"lat": 13.1137, "lng": 80.2954}


def _lab(verified=True):
    tag = uuid.uuid4().hex[:6]
    with session() as db:
        s = Store(kind="lab", name=f"Lab {tag}", city="Chennai", lat=13.115, lng=80.296, active=True, verified=verified, home_collection=True)
        db.add(s)
        db.flush()
        for code, (name, price, tat, fast) in TESTS.items():
            db.add(LabTest(store_id=s.id, code=code, name=name, price=price, tat_hours=tat, fasting=fast))
        owner = PartnerUser(store_id=s.id, email=f"o{tag}@lab.test", name="Owner", role="owner", pw_hash=hash_pw(PW), active=True, must_change=False)
        tech = PartnerUser(store_id=s.id, email=f"t{tag}@lab.test", name="Tech", phone="98400" + tag[:5].translate(str.maketrans("abcdef", "123456")),
                           role="tech", pw_hash=hash_pw(PW), active=True, must_change=False)
        db.add_all([owner, tech])
        db.flush()
        return s.id, owner.email, tech.email, tech.id


def _family():
    c = TestClient(server.app)
    c.__enter__()
    c.headers.update(H)
    u = uuid.uuid4().hex[:6]
    r = c.post("/api/v1/auth/signup/start", json={"name": "Kavya Raman", "email": f"k{u}@ex.com", "phone": "9" + str(uuid.uuid4().int)[-9:].zfill(9),
                                                   "password": "Mango-river-kite-82!", "terms": True}).json()
    c.post("/api/v1/auth/signup/verify", json={"flow": r["flow"], "code": r["demo"]})
    pid = c.post("/api/v2/people", json={"name": "Kavya Raman", "profile": {"dob": "1992-05-14", "sex": "female"}}).json()["id"]
    return c, pid


def _partner(email):
    c = TestClient(server.app)
    c.__enter__()
    c.headers.update(H)
    assert c.post("/api/partner/login", json={"email": email, "password": PW}).status_code == 200
    return c


def test_partners_still_in_onboarding_are_not_offered_to_families():
    _lab(verified=False)
    c, _ = _family()
    labs = c.post("/api/v1/labs/quotes", json={"tests": ["CBC"], "home": True, **LL}).json()["labs"]
    with session() as db:
        pending = {s.id for s in db.query(Store).filter(Store.verified == False).all()}  # noqa: E712
    assert not pending & {l["id"] for l in labs}


def test_a_new_partner_cannot_be_created_already_live():
    from api.admin import StoreIn, add_store
    with session() as db:
        from api.models import Admin
        a = Admin(email=f"a{uuid.uuid4().hex[:6]}@uh.test", pw_hash="x")
        db.add(a)
        db.flush()
        j = add_store(StoreIn(kind="pharmacy", name="Shortcut Pharmacy", city="Chennai", lat=13.1, lng=80.2, verified=True), a, db)
        assert db.get(Store, j["id"]).verified is False
        assert db.get(Store, j["id"]).rating == 0


def test_fasting_tests_are_offered_morning_slots_only():
    _lab()
    c, _ = _family()
    labs = c.post("/api/v1/labs/quotes", json={"tests": ["FBS"] if "FBS" in TESTS else [k for k, v in TESTS.items() if v[3]][:1], "home": True, **LL}).json()["labs"]
    slots = [s for l in labs if l["fasting"] for s in l["slots"]]
    assert slots and not any(s.endswith(("04:00 PM", "4:00 PM", "05:00 PM", "5:00 PM")) for s in slots)


def test_badges_need_a_real_comparison():
    _lab()
    c, _ = _family()
    labs = c.post("/api/v1/labs/quotes", json={"tests": ["CBC"], "home": True, **LL}).json()["labs"]
    assert all("Best rated" not in l["tags"] for l in labs)   # nobody has been rated yet


def test_a_lab_report_reaches_the_persons_lab_tab_and_technicians_stay_in_their_lane():
    sid, owner, tech_email, tech_id = _lab()
    fam, pid = _family()
    with session() as db:
        from api.models import User
        hh = db.query(User).order_by(User.created.desc()).first().household_id
        o = Order(household_id=hh, store_id=sid, kind="lab", status="confirmed", items=[{"code": "CBC", "name": "Complete blood count (CBC)", "price": 350}],
                  total=350, member="Kavya Raman", member_id=pid, slot="Sun 15 Nov · 7:00 AM", door_code="4177", created=now(),
                  addr={"line1": "Flat 3B", "city": "Chennai", "pin": "600021", "phone": "9840011134", "lat": 13.11, "lng": 80.29})
        db.add(o)
        db.flush()
        oid = o.id
    own, tc = _partner(owner), _partner(tech_email)
    assert own.post(f"/api/partner/orders/{oid}/assign", json={"agent": tech_id}).status_code == 200
    assert tc.post(f"/api/partner/orders/{oid}/status", json={"status": "cancelled", "note": "x"}).status_code == 403
    assert tc.post(f"/api/partner/orders/{oid}/status", json={"status": "en_route"}).status_code == 200
    assert tc.post(f"/api/partner/orders/{oid}/status", json={"status": "collected", "code": "4177"}).status_code == 200
    assert own.post(f"/api/partner/orders/{oid}/status", json={"status": "processing"}).status_code == 200
    pdf = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF"
    r = own.put(f"/api/partner/orders/{oid}/report", content=pdf, headers={"content-type": "application/pdf", "x-file-name": "cbc.pdf"})
    assert r.status_code == 200, r.text
    with session() as db:
        assert db.query(HealthRecord).filter(HealthRecord.person_id == pid, HealthRecord.kind == "report").count() == 1


def test_medicine_cancellation_terms_talk_about_the_pharmacy_not_a_slot():
    from api.booking import cancel_terms
    o = Order(kind="medicine", status="checking", slot="")
    assert "pharmacy packs" in cancel_terms(o)["why"]
    o.status = "packing"
    assert cancel_terms(o)["can"] is False


def test_brand_names_find_the_generic():
    from api.ai import match_sku
    assert match_sku("Dolo 650")["id"] == "para500"
    assert match_sku("Telma 40")["id"] == "telmi40"

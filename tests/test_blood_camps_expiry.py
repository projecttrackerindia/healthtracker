"""Blood bank: bags carry expiry dates, banks run donation camps that nearby donors can book, and a bank can ask only the donors it picks.
Run: python -m pytest -q tests/test_blood_camps_expiry.py"""
import os
import time
import uuid

os.environ.setdefault("OTP_DEMO", "1")
os.environ.setdefault("PWNED_CHECK", "0")
os.environ["DATABASE_URL"] = "sqlite:///./data/test_bank.db"

from fastapi.testclient import TestClient  # noqa: E402

import server  # noqa: E402
from api.db import Base, engine, session  # noqa: E402
from api.models import BloodStock, Donor, Notice, PartnerUser, Store, User  # noqa: E402
from api.security import hash_pw  # noqa: E402

H = {"x-tht": "1"}
PW = "Zq!8vB#2mLp@9xT"
Base.metadata.create_all(engine)
day = lambda n: time.strftime("%Y-%m-%d", time.localtime(time.time() + n * 86400))  # noqa: E731


def bank():
    tag = uuid.uuid4().hex[:8]
    with session() as db:
        s = Store(kind="bloodbank", name=f"Kaveri {tag}", city="Chennai", lat=13.06, lng=80.25, active=True, verified=True)
        db.add(s)
        db.flush()
        u = PartnerUser(store_id=s.id, email=f"b{tag}@x.test", name="Bank", role="owner", pw_hash=hash_pw(PW), active=True, must_change=False)
        db.add(u)
        db.flush()
        sid, email = s.id, u.email
    c = TestClient(server.app)
    c.__enter__()
    c.headers.update({**H, "x-forwarded-for": f"10.8.{uuid.uuid4().int % 250}.{uuid.uuid4().int % 250}"})
    assert c.post("/api/partner/login", json={"email": email, "password": PW}).status_code == 200
    return c, sid


def family():
    c = TestClient(server.app)
    c.__enter__()
    c.headers.update({**H, "x-forwarded-for": f"10.7.{uuid.uuid4().int % 250}.{uuid.uuid4().int % 250}"})
    u = uuid.uuid4().hex[:8]
    r = c.post("/api/v1/auth/signup/start", json={"name": "Arjun", "email": f"{u}@example.com", "phone": "9" + str(uuid.uuid4().int)[-9:].zfill(9), "password": PW, "terms": True})
    r = c.post("/api/v1/auth/signup/verify", json={"flow": r.json()["flow"], "code": r.json()["demo"]})
    assert r.status_code == 200, r.text
    c.post("/api/v2/people", json={"name": "Arjun", "profile": {"dob": "1990-03-12", "sex": "male", "blood": "O+"}})
    uid = c.get("/api/v2/me").json()["user"]["id"]
    with session() as db:
        hh = db.get(User, uid).household_id
    assert hh
    with session() as db:
        d = Donor(household_id=hh, member_id="m" + u, name="Arjun Sharma", group="O+", lat=13.065, lng=80.252, phone="9876500000", active=True)
        db.add(d)
        db.flush()
        c.donor, c.hh = d.id, hh
    return c


def test_batches_set_the_count_and_flag_what_expires_soon():
    c, sid = bank()
    r = c.put("/api/partner/blood/stock", json={"group": "A+", "batches": [{"n": 2, "exp": day(3)}, {"n": 5, "exp": day(30)}]})
    assert r.status_code == 200 and r.json()["units"] == 7
    row = [x for x in c.get("/api/partner/blood/stock").json()["stock"] if x["group"] == "A+"][0]
    assert row["expiring"] == 2 and row["nextExpiry"] == day(3)
    assert c.put("/api/partner/blood/stock", json={"group": "A+", "batches": [{"n": 1, "exp": day(-1)}]}).status_code == 400
    with session() as db:   # a bag that passed its date drops out of the count by itself
        x = db.query(BloodStock).filter_by(store_id=sid, group="A+").one()
        x.batches = [{"n": 2, "exp": day(-1)}, {"n": 5, "exp": day(30)}]
    row = [x for x in c.get("/api/partner/blood/stock").json()["stock"] if x["group"] == "A+"][0]
    assert row["units"] == 5 and row["expiring"] == 0
    assert c.put("/api/partner/blood/stock", json={"group": "B+", "units": 4}).json()["units"] == 4


def test_a_camp_tells_nearby_donors_and_they_can_book_and_cancel():
    f = family()
    c, _ = bank()
    assert c.post("/api/partner/bank/camps", json={"day": day(-2), "place": "Hall"}).status_code == 400
    camp = c.post("/api/partner/bank/camps", json={"day": day(5), "place": "Anna Nagar Community Hall", "slots": 5}).json()
    assert camp["notified"] >= 1 and camp["left"] == 5
    with session() as db:
        assert db.query(Notice).filter_by(household_id=f.hh, kind="blood").count() >= 1
    mine = [x for x in f.get("/api/v2/camps").json()["camps"] if x["id"] == camp["id"]]
    assert mine and mine[0]["mine"] is False and mine[0]["km"] < 15
    assert f.post(f"/api/v2/camps/{camp['id']}/book").json()["mine"] is True
    assert c.get("/api/partner/bank/camps").json()["camps"][0]["booked"] == 1
    assert f.post(f"/api/v2/camps/{camp['id']}/unbook").json()["booked"] == 0
    assert c.post(f"/api/partner/bank/camps/{camp['id']}/cancel").json()["cancelled"] is True
    assert not [x for x in f.get("/api/v2/camps").json()["camps"] if x["id"] == camp["id"]]


def test_nearby_donors_come_with_ids_so_the_bank_can_pick():
    f = family()
    c, _ = bank()
    ds = c.get("/api/partner/bank/donors?group=O%2B").json()["donors"]
    assert any(d["id"] == f.donor for d in ds)

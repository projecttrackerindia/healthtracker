"""Board 12: hospitals ask a blood bank for units; the bank gives what it can and the shelf count follows.
Run: python -m pytest -q tests/test_blood_bank_requests.py"""
import os
import uuid

os.environ.setdefault("OTP_DEMO", "1")
os.environ.setdefault("PWNED_CHECK", "0")
os.environ["DATABASE_URL"] = "sqlite:///./data/test_bank.db"

from fastapi.testclient import TestClient  # noqa: E402

import server  # noqa: E402
from api.db import Base, engine, session  # noqa: E402
from api.models import BloodStock, Donor, PartnerUser, Store  # noqa: E402
from api.security import hash_pw  # noqa: E402

H = {"x-tht": "1"}
PW = "Zq!8vB#2mLp@9xT"
Base.metadata.create_all(engine)


def two():
    tag = uuid.uuid4().hex[:8]
    with session() as db:
        bank = Store(kind="bloodbank", name=f"Kaveri {tag}", city="Chennai", lat=13.06, lng=80.25, active=True, verified=True)
        hosp = Store(kind="hospital", name=f"Apollo {tag}", city="Chennai", lat=13.061, lng=80.253, active=True, verified=True)
        db.add_all([bank, hosp])
        db.flush()
        db.add(BloodStock(store_id=bank.id, group="B+", component="whole", units=3))
        b = PartnerUser(store_id=bank.id, email=f"b{tag}@x.test", name="Bank", role="owner", pw_hash=hash_pw(PW), active=True, must_change=False)
        h = PartnerUser(store_id=hosp.id, email=f"h{tag}@x.test", name="Dr Karthik", role="doctor", reg_no="TN1", verified=True, pw_hash=hash_pw(PW), active=True, must_change=False)
        db.add_all([b, h])
        db.add(Donor(household_id="h" + tag, member_id="m" + tag, name="Arjun Sharma", group="O-", lat=13.07, lng=80.255, phone="9876500000", active=True))
        db.flush()
        return bank.id, b.email, h.email


def login(email):
    c = TestClient(server.app)
    c.__enter__()
    c.headers.update({**H, "x-forwarded-for": f"10.9.{uuid.uuid4().int % 250}.{uuid.uuid4().int % 250}"})
    assert c.post("/api/partner/login", json={"email": email, "password": PW}).status_code == 200
    return c


def test_a_hospital_asks_and_the_bank_gives_what_it_has():
    bank_id, be, he = two()
    hosp, bank = login(he), login(be)
    assert any(b["id"] == bank_id and b["has"] is True for b in hosp.get("/api/partner/bank/banks?group=B%2B").json()["banks"])
    q = hosp.post("/api/partner/bank/requests", json={"bank": bank_id, "group": "B+", "units": 2, "reason": "Surgery", "needBy": "surgery at 1 PM", "urgent": True, "patient": "Ravi"}).json()
    assert q["status"] == "new" and q["doctor"] == "Dr Karthik" and q["replyBy"] > q["created"]
    inbox = bank.get("/api/partner/bank/requests").json()
    assert inbox["side"] == "bank" and inbox["requests"][0]["id"] == q["id"] and inbox["requests"][0]["from"]["name"].startswith("Apollo")
    assert bank.get("/api/partner/me").json()["counts"]["unitRequests"] == 1
    r = bank.post(f"/api/partner/bank/requests/{q['id']}/answer", json={"units": 2}).json()
    assert r["status"] == "confirmed" and r["given"] == 2
    with session() as db:
        assert db.query(BloodStock).filter_by(store_id=bank_id, group="B+").one().units == 1
    assert bank.post(f"/api/partner/bank/requests/{q['id']}/answer", json={"units": 1}).status_code == 409
    assert bank.post(f"/api/partner/bank/requests/{q['id']}/status", json={"to": "sent"}).status_code == 409
    assert bank.post(f"/api/partner/bank/requests/{q['id']}/status", json={"to": "packed"}).json()["status"] == "packed"
    assert hosp.get("/api/partner/bank/requests").json()["requests"][0]["status"] == "packed"


def test_the_bank_cannot_give_more_than_the_shelf_and_can_give_part():
    bank_id, be, he = two()
    hosp, bank = login(he), login(be)
    q = hosp.post("/api/partner/bank/requests", json={"bank": bank_id, "group": "B+", "units": 5}).json()
    assert bank.post(f"/api/partner/bank/requests/{q['id']}/answer", json={"units": 5}).status_code == 409
    r = bank.post(f"/api/partner/bank/requests/{q['id']}/answer", json={"units": 3}).json()
    assert r["status"] == "partial" and r["given"] == 3


def test_only_hospitals_ask_and_only_the_bank_answers():
    bank_id, be, he = two()
    hosp, bank = login(he), login(be)
    assert bank.post("/api/partner/bank/requests", json={"bank": bank_id, "group": "B+"}).status_code == 403
    q = hosp.post("/api/partner/bank/requests", json={"bank": bank_id, "group": "B+"}).json()
    assert hosp.post(f"/api/partner/bank/requests/{q['id']}/answer", json={"units": 1}).status_code == 403
    assert hosp.post(f"/api/partner/bank/requests/{q['id']}/status", json={"to": "cancelled"}).json()["status"] == "cancelled"


def test_donors_near_the_bank_show_first_name_and_initial_only():
    bank_id, be, he = two()
    d = login(be).get("/api/partner/bank/donors?group=B%2B").json()
    hit = next(x for x in d["donors"] if x["name"].startswith("Arjun"))
    assert hit["name"] == "Arjun S" and "phone" not in hit and hit["km"] < 3


def test_given_units_leave_the_oldest_bags_first_and_stay_gone():
    import time as _t
    bank_id, be, he = two()
    bank, hosp = login(be), login(he)
    d = lambda n: _t.strftime("%Y-%m-%d", _t.localtime(_t.time() + n * 86400))  # noqa: E731
    assert bank.put("/api/partner/blood/stock", json={"group": "O+", "batches": [{"n": 3, "exp": d(30)}, {"n": 2, "exp": d(4)}]}).json()["units"] == 5
    q = hosp.post("/api/partner/bank/requests", json={"bank": bank_id, "group": "O+", "units": 3}).json()
    assert bank.post(f"/api/partner/bank/requests/{q['id']}/answer", json={"units": 3}).json()["given"] == 3
    row = [x for x in bank.get("/api/partner/blood/stock").json()["stock"] if x["group"] == "O+"][0]
    assert row["units"] == 2 and row["batches"] == [{"n": 2, "exp": d(30)}]    # the two near their date went first


def test_earnings_count_units_at_the_banks_own_charges_and_today_sums_up():
    bank_id, be, he = two()
    bank, hosp = login(be), login(he)
    q = hosp.post("/api/partner/bank/requests", json={"bank": bank_id, "group": "B+", "units": 2, "urgent": True}).json()
    t = bank.get("/api/partner/bank/today").json()
    assert t["counts"]["waiting"] >= 1 and t["waiting"][0]["id"] == q["id"]
    e = bank.get("/api/partner/bank/earnings").json()
    assert e["feesSet"] is False
    assert bank.put("/api/partner/bank/fees", json={"fees": {"whole": 1550, "platelets": 400, "junk": 9}}).json()["fees"] == {"whole": 1550, "platelets": 400}
    bank.post(f"/api/partner/bank/requests/{q['id']}/answer", json={"units": 2})
    m = bank.get("/api/partner/bank/earnings").json()["months"][0]
    assert m["units"] >= 2 and m["amount"] >= 3100 and m["byHospital"][0]["units"] >= 2
    assert hosp.get("/api/partner/bank/earnings").status_code == 403

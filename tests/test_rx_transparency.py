"""The family is told who checked their prescription, and the pharmacist is told how old it is.

Run: python -m pytest -q tests/test_rx_transparency.py
"""
import os
import uuid
from datetime import date, timedelta

os.environ.setdefault("OTP_DEMO", "1")
os.environ.setdefault("PWNED_CHECK", "0")
os.environ["DATABASE_URL"] = "sqlite:///./data/test_rxtrans.db"

from fastapi.testclient import TestClient  # noqa: E402

import server  # noqa: E402
from api.db import Base, engine, session  # noqa: E402
from api.models import Household, Order, PartnerUser, Store, StoredFile, now  # noqa: E402
from api.security import hash_pw  # noqa: E402

H = {"x-tht": "1"}
PW = "Zq!8vB#2mLp@9xT"
Base.metadata.create_all(engine)


def world():
    tag = uuid.uuid4().hex[:8]
    fam = TestClient(server.app)
    fam.__enter__()
    key = uuid.uuid4().hex
    fam.headers["X-DoKKo-Key"] = key
    fam.post("/api/v1/hello", headers=H, json={"name": "Meera", "members": 2})
    with session() as db:
        import sqlalchemy as sa
        hid = db.scalar(sa.select(Household).where(Household.key == key)).id
        s = Store(kind="pharmacy", name=f"Apollo {tag}", city="Hyderabad", lat=17.44, lng=78.35, active=True)
        db.add(s)
        db.flush()
        db.add(PartnerUser(store_id=s.id, email=f"o{tag}@ph.test", name="Priya Nair", role="owner",
                           reg_no="AP/12345", pw_hash=hash_pw(PW), active=True, must_change=False))
        fid = f"rx_{tag}"
        db.add(StoredFile(household_id=hid, file_id=fid, name="rx.pdf", mime="application/pdf", blob=b"x", size=1))
        o = Order(household_id=hid, store_id=s.id, kind="medicine", status="checking", member="Meera",
                  items=[{"sku": "AMOX500", "name": "Amoxicillin 500mg", "price": 85, "qty": 2, "rx": True}],
                  total=170, payment="cod", rx_shared=True, rx_files=[fid], created=now())
        db.add(o)
        db.flush()
        return fam, o.id, f"o{tag}@ph.test"


def pharmacy(email):
    c = TestClient(server.app)
    c.__enter__()
    assert c.post("/api/partner/login", headers=H, json={"email": email, "password": PW}).status_code == 200
    return c


def test_the_family_sees_nothing_until_it_has_been_checked():
    fam, oid, email = world()
    row = next(o for o in fam.get("/api/v1/orders").json()["orders"] if o["id"] == oid)
    assert row["checkedBy"] is None


def test_the_family_sees_who_checked_it_and_their_registration():
    """A registration number is a public professional credential, and showing it is most of what separates a
    pharmacy from a website that posts medicines through a letterbox."""
    fam, oid, email = world()
    pharmacy(email).post(f"/api/partner/orders/{oid}/verify",
                         json={"doctor": "Dr A Sharma", "regNo": "TSMC/55512", "rxDate": "2026-10-19"})
    row = next(o for o in fam.get("/api/v1/orders").json()["orders"] if o["id"] == oid)
    assert row["checkedBy"]["name"] == "Priya Nair" and row["checkedBy"]["regNo"] == "AP/12345"
    assert row["checkedBy"]["at"] > 0


def test_the_family_is_not_shown_the_prescribers_details_back():
    """They wrote it; it is their own prescription. What is new to them is who at the pharmacy checked it."""
    fam, oid, email = world()
    pharmacy(email).post(f"/api/partner/orders/{oid}/verify",
                         json={"doctor": "Dr A Sharma", "regNo": "TSMC/55512"})
    row = next(o for o in fam.get("/api/v1/orders").json()["orders"] if o["id"] == oid)
    assert set(row["checkedBy"]) == {"name", "regNo", "at"}


def test_a_lab_booking_carries_no_pharmacist():
    fam, oid, email = world()
    with session() as db:
        db.get(Order, oid).kind = "lab"
    row = next(o for o in fam.get("/api/v1/orders").json()["orders"] if o["id"] == oid)
    assert row["checkedBy"] is None


# ---------------------------------------------------------------- how old the prescription was
def test_the_age_rules_are_served_from_one_place():
    """Otherwise the thirty days lives in the console's JavaScript and drifts from whatever the server says."""
    fam, oid, email = world()
    r = pharmacy(email).get("/api/partner/rx-rules").json()
    assert r["chronicDays"] == 30 and r["acuteDays"] == 7 and r["note"]


def test_the_age_is_recorded_with_the_sign_off():
    fam, oid, email = world()
    old = (date.today() - timedelta(days=45)).isoformat()
    r = pharmacy(email).post(f"/api/partner/orders/{oid}/verify",
                             json={"doctor": "Dr A Sharma", "regNo": "TSMC/55512", "rxDate": old})
    assert r.json()["verified"]["rxDate"] == old and r.json()["verified"]["rxAgeDays"] == 45


def test_an_old_prescription_is_flagged_and_never_refused():
    """The registered pharmacist is the professional. Software putting its judgement above theirs is the
    thing the Telemedicine Practice Guidelines forbid outright."""
    fam, oid, email = world()
    ancient = (date.today() - timedelta(days=400)).isoformat()
    r = pharmacy(email).post(f"/api/partner/orders/{oid}/verify",
                             json={"doctor": "Dr A Sharma", "regNo": "TSMC/55512", "rxDate": ancient})
    assert r.status_code == 200 and r.json()["verified"]["rxAgeDays"] == 400


def test_an_unrecorded_or_unreadable_date_gives_no_age_rather_than_a_wrong_one():
    fam, oid, email = world()
    r = pharmacy(email).post(f"/api/partner/orders/{oid}/verify",
                             json={"doctor": "Dr A Sharma", "regNo": "TSMC/55512", "rxDate": ""})
    assert r.json()["verified"]["rxAgeDays"] is None


def test_a_future_dated_prescription_reads_as_zero_days_not_a_negative_number():
    fam, oid, email = world()
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    r = pharmacy(email).post(f"/api/partner/orders/{oid}/verify",
                             json={"doctor": "Dr A Sharma", "regNo": "TSMC/55512", "rxDate": tomorrow})
    assert r.json()["verified"]["rxAgeDays"] == 0


def test_the_layer_is_in_the_page():
    from pathlib import Path
    page = Path("web/index.html").read_text(encoding="utf-8")
    assert "/*live-p38*/" in page and "lv38" in page
    assert "dk-r3" in Path("web/sw.js").read_text(encoding="utf-8")   # bumped by each later layer

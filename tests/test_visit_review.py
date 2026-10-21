"""The family rates the person who came to their door — separately from the lab that sent them.

Run: python -m pytest -q tests/test_visit_review.py
"""
import os
import uuid

os.environ.setdefault("OTP_DEMO", "1")
os.environ.setdefault("PWNED_CHECK", "0")
os.environ["DATABASE_URL"] = "sqlite:///./data/test_visitreview.db"

from fastapi.testclient import TestClient  # noqa: E402

import server  # noqa: E402
from api.db import Base, engine, session  # noqa: E402
from api.models import Household, Order, PartnerUser, Store, now  # noqa: E402
from api.security import hash_pw  # noqa: E402

H = {"x-tht": "1"}
PW = "Zq!8vB#2mLp@9xT"
Base.metadata.create_all(engine)


def world():
    """A lab, an owner, a technician, a family and a booking already assigned to that technician."""
    tag = uuid.uuid4().hex[:8]
    c = TestClient(server.app)
    c.__enter__()
    key = uuid.uuid4().hex
    c.headers["X-DoKKo-Key"] = key
    c.post("/api/v1/hello", headers=H, json={"name": "Meera", "members": 2})
    with session() as db:
        import sqlalchemy as sa
        hid = db.scalar(sa.select(Household).where(Household.key == key)).id
        s = Store(kind="lab", name=f"Lucid {tag}", city="Hyderabad", lat=17.44, lng=78.35, active=True)
        db.add(s)
        db.flush()
        owner = PartnerUser(store_id=s.id, email=f"o{tag}@lab.test", name="Owner", role="owner",
                            pw_hash=hash_pw(PW), active=True, must_change=False)
        tech = PartnerUser(store_id=s.id, email=f"t{tag}@lab.test", name="Ravi Kumar", phone=f"98765{tag[:5]}",
                           role="tech", pw_hash=hash_pw(PW), active=True, must_change=False)
        db.add_all([owner, tech])
        db.flush()
        o = Order(household_id=hid, store_id=s.id, kind="lab", status="collected",
                  items=[{"code": "LIPID", "name": "Lipid profile", "price": 650}], total=650,
                  member="Meera", slot="Today 7-9 AM", agent_id=tech.id, done_at=now(),
                  timeline=[{"s": "assigned", "t": now(), "note": "Ravi Kumar"}, {"s": "collected", "t": now()}],
                  addr={"line1": "12 Gachibowli Main Rd", "city": "Hyderabad", "phone": "9876500022"},
                  created=now())
        db.add(o)
        db.flush()
        return c, o.id, tech.id, owner.email, s.id


def lab(email: str):
    c = TestClient(server.app)
    c.__enter__()
    assert c.post("/api/partner/login", headers=H, json={"email": email, "password": PW}).status_code == 200
    return c


def test_the_family_is_asked_once_the_sample_is_in_the_bag():
    fam, oid, tid, owner, sid = world()
    row = next(o for o in fam.get("/api/v1/orders").json()["orders"] if o["id"] == oid)
    assert row["canRateVisit"] is True and row["visitRating"] is None


def test_rating_the_visit_moves_the_technicians_own_average_not_the_labs():
    fam, oid, tid, owner, sid = world()
    before = next(o for o in lab(owner).get("/api/partner/techs").json()["techs"] if o["id"] == tid)
    assert before["ratingN"] == 0

    r = fam.post(f"/api/v1/orders/{oid}/visit-rating", json={"rating": 5, "tags": ["Gentle", "On time"], "note": "Very quick"})
    assert r.status_code == 200, r.text
    assert r.json()["visitRating"] == 5 and r.json()["canRateVisit"] is False

    after = next(o for o in lab(owner).get("/api/partner/techs").json()["techs"] if o["id"] == tid)
    assert after["rating"] == 5 and after["ratingN"] == 1
    with session() as db:                       # the store's own rating is a different judgement
        assert db.get(Order, oid).rating is None


def test_the_average_is_a_running_mean_so_one_bad_morning_is_not_the_whole_record():
    fam1, oid1, tid, owner, sid = world()
    fam1.post(f"/api/v1/orders/{oid1}/visit-rating", json={"rating": 5})
    # a second booking for the same technician
    with session() as db:
        o = Order(household_id=db.get(Order, oid1).household_id, store_id=sid, kind="lab", status="collected",
                  items=[], total=0, member="Arjun", agent_id=tid, done_at=now(), created=now())
        db.add(o)
        db.flush()
        oid2 = o.id
    fam1.post(f"/api/v1/orders/{oid2}/visit-rating", json={"rating": 2})
    t = next(x for x in lab(owner).get("/api/partner/techs").json()["techs"] if x["id"] == tid)
    assert t["rating"] == 3.5 and t["ratingN"] == 2


def test_you_cannot_rate_a_visit_twice():
    fam, oid, tid, owner, sid = world()
    assert fam.post(f"/api/v1/orders/{oid}/visit-rating", json={"rating": 4}).status_code == 200
    r = fam.post(f"/api/v1/orders/{oid}/visit-rating", json={"rating": 1})
    assert r.status_code == 409
    t = next(x for x in lab(owner).get("/api/partner/techs").json()["techs"] if x["id"] == tid)
    assert t["ratingN"] == 1


def test_you_cannot_rate_a_visit_that_has_not_happened():
    fam, oid, tid, owner, sid = world()
    with session() as db:
        o = db.get(Order, oid)
        o.done_at, o.status = None, "en_route"
    r = fam.post(f"/api/v1/orders/{oid}/visit-rating", json={"rating": 5})
    assert r.status_code == 409 and "collected" in r.json()["detail"]


def test_a_booking_with_nobody_on_it_has_no_visit_to_rate():
    """A family who walked into the lab themselves is not asked about a technician."""
    fam, oid, tid, owner, sid = world()
    with session() as db:
        db.get(Order, oid).agent_id = None
    row = next(o for o in fam.get("/api/v1/orders").json()["orders"] if o["id"] == oid)
    assert row["canRateVisit"] is False
    assert fam.post(f"/api/v1/orders/{oid}/visit-rating", json={"rating": 5}).status_code == 400


def test_another_family_cannot_rate_this_visit():
    fam, oid, tid, owner, sid = world()
    other = TestClient(server.app)
    other.__enter__()
    other.headers["X-DoKKo-Key"] = uuid.uuid4().hex
    other.post("/api/v1/hello", headers=H, json={"name": "Someone", "members": 1})
    assert other.post(f"/api/v1/orders/{oid}/visit-rating", json={"rating": 1}).status_code == 404


def test_only_the_tags_we_offered_are_stored():
    """Otherwise the tag list is a free text field with a tidy name, and nothing can be counted."""
    fam, oid, tid, owner, sid = world()
    fam.post(f"/api/v1/orders/{oid}/visit-rating",
             json={"rating": 5, "tags": ["Gentle", "<script>x</script>", "Free money"]})
    with session() as db:
        assert db.get(Order, oid).visit_tags == ["Gentle"]


def test_the_rating_has_to_be_one_to_five():
    fam, oid, tid, owner, sid = world()
    assert fam.post(f"/api/v1/orders/{oid}/visit-rating", json={"rating": 0}).status_code == 422
    assert fam.post(f"/api/v1/orders/{oid}/visit-rating", json={"rating": 6}).status_code == 422


def test_the_tag_lists_are_offered_to_the_app():
    fam, oid, tid, owner, sid = world()
    t = fam.get("/api/v1/visit-tags").json()
    assert "On time" in t["good"] and "Late" in t["bad"]
    assert not set(t["good"]) & set(t["bad"])


def test_the_technician_sees_their_own_rating():
    fam, oid, tid, owner, sid = world()
    fam.post(f"/api/v1/orders/{oid}/visit-rating", json={"rating": 4})
    with session() as db:
        email = db.get(PartnerUser, tid).email
    me = lab(email).get("/api/partner/me").json()
    assert me["user"]["rating"] == 4 and me["user"]["ratingN"] == 1

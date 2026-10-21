"""The lab booking gains a person: assign, set off, arrive, collect — and the family can watch.
Run: python -m pytest -q tests/test_lab_technician.py"""
import os
import uuid

os.environ.setdefault("OTP_DEMO", "1")
os.environ.setdefault("PWNED_CHECK", "0")
os.environ["DATABASE_URL"] = "sqlite:///./data/test_labtech.db"

from fastapi.testclient import TestClient  # noqa: E402

import server  # noqa: E402
from api.db import Base, engine, session  # noqa: E402
from api.models import Order, PartnerUser, Store, now  # noqa: E402
from api.security import hash_pw  # noqa: E402

H = {"x-tht": "1"}

# setup_lab() writes before any TestClient has started the app, which is what normally creates the schema.
Base.metadata.create_all(engine)


def setup_lab():
    """A lab, an owner and one technician on its roster."""
    tag = uuid.uuid4().hex[:8]
    with session() as db:
        s = Store(kind="lab", name=f"Lucid {tag}", city="Hyderabad", lat=17.44, lng=78.35, active=True)
        db.add(s)
        db.flush()
        owner = PartnerUser(store_id=s.id, email=f"o{tag}@lab.test", name="Owner", role="owner",
                            pw_hash=hash_pw("Zq!8vB#2mLp@9xT"), active=True, must_change=False)
        tech = PartnerUser(store_id=s.id, email=f"t{tag}@lab.test", name="Ravi K", phone="9876500011",
                           role="tech", pw_hash=hash_pw("Zq!8vB#2mLp@9xT"), active=True, must_change=False)
        db.add_all([owner, tech])
        db.flush()
        return s.id, owner.email, tech.email, tech.id


def place_booking(store_id: str, key: str) -> str:
    with session() as db:
        o = Order(household_id=_household(key), store_id=store_id, kind="lab", status="placed",
                  items=[{"code": "LIPID", "name": "Lipid profile", "price": 650}], total=650,
                  member="Meera", slot="Tomorrow 7–9 AM",
                  addr={"line1": "12 Gachibowli Main Rd", "area": "Gachibowli", "city": "Hyderabad",
                        "pin": "500032", "phone": "9876500022", "lat": 17.441, "lng": 78.352},
                  created=now())
        db.add(o)
        db.flush()
        return o.id


def _household(key: str) -> str:
    from api.models import Household

    with session() as db:
        h = db.scalar(__import__("sqlalchemy").select(Household).where(Household.key == key))
        return h.id


def family():
    c = TestClient(server.app)
    c.__enter__()
    key = uuid.uuid4().hex
    c.headers["X-DoKKo-Key"] = key
    c.post("/api/v1/hello", headers=H, json={"name": "Meera", "members": 2})
    return c, key


def partner(email: str):
    c = TestClient(server.app)
    c.__enter__()
    r = c.post("/api/partner/login", headers=H, json={"email": email, "password": "Zq!8vB#2mLp@9xT"})
    assert r.status_code == 200, r.text
    return c


# ---------------------------------------------------------------- the roster and the assignment
def test_a_lab_assigns_a_named_technician():
    store_id, owner_email, tech_email, tech_id = setup_lab()
    fam, key = family()
    oid = place_booking(store_id, key)
    lab = partner(owner_email)

    roster = lab.get("/api/partner/techs").json()["techs"]
    assert any(t["id"] == tech_id and t["name"] == "Ravi K" for t in roster)

    # the booking has to be confirmed before anyone is sent to a door
    r = lab.post(f"/api/partner/orders/{oid}/assign", json={"agent": tech_id})
    assert r.status_code == 400 and "Confirm" in r.json()["detail"]

    lab.post(f"/api/partner/orders/{oid}/status", json={"status": "confirmed"})
    r = lab.post(f"/api/partner/orders/{oid}/assign", json={"agent": tech_id})
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "assigned"


def test_a_lab_cannot_assign_another_labs_technician():
    store_a, owner_a, _, _ = setup_lab()
    _, _, _, tech_b = setup_lab()
    fam, key = family()
    oid = place_booking(store_a, key)
    lab = partner(owner_a)
    lab.post(f"/api/partner/orders/{oid}/status", json={"status": "confirmed"})
    r = lab.post(f"/api/partner/orders/{oid}/assign", json={"agent": tech_b})
    assert r.status_code == 404


# ---------------------------------------------------------------- the technician's four taps
def test_the_job_walks_from_assigned_to_collected():
    store_id, owner_email, tech_email, tech_id = setup_lab()
    fam, key = family()
    oid = place_booking(store_id, key)
    lab = partner(owner_email)
    lab.post(f"/api/partner/orders/{oid}/status", json={"status": "confirmed"})
    lab.post(f"/api/partner/orders/{oid}/assign", json={"agent": tech_id})

    tech = partner(tech_email)
    jobs = tech.get("/api/partner/tech/jobs").json()["jobs"]
    assert len(jobs) == 1 and jobs[0]["id"] == oid
    assert jobs[0]["member"] == "Meera" and "Gachibowli" in jobs[0]["address"]

    assert tech.post(f"/api/partner/tech/jobs/{oid}/start", json={}).json()["status"] == "en_route"
    assert tech.post(f"/api/partner/tech/jobs/{oid}/arrived", json={}).json()["status"] == "arrived"
    assert tech.post(f"/api/partner/tech/jobs/{oid}/collected", json={}).json()["status"] == "collected"

    with session() as db:
        o = db.get(Order, oid)
        assert o.started_at and o.arrived_at and o.done_at
        assert [t["s"] for t in o.timeline][-3:] == ["en_route", "arrived", "collected"]


def test_tapping_twice_is_a_tap():
    """Signal drops. A technician who taps again because nothing happened must not see an error."""
    store_id, owner_email, tech_email, tech_id = setup_lab()
    fam, key = family()
    oid = place_booking(store_id, key)
    lab = partner(owner_email)
    lab.post(f"/api/partner/orders/{oid}/status", json={"status": "confirmed"})
    lab.post(f"/api/partner/orders/{oid}/assign", json={"agent": tech_id})
    tech = partner(tech_email)
    tech.post(f"/api/partner/tech/jobs/{oid}/start", json={})
    r = tech.post(f"/api/partner/tech/jobs/{oid}/start", json={})
    assert r.status_code == 200 and r.json()["status"] == "en_route"


def test_a_technician_sees_only_their_own_jobs():
    store_id, owner_email, tech_a_email, tech_a = setup_lab()
    with session() as db:
        s = db.get(Store, store_id)
        other = PartnerUser(store_id=s.id, email=f"t2{uuid.uuid4().hex[:6]}@lab.test", name="Other",
                            role="tech", pw_hash=hash_pw("Zq!8vB#2mLp@9xT"), active=True, must_change=False)
        db.add(other)
        db.flush()
        other_email = other.email
    fam, key = family()
    oid = place_booking(store_id, key)
    lab = partner(owner_email)
    lab.post(f"/api/partner/orders/{oid}/status", json={"status": "confirmed"})
    lab.post(f"/api/partner/orders/{oid}/assign", json={"agent": tech_a})

    nosy = partner(other_email)
    assert nosy.get("/api/partner/tech/jobs").json()["jobs"] == []
    assert nosy.post(f"/api/partner/tech/jobs/{oid}/start", json={}).status_code == 403


# ---------------------------------------------------------------- the trail
def test_position_is_only_accepted_while_travelling():
    store_id, owner_email, tech_email, tech_id = setup_lab()
    fam, key = family()
    oid = place_booking(store_id, key)
    lab = partner(owner_email)
    lab.post(f"/api/partner/orders/{oid}/status", json={"status": "confirmed"})
    lab.post(f"/api/partner/orders/{oid}/assign", json={"agent": tech_id})
    tech = partner(tech_email)

    # assigned but not started: nothing is recorded
    assert tech.post(f"/api/partner/tech/jobs/{oid}/ping", json={"lat": 17.44, "lng": 78.35}).json()["tracking"] is False

    tech.post(f"/api/partner/tech/jobs/{oid}/start", json={})
    assert tech.post(f"/api/partner/tech/jobs/{oid}/ping", json={"lat": 17.44, "lng": 78.35}).json()["tracking"] is True

    # once collected, the phone stops being able to broadcast the person
    tech.post(f"/api/partner/tech/jobs/{oid}/collected", json={})
    assert tech.post(f"/api/partner/tech/jobs/{oid}/ping", json={"lat": 17.44, "lng": 78.35}).json()["tracking"] is False


def test_the_family_sees_the_technician_only_while_they_travel():
    store_id, owner_email, tech_email, tech_id = setup_lab()
    fam, key = family()
    oid = place_booking(store_id, key)
    lab = partner(owner_email)
    lab.post(f"/api/partner/orders/{oid}/status", json={"status": "confirmed"})
    lab.post(f"/api/partner/orders/{oid}/assign", json={"agent": tech_id})

    t = fam.get(f"/api/v1/orders/{oid}/track").json()
    assert t["live"] is False and t["agent"]["name"] == "Ravi K"

    tech = partner(tech_email)
    tech.post(f"/api/partner/tech/jobs/{oid}/start", json={})
    tech.post(f"/api/partner/tech/jobs/{oid}/ping", json={"lat": 17.439, "lng": 78.351})
    t = fam.get(f"/api/v1/orders/{oid}/track").json()
    assert t["live"] is True and round(t["lat"], 3) == 17.439

    tech.post(f"/api/partner/tech/jobs/{oid}/collected", json={})
    assert fam.get(f"/api/v1/orders/{oid}/track").json()["live"] is False


def test_another_family_cannot_track_this_booking():
    store_id, owner_email, tech_email, tech_id = setup_lab()
    fam, key = family()
    oid = place_booking(store_id, key)
    other, _ = family()
    assert other.get(f"/api/v1/orders/{oid}/track").status_code == 404


# ---------------------------------------------------------------- the app itself
def test_the_technician_app_is_its_own_installable_app():
    c = TestClient(server.app)
    c.__enter__()
    page = c.get("/tech")
    assert page.status_code == 200 and "Collect" in page.text
    m = c.get("/tech/manifest.webmanifest")
    assert m.status_code == 200
    j = m.json()
    assert j["short_name"] == "Collect" and j["start_url"] == "/tech"
    assert j["theme_color"] == "#0B8A7C", "the partner colour is set in BRAND.md, not invented per app"
    assert "partner-icon" in j["icons"][0]["src"], "use the brand partner icon, not a one-off"

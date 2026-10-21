"""The lab runs its own collection team, and a booking cannot claim a technician it has not got.

Before this, no PartnerUser could be created with role "tech" anywhere in the system: admin refused the role
and the partner portal had no roster screen. The assign endpoint and the whole technician app were therefore
unreachable in production. These tests pin the way in.

Run: python -m pytest -q tests/test_lab_roster.py
"""
import os
import uuid

os.environ.setdefault("OTP_DEMO", "1")
os.environ.setdefault("PWNED_CHECK", "0")
os.environ["DATABASE_URL"] = "sqlite:///./data/test_labroster.db"

from fastapi.testclient import TestClient  # noqa: E402

import server  # noqa: E402
from api.db import Base, engine, session  # noqa: E402
from api.models import Household, Order, PartnerUser, Store, now  # noqa: E402
from api.security import hash_pw  # noqa: E402

H = {"x-tht": "1"}
PW = "Zq!8vB#2mLp@9xT"
Base.metadata.create_all(engine)

_n = iter(range(10, 99))


def a_lab(kind: str = "lab"):
    """A store with an owner and a member of staff who is not the owner."""
    tag = uuid.uuid4().hex[:8]
    with session() as db:
        s = Store(kind=kind, name=f"Lucid {tag}", city="Hyderabad", lat=17.44, lng=78.35, active=True)
        db.add(s)
        db.flush()
        owner = PartnerUser(store_id=s.id, email=f"o{tag}@lab.test", name="Owner", role="owner",
                            pw_hash=hash_pw(PW), active=True, must_change=False)
        staff = PartnerUser(store_id=s.id, email=f"s{tag}@lab.test", name="Desk", role="staff",
                            pw_hash=hash_pw(PW), active=True, must_change=False)
        db.add_all([owner, staff])
        db.flush()
        return s.id, owner.email, staff.email


def signed_in(email: str, password: str = PW):
    c = TestClient(server.app)
    c.__enter__()
    r = c.post("/api/partner/login", headers=H, json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return c


def family():
    c = TestClient(server.app)
    c.__enter__()
    key = uuid.uuid4().hex
    c.headers["X-DoKKo-Key"] = key
    c.post("/api/v1/hello", headers=H, json={"name": "Meera", "members": 2})
    with session() as db:
        import sqlalchemy as sa
        hid = db.scalar(sa.select(Household).where(Household.key == key)).id
    return c, hid


def booking(store_id: str, hid: str, status: str = "confirmed") -> str:
    with session() as db:
        o = Order(household_id=hid, store_id=store_id, kind="lab", status=status,
                  items=[{"code": "LIPID", "name": "Lipid profile", "price": 650}], total=650,
                  member="Meera", slot="Tomorrow 7-9 AM",
                  addr={"line1": "12 Gachibowli Main Rd", "city": "Hyderabad", "phone": "9876500022",
                        "lat": 17.441, "lng": 78.352},
                  created=now())
        db.add(o)
        db.flush()
        return o.id


def mobile() -> str:
    return f"98765{next(_n):02d}{uuid.uuid4().int % 1000:03d}"


# ---------------------------------------------------------------- the roster
def test_owner_adds_a_technician_and_gets_a_one_time_password():
    sid, owner, _ = a_lab()
    lab = signed_in(owner)
    ph = mobile()
    r = lab.post("/api/partner/techs", json={"name": "Ravi Kumar", "phone": ph})
    assert r.status_code == 200, r.text
    g = r.json()
    assert g["name"] == "Ravi Kumar" and g["phone"] == ph
    assert g["signIn"] == ph and len(g["tempPassword"]) >= 6
    # It is shown once and never kept in the clear.
    assert lab.get("/api/partner/techs").json()["techs"][0].get("tempPassword") is None


def test_the_technician_signs_in_with_the_mobile_number_the_lab_registered():
    """A phlebotomist between houses remembers their phone number, not an address the lab invented."""
    sid, owner, _ = a_lab()
    lab = signed_in(owner)
    ph = mobile()
    temp = lab.post("/api/partner/techs", json={"name": "Ravi Kumar", "phone": ph}).json()["tempPassword"]

    c = TestClient(server.app)
    c.__enter__()
    r = c.post("/api/partner/login", headers=H, json={"email": ph, "password": temp})
    assert r.status_code == 200, r.text
    assert r.json()["user"]["role"] == "tech" and r.json()["user"]["mustChange"] is True
    # +91 and spaces are how people write their own number.
    c2 = TestClient(server.app)
    c2.__enter__()
    assert c2.post("/api/partner/login", headers=H,
                   json={"email": f"+91 {ph[:5]} {ph[5:]}", "password": temp}).status_code == 200


def test_a_technician_without_an_email_is_never_shown_a_made_up_one():
    """The account is keyed by a reserved .invalid address because the column demands one. It is an internal
    key, not an address: nothing is sent to it and nobody is shown it."""
    sid, owner, _ = a_lab()
    lab = signed_in(owner)
    t = lab.post("/api/partner/techs", json={"name": "Ravi Kumar", "phone": mobile()}).json()
    assert t["email"] == ""
    assert "invalid" not in str(lab.get("/api/partner/techs").json())


def test_the_details_the_family_will_rely_on_are_required():
    sid, owner, _ = a_lab()
    lab = signed_in(owner)
    assert lab.post("/api/partner/techs", json={"name": "R", "phone": mobile()}).status_code == 400
    assert lab.post("/api/partner/techs", json={"name": "Ravi Kumar", "phone": "12345"}).status_code == 400
    # 1-5 are not Indian mobile prefixes; a family dialling it reaches nobody.
    assert lab.post("/api/partner/techs", json={"name": "Ravi Kumar", "phone": "1234567890"}).status_code == 400


def test_a_mobile_number_can_only_point_at_one_person():
    """It is a sign-in identifier, so a duplicate would make the login ambiguous."""
    sid, owner, _ = a_lab()
    lab = signed_in(owner)
    ph = mobile()
    assert lab.post("/api/partner/techs", json={"name": "Ravi Kumar", "phone": ph}).status_code == 200
    r = lab.post("/api/partner/techs", json={"name": "Suresh B", "phone": f"+91{ph}"})
    assert r.status_code == 400 and "already" in r.json()["detail"]


def test_only_the_owner_changes_the_team():
    sid, owner, staff = a_lab()
    desk = signed_in(staff)
    assert desk.post("/api/partner/techs", json={"name": "Ravi Kumar", "phone": mobile()}).status_code == 403
    # but the desk can still see who is on it, because the desk is who assigns jobs
    assert desk.get("/api/partner/techs").status_code == 200


def test_a_pharmacy_has_no_collection_team():
    sid, owner, _ = a_lab(kind="pharmacy")
    ph = signed_in(owner)
    assert ph.post("/api/partner/techs", json={"name": "Ravi Kumar", "phone": mobile()}).status_code == 400


def test_turning_someone_off_stops_the_sign_in_but_not_a_job_in_their_hands():
    sid, owner, _ = a_lab()
    lab = signed_in(owner)
    fam, hid = family()
    ph = mobile()
    t = lab.post("/api/partner/techs", json={"name": "Ravi Kumar", "phone": ph}).json()
    oid = booking(sid, hid)
    assert lab.post(f"/api/partner/orders/{oid}/assign", json={"agent": t["id"]}).status_code == 200

    # assigned but not yet travelling: they can be stood down
    assert lab.post(f"/api/partner/techs/{t['id']}/active", json={"active": False}).status_code == 200
    assert lab.post(f"/api/partner/techs/{t['id']}/active", json={"active": True}).status_code == 200

    with session() as db:                       # they set off
        db.get(Order, oid).status = "en_route"
    r = lab.post(f"/api/partner/techs/{t['id']}/active", json={"active": False})
    assert r.status_code == 400 and "Reassign" in r.json()["detail"]


def test_a_reset_password_lets_them_back_in_and_the_old_one_does_not():
    sid, owner, _ = a_lab()
    lab = signed_in(owner)
    ph = mobile()
    t = lab.post("/api/partner/techs", json={"name": "Ravi Kumar", "phone": ph}).json()
    fresh = lab.post(f"/api/partner/techs/{t['id']}/reset", json={}).json()
    assert fresh["signIn"] == ph and fresh["tempPassword"] != t["tempPassword"]

    c = TestClient(server.app)
    c.__enter__()
    assert c.post("/api/partner/login", headers=H, json={"email": ph, "password": t["tempPassword"]}).status_code == 401
    assert c.post("/api/partner/login", headers=H, json={"email": ph, "password": fresh["tempPassword"]}).status_code == 200


# ---------------------------------------------------------------- the booking cannot claim a person it has not got
def test_a_booking_cannot_be_marked_assigned_without_naming_anybody():
    """This is the fault the family's old status line came from: "Phlebotomist assigned" with no phlebotomist."""
    sid, owner, _ = a_lab()
    lab = signed_in(owner)
    fam, hid = family()
    oid = booking(sid, hid)
    r = lab.post(f"/api/partner/orders/{oid}/status", json={"status": "assigned"})
    assert r.status_code == 400 and "technician" in r.json()["detail"].lower()
    with session() as db:
        assert db.get(Order, oid).status == "confirmed"


def test_the_console_offers_no_blind_assign_button():
    sid, owner, _ = a_lab()
    lab = signed_in(owner)
    fam, hid = family()
    oid = booking(sid, hid)
    row = next(o for o in lab.get("/api/partner/orders").json()["orders"] if o["id"] == oid)
    assert "assigned" not in row["next"]         # no plain status button
    assert row["canAssign"] is True              # the picker, instead
    assert row["agent"] is None


def test_the_console_shows_who_is_going():
    sid, owner, _ = a_lab()
    lab = signed_in(owner)
    fam, hid = family()
    ph = mobile()
    t = lab.post("/api/partner/techs", json={"name": "Ravi Kumar", "phone": ph}).json()
    oid = booking(sid, hid)
    lab.post(f"/api/partner/orders/{oid}/assign", json={"agent": t["id"]})
    row = next(o for o in lab.get("/api/partner/orders").json()["orders"] if o["id"] == oid)
    assert row["agent"]["name"] == "Ravi Kumar" and row["agent"]["phone"] == ph
    assert row["canAssign"] is True              # reassignment is still possible


def test_reassigning_moves_the_job_and_the_roster_shows_the_load():
    sid, owner, _ = a_lab()
    lab = signed_in(owner)
    fam, hid = family()
    a = lab.post("/api/partner/techs", json={"name": "Ravi Kumar", "phone": mobile()}).json()
    b = lab.post("/api/partner/techs", json={"name": "Suresh B", "phone": mobile()}).json()
    oid = booking(sid, hid)
    lab.post(f"/api/partner/orders/{oid}/assign", json={"agent": a["id"]})
    lab.post(f"/api/partner/orders/{oid}/assign", json={"agent": b["id"]})
    by_id = {t["id"]: t for t in lab.get("/api/partner/techs").json()["techs"]}
    assert by_id[a["id"]]["openJobs"] == 0 and by_id[b["id"]]["openJobs"] == 1
    with session() as db:
        assert db.get(Order, oid).agent_id == b["id"]


def test_an_inactive_technician_cannot_be_sent_anywhere():
    sid, owner, _ = a_lab()
    lab = signed_in(owner)
    fam, hid = family()
    t = lab.post("/api/partner/techs", json={"name": "Ravi Kumar", "phone": mobile()}).json()
    lab.post(f"/api/partner/techs/{t['id']}/active", json={"active": False})
    oid = booking(sid, hid)
    r = lab.post(f"/api/partner/orders/{oid}/assign", json={"agent": t["id"]})
    assert r.status_code == 400 and "not active" in r.json()["detail"]


def test_one_lab_cannot_touch_another_labs_team():
    sid_a, owner_a, _ = a_lab()
    sid_b, owner_b, _ = a_lab()
    lab_a, lab_b = signed_in(owner_a), signed_in(owner_b)
    t = lab_a.post("/api/partner/techs", json={"name": "Ravi Kumar", "phone": mobile()}).json()
    assert t["id"] not in [x["id"] for x in lab_b.get("/api/partner/techs").json()["techs"]]
    assert lab_b.post(f"/api/partner/techs/{t['id']}/reset", json={}).status_code == 404
    assert lab_b.post(f"/api/partner/techs/{t['id']}/active", json={"active": False}).status_code == 404


def test_the_roster_says_who_is_out_right_now():
    sid, owner, _ = a_lab()
    lab = signed_in(owner)
    fam, hid = family()
    t = lab.post("/api/partner/techs", json={"name": "Ravi Kumar", "phone": mobile()}).json()
    oid = booking(sid, hid)
    lab.post(f"/api/partner/orders/{oid}/assign", json={"agent": t["id"]})
    assert lab.get("/api/partner/techs").json()["techs"][0]["live"] == ""
    with session() as db:
        db.get(Order, oid).status = "en_route"
    row = lab.get("/api/partner/techs").json()["techs"][0]
    assert row["live"] == "en_route" and row["liveOrder"] == oid


# ---------------------------------------------------------------- the slip of paper stops being a way in
def test_the_one_time_password_opens_nothing_until_it_is_replaced():
    """A new technician's password was written on a slip and handed over a counter. Behind the job list are
    families' addresses and phone numbers."""
    sid, owner, _ = a_lab()
    lab = signed_in(owner)
    fam, hid = family()
    ph = mobile()
    t = lab.post("/api/partner/techs", json={"name": "Ravi Kumar", "phone": ph}).json()
    oid = booking(sid, hid)
    lab.post(f"/api/partner/orders/{oid}/assign", json={"agent": t["id"]})

    tech = TestClient(server.app)
    tech.__enter__()
    tech.post("/api/partner/login", headers=H, json={"email": ph, "password": t["tempPassword"]})
    r = tech.get("/api/partner/tech/jobs")
    assert r.status_code == 403 and "password" in r.json()["detail"].lower()
    # and no job can be moved either
    assert tech.post(f"/api/partner/tech/jobs/{oid}/start", json={"note": ""}).status_code == 403

    r = tech.post("/api/partner/password", json={"current": t["tempPassword"], "new": "ThisIsMineNow#7"})
    assert r.status_code == 200, r.text
    jobs = tech.get("/api/partner/tech/jobs")
    assert jobs.status_code == 200 and jobs.json()["jobs"][0]["id"] == oid


def test_the_technician_app_is_told_a_password_is_still_needed():
    sid, owner, _ = a_lab()
    lab = signed_in(owner)
    ph = mobile()
    t = lab.post("/api/partner/techs", json={"name": "Ravi Kumar", "phone": ph}).json()
    tech = TestClient(server.app)
    tech.__enter__()
    me = tech.post("/api/partner/login", headers=H, json={"email": ph, "password": t["tempPassword"]}).json()
    assert me["user"]["mustChange"] is True and me["user"]["phone"] == ph
    assert me["user"]["email"] == ""          # the internal key is never shown as an address

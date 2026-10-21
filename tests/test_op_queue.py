"""The OP queue: walk-ins, a number, and an estimate that only speaks when it can.

Run: python -m pytest -q tests/test_op_queue.py
"""
import os
import uuid

os.environ.setdefault("OTP_DEMO", "1")
os.environ.setdefault("PWNED_CHECK", "0")
os.environ["DATABASE_URL"] = "sqlite:///./data/test_opqueue.db"

from fastapi.testclient import TestClient  # noqa: E402

import server  # noqa: E402
from api.db import Base, engine, session  # noqa: E402
from api.models import Household, PartnerUser, Store, Token, now  # noqa: E402
from api.queue import today  # noqa: E402
from api.security import hash_pw  # noqa: E402

H = {"x-tht": "1"}
PW = "Zq!8vB#2mLp@9xT"
Base.metadata.create_all(engine)


def a_clinic(kind="hospital", verified=True):
    tag = uuid.uuid4().hex[:8]
    with session() as db:
        s = Store(kind=kind, name=f"Sunrise {tag}", city="Hyderabad", lat=17.44, lng=78.35, active=True)
        db.add(s)
        db.flush()
        owner = PartnerUser(store_id=s.id, email=f"o{tag}@cl.test", name="Reception", role="owner",
                            pw_hash=hash_pw(PW), active=True, must_change=False)
        doc = PartnerUser(store_id=s.id, email=f"d{tag}@cl.test", name="Dr Rao", role="doctor",
                          reg_no="TSMC/55512", specialty="General medicine", verified=verified,
                          pw_hash=hash_pw(PW), active=True, must_change=False)
        db.add_all([owner, doc])
        db.flush()
        return s.id, owner.email, doc.id, doc.email


def family(name="Meera"):
    c = TestClient(server.app)
    c.__enter__()
    key = uuid.uuid4().hex
    c.headers["X-DoKKo-Key"] = key
    c.post("/api/v1/hello", headers=H, json={"name": name, "members": 2})
    return c


def counter(email):
    c = TestClient(server.app)
    c.__enter__()
    assert c.post("/api/partner/login", headers=H, json={"email": email, "password": PW}).status_code == 200
    return c


def seen(did, mins, n=4):
    """n consultations this doctor has already finished today, each `mins` long."""
    with session() as db:
        d = db.get(PartnerUser, did)
        last = db.query(Token).filter(Token.doctor_id == did).count()
        t0 = now() - 7200
        for i in range(n):
            db.add(Token(store_id=d.store_id, doctor_id=did, household_id="", member=f"Past {i}",
                         day=today(), number=900 + last + i, state="done", created=t0,
                         started_at=t0 + i * 600, done_at=t0 + i * 600 + mins * 60))


# ---------------------------------------------------------------- taking a number
def test_the_number_starts_at_one_and_counts_up_for_that_doctor_today():
    """Which is how every OP counter in the country already works, and so is the number people look for."""
    sid, owner, did, demail = a_clinic()
    a, b = family("Meera"), family("Arjun")
    t1 = a.post("/api/v1/queue", json={"store": sid, "doctor": did, "member": "Meera"}).json()
    t2 = b.post("/api/v1/queue", json={"store": sid, "doctor": did, "member": "Arjun"}).json()
    assert t1["number"] == 1 and t2["number"] == 2
    assert t1["state"] == "waiting" and t1["doctor"] == "Dr Rao"


def test_tapping_twice_in_a_waiting_room_does_not_put_you_behind_yourself():
    sid, owner, did, demail = a_clinic()
    f = family()
    one = f.post("/api/v1/queue", json={"store": sid, "doctor": did, "member": "Meera"}).json()
    two = f.post("/api/v1/queue", json={"store": sid, "doctor": did, "member": "Meera"}).json()
    assert one["id"] == two["id"] and two["number"] == 1


def test_an_unverified_doctor_takes_nobody():
    sid, owner, did, demail = a_clinic(verified=False)
    r = family().post("/api/v1/queue", json={"store": sid, "doctor": did, "member": "Meera"})
    assert r.status_code == 400 and "registration" in r.json()["detail"]


def test_a_pharmacy_does_not_run_an_outpatient_queue():
    sid, owner, did, demail = a_clinic(kind="pharmacy")
    assert family().post("/api/v1/queue", json={"store": sid, "doctor": did, "member": "M"}).status_code == 404


# ---------------------------------------------------------------- the estimate
def test_no_estimate_is_offered_until_the_day_can_support_one():
    """A wrong "10 minutes" is why people stop watching the board and crowd the door."""
    sid, owner, did, demail = a_clinic()
    a, b = family("Meera"), family("Arjun")
    a.post("/api/v1/queue", json={"store": sid, "doctor": did, "member": "Meera"})
    t = b.post("/api/v1/queue", json={"store": sid, "doctor": did, "member": "Arjun"}).json()
    assert t["ahead"] == 1 and t["waitMin"] is None and t["pacing"] is False


def test_once_the_doctor_has_a_pace_the_estimate_follows_it():
    sid, owner, did, demail = a_clinic()
    seen(did, mins=8)
    a, b = family("Meera"), family("Arjun")
    a.post("/api/v1/queue", json={"store": sid, "doctor": did, "member": "Meera"})
    t = b.post("/api/v1/queue", json={"store": sid, "doctor": did, "member": "Arjun"}).json()
    assert t["pacing"] is True and t["ahead"] == 1 and t["waitMin"] == 8


def test_the_person_in_the_room_still_counts_as_ahead_of_you():
    sid, owner, did, demail = a_clinic()
    a, b = family("Meera"), family("Arjun")
    t1 = a.post("/api/v1/queue", json={"store": sid, "doctor": did, "member": "Meera"}).json()
    t2 = b.post("/api/v1/queue", json={"store": sid, "doctor": did, "member": "Arjun"}).json()
    c = counter(owner)
    c.post(f"/api/partner/queue/{t1['id']}/move", json={"to": "called"})
    c.post(f"/api/partner/queue/{t1['id']}/move", json={"to": "in"})
    assert b.get(f"/api/v1/queue/{t2['id']}").json()["ahead"] == 1


def test_somebody_leaving_shortens_the_queue_behind_them():
    sid, owner, did, demail = a_clinic()
    a, b = family("Meera"), family("Arjun")
    t1 = a.post("/api/v1/queue", json={"store": sid, "doctor": did, "member": "Meera"}).json()
    t2 = b.post("/api/v1/queue", json={"store": sid, "doctor": did, "member": "Arjun"}).json()
    assert a.post(f"/api/v1/queue/{t1['id']}/leave").json()["state"] == "skipped"
    assert b.get(f"/api/v1/queue/{t2['id']}").json()["ahead"] == 0


def test_the_family_sees_the_wait_before_deciding_to_set_off():
    sid, owner, did, demail = a_clinic()
    seen(did, mins=6)
    family("Meera").post("/api/v1/queue", json={"store": sid, "doctor": did, "member": "Meera"})
    d = family().get(f"/api/v1/doctors?store={sid}").json()["doctors"][0]
    assert d["queue"]["waiting"] == 1 and d["queue"]["paceMin"] == 6 and d["queue"]["waitMin"] == 6


# ---------------------------------------------------------------- the counter
def test_calling_the_next_number_finishes_the_one_in_the_room():
    """Which is the whole job at an OP counter, and should not be two taps."""
    sid, owner, did, demail = a_clinic()
    a, b = family("Meera"), family("Arjun")
    t1 = a.post("/api/v1/queue", json={"store": sid, "doctor": did, "member": "Meera"}).json()
    t2 = b.post("/api/v1/queue", json={"store": sid, "doctor": did, "member": "Arjun"}).json()
    c = counter(owner)
    first = c.post(f"/api/partner/queue/next?doctor={did}").json()
    assert first["called"]["number"] == 1 and first["finished"] is None and first["waiting"] == 1
    second = c.post(f"/api/partner/queue/next?doctor={did}").json()
    assert second["called"]["number"] == 2 and second["finished"] == t1["id"] and second["waiting"] == 0
    with session() as db:
        assert db.get(Token, t1["id"]).state == "done"


def test_calling_next_on_an_empty_queue_says_so_rather_than_erroring():
    sid, owner, did, demail = a_clinic()
    r = counter(owner).post(f"/api/partner/queue/next?doctor={did}").json()
    assert r["called"] is None and r["waiting"] == 0


def test_the_family_is_told_when_their_number_is_called():
    sid, owner, did, demail = a_clinic()
    f = family()
    t = f.post("/api/v1/queue", json={"store": sid, "doctor": did, "member": "Meera"}).json()
    counter(owner).post(f"/api/partner/queue/next?doctor={did}")
    titles = [n["title"] for n in f.get("/api/v1/inbox").json()["notices"]]
    assert any(f"token {t['number']} called" in x for x in titles)


def test_a_number_only_moves_forwards():
    sid, owner, did, demail = a_clinic()
    f = family()
    t = f.post("/api/v1/queue", json={"store": sid, "doctor": did, "member": "Meera"}).json()
    c = counter(owner)
    assert c.post(f"/api/partner/queue/{t['id']}/move", json={"to": "done"}).status_code == 400
    assert c.post(f"/api/partner/queue/{t['id']}/move", json={"to": "called"}).status_code == 200
    assert c.post(f"/api/partner/queue/{t['id']}/move", json={"to": "waiting"}).status_code == 400


def test_somebody_not_at_the_door_is_passed_over_and_told_how_to_get_back_in():
    sid, owner, did, demail = a_clinic()
    f = family()
    t = f.post("/api/v1/queue", json={"store": sid, "doctor": did, "member": "Meera"}).json()
    c = counter(owner)
    c.post(f"/api/partner/queue/{t['id']}/move", json={"to": "called"})
    assert c.post(f"/api/partner/queue/{t['id']}/move", json={"to": "skipped"}).json()["state"] == "skipped"
    bodies = [n["body"] for n in f.get("/api/v1/inbox").json()["notices"]]
    assert any("Ask at the counter" in b for b in bodies)


def test_the_counter_adds_the_person_who_simply_walked_in():
    """Most of a morning's queue, in most clinics. No household, so nothing is sent to a phone."""
    sid, owner, did, demail = a_clinic()
    c = counter(owner)
    t = c.post("/api/partner/queue/add", json={"store": sid, "doctor": did, "member": "Walk-in Sita",
                                               "phone": "9876500022"}).json()
    assert t["number"] == 1 and t["member"] == "Walk-in Sita" and t["phone"] == "9876500022"
    assert c.post("/api/partner/queue/add", json={"store": sid, "doctor": did, "member": ""}).status_code == 400


def test_the_counter_list_shows_the_phone_and_the_family_view_does_not():
    sid, owner, did, demail = a_clinic()
    f = family()
    t = f.post("/api/v1/queue", json={"store": sid, "doctor": did, "member": "Meera",
                                      "phone": "9876500022"}).json()
    assert "phone" not in t
    row = counter(owner).get(f"/api/partner/queue?doctor={did}").json()["tokens"][0]
    assert row["phone"] == "9876500022" and row["waitedMin"] >= 0


def test_a_doctor_signing_in_sees_their_own_queue_without_picking():
    sid, owner, did, demail = a_clinic()
    family().post("/api/v1/queue", json={"store": sid, "doctor": did, "member": "Meera"})
    q = counter(demail).get("/api/partner/queue").json()
    assert q["doctor"]["id"] == did and q["waiting"] == 1


def test_a_doctor_cannot_reach_into_another_doctors_queue():
    sid, owner, did, demail = a_clinic()
    with session() as db:
        other = PartnerUser(store_id=sid, email=f"x{uuid.uuid4().hex[:6]}@cl.test", name="Dr Iyer",
                            role="doctor", reg_no="TSMC/9", verified=True, pw_hash=hash_pw(PW),
                            active=True, must_change=False)
        db.add(other)
        db.flush()
        oid = other.id
        oemail = other.email
    t = family().post("/api/v1/queue", json={"store": sid, "doctor": did, "member": "Meera"}).json()
    assert counter(oemail).post(f"/api/partner/queue/{t['id']}/move", json={"to": "called"}).status_code == 403


def test_one_clinic_cannot_see_anothers_queue():
    sid_a, owner_a, did_a, _ = a_clinic()
    sid_b, owner_b, did_b, _ = a_clinic()
    family().post("/api/v1/queue", json={"store": sid_a, "doctor": did_a, "member": "Meera"})
    assert counter(owner_b).get(f"/api/partner/queue?doctor={did_a}").status_code == 404


def test_the_doctor_list_shows_who_is_waiting_for_whom():
    sid, owner, did, demail = a_clinic()
    family().post("/api/v1/queue", json={"store": sid, "doctor": did, "member": "Meera"})
    d = counter(owner).get("/api/partner/doctors").json()["doctors"][0]
    assert d["waiting"] == 1 and d["withNow"] is None and d["specialty"] == "General medicine"
    counter(owner).post(f"/api/partner/queue/next?doctor={did}")
    d = counter(owner).get("/api/partner/doctors").json()["doctors"][0]
    assert d["waiting"] == 0 and d["withNow"] == 1

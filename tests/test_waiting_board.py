"""The screen on the waiting-room wall: signed in once by a token, showing numbers and never names.

Run: python -m pytest -q tests/test_waiting_board.py
"""
import os
import uuid

os.environ.setdefault("OTP_DEMO", "1")
os.environ.setdefault("PWNED_CHECK", "0")
os.environ["DATABASE_URL"] = "sqlite:///./data/test_board.db"

from fastapi.testclient import TestClient  # noqa: E402

import server  # noqa: E402
from api.db import Base, engine, session  # noqa: E402
from api.models import PartnerUser, Store, Token, now  # noqa: E402
from api.queue import today  # noqa: E402
from api.security import hash_pw  # noqa: E402

H = {"x-tht": "1"}
PW = "Zq!8vB#2mLp@9xT"
Base.metadata.create_all(engine)


def a_clinic():
    tag = uuid.uuid4().hex[:8]
    with session() as db:
        s = Store(kind="hospital", name=f"Sunrise {tag}", city="Hyderabad", lat=17.44, lng=78.39, active=True)
        db.add(s)
        db.flush()
        owner = PartnerUser(store_id=s.id, email=f"o{tag}@cl.test", name="Reception", role="owner",
                            pw_hash=hash_pw(PW), active=True, must_change=False)
        desk = PartnerUser(store_id=s.id, email=f"s{tag}@cl.test", name="Desk", role="staff",
                           pw_hash=hash_pw(PW), active=True, must_change=False)
        doc = PartnerUser(store_id=s.id, email=f"d{tag}@cl.test", name="Dr Rao", role="doctor",
                          reg_no="TSMC/5", specialty="General medicine", verified=True,
                          pw_hash=hash_pw(PW), active=True, must_change=False)
        db.add_all([owner, desk, doc])
        db.flush()
        return s.id, owner.email, desk.email, doc.id


def tok(sid, did, number, state, member="Meera Raghavan"):
    with session() as db:
        db.add(Token(store_id=sid, doctor_id=did, household_id="", member=member, phone="9876500022",
                     day=today(), number=number, state=state, created=now()))


def signed_in(email):
    c = TestClient(server.app)
    c.__enter__()
    assert c.post("/api/partner/login", headers=H, json={"email": email, "password": PW}).status_code == 200
    return c


def anyone():
    c = TestClient(server.app)
    c.__enter__()
    return c


def test_the_owner_sets_the_screen_up_once():
    sid, owner, desk, did = a_clinic()
    c = signed_in(owner)
    assert c.get("/api/partner/board-token").json()["token"] == ""
    r = c.post("/api/partner/board-token").json()
    assert len(r["token"]) >= 16 and r["url"] == f"/counter?t={r['token']}"
    assert c.get("/api/partner/board-token").json()["token"] == r["token"]


def test_only_the_owner_sets_it_up():
    sid, owner, desk, did = a_clinic()
    assert signed_in(desk).post("/api/partner/board-token").status_code == 403


def test_the_screen_needs_no_sign_in():
    """A television that wants an email and a password every morning is one that gets switched off."""
    sid, owner, desk, did = a_clinic()
    t = signed_in(owner).post("/api/partner/board-token").json()["token"]
    tok(sid, did, 5, "in")
    tok(sid, did, 6, "waiting")
    b = anyone().get(f"/api/v1/board/{t}").json()
    assert b["rooms"][0]["doctor"] == "Dr Rao" and b["rooms"][0]["now"] == 5 and b["rooms"][0]["next"] == [6]


def test_it_shows_numbers_and_doctors_and_never_a_patients_name():
    """A waiting room is a public place, and the link is shareable by its nature."""
    sid, owner, desk, did = a_clinic()
    t = signed_in(owner).post("/api/partner/board-token").json()["token"]
    tok(sid, did, 1, "in", member="Meera Raghavan")
    body = anyone().get(f"/api/v1/board/{t}").text
    assert "Meera" not in body and "9876500022" not in body


def test_being_called_is_marked_so_the_screen_can_say_please_come_in():
    sid, owner, desk, did = a_clinic()
    t = signed_in(owner).post("/api/partner/board-token").json()["token"]
    tok(sid, did, 3, "called")
    r = anyone().get(f"/api/v1/board/{t}").json()["rooms"][0]
    assert r["now"] == 3 and r["calling"] is True


def test_only_the_next_few_numbers_are_shown_with_a_count_of_the_rest():
    sid, owner, desk, did = a_clinic()
    t = signed_in(owner).post("/api/partner/board-token").json()["token"]
    for n in range(1, 9):
        tok(sid, did, n, "waiting")
    r = anyone().get(f"/api/v1/board/{t}").json()["rooms"][0]
    assert r["next"] == [1, 2, 3, 4] and r["waiting"] == 8


def test_a_doctor_with_nobody_waiting_is_not_on_the_wall():
    sid, owner, desk, did = a_clinic()
    t = signed_in(owner).post("/api/partner/board-token").json()["token"]
    assert anyone().get(f"/api/v1/board/{t}").json()["rooms"] == []


def test_finished_numbers_leave_the_screen():
    sid, owner, desk, did = a_clinic()
    t = signed_in(owner).post("/api/partner/board-token").json()["token"]
    tok(sid, did, 1, "done")
    tok(sid, did, 2, "skipped")
    assert anyone().get(f"/api/v1/board/{t}").json()["rooms"] == []


def test_replacing_the_link_blanks_the_old_screen():
    """Which is how a clinic takes back a link that walked out of the building."""
    sid, owner, desk, did = a_clinic()
    c = signed_in(owner)
    first = c.post("/api/partner/board-token").json()["token"]
    tok(sid, did, 1, "in")
    assert anyone().get(f"/api/v1/board/{first}").status_code == 200
    second = c.post("/api/partner/board-token").json()["token"]
    assert second != first
    assert anyone().get(f"/api/v1/board/{first}").status_code == 404
    assert anyone().get(f"/api/v1/board/{second}").status_code == 200


def test_a_guessed_or_short_token_opens_nothing():
    assert anyone().get("/api/v1/board/abc").status_code == 404
    assert anyone().get("/api/v1/board/" + "x" * 24).status_code == 404


def test_a_closed_clinic_screen_goes_dark():
    sid, owner, desk, did = a_clinic()
    t = signed_in(owner).post("/api/partner/board-token").json()["token"]
    tok(sid, did, 1, "in")
    with session() as db:
        db.get(Store, sid).active = False
    assert anyone().get(f"/api/v1/board/{t}").status_code == 404


def test_one_clinic_screen_never_shows_another_clinics_queue():
    sid_a, owner_a, _, did_a = a_clinic()
    sid_b, owner_b, _, did_b = a_clinic()
    ta = signed_in(owner_a).post("/api/partner/board-token").json()["token"]
    signed_in(owner_b).post("/api/partner/board-token")
    tok(sid_b, did_b, 9, "in")
    assert anyone().get(f"/api/v1/board/{ta}").json()["rooms"] == []


def test_the_page_is_served():
    r = anyone().get("/counter")
    assert r.status_code == 200 and "Now serving" in r.text

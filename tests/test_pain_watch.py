"""Pain map and the doctor's "watch" notes (Nov 2026).
Run: python -m pytest -q tests/test_pain_watch.py"""
import os

os.environ.setdefault("OTP_DEMO", "1")
os.environ.setdefault("PWNED_CHECK", "0")
os.environ["DATABASE_URL"] = "sqlite:///./data/test_pain.db"

import pytest  # noqa: E402
from fastapi import HTTPException  # noqa: E402

from api.db import Base, engine, session  # noqa: E402
from api.family import decrypt, encrypt  # noqa: E402
from api.models import HealthRecord, Person, Token  # noqa: E402
from api.people import _check_record  # noqa: E402

Base.metadata.create_all(engine)
from tests.test_visit_consult import partner, visit_in_room  # noqa: E402

GOOD = {"name": "Upper belly · right", "side": "front", "pos": [-0.12, 1.04, 0.45], "sev": 6, "since": "week",
        "feel": ["dull"], "worse": ["food"], "log": [{"d": "2026-11-24", "sev": 6}], "active": True}


def test_a_pain_spot_is_plain_choices_and_a_place():
    _check_record("pain", dict(GOOD), "")
    for bad in ({"sev": 11}, {"sev": 0}, {"side": "top"}, {"since": "forever"}, {"feel": ["stabbing"]}, {"name": ""},
                {"pos": [1, 2]}, {"log": [{"d": "yesterday", "sev": 3}]}, {"active": "yes"}):
        with pytest.raises(HTTPException):
            _check_record("pain", {**GOOD, **bad}, "")


def test_the_family_cannot_write_a_doctors_watch_note():
    with pytest.raises(HTTPException) as e:
        _check_record("watch", {"items": [{"label": "x"}]}, "")
    assert e.value.status_code == 403


def test_the_doctor_marks_what_to_watch_and_it_lands_on_that_person():
    sid, did, demail, desk, other, fam, tid = visit_in_room()
    doc = partner(demail)
    body = {"items": [{"label": "LDL · recheck in 3 months", "org": "heart", "code": "ldl"}, {"label": "Pain · tell me if worse", "pos": [-0.12, 1.04, 0.45]}]}
    assert doc.post(f"/api/partner/queue/{tid}/watch", json=body).status_code == 409          # not called in yet
    for to in ("called", "in"):
        assert doc.post(f"/api/partner/queue/{tid}/move", json={"to": to}).status_code == 200
    assert doc.post(f"/api/partner/queue/{tid}/watch", json=body).status_code == 409          # no family member linked
    with session() as db:
        t = db.get(Token, tid)
        p = Person(household_id=t.household_id, name="Meera K", blob=encrypt({}))
        db.add(p)
        db.flush()
        t.member_id, pid = p.id, p.id
    assert partner(desk).post(f"/api/partner/queue/{tid}/watch", json=body).status_code == 403
    assert partner(other).post(f"/api/partner/queue/{tid}/watch", json=body).status_code == 403
    assert doc.post(f"/api/partner/queue/{tid}/watch", json={"items": [{"label": "  "}]}).status_code == 400
    r = doc.post(f"/api/partner/queue/{tid}/watch", json=body)
    assert r.status_code == 200 and len(r.json()["items"]) == 2
    assert doc.post(f"/api/partner/queue/{tid}/watch", json=body).status_code == 200        # sending again replaces
    with session() as db:
        rows = [x for x in db.query(HealthRecord).filter(HealthRecord.person_id == pid, HealthRecord.kind == "watch")]
        assert len(rows) == 1 and b"LDL" not in rows[0].blob
        d = decrypt(rows[0].blob)
        assert d["doctor"] == "Dr Anitha" and d["items"][0]["org"] == "heart" and d["items"][1]["pos"] == [-0.12, 1.04, 0.45]

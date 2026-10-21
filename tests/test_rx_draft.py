"""Filling the prescription form from what the doctor said — and refusing to fill in what they did not.

The Telemedicine Practice Guidelines (§5.4) are explicit that software must not prescribe. So the rule is
extraction, not completion: an empty field the doctor has to fill in is correct; a plausible "5 days"
nobody said is a fabricated prescription with a real registration number at the bottom of it.

Run: python -m pytest -q tests/test_rx_draft.py
"""
import os
import uuid

os.environ.setdefault("OTP_DEMO", "1")
os.environ.setdefault("PWNED_CHECK", "0")
os.environ["DATABASE_URL"] = "sqlite:///./data/test_rxdraft.db"

from fastapi.testclient import TestClient  # noqa: E402

import server  # noqa: E402
from api.consult import _parse_draft  # noqa: E402
from api.db import Base, engine, session  # noqa: E402
from api.models import Appointment, Household, PartnerUser, Store, now  # noqa: E402
from api.security import hash_pw  # noqa: E402

H = {"x-tht": "1"}
PW = "Zq!8vB#2mLp@9xT"
Base.metadata.create_all(engine)


def world(transcript=True, verified=True):
    tag = uuid.uuid4().hex[:8]
    with session() as db:
        s = Store(kind="hospital", name=f"Sunrise {tag}", city="Hyderabad", lat=17.44, lng=78.39, active=True)
        h = Household(key=uuid.uuid4().hex, name="Meera's family", city="Hyderabad")
        db.add_all([s, h])
        db.flush()
        doc = PartnerUser(store_id=s.id, email=f"d{tag}@cl.test", name="Rao", role="doctor",
                          reg_no="TSMC/55512", specialty="General medicine", verified=verified,
                          pw_hash=hash_pw(PW), active=True, must_change=False)
        db.add(doc)
        db.flush()
        a = Appointment(household_id=h.id, member_id="m1", member_name="Meera", store_id=s.id, kind="video",
                        date="2026-10-21", status="confirmed", doctor="Rao", call_started=now() - 900,
                        transcript=[{"who": "doctor", "t": now() - 800, "text": "Start azithromycin five hundred, once a day for three days"},
                                    {"who": "family", "t": now() - 700, "text": "After food doctor?"},
                                    {"who": "doctor", "t": now() - 600, "text": "Yes after food. And paracetamol if the fever comes back"}]
                        if transcript else [],
                        created=now())
        db.add(a)
        db.flush()
        return a.id, doc.email, h.id


def doctor(email):
    c = TestClient(server.app)
    c.__enter__()
    assert c.post("/api/partner/login", headers=H, json={"email": email, "password": PW}).status_code == 200
    return c


# ---------------------------------------------------------------- what the parser will and will not keep
def test_only_the_fields_the_form_can_hold_survive():
    d = _parse_draft('{"items":[{"name":"Azithromycin","strength":"500 mg","form":"tablet",'
                     '"frequency":"od","duration":"3 days","instructions":"after food","heard":"once a day"}],'
                     '"advice":"rest","followUp":"1 week","diagnosis":"throat infection","unclear":[]}')
    assert d["items"][0]["name"] == "Azithromycin" and d["items"][0]["frequency"] == "od"
    assert d["items"][0]["heard"] == "once a day" and d["items"][0]["rx"] is True
    assert d["diagnosis"] == "throat infection" and d["followUp"] == "1 week"


def test_a_frequency_the_form_does_not_know_becomes_empty_rather_than_a_guess():
    """"As the doctor advised" would otherwise land on a signed prescription as a blank nobody noticed."""
    d = _parse_draft('{"items":[{"name":"Azithromycin","frequency":"as the doctor advised"}]}')
    assert d["items"][0]["frequency"] == ""


def test_an_unknown_dosage_form_is_dropped_too():
    d = _parse_draft('{"items":[{"name":"Azithromycin","form":"sachet-ish"}]}')
    assert d["items"][0]["form"] == ""


def test_a_medicine_with_no_name_is_not_a_medicine():
    d = _parse_draft('{"items":[{"name":"","strength":"500 mg"},{"name":"Paracetamol"}]}')
    assert [i["name"] for i in d["items"]] == ["Paracetamol"]


def test_unreadable_output_gives_an_empty_draft_and_says_so():
    d = _parse_draft("I could not parse that")
    assert d["items"] == [] and "fill the form in yourself" in d["warning"]


def test_a_flag_about_a_medicine_that_is_not_on_the_form_is_dropped():
    """A warning the doctor cannot act on is noise."""
    d = _parse_draft('{"items":[{"name":"Azithromycin"}],"unclear":["Azithromycin","Amoxicillin"]}')
    assert d["unclear"] == ["azithromycin"] or d["unclear"] == ["Azithromycin"]
    assert len(d["unclear"]) == 1


def test_the_draft_is_capped_so_one_bad_response_cannot_flood_the_form():
    many = ",".join('{"name":"Med%d"}' % i for i in range(40))
    assert len(_parse_draft('{"items":[%s]}' % many)["items"]) == 20


# ---------------------------------------------------------------- the endpoint
def test_there_is_nothing_to_draft_from_without_captions():
    aid, email, hid = world(transcript=False)
    r = doctor(email).post(f"/api/partner/consults/{aid}/rx-draft")
    assert r.status_code == 400 and "captions" in r.json()["detail"]


def test_drafting_saves_nothing_by_itself():
    aid, email, hid = world()
    doctor(email).post(f"/api/partner/consults/{aid}/rx-draft")
    with session() as db:
        assert db.get(Appointment, aid).rx is None


def test_only_a_verified_doctor_can_draft():
    aid, email, hid = world(verified=False)
    assert doctor(email).post(f"/api/partner/consults/{aid}/rx-draft").status_code == 403


# ---------------------------------------------------------------- the back door this closed
def test_a_prescription_cannot_be_signed_without_saying_how_often():
    """RxItem.frequency defaulted to "od", so a client that left it out produced a signed prescription
    saying "once a day" that nobody had said."""
    aid, email, hid = world()
    c = doctor(email)
    r = c.put(f"/api/partner/consults/{aid}/rx", json={"items": [{"name": "Azithromycin", "strength": "500 mg"}]})
    assert r.status_code == 400 and "How often" in r.json()["detail"]
    with session() as db:
        assert db.get(Appointment, aid).rx is None


def test_a_nonsense_frequency_is_refused_rather_than_printed():
    aid, email, hid = world()
    r = doctor(email).put(f"/api/partner/consults/{aid}/rx",
                          json={"items": [{"name": "Azithromycin", "frequency": "whenever"}]})
    assert r.status_code == 400


def test_a_complete_prescription_still_signs():
    aid, email, hid = world()
    r = doctor(email).put(f"/api/partner/consults/{aid}/rx",
                          json={"items": [{"name": "Azithromycin", "strength": "500 mg", "form": "tablet",
                                           "frequency": "od", "duration": "3 days"}],
                                "advice": "Rest and fluids", "diagnosis": "Throat infection"})
    assert r.status_code == 200, r.text
    with session() as db:
        rx = db.get(Appointment, aid).rx
        assert rx["items"][0]["frequency"] == "od" and rx["regNo"] == "TSMC/55512"

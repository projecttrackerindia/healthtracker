"""A prescription read in the family's own language, dictation in Tamil or Hindi, and tests the doctor asks for.
Run: python -m pytest -q tests/test_rx_languages.py"""
import os

os.environ.setdefault("OTP_DEMO", "1")
os.environ.setdefault("PWNED_CHECK", "0")
os.environ["DATABASE_URL"] = "sqlite:///./data/test_visit.db"

import pytest  # noqa: E402

from api import ai as AI  # noqa: E402
from api import rxlang  # noqa: E402
from api.consult import match_tests  # noqa: E402
from tests.test_visit_consult import partner, visit_in_room  # noqa: E402

RX = {"items": [{"name": "Metformin", "strength": "1000 mg", "frequency": "bd", "instructions": "after food", "duration": "3 months"}],
      "tests": [{"code": "hba1c", "name": "HbA1c", "when": "3 months"}], "advice": "Walk 30 min daily", "diagnosis": "Sugar is high", "followUp": "3 months"}


def test_how_often_comes_from_the_hand_written_table_never_a_model(monkeypatch):
    monkeypatch.setattr(AI, "available", lambda: False)
    r = rxlang.read_in(RX, "ta")
    assert r["items"][0]["how"] == "நாளுக்கு இரண்டு முறை" and r["items"][0]["name"] == "Metformin" and r["items"][0]["strength"] == "1000 mg"
    assert r["wordsLeftInEnglish"] is True and r["advice"] == "Walk 30 min daily"     # honest: the doctor's words stay English
    for lang in rxlang.LANGS:
        assert set(rxlang.FREQ_T[lang]) == set(rxlang.FREQ_T["en"]) and len(rxlang.LABELS[lang]) == 5
    with pytest.raises(Exception):
        rxlang.read_in(RX, "xx")


def test_translated_words_keep_the_shape_and_numbers(monkeypatch):
    monkeypatch.setattr(AI, "available", lambda: True)
    monkeypatch.setattr(rxlang, "_ask", lambda system, payload, mt=1200: {"diagnosis": "சர்க்கரை அதிகம்", "advice": "தினமும் 30 நிமிடம் நடக்கவும்", "followUp": "3 மாதம்",
                                                                             "items": [{"instructions": "உணவுக்குப் பின்", "duration": "3 மாதம்"}], "tests": ["3 மாதத்தில்"]})
    r = rxlang.read_in(RX, "ta")
    assert r["machine"] is True and r["items"][0]["instructions"] == "உணவுக்குப் பின்" and r["tests"][0] == {"name": "HbA1c", "when": "3 மாதத்தில்"}
    got, changed = rxlang.cached({**RX, "tr": {"ta": r}}, "ta")
    assert changed is False and got is r


def test_dictation_in_tamil_is_read_in_english_or_the_doctor_is_told_plainly(monkeypatch):
    sid, did, demail, desk, other, fam, tid = visit_in_room()
    doc = partner(demail)
    monkeypatch.setattr(AI, "available", lambda: False)
    r = doc.post(f"/api/partner/queue/{tid}/rx-draft", json={"text": "மெட்ஃபார்மின் 500 இரண்டு வேளை"})
    assert r.status_code == 503 and "type it in English" in r.json()["detail"]
    monkeypatch.setattr(AI, "available", lambda: True)
    monkeypatch.setattr(rxlang, "_ask", lambda system, payload, mt=900: {"english": "Metformin 500 twice a day. Repeat HbA1c in 3 months."})
    d = doc.post(f"/api/partner/queue/{tid}/rx-draft", json={"text": "மெட்ஃபார்மின் 500 இரண்டு வேளை, HbA1c மூன்று மாதத்தில்"}).json()
    assert d["english"].startswith("Metformin") and d["items"][0]["name"].lower().startswith("metformin") and d["items"][0]["frequency"] == "bd"
    assert d["tests"][0]["code"] == "hba1c"


def test_the_family_reads_a_signed_visit_prescription_in_their_language(monkeypatch):
    sid, did, demail, desk, other, fam, tid = visit_in_room()
    doc = partner(demail)
    doc.post(f"/api/partner/queue/{tid}/move", json={"to": "called"})
    r = doc.put(f"/api/partner/queue/{tid}/rx", json={"items": [{"name": "Metformin", "strength": "1000 mg", "frequency": "bd"}], "tests": [{"code": "hba1c", "name": "HbA1c", "when": "3 months"}]})
    if r.status_code == 502:
        pytest.skip("PDF library not installed here")
    monkeypatch.setattr(AI, "available", lambda: False)
    g = fam.get(f"/api/v1/rx/visit/{tid}?lang=hi").json()
    assert g["rx"]["tests"][0]["code"] == "hba1c" and g["reading"]["items"][0]["how"] == "दिन में दो बार" and "tr" not in g["rx"]
    assert fam.get("/api/v1/rx/visit/nope").status_code == 404


def test_spoken_test_names_are_matched_to_the_catalogue():
    t = match_tests([{"name": "HbA1c", "when": "3 months"}, {"name": "thyroid profile"}, {"name": "Some rare test"}])
    assert t[0]["code"] == "hba1c" and t[0]["when"] == "3 months" and t[2] == {"code": "", "name": "Some rare test", "when": ""}


def test_an_ordered_test_is_offered_to_the_family_once_when_it_falls_due():
    import time

    from api.db import session
    from api.models import Notice, VisitRx
    from api.proactive import due_at, tests_due
    t0 = int(time.time()) - 88 * 86400              # signed 88 days ago: "3 months" falls due in 2 days
    assert due_at(t0, "3 months") == t0 + 90 * 86400 and due_at(t0, "before next visit") is None
    import uuid
    tid, hh = "tk" + uuid.uuid4().hex[:10], "h" + uuid.uuid4().hex[:10]
    with session() as db:
        db.add(VisitRx(token_id=tid, store_id="s", household_id=hh, member_id="m1", doctor_id="d", t=t0,
                       rx={"t": t0, "doctor": "Anitha", "tests": [{"code": "hba1c", "name": "HbA1c", "when": "3 months"}, {"code": "cbc", "name": "CBC", "when": ""}]}))
    with session() as db:
        assert tests_due(db, int(time.time())) >= 1
        assert tests_due(db, int(time.time())) == 0      # once only
        db.flush()
        n = db.query(Notice).filter_by(household_id=hh).all()
        assert len(n) == 1 and n[0].title.startswith("HbA1c is due around") and n[0].ref["testsDue"][0]["code"] == "hba1c"

"""Findings from the November 2026 VAPT and DPDP review, each pinned so it cannot come back."""
import os
import uuid

os.environ.setdefault("OTP_DEMO", "1")
os.environ.setdefault("APP_ENV", "development")

import pytest
from fastapi.testclient import TestClient

import server
from api.db import Base, engine, session


@pytest.fixture()
def anon():
    Base.metadata.create_all(engine)
    with TestClient(server.app, base_url="https://urbanhealth.in") as c:
        c.headers.update({"x-tht": "1"})
        yield c


def _signed_in() -> TestClient:
    c = TestClient(server.app, base_url="https://urbanhealth.in")
    c.headers.update({"x-tht": "1"})
    u = uuid.uuid4().hex[:6]
    r = c.post("/api/v1/auth/signup/start", json={"name": "Dpdp Test", "email": f"d{u}@ex.com", "phone": "9" + str(uuid.uuid4().int)[-9:].zfill(9),
                                                   "password": "Zq!8vB#2mLp@9xT", "terms": True})
    assert r.status_code == 200, r.text
    d = r.json()
    assert c.post("/api/v1/auth/signup/verify", json={"flow": d["flow"], "code": d["demo"]}).status_code == 200
    return c


def test_payment_accounts_and_call_relays_need_a_signed_in_person(anon):
    assert anon.get("/api/v1/pay/upi/accounts").status_code == 401
    assert anon.get("/api/v1/consults/ice").status_code == 401
    c = _signed_in()
    assert c.get("/api/v1/consults/ice").status_code == 200


def test_the_api_map_is_not_published(anon):
    assert anon.get("/api/v1/openapi.json").status_code != 200 or "paths" not in anon.get("/api/v1/openapi.json").text


def test_pages_refuse_framing_and_say_nothing_about_the_server(anon):
    r = anon.get("/")
    assert r.headers["x-frame-options"] == "DENY"
    assert "server" not in {k.lower() for k in r.headers}
    assert r.headers["cross-origin-resource-policy"] == "same-site"
    # pages the app frames itself keep working
    assert anon.get("/kid").headers["x-frame-options"] == "SAMEORIGIN"


def test_nominee_is_saved_encrypted_shown_only_to_its_owner_and_removable():
    c = _signed_in()
    assert c.get("/api/v2/privacy/nominee").json() == {"nominee": None}
    assert c.put("/api/v2/privacy/nominee", json={"name": "Asha Rao", "relation": "Sister", "contact": "not a contact"}).status_code == 400
    r = c.put("/api/v2/privacy/nominee", json={"name": "Asha Rao", "relation": "Sister", "contact": "9876543210"})
    assert r.status_code == 200 and r.json()["nominee"]["name"] == "Asha Rao"
    from api.models import Setting, User
    with session() as db:
        rows = db.query(Setting).filter(Setting.key.like("nominee:%")).all()
        assert rows and all("Asha" not in str(s.value) for s in rows)   # stored encrypted
    other = _signed_in()
    assert other.get("/api/v2/privacy/nominee").json() == {"nominee": None}
    assert c.delete("/api/v2/privacy/nominee").json() == {"ok": True}
    assert c.get("/api/v2/privacy/nominee").json() == {"nominee": None}
    assert TestClient(server.app).get("/api/v2/privacy/nominee").status_code == 401


def test_adding_a_child_keeps_the_guardians_declaration():
    c = _signed_in()
    r = c.post("/api/v2/people", json={"name": "Little One", "dependent": True, "same_ok": True, "profile": {"dob": "2020-03-01", "sex": "female"}})
    assert r.status_code == 200, r.text
    pid = r.json()["id"]
    from api.models import ConsentLog
    with session() as db:
        assert db.query(ConsentLog).filter(ConsentLog.kind == "guardian:" + pid[:15]).count() == 1


def test_aadhaar_xml_is_parsed_without_entity_expansion():
    from api import digilocker
    bomb = b'<?xml version="1.0"?><!DOCTYPE l [<!ENTITY a "aaaaaaaaaa"><!ENTITY b "&a;&a;&a;&a;&a;&a;&a;&a;">]><r>&b;</r>'
    with pytest.raises(Exception):
        digilocker._parse_ekyc(bomb)

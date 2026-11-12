"""A child's vaccine visits and growth measurements are records like any other: only a parent or guardian adds them,
and nonsense values are refused before they are stored."""
import os
import uuid

os.environ.setdefault("OTP_DEMO", "1")
os.environ.setdefault("PWNED_CHECK", "0")
os.environ["DATABASE_URL"] = "sqlite:///./data/test_kids_records.db"

from fastapi.testclient import TestClient  # noqa: E402

import server  # noqa: E402


def parent():
    c = TestClient(server.app)
    c.__enter__()
    c.headers.update({"x-tht": "1"})
    r = c.post("/api/v1/auth/signup/start", json={"name": "Jyothsna V", "email": f"{uuid.uuid4().hex[:8]}@example.com",
                                                  "phone": "9" + str(uuid.uuid4().int)[-9:].zfill(9), "password": "Zq!8vB#2mLp@9xT", "terms": True}).json()
    c.post("/api/v1/auth/signup/verify", json={"flow": r["flow"], "code": r["demo"]})
    c.post("/api/v2/people", json={"name": "Jyothsna V", "profile": {"dob": "1994-03-08", "sex": "female"}})
    kid = c.post("/api/v2/people", json={"name": "Anvika Rao", "dependent": True, "same_ok": True, "profile": {"dob": "2022-05-02", "sex": "female"}}).json()["id"]
    return c, kid


def test_vaccine_visit_and_growth():
    c, kid = parent()
    r = c.post(f"/api/v2/people/{kid}/records", json={"kind": "vax", "day": "2022-06-14", "data": {"g": "6w", "at": "Rainbow"}})
    assert r.status_code == 200 and r.json()["g"] == "6w"
    r = c.post(f"/api/v2/people/{kid}/records", json={"kind": "growth", "day": "2026-11-01", "data": {"w": "16.2", "h": 104}})
    assert r.status_code == 200 and r.json()["w"] == 16.2
    kinds = {x["kind"] for x in c.get(f"/api/v2/people/{kid}/records").json()}
    assert {"vax", "growth"} <= kinds


def test_bad_values_refused():
    c, kid = parent()
    for data in ({"g": ""}, {"g": "<script>"}):
        assert c.post(f"/api/v2/people/{kid}/records", json={"kind": "vax", "data": data}).status_code == 400
    for data in ({}, {"w": 999}, {"h": 5}, {"w": "abc"}, {"hc": 90, "w": 10}):
        assert c.post(f"/api/v2/people/{kid}/records", json={"kind": "growth", "data": data}).status_code == 400


def test_pregnancy_loss_and_mood():
    c, _ = parent()
    me = next(p for p in c.get("/api/v2/me").json()["people"] if p["self"])["id"]
    r = c.post(f"/api/v2/people/{me}/records", json={"kind": "preg", "data": {"stage": "loss", "ended": "2026-11-12"}})
    assert r.status_code == 200
    assert c.post(f"/api/v2/people/{me}/records", json={"kind": "mood", "data": {"v": "low"}}).status_code == 200
    assert c.post(f"/api/v2/people/{me}/records", json={"kind": "mood", "data": {"v": "sad!"}}).status_code == 400

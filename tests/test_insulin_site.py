"""An insulin dose can carry where it was injected, so the app can suggest the next spot; anything else is refused.
Run: python -m pytest -q tests/test_insulin_site.py"""
import os
import uuid

os.environ.setdefault("OTP_DEMO", "1")
os.environ.setdefault("PWNED_CHECK", "0")
os.environ["DATABASE_URL"] = "sqlite:///./data/test_insulin_site.db"

from fastapi.testclient import TestClient  # noqa: E402

import server  # noqa: E402


def me():
    c = TestClient(server.app)
    c.__enter__()
    c.headers.update({"x-tht": "1"})
    r = c.post("/api/v1/auth/signup/start", json={"name": "Lakshmi R", "email": f"{uuid.uuid4().hex[:8]}@example.com",
                                                  "phone": "9" + str(uuid.uuid4().int)[-9:].zfill(9), "password": "Zq!8vB#2mLp@9xT", "terms": True}).json()
    c.post("/api/v1/auth/signup/verify", json={"flow": r["flow"], "code": r["demo"]})
    pid = c.post("/api/v2/people", json={"name": "Lakshmi R", "profile": {"dob": "1960-03-08", "sex": "female"}}).json()["id"]
    return c, pid


def test_dose_with_site_is_kept():
    c, pid = me()
    for site in ("belly-r-0", "thigh-l-5", "arm-r", "arm-l-3"):
        r = c.post(f"/api/v2/people/{pid}/records", json={"kind": "dose", "day": "2026-11-17", "data": {"med": "m1", "time": "20:00", "at": 1, "site": site}})
        assert r.status_code == 200, r.text
        assert r.json()["site"] == site
    r = c.post(f"/api/v2/people/{pid}/records", json={"kind": "dose", "day": "2026-11-17", "data": {"med": "m2", "time": "08:00", "at": 1}})
    assert r.status_code == 200


def test_unknown_site_refused():
    c, pid = me()
    for site in ("neck-r-0", "belly-x-1", "thigh-l-9", "<script>", "belly-r-0-1"):
        r = c.post(f"/api/v2/people/{pid}/records", json={"kind": "dose", "day": "2026-11-17", "data": {"med": "m1", "time": "20:00", "site": site}})
        assert r.status_code == 400, site


def test_reminder_names_the_longest_rested_area():
    from api import reminders
    from api.db import session
    c, pid = me()
    with session() as db:
        assert reminders.insulin_next(db, pid) == "belly-r"          # nothing logged yet: first area
    for site, at in (("belly-r-0", 100), ("belly-l-2", 200), ("thigh-r-1", 300), ("thigh-l-0", 400), ("arm-r-3", 500)):
        c.post(f"/api/v2/people/{pid}/records", json={"kind": "dose", "day": "2026-11-17", "data": {"med": "m1", "time": "20:00", "at": at, "site": site}})
    with session() as db:
        assert reminders.insulin_next(db, pid) == "arm-l"            # never used
    c.post(f"/api/v2/people/{pid}/records", json={"kind": "dose", "day": "2026-11-18", "data": {"med": "m1", "time": "20:00", "at": 600, "site": "arm-l-0"}})
    with session() as db:
        assert reminders.insulin_next(db, pid) == "belly-r"          # used longest ago
    assert reminders._zone_line("en", "thigh-l") == "Next spot: left thigh"
    assert reminders._zone_line("ta", "belly-r").startswith("அடுத்த இடம்")
    assert reminders._zone_line("xx", "arm-r") == "Next spot: right upper arm"

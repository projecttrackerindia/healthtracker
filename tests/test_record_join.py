"""Page 2 of a report uploaded on another day can be put with page 1: it takes page 1's date and lab, keeps what
was read from it, and only someone who can write to that person can do it."""
import os
import uuid

os.environ.setdefault("OTP_DEMO", "1")
os.environ.setdefault("PWNED_CHECK", "0")
os.environ["DATABASE_URL"] = "sqlite:///./data/test_recjoin.db"

from fastapi.testclient import TestClient  # noqa: E402

import server  # noqa: E402
from api.db import Base, engine  # noqa: E402

H = {"x-tht": "1"}
PW = "Zq!8vB#2mLp@9xT"
Base.metadata.create_all(engine)


def signed_in():
    c = TestClient(server.app)
    c.__enter__()
    u = uuid.uuid4().hex[:8]
    j = c.post("/api/v1/auth/signup/start", headers=H, json={"name": "Meena", "email": f"{u}@example.com",
                                                            "phone": "9" + str(uuid.uuid4().int)[-9:], "password": PW, "terms": True}).json()
    assert c.post("/api/v1/auth/signup/verify", headers=H, json={"flow": j["flow"], "code": j["demo"]}).status_code == 200
    me = c.post("/api/v2/people", headers=H, json={"name": "Meena", "profile": {"dob": "2000-01-01", "sex": "female"}}).json()
    return c, me["id"]


def rec(c, pid, day, title, lab=""):
    d = {"title": title, "findings": [{"test": "Cervical length", "value": "3.9", "unit": "cm", "flag": "normal"}]}
    if lab:
        d["lab"] = lab
    r = c.post(f"/api/v2/people/{pid}/records", headers=H, json={"kind": "report", "day": day, "data": d})
    assert r.status_code == 200, r.text
    return r.json()


def test_page_two_joins_page_one():
    c, pid = signed_in()
    p1 = rec(c, pid, "2026-09-16", "TIFFA ultrasound, page 1", "Sri Venkata Sai Diagnostics")
    p2 = rec(c, pid, "2026-11-15", "Foetal anomaly ultrasound (page 2)")
    r = c.post(f"/api/v2/records/{p2['id']}/join", headers=H, json={"to": p1["id"]})
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["day"] == "2026-09-16"
    assert j.get("lab") == "Sri Venkata Sai Diagnostics"
    assert j.get("joined") == p1["id"]
    assert j.get("findings") and j["findings"][0]["value"] == "3.9"


def test_join_needs_the_same_person():
    c, pid = signed_in()
    d, other = signed_in()
    p1 = rec(c, pid, "2026-09-16", "Scan page 1")
    p2 = rec(d, other, "2026-11-15", "Scan page 2")
    assert c.post(f"/api/v2/records/{p1['id']}/join", headers=H, json={"to": p2["id"]}).status_code in (400, 403, 404)

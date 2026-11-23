"""Anatomy review: the research team approves the models we built, families see only the state and the date.

Run: python -m pytest -q tests/test_anatomy_review.py
"""
import os
import uuid

os.environ.setdefault("OTP_DEMO", "1")
os.environ.setdefault("PWNED_CHECK", "0")
os.environ["DATABASE_URL"] = "sqlite:///./data/test_anatomy_review.db"

from fastapi.testclient import TestClient  # noqa: E402

import server  # noqa: E402
from api.db import Base, engine, session  # noqa: E402
from api.models import Admin  # noqa: E402
from api.security import hash_pw  # noqa: E402

H = {"x-tht": "1"}
PW = "Zq!8vB#2mLp@9xT"
Base.metadata.create_all(engine)


def admin(role="owner"):
    tag = uuid.uuid4().hex[:8]
    with session() as db:
        db.add(Admin(email=f"a{tag}@tht.test", pw_hash=hash_pw(PW), role=role))
    c = TestClient(server.app)
    c.headers.update({**H, "x-forwarded-for": f"10.8.{int(tag[:2], 16)}.{int(tag[2:4], 16)}"})
    assert c.post("/api/admin/login", json={"email": f"a{tag}@tht.test", "password": PW}).status_code == 200
    return c, f"a{tag}@tht.test"


def test_content_staff_approve_and_families_see_only_state_and_date():
    c, email = admin("content")
    q = c.get("/api/admin/anatomy").json()
    ids = [x["id"] for x in q["items"]]
    assert "x-nephron" in ids and "vh-sections" in ids and q["open"] >= 1
    r = c.post("/api/admin/anatomy/x-nephron", json={"state": "approved", "note": "Matches Kriz & Kaissling, checked against HRA KTU"})
    assert r.status_code == 200 and r.json()["state"] == "approved" and r.json()["notes"][-1]["by"] == email
    pub = TestClient(server.app).get("/api/v1/anatomy/review", headers=H).json()["items"]
    assert pub["x-nephron"]["state"] == "approved" and pub["x-nephron"]["at"]
    assert set(pub["x-nephron"]) == {"state", "at"}  # no reviewer name, no notes
    assert pub["x-skin"]["state"] in ("pending", "changes", "approved")


def test_needs_changes_must_say_what():
    c, _ = admin()
    assert c.post("/api/admin/anatomy/x-pleura", json={"state": "changes", "note": " "}).status_code == 422
    r = c.post("/api/admin/anatomy/x-pleura", json={"state": "changes", "note": "Parietal layer should line the diaphragm too"})
    assert r.status_code == 200 and r.json()["state"] == "changes"
    first = c.get("/api/admin/anatomy").json()["items"][0]
    assert first["state"] == "changes"  # what needs work comes first
    assert c.post("/api/admin/anatomy/nope", json={"state": "approved"}).status_code == 404
    assert c.post("/api/admin/anatomy/x-pleura", json={"state": "maybe"}).status_code == 422


def test_families_cannot_review():
    anon = TestClient(server.app)
    anon.headers.update(H)
    assert anon.post("/api/admin/anatomy/x-skin", json={"state": "approved"}).status_code == 401

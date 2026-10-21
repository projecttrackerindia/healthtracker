"""Round 26: backups the family can see. Run: python -m pytest -q tests/test_round26.py"""
import io
import os
import uuid
import zipfile
from datetime import date
from pathlib import Path

os.environ.setdefault("OTP_DEMO", "1")
os.environ.setdefault("PWNED_CHECK", "0")
os.environ["DATABASE_URL"] = "sqlite:///./data/test_round26.db"

from fastapi.testclient import TestClient  # noqa: E402

import server  # noqa: E402
from api import backup, messaging  # noqa: E402
from api.db import SessionLocal  # noqa: E402
from api.models import Household, ReminderSent, User  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
H = {"x-tht": "1"}


def client():
    c = TestClient(server.app)
    c.__enter__()
    return c


def signup(c):
    u = uuid.uuid4().hex[:8]
    r = c.post("/api/v1/auth/signup/start", headers=H, json={"name": "Meera Raghavan", "email": f"{u}@example.com", "phone": "9" + str(uuid.uuid4().int)[-9:], "password": "Zq!8vB#2mLp@9xT", "terms": True})
    r = c.post("/api/v1/auth/signup/verify", headers=H, json={"flow": r.json()["flow"], "code": r.json()["demo"]})
    assert r.status_code == 200, r.text
    c.headers["X-DoKKo-Key"] = uuid.uuid4().hex
    assert c.post("/api/v1/hello", json={"name": "T", "members": 1}).status_code == 200
    assert c.put("/api/v1/sync", headers=H, json={"base": 0, "state": {"members": [{"id": "m1", "name": "Meera Raghavan", "rel": "You"}], "vitals": {"m1": [{"t": 1, "hr": 70}]}}, "sect": {"members": 1}}).status_code == 200
    return r.json()["user"], f"{u}@example.com"


def test_send_now_mails_the_record_and_status_reflects_it(monkeypatch):
    mails = []
    monkeypatch.setenv("SMTP_HOST", "smtp.test")
    monkeypatch.setattr(messaging, "send_mail_attachment", lambda to, subject, text, filename, data, mime="application/zip": mails.append((to, subject, filename, data)))
    c = client()
    user, email = signup(c)
    st = c.get("/api/v1/backup/status", headers=H).json()
    assert st["synced"] is True and st["lastEmail"] is None and st["willEmail"] == [email] and st["email"] is True
    r = c.post("/api/v1/backup/send", headers=H, json={})
    assert r.status_code == 200, r.text
    assert len(mails) == 1 and mails[0][0] == email and mails[0][1].startswith("Your family's health record — backup")
    z = zipfile.ZipFile(io.BytesIO(mails[0][3]))
    names = z.namelist()
    assert "record.json" in names and "README.txt" in names and "documents/index.json" in names and not any(n.startswith("documents/") and n != "documents/index.json" for n in names)
    assert b"Meera Raghavan" in z.read("record.json")
    st = c.get("/api/v1/backup/status", headers=H).json()
    assert st["lastEmail"] and st["emailTo"] == email


def test_send_now_needs_a_verified_email(monkeypatch):
    monkeypatch.setenv("SMTP_HOST", "smtp.test")
    c = client()
    user, email = signup(c)
    with SessionLocal() as db:
        u = db.get(User, user["id"]); u.email_verified = False; db.commit()
    r = c.post("/api/v1/backup/send", headers=H, json={})
    assert r.status_code == 409 and "Verify your email" in r.json()["detail"]


def test_monthly_runs_on_the_first_once_per_household(monkeypatch):
    mails = []
    monkeypatch.setenv("SMTP_HOST", "smtp.test")
    monkeypatch.setattr(messaging, "send_mail_attachment", lambda to, subject, text, filename, data, mime="application/zip": mails.append(to))
    c = client()
    user, email = signup(c)
    with SessionLocal() as db:
        assert backup.monthly(db, date(2026, 11, 2)) == 0          # not the first
        n = backup.monthly(db, date(2026, 11, 1))
        db.commit()
        assert n >= 1 and email in mails
        before = len(mails)
        assert backup.monthly(db, date(2026, 11, 1)) == 0 and len(mails) == before   # same month: once
        db.query(ReminderSent).filter(ReminderSent.key.like("backup:%")).delete(); db.commit()


def test_page_carries_layer_26():
    html = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
    assert "/*live-p26*/" in html and "SX.act.bkpsend=" in html and "/backup/status" in html
    assert "There is no Urban Health server account in this build" not in html

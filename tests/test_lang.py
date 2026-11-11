"""Account language: saved through /api/v2/me/lang, returned by /api/v2/me, and used for medicine reminder text."""
import os
import uuid

os.environ.setdefault("OTP_DEMO", "1")
os.environ.setdefault("PWNED_CHECK", "0")
os.environ["DATABASE_URL"] = "sqlite:///./data/test_lang.db"

from fastapi.testclient import TestClient  # noqa: E402

import server  # noqa: E402
from api import reminders  # noqa: E402

H = {"x-tht": "1"}


def signup(c):
    u = uuid.uuid4().hex[:8]
    r = c.post("/api/v1/auth/signup/start", headers=H, json={"name": "Lang " + u, "email": f"{u}@example.com",
               "phone": "9" + str(uuid.uuid4().int)[-9:].zfill(9), "password": "Zq!8vB#2mLp@9xT", "terms": True})
    r = c.post("/api/v1/auth/signup/verify", headers=H, json={"flow": r.json()["flow"], "code": r.json()["demo"]})
    assert r.status_code == 200, r.text


def test_language_is_saved_and_returned():
    c = TestClient(server.app)
    signup(c)
    assert c.get("/api/v2/me", headers=H).json()["user"]["lang"] == "en"
    assert c.put("/api/v2/me/lang", headers=H, json={"lang": "ta"}).status_code == 200
    assert c.get("/api/v2/me", headers=H).json()["user"]["lang"] == "ta"
    assert c.put("/api/v2/me/lang", headers=H, json={"lang": "xx"}).status_code == 422


def test_reminder_text_follows_language():
    assert reminders._say("ta", "due_own", t="08:30", first="Amma") == "உங்கள் 08:30 மருந்துகளுக்கான நேரம்"
    assert reminders._say("te", "missed_other", t="21:00", first="Appa").startswith("Appa 21:00")
    assert reminders._say("zz", "due_other", t="08:30", first="Amma") == "Amma: 08:30 medicines"

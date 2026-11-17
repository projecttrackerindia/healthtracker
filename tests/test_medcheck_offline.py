"""The allergy and repeat checks never wait for the AI: they still run when it is off, and the app is told the check was limited.
Run: python -m pytest -q tests/test_medcheck_offline.py"""
import os
import uuid

os.environ.setdefault("OTP_DEMO", "1")
os.environ.setdefault("PWNED_CHECK", "0")

from fastapi.testclient import TestClient  # noqa: E402

import server  # noqa: E402
from api import agent  # noqa: E402


def test_allergy_clash_is_flagged_even_with_the_ai_off(monkeypatch):
    monkeypatch.setattr(agent, "enabled", lambda: False)
    c = TestClient(server.app)
    c.headers.update({"x-tht": "1", "x-forwarded-for": f"10.9.{uuid.uuid4().int % 250}.{uuid.uuid4().int % 250}"})
    c.headers["X-DoKKo-Key"] = uuid.uuid4().hex
    c.post("/api/v1/hello", json={"name": "T", "members": 1})
    r = c.post("/api/v1/ai/medcheck", json={"member": "m1", "context": {
        "medicines": [{"name": "Amoxicillin 500"}, {"name": "Metformin 500"}, {"name": "Metformin 1000"}], "allergies": ["amoxicillin"]}})
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["limited"] is True and d["ok"] is False
    assert d["alerts"][0]["title"] == "Listed allergy" and "Amoxicillin" in d["alerts"][0]["detail"]
    assert d["duplicates"][0]["medicines"] == ["Metformin 500", "Metformin 1000"]

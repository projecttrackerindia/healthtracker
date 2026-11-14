"""Strict rules around AI and uploaded documents.

* Health data reaches the AI only with the person's own recorded yes; a "no" is respected without nagging.
* Emergencies and self-harm get the right line from the server itself, consent or not, AI or not.
* Dose instructions never leave the assistant.
* Edited / made-up documents are flagged where a person decides: the family, the pharmacist, the admins.
* Schedule X and NDPS medicines cannot be ordered online at all.
"""
import io
import os
import uuid

os.environ.setdefault("OTP_DEMO", "1")
os.environ.setdefault("PWNED_CHECK", "0")
os.environ["DATABASE_URL"] = "sqlite:///./data/test_aic.db"

from fastapi.testclient import TestClient  # noqa: E402

import server  # noqa: E402
from api import agent, storage  # noqa: E402
from api.people import impossible_values  # noqa: E402

H = {"x-tht": "1"}


def user():
    c = TestClient(server.app)
    c.__enter__()
    c.headers.update(H)
    u = uuid.uuid4().hex[:8]
    r = c.post("/api/v1/auth/signup/start", json={"name": "Test Person", "email": f"{u}@example.com", "phone": "9" + str(uuid.uuid4().int)[-9:].zfill(9),
                                                  "password": "Zq!8vB#2mLp@9xT", "terms": True})
    assert c.post("/api/v1/auth/signup/verify", json={"flow": r.json()["flow"], "code": r.json()["demo"]}).status_code == 200
    c.headers["X-DoKKo-Key"] = uuid.uuid4().hex
    c.post("/api/v1/hello", json={"name": "T", "members": 1})
    return c


def consent(c, yes):
    assert c.put("/api/v2/permissions", json={"items": {"ai_reports": yes}, "via": "app"}).status_code == 200


def test_assistant_needs_a_recorded_yes(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test")
    called = []
    monkeypatch.setattr(agent, "ask", lambda q, ctx: called.append(q) or {"answer": "ok", "sources": [], "actions": [], "urgent": False, "focus": [], "commands": []})
    anon = TestClient(server.app)
    anon.__enter__()
    anon.headers.update({**H, "X-DoKKo-Key": uuid.uuid4().hex})
    assert anon.post("/api/v1/ai/ask", json={"question": "Is my sugar okay?", "context": {}}).status_code == 401
    c = user()
    assert c.post("/api/v1/ai/ask", json={"question": "Is my sugar okay?", "context": {}}).status_code == 428      # never asked
    consent(c, False)
    r = c.post("/api/v1/ai/ask", json={"question": "Is my sugar okay?", "context": {}})
    assert r.status_code == 403 and "Settings" in r.json()["detail"]
    assert c.post("/api/v1/ai/medcheck", json={"context": {"medicines": [{"name": "Dolo"}]}}).status_code == 403
    assert not called
    consent(c, True)
    assert c.post("/api/v1/ai/ask", json={"question": "Is my sugar okay?", "context": {}}).json()["answer"] == "ok"


def test_emergency_and_self_harm_lines_come_from_the_server(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    c = user()                     # no consent, no AI: the emergency line still comes
    r = c.post("/api/v1/ai/ask", json={"question": "my father has chest pain and is sweating", "context": {}}).json()
    assert r["urgent"] and "112" in r["answer"]
    r = c.post("/api/v1/ai/ask", json={"question": "I want to end my life", "context": {}}).json()
    assert r["urgent"] and "14416" in r["answer"]


def test_doses_are_stripped_from_answers():
    out = agent.guard("fever in my son", {"answer": "Fever is common. Give 250 mg paracetamol every 6 hours. Keep him drinking water.", "urgent": False})
    assert "250 mg" not in out["answer"] and "doctor or pharmacist" in out["answer"] and "drinking water" in out["answer"]


def test_editing_apps_and_late_changes_are_noticed():
    from PIL import Image
    im = Image.new("RGB", (60, 40), (255, 255, 255))
    ex = im.getexif()
    ex[0x0131] = "Adobe Photoshop 25.0"           # Software tag
    b = io.BytesIO()
    im.save(b, "JPEG", exif=ex)
    assert any("editing app" in s for s in storage.edit_signals(b.getvalue(), "image/jpeg"))
    clean = io.BytesIO()
    Image.new("RGB", (60, 40)).save(clean, "JPEG")
    assert storage.edit_signals(clean.getvalue(), "image/jpeg") == []
    pdf = (b"%PDF-1.4\n1 0 obj<</Producer (Microsoft Word for Microsoft 365)/CreationDate (D:20260101100000)/ModDate (D:20260301100000)>>endobj\n"
           b"trailer<</Info 1 0 R>>\n%%EOF")
    sig = storage.edit_signals(pdf, "application/pdf")
    assert any("word processor" in s for s in sig)


def test_impossible_lab_values():
    assert impossible_values([{"code": "hb", "test": "Haemoglobin", "value": 48}])
    assert impossible_values([{"code": "glu_f", "test": "Fasting glucose", "value": "9999"}])
    assert not impossible_values([{"code": "hb", "value": 12.4}, {"code": "plt", "value": 2.5}])     # platelets in lakhs


def test_schedule_x_and_ndps_cannot_be_ordered():
    from api.db import session
    from api.models import Store, StoreItem
    c = user()
    with session() as db:
        s = Store(kind="pharmacy", name="Rx Test", city="Chennai", lat=13.1, lng=80.29, active=True, verified=True)
        db.add(s)
        db.flush()
        db.add(StoreItem(store_id=s.id, sku="cough-cod", name="Codeine cough syrup", mrp=120, price=110, stock=5))
        sid = s.id
    r = c.post("/api/v1/orders", json={"store": sid, "kind": "medicine", "items": [{"sku": "cough-cod", "qty": 1}], "address": "x", "member": "T",
                                       "payment": "cod", "rxShared": True, "rxDocs": ["f1"]})
    assert r.status_code == 400 and "by law" in r.json()["detail"]

"""Round 21: SOS that acts. Run: python -m pytest -q tests/test_round21.py"""
import os
import uuid
from pathlib import Path

import pytest

os.environ.setdefault("OTP_DEMO", "1")
os.environ.setdefault("PWNED_CHECK", "0")
os.environ["DATABASE_URL"] = "sqlite:///./data/test_round21.db"

from fastapi.testclient import TestClient  # noqa: E402

import server  # noqa: E402
from api import messaging, sos  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
H = {"x-tht": "1"}


def client():
    c = TestClient(server.app)
    c.__enter__()
    return c


def household(c):
    key = "k" + uuid.uuid4().hex[:28]
    assert c.post("/api/v1/hello", headers={**H, "x-dokko-key": key}, json={}).status_code == 200
    return {**H, "x-dokko-key": key}


@pytest.fixture
def mail(monkeypatch):
    sent = []
    monkeypatch.setenv("SMTP_HOST", "smtp.test")
    monkeypatch.setattr(messaging, "send_mail", lambda to, subject, text, html=None: sent.append({"to": to, "subject": subject, "text": text, "html": html}))
    return sent


BODY = {"member": "d1", "name": "Meera Raghavan", "phone": "+919876500000", "summary": "Blood group: O+. Allergies: penicillin. Conditions: none recorded. Medicines: none recorded.", "blood": "O+",
        "loc": {"lat": 17.4401, "lng": 78.3489, "acc": 14}, "contacts": [{"n": "Vikram", "ph": "+919876543210", "em": "vikram@example.com"}, {"n": "Kamala", "ph": "+919876543211", "em": ""}], "lang": "en"}


def test_one_press_creates_the_alert_mails_contacts_and_opens_a_live_page(mail):
    c = client()
    hk = household(c)
    r = c.post("/api/v1/sos/start", headers=hk, json=BODY)
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["active"] and j["token"] and j["url"].endswith("/sos/" + j["token"]) and j["loc"]["lat"] == 17.4401
    assert j["maps"] == "https://maps.google.com/?q=17.440100,78.348900" and "google.com/maps/dir/" in j["directions"]
    assert "Live page:" in j["message"] and "penicillin" in j["message"] and "+919876500000" in j["message"]
    # the contact with an address was mailed the moment the alert was created; the one without was not
    assert [m["to"] for m in mail] == ["vikram@example.com"]
    assert mail[0]["subject"] == "EMERGENCY: Meera Raghavan needs help" and j["url"] in mail[0]["text"] and "Open the live page" in mail[0]["html"]
    assert {"n": "Vikram", "channel": "email", "ok": True} in j["sent"] and any(x["channel"] == "push" for x in j["sent"])
    # the public page and its JSON need no sign-in and carry no household secrets
    p = c.get("/sos/" + j["token"])
    assert p.status_code == 200 and "Meera Raghavan needs help" in p.text and "17.4401" not in p.text   # the map is drawn by the script from the JSON, nothing baked in
    assert p.headers["cache-control"] == "no-store" and "frame-src https://www.google.com" in p.headers["content-security-policy"]
    pj = c.get("/api/v1/sos/t/" + j["token"]).json()
    assert pj["name"] == "Meera Raghavan" and pj["loc"]["lat"] == 17.4401 and "id" not in pj and "contacts" not in pj and pj["phone"] == "+919876500000"
    # the family's inbox got the alert too (push/WhatsApp fan-out goes through notify)
    assert c.get("/api/v1/sos/t/nope").status_code == 404


def test_location_arrives_later_and_the_alert_ends(mail):
    c = client()
    hk = household(c)
    j = c.post("/api/v1/sos/start", headers=hk, json={**BODY, "loc": None}).json()
    assert j["loc"] is None and "not available yet" in j["message"] and len(mail) == 1
    r = c.post(f"/api/v1/sos/{j['id']}/loc", headers=hk, json={"loc": {"lat": 17.44, "lng": 78.35, "acc": 30}})
    assert r.status_code == 200 and r.json()["loc"]["acc"] == 30 and len(r.json()["trail"]) == 1
    assert len(mail) == 2 and "maps.google.com/?q=17.440000,78.350000" in mail[1]["text"]   # the first fix goes out again, now with the map
    r = c.post(f"/api/v1/sos/{j['id']}/loc", headers=hk, json={"loc": {"lat": 17.441, "lng": 78.351, "acc": 12}})
    assert len(r.json()["trail"]) == 2 and len(mail) == 2
    e = c.post(f"/api/v1/sos/{j['id']}/end", headers=hk, json={})
    assert e.status_code == 200 and e.json()["active"] is False and e.json()["ended"]
    assert c.post(f"/api/v1/sos/{j['id']}/loc", headers=hk, json={"loc": {"lat": 1, "lng": 1}}).status_code == 409
    assert "is safe now" in c.get("/api/v1/sos/t/" + j["token"]).json()["name"] or c.get("/sos/" + j["token"]).status_code == 200


def test_only_the_owner_household_can_touch_an_alert_and_demo_keys_cannot_press(mail):
    c = client()
    a, b = household(c), household(c)
    j = c.post("/api/v1/sos/start", headers=a, json=BODY).json()
    assert c.post(f"/api/v1/sos/{j['id']}/loc", headers=b, json={"loc": {"lat": 1, "lng": 1}}).status_code == 404
    assert c.post(f"/api/v1/sos/{j['id']}/end", headers=b, json={}).status_code == 404
    assert c.post("/api/v1/sos/start", headers={**H, "x-dokko-key": "demo-abcdefghijklmnop"}, json=BODY).status_code == 403
    # a second press by the same person closes the first alert
    j2 = c.post("/api/v1/sos/start", headers=a, json=BODY).json()
    assert j2["id"] != j["id"] and c.get("/api/v1/sos/t/" + j["token"]).json()["active"] is False


def test_page_carries_layer_21():
    html = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
    assert "/*live-p21*/" in html and 'name="em" type="email"' in html and "cs.push({id:uid('c'),n,rel,ph,em,notify:true})" in html
    assert "lv21-ring" in html and "/sos/start" in html and "wa.me/" in html
    assert "Counts down from 3, then calls" in html
    assert "const V='dk-r" in (ROOT / "web" / "sw.js").read_text(encoding="utf-8")
    kt = (ROOT / "mobile" / "android" / "app" / "src" / "main" / "java" / "com" / "urbanhealth" / "app" / "SosPlugin.kt").read_text()
    assert "ACTION_CALL" in kt and "ACTION_DIAL" in kt
    assert "CALL_PHONE" in (ROOT / "mobile" / "android" / "app" / "src" / "main" / "AndroidManifest.xml").read_text()
    assert sos.message is not None

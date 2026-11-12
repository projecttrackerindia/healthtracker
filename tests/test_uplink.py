"""Upload links: a lab not on Urban Health uploads a report; nothing is filed until the person accepts it, and a
report printed for someone else (wrong age or sex) is paused for the person to decide."""
import io

from fastapi.testclient import TestClient

import server
from tests.test_people_v2 import person
from api import ai

PDF = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"


def _reading(name, age, sex):
    return lambda *a, **k: {"engine": "test", "title": "Lipid profile", "date": "2026-11-10", "findings": [{"test": "LDL", "value": "162", "unit": "mg/dL", "flag": "high"}],
                            "patient": {"name": name, "age_years": age, "sex": sex}}


def _lab():
    c = TestClient(server.app)
    c.__enter__()
    return c


def test_link_upload_review_accept_and_security(monkeypatch):
    c = person("Prasanna Kumar", {"sex": "male", "dob": "1989-06-12", "blood": "O+", "phone": "+919876504321"})
    link = c.post(f"/api/v2/people/{c.pid}/upload-links", json={"hours": 48, "maxFiles": 2}).json()
    assert link["live"] and len(link["code"]) == 6 and "/u/" in link["url"]
    tok = link["url"].rsplit("/", 1)[1]
    lab = _lab()
    page = lab.get(f"/u/{tok}")
    assert page.status_code == 200 and "Prasanna Kumar" in page.text and "4321" in page.text and "noindex" in page.headers["x-robots-tag"]
    assert "O+" not in page.text                                               # nothing medical on the lab's page
    up = lambda **k: lab.post(f"/u/{tok}/upload", headers={"x-tht": "1"}, files={"file": ("r.pdf", io.BytesIO(PDF), "application/pdf")},
                              data={"lab": "Apollo Diagnostics", "confirm": "1", **k})
    assert lab.post(f"/u/{tok}/upload", files={"file": ("r.pdf", io.BytesIO(PDF), "application/pdf")}, data={"lab": "x"}).status_code == 403   # no header
    assert up(code="000000").status_code == 403                                 # wrong code counts a try
    monkeypatch.setattr(ai, "analyze", _reading("Prasanna K", 37, "male"))
    r = up(code=link["code"])
    assert r.status_code == 200 and r.json()["left"] == 1, r.text
    # held apart: not in records, waiting in uploads
    assert not [x for x in c.get(f"/api/v2/people/{c.pid}/records").json() if x["kind"] == "report"]
    pend = c.get(f"/api/v2/people/{c.pid}/uploads").json()
    assert len(pend) == 1 and pend[0]["match"]["ok"] and pend[0]["via"]["lab"] == "Apollo Diagnostics"
    assert any(x["who"] == "Apollo Diagnostics" and x["ext"] for x in c.get(f"/api/v2/people/{c.pid}/access-log").json())
    acc = c.post(f"/api/v2/uploads/{pend[0]['id']}/accept").json()
    assert acc["kind"] == "report"
    assert [x for x in c.get(f"/api/v2/people/{c.pid}/records").json() if x["kind"] == "report"]
    # a report for someone else: age 63 vs 37 is paused, then removed
    monkeypatch.setattr(ai, "analyze", _reading("Prasanna K", 63, "male"))
    assert up(code=link["code"]).status_code == 200
    bad = c.get(f"/api/v2/people/{c.pid}/uploads").json()[0]
    assert not bad["match"]["ok"] and bad["match"]["age"] == "differs"
    assert c.post(f"/api/v2/uploads/{bad['id']}/ask").status_code == 200
    assert c.delete(f"/api/v2/uploads/{bad['id']}").status_code == 200 and c.get(f"/api/v2/people/{c.pid}/uploads").json() == []
    # the link is used up; a cancelled link and other families' links are closed
    assert lab.get(f"/u/{tok}").status_code == 410
    l2 = c.post(f"/api/v2/people/{c.pid}/upload-links", json={}).json()
    other = person("Ravi")
    assert other.delete(f"/api/v2/upload-links/{l2['id']}").status_code in (403, 404)
    assert c.delete(f"/api/v2/upload-links/{l2['id']}").status_code == 200
    assert lab.get("/u/" + l2["url"].rsplit("/", 1)[1]).status_code == 404
    assert lab.get("/u/not-a-real-token-xxxxxxxx").status_code == 404


def test_code_locks_after_five():
    c = person("Meena", {"sex": "female", "dob": "1990-01-01"})
    link = c.post(f"/api/v2/people/{c.pid}/upload-links", json={}).json()
    tok, lab = link["url"].rsplit("/", 1)[1], _lab()
    for _ in range(5):
        lab.post(f"/u/{tok}/upload", headers={"x-tht": "1"}, files={"file": ("r.pdf", io.BytesIO(PDF), "application/pdf")}, data={"lab": "Some Lab", "confirm": "1", "code": "111111"})
    assert lab.get(f"/u/{tok}").status_code == 423


def test_delete_with_48_hours_notice():
    from api.db import SessionLocal
    from api.models import Setting, User
    from api import people
    c = person("Lakshmi", {"sex": "female", "dob": "1980-02-02"})
    r = c.post("/api/v1/auth/account/delete", json={"confirm": "DELETE", "later": True}).json()
    assert r["scheduled"] > 0 and c.get("/api/v1/auth/account/delete").json()["at"] == r["scheduled"]
    assert c.post("/api/v1/auth/account/delete/cancel").json() == {"at": None}
    c.post("/api/v1/auth/account/delete", json={"confirm": "DELETE", "later": True})
    with SessionLocal() as db:
        s = db.get(Setting, "erase:" + c.uid)
        s.value = {"at": 1}
        db.commit()
        assert people.erase_due(db) == 1
        assert db.get(User, c.uid) is None


def test_insurance_terms_and_claims(monkeypatch):
    c = person("Ravi", {"sex": "male", "dob": "1985-01-01"})
    card = c.post("/api/v2/schemes/cards", json={"scheme": "private", "number": "P/2116/0042731", "insurer": "Star Health", "plan": "Family Floater", "sumInsured": 1000000, "members": [c.pid]}).json()
    cid = card["id"]
    assert card["left"] == 1000000 and card["used"] == 0
    c.post(f"/api/v2/schemes/cards/{cid}/file/doc", files={"file": ("p.pdf", io.BytesIO(PDF), "application/pdf")})
    monkeypatch.setattr(ai, "analyze_policy", lambda *a, **k: {"readable": True, "room_rent": "1% of sum insured per day", "copay": "none", "waiting_ped_months": 36,
                                                               "no_claim_bonus": "10% per claim-free year", "valid_from": "2026-01-01", "tpa_phone": "1800 425 2255"})
    t = c.post(f"/api/v2/schemes/cards/{cid}/read-policy").json()
    assert t["terms"]["room_rent"].startswith("1%") and t["terms"]["waiting_ped_months"] == 36 and t["help"] == "18004252255"
    cl = c.post(f"/api/v2/schemes/cards/{cid}/claims", json={"hospital": "Kauvery", "amount": 180000, "date": "2026-11-02", "status": "submitted"}).json()["claims"][0]
    after = c.put(f"/api/v2/schemes/cards/{cid}/claims/{cl['id']}", json={"hospital": "Kauvery", "amount": 180000, "approved": 160000, "date": "2026-11-02", "status": "approved"}).json()
    assert after["used"] == 160000 and after["left"] == 840000 and [s["s"] for s in after["claims"][0]["steps"]] == ["submitted", "approved"]
    assert c.delete(f"/api/v2/schemes/cards/{cid}/claims/{cl['id']}").json()["claims"] == []
    assert person("Other").post(f"/api/v2/schemes/cards/{cid}/claims", json={"hospital": "X Hospital"}).status_code == 404

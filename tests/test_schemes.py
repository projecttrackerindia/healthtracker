import os
import sys

os.environ.setdefault("OTP_DEMO", "1")
os.environ.setdefault("PWNED_CHECK", "0")
os.environ["DATABASE_URL"] = "sqlite:///./data/test_schemes.db"
sys.path.insert(0, os.path.dirname(__file__))
import test_round7 as R  # noqa: E402


def test_checker_and_cards():
    f = R.family()
    cat = f.get("/api/v2/schemes").json()
    assert "Telangana" in cat["states"] and any(s["id"] == "pmjay" for s in cat["schemes"])
    r = f.post("/api/v2/schemes/check", json={"state": "Telangana", "age": 72, "rationCard": "yes"}).json()["results"]
    ids = [x["id"] for x in r]
    assert ids[:3] == ["vayvandana", "aarogyasri", "pmjay"] or {"vayvandana", "aarogyasri"} <= set(ids)
    assert all(x["level"] in ("likely", "maybe", "note") for x in r)
    g = f.post("/api/v2/schemes/check", json={"state": "Telangana", "age": 40, "job": "central"}).json()["results"]
    assert g[0]["id"] == "cghs" and not any(x["id"] == "pmjay" for x in g) and any(x["id"] == "note" for x in g)
    assert f.post("/api/v2/schemes/check", json={"age": 300}).status_code == 400
    assert f.post("/api/v2/schemes/cards", json={"scheme": "pmjay", "number": "1234 5678 9012"}).status_code == 400   # Aadhaar-shaped
    c = f.post("/api/v2/schemes/cards", json={"scheme": "pmjay", "number": "ab-12cd34ef", "memberId": "m1"})
    assert c.status_code == 200 and c.json()["last4"] == "34EF" and "number" not in c.json()
    assert f.get(f"/api/v2/schemes/cards/{c.json()['id']}").json()["number"] == "AB-12CD34EF"
    assert R.family().get(f"/api/v2/schemes/cards/{c.json()['id']}").status_code == 404
    assert f.delete(f"/api/v2/schemes/cards/{c.json()['id']}").json()["ok"]


def test_private_card_with_photo_and_pdf():
    f = R.family()
    assert f.post("/api/v2/schemes/cards", json={"scheme": "private", "number": "P/141117/01/2026/004821"}).status_code == 400   # insurer needed
    c = f.post("/api/v2/schemes/cards", json={"scheme": "private", "number": "P/141117/01/2026/004821", "insurer": "Star Health", "plan": "Family Floater",
                                                "sumInsured": 1000000, "validUntil": "2027-03-31", "helpline": "1800 425 2255"})
    assert c.status_code == 200, c.text
    cid = c.json()["id"]
    assert c.json()["name"] == "Star Health" and c.json()["last4"] == "4821"
    assert f.post(f"/api/v2/schemes/cards/{cid}/file/front", files={"file": ("x.txt", b"hello", "text/plain")}).status_code == 415
    ok = f.post(f"/api/v2/schemes/cards/{cid}/file/front", files={"file": ("c.jpg", b"\xff\xd8\xff\xe0card", "image/jpeg")})
    assert ok.status_code == 200 and ok.json()["files"] == ["front"]
    assert f.post(f"/api/v2/schemes/cards/{cid}/file/doc", files={"file": ("p.pdf", b"%PDF-1.4 policy", "application/pdf")}).status_code == 200
    g = f.get(f"/api/v2/schemes/cards/{cid}/file/doc")
    assert g.status_code == 200 and g.content.startswith(b"%PDF")
    assert R.family().get(f"/api/v2/schemes/cards/{cid}/file/doc").status_code == 404

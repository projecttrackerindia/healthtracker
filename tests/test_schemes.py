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
    assert f.get(f"/api/v2/schemes/cards/{c.json()['id']}").json()["number"] == "AB12CD34EF"
    assert R.family().get(f"/api/v2/schemes/cards/{c.json()['id']}").status_code == 404
    assert f.delete(f"/api/v2/schemes/cards/{c.json()['id']}").json()["ok"]

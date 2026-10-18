"""Places (OSM proxy), branded receipts, returns, prescription gate, production order progression."""
import json
import os
import uuid

os.environ.setdefault("OTP_DEMO", "1")
os.environ.setdefault("PWNED_CHECK", "0")
os.environ["DATABASE_URL"] = "sqlite:///./data/test_r6.db"

from fastapi.testclient import TestClient  # noqa: E402

import server  # noqa: E402
from api import places, db as DB  # noqa: E402
from api.models import LabTest, Store, StoreItem  # noqa: E402

H = {"x-tht": "1"}


def client():
    c = TestClient(server.app)
    c.__enter__()
    c.headers["X-DoKKo-Key"] = uuid.uuid4().hex
    assert c.post("/api/v1/hello", json={"name": "T", "members": 1}).status_code == 200
    return c


def seed_store():
    with DB.session() as db:
        s = Store(kind="pharmacy", name="Test Pharmacy", city="Hyderabad", area="Madhapur", lat=17.448, lng=78.391, phone="04012345678", licence="TG/HYD/123", verified=True)
        db.add(s); db.flush()
        db.add(StoreItem(store_id=s.id, sku="ator10", name="Atorvastatin 10", price=90, mrp=100, stock=50))
        db.add(StoreItem(store_id=s.id, sku="para650", name="Paracetamol 650", price=20, mrp=25, stock=50))
        lab = Store(kind="lab", name="Test Lab", city="Hyderabad", area="Gachibowli", lat=17.44, lng=78.348, home_collection=True, verified=True)
        db.add(lab); db.flush()
        db.add(LabTest(store_id=lab.id, code="hba1c", name="HbA1c", price=450, tat_hours=24, fasting=False))
        return s.id, lab.id


def test_where_and_places_use_cache_and_merge_partners(monkeypatch):
    sid, lid = seed_store()
    calls = []

    def fake_get(url, data=None, timeout=12):
        calls.append(url)
        if "nominatim" in url:
            return {"address": {"suburb": "Madhapur", "city": "Hyderabad", "state": "Telangana", "postcode": "500081", "country_code": "in"}}
        return {"elements": [{"type": "node", "id": 1, "lat": 17.45, "lon": 78.39, "tags": {"name": "City Hospital", "amenity": "hospital", "phone": "+91 40 1111", "emergency": "yes"}},
                             {"type": "way", "id": 2, "center": {"lat": 17.46, "lon": 78.40}, "tags": {"name": "Area Clinic"}}, {"type": "node", "id": 3, "lat": 17.4, "lon": 78.4, "tags": {}}]}

    monkeypatch.setattr(places, "_get", fake_get)
    c = client()
    w = c.get("/api/v1/geo/where?lat=17.4481&lng=78.3911").json()
    assert w["ok"] and w["place"] == "Madhapur" and w["stateCode"] == "TS"
    assert c.get("/api/v1/geo/where?lat=17.4483&lng=78.3913").json()["city"] == "Hyderabad" and len(calls) == 1   # same ~1 km cell: cached
    p = c.get("/api/v1/places?kind=hospital&lat=17.448&lng=78.391").json()
    assert p["ok"] and [x["name"] for x in p["places"]] == ["City Hospital", "Area Clinic"] and p["places"][0]["emergency"] is True
    assert c.get("/api/v1/places?kind=hospital&lat=17.448&lng=78.391").json()["ok"] and len(calls) == 2            # cached
    labs = c.get("/api/v1/places?kind=lab&lat=17.448&lng=78.391").json()
    assert labs["partners"] and labs["partners"][0]["name"] == "Test Lab" and labs["partners"][0]["partner"] is True
    assert c.get("/api/v1/places?kind=zoo&lat=1&lng=1").status_code == 400
    assert c.get("/api/v1/places?kind=lab").status_code == 400


def test_places_degrade_when_osm_is_down(monkeypatch):
    def boom(*a, **k):
        raise TimeoutError("slow")
    monkeypatch.setattr(places, "_get", boom)
    places._CACHE.clear()
    c = client()
    p = c.get("/api/v1/places?kind=pharmacy&lat=17.448&lng=78.391").json()
    assert p["ok"] is False and p["note"] and isinstance(p["partners"], list)
    assert c.get("/api/v1/geo/where?lat=10&lng=10").json() == {"ok": False}


def test_rx_gate_receipt_and_return(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    sid, lid = seed_store()
    c = client()
    r = c.post("/api/v1/orders", json={"store": sid, "kind": "medicine", "items": [{"sku": "ator10", "qty": 1, "rx": False}], "address": "12 Road, Madhapur", "member": "Prasanna", "rxShared": False})
    assert r.status_code == 400 and "prescription" in r.json()["detail"].lower()
    r = c.post("/api/v1/orders", json={"store": sid, "kind": "medicine", "items": [{"sku": "ator10", "qty": 1, "rx": True}, {"sku": "para650", "qty": 2}], "address": "12 Road, Madhapur", "member": "Prasanna", "rxShared": True})
    assert r.status_code == 200, r.text
    o = r.json()
    assert o["status"] == "placed" and o["step"] == 0            # production: the clock never advances an order
    pdf = c.get(f"/api/v1/orders/{o['id']}/receipt.pdf")
    assert pdf.status_code == 200 and pdf.content[:4] == b"%PDF" and len(pdf.content) > 2000
    try:
        import pymupdf
    except ImportError:
        import fitz as pymupdf
    text = pymupdf.open(stream=pdf.content, filetype="pdf")[0].get_text()
    assert "ORDER RECEIPT" in text and "Test Pharmacy" in text and "Paracetamol 650" in text and "Atorvastatin 10 (Rx)" in text and "130" in text
    assert c.post(f"/api/v1/orders/{o['id']}/return", json={"reason": "nope"}).status_code == 400
    bad = c.post(f"/api/v1/orders/{o['id']}/return", json={"reason": "not_needed", "items": ["ator10"]})
    assert bad.status_code == 400 and "Prescription" in bad.json()["detail"]
    ok = c.post(f"/api/v1/orders/{o['id']}/return", json={"reason": "damaged", "note": "strip crushed"})
    assert ok.status_code == 200 and ok.json()["status"] == "return_requested"
    assert c.get("/api/v1/orders").json()["orders"][0]["status"] == "return_requested"
    assert c.post(f"/api/v1/orders/{o['id']}/return", json={"reason": "damaged"}).status_code == 400
    other = client()
    assert other.get(f"/api/v1/orders/{o['id']}/receipt.pdf").status_code == 404
    assert "medicines" in c.get("/api/v1/returns/policy").json()

"""Medicine orders hop to the next pharmacy, land on the desk when nobody takes them, and are packed with proof."""
import os
import sys

os.environ.setdefault("OTP_DEMO", "1")
os.environ.setdefault("PWNED_CHECK", "0")
os.environ["DATABASE_URL"] = "sqlite:///./data/test_dispatch.db"
sys.path.insert(0, os.path.dirname(__file__))
import test_round7 as R  # noqa: E402
from api import dispatch  # noqa: E402
from api.models import Order, Store, StoreItem  # noqa: E402

ADDR = {"label": "Home", "line1": "Flat 4", "line2": "Road 3", "pin": "500081", "lat": 17.4485, "lng": 78.3912}


def test_offer_hops_then_desk_then_pack_and_pickup(monkeypatch):
    monkeypatch.setattr(dispatch, "MAX_STORES", 2)
    _, ph, _ = R.stores()
    with R.DB.session() as db:
        db.get(Store, ph).delivery = True
        db.add(StoreItem(store_id=ph, sku="para500", name="Paracetamol", price=25, mrp=28, stock=9))
        b = Store(kind="pharmacy", name="MedPlus Hitech", city="Hyderabad", area="Hitech City", lat=17.452, lng=78.389, verified=True, delivery=True)
        db.add(b); db.flush(); bid = b.id
        db.add(StoreItem(store_id=bid, sku="para500", name="Paracetamol", price=25, mrp=100, stock=5))
    f, a = R.family(), R.admin()
    o = f.post("/api/v1/orders", json={"store": ph, "kind": "medicine", "items": [{"sku": "para500", "qty": 1}], "member": "P", "payment": "cod", "addr": ADDR})
    assert o.status_code == 200, o.text
    oid = o.json()["id"]
    assert o.json()["live"]["phase"] == "finding"
    with R.DB.session() as db:
        db.get(Order, oid).offered_at = 1
        assert dispatch.tick(db) == 1
        x = db.get(Order, oid)
        assert x.store_id != ph and x.tried == [ph]
        bid = x.store_id
        bname = db.get(Store, bid).name
    pb = R.partner(a, bid)
    assert pb.post(f"/api/partner/orders/{oid}/pass", json={"reason": "no_stock"}).json()["ok"]
    d = a.get("/api/admin/dispatch").json()
    row = next(u for u in d["unclaimed"] if u["id"] == oid)
    assert row["stores"] and set(row["tried"]) == {"Apollo Pharmacy", bname}
    assert any("no pharmacy" in n["title"] for n in a.get("/api/admin/console/today").json()["needs"])
    assert a.post(f"/api/admin/dispatch/{oid}/assign", json={"store": bid}).json()["ok"]
    assert next(x for x in f.get("/api/v1/orders").json()["orders"] if x["id"] == oid)["live"]["phase"] == "accepted"
    assert pb.post(f"/api/partner/orders/{oid}/pack", data={"lines": "0", "bill": "88"}).status_code == 400          # no bill photo
    ok = pb.post(f"/api/partner/orders/{oid}/pack", data={"lines": "0", "bill": "88"}, files={"billPhoto": ("b.jpg", b"\xff\xd8bill", "image/jpeg")})
    assert ok.status_code == 200, ok.text
    assert pb.post(f"/api/partner/orders/{oid}/need-rider").status_code == 200
    assert any(p["id"] == oid for p in a.get("/api/admin/dispatch").json()["pickups"])
    assert a.post(f"/api/admin/dispatch/{oid}/pickup-done").json()["ok"]
    lv = next(x for x in f.get("/api/v1/orders").json()["orders"] if x["id"] == oid)["live"]
    assert lv["phase"] == "out" and lv["etaMin"] >= 1

"""Address with a map pin, serviceability, doorstep code, partner privacy, cancel rules and the invoice."""
import os
import time

os.environ.setdefault("OTP_DEMO", "1")
os.environ.setdefault("PWNED_CHECK", "0")
os.environ["DATABASE_URL"] = "sqlite:///./data/test_booking.db"

import sys  # noqa: E402
sys.path.insert(0, os.path.dirname(__file__))
import test_round7 as R  # noqa: E402
from api import booking  # noqa: E402

FULL = {"label": "Home", "line1": "Flat 402, 4th floor", "line2": "Sri Sai Residency, Road 3", "landmark": "Opp. Ratnadeep",
        "pin": "500081", "lat": 17.4485, "lng": 78.3912, "acc": 10, "name": "Prasanna", "phone": "9876543210", "note": "Ring twice"}


def slot(hours):
    t = time.gmtime(time.time() + 19800 + hours * 3600)
    return time.strftime("%a %d %b · ", t) + time.strftime("%I:%M %p", t).lstrip("0")


def test_address_rules_and_saved_book():
    f = R.family()
    assert f.post("/api/v2/addresses", json={**FULL, "line2": ""}).status_code in (400, 422)
    assert f.post("/api/v2/addresses", json={**FULL, "pin": "12345"}).status_code in (400, 422)
    assert f.post("/api/v2/addresses", json={**FULL, "lat": 51.5, "lng": -0.1}).status_code in (400, 422)
    assert f.post("/api/v2/addresses", json={**FULL, "phone": "12345"}).status_code == 400           # not a 10-digit mobile
    assert f.post("/api/v2/addresses", json=FULL).status_code == 428                                  # a new number: code first
    code = f.post("/api/v2/addresses/phone-code", json={"phone": FULL["phone"]}).json()["demo"]
    assert f.post("/api/v2/addresses", json={**FULL, "phoneCode": "000000" if code != "000000" else "111111"}).status_code == 400
    a = f.post("/api/v2/addresses", json={**FULL, "phoneCode": code})
    assert a.status_code == 200, a.text
    assert a.json()["phone"].endswith("9876543210")
    assert [x["id"] for x in f.get("/api/v2/addresses").json()["rows"]] == [a.json()["id"]]
    assert R.family().delete(f"/api/v2/addresses/{a.json()['id']}").status_code == 404   # not someone else's


def test_home_visit_needs_pin_code_and_hides_address_until_visit_day():
    lab, ph, _ = R.stores()
    f, ad = R.family(), R.admin()
    p = R.partner(ad, lab)
    body = {"store": lab, "kind": "lab", "items": [{"code": "hba1c"}], "member": "P", "memberId": "m1", "slot": slot(50), "payment": "cod"}
    assert f.post("/api/v1/orders", json={**body, "addr": {"line1": "x"}}).status_code == 400
    far = f.post("/api/v1/orders", json={**body, "addr": {**FULL, "pin": "110001", "lat": 28.61, "lng": 77.21}})
    assert far.status_code == 409 and "visit the lab" in far.json()["detail"]
    assert f.post("/api/v1/orders", json={**body, "slot": slot(0.2), "addr": FULL}).status_code == 400
    o = f.post("/api/v1/orders", json={**body, "addr": FULL})
    assert o.status_code == 200, o.text
    o = o.json()
    assert len(o["doorCode"]) == 4
    po = next(x for x in p.get("/api/partner/orders").json()["orders"] if x["id"] == o["id"])
    assert "doorCode" not in po and po["needsCode"] and po["addrHidden"] and "Flat 402" not in str(po)
    p.post(f"/api/partner/orders/{o['id']}/status", json={"status": "confirmed", "code": ""})
    bad = p.post(f"/api/partner/orders/{o['id']}/status", json={"status": "collected", "code": "0000" if o["doorCode"] != "0000" else "1111"})
    assert bad.status_code == 400 and "doorstep code" in bad.json()["detail"]
    ok = p.post(f"/api/partner/orders/{o['id']}/status", json={"status": "collected", "code": o["doorCode"], "sample": "BC-77<x>"})
    assert ok.status_code == 200, ok.text
    assert f.get(f"/api/v1/orders/{o['id']}/track").json().get("sampleId", "BC-77x") == "BC-77x"


def test_cancel_free_early_fee_late_and_invoice():
    lab, _, _ = R.stores()
    f = R.family()
    base = {"store": lab, "kind": "lab", "items": [{"code": "hba1c"}], "member": "P", "memberId": "m1", "payment": "cod", "addr": FULL}
    early = f.post("/api/v1/orders", json={**base, "slot": slot(30)}).json()
    t = f.get(f"/api/v2/orders/{early['id']}/terms").json()
    assert t["free"] and t["canMove"]
    assert f.post(f"/api/v2/orders/{early['id']}/reschedule", json={"slot": slot(54)}).json()["ok"]
    assert f.post(f"/api/v2/orders/{early['id']}/cancel").json()["fee"] == 0
    late = f.post("/api/v1/orders", json={**base, "slot": slot(1.5)}).json()
    assert f.post(f"/api/v2/orders/{late['id']}/cancel").json()["fee"] == booking.LATE_CANCEL_FEE
    live = f.post("/api/v1/orders", json={**base, "slot": slot(40)}).json()
    assert f.get(f"/api/v2/orders/{early['id']}/invoice").status_code == 409
    assert f.get(f"/api/v2/orders/{live['id']}/invoice").status_code == 409            # not before the visit
    with R.DB.session() as db:
        db.get(booking.Order, live["id"]).status = "collected"
    inv = f.get(f"/api/v2/orders/{live['id']}/invoice")
    assert inv.status_code == 200 and "Invoice" in inv.text and live["id"] in inv.text


def test_slot_capacity_and_area_wait():
    lab, _, _ = R.stores()
    s = slot(70)
    with R.DB.session() as db:
        st = db.get(R.Store, lab)
        st.profile = {"slotCap": 1}
    f = R.family()
    base = {"store": lab, "kind": "lab", "items": [{"code": "hba1c"}], "member": "P", "memberId": "m1", "payment": "cod", "addr": FULL, "slot": s}
    assert f.post("/api/v1/orders", json=base).status_code == 200
    full = R.family().post("/api/v1/orders", json=base)
    assert full.status_code == 409 and "filled up" in full.json()["detail"]
    sv = f.get("/api/v2/serviceable?pin=110001&lat=28.61&lng=77.21").json()
    assert not sv["labs"]
    assert f.post("/api/v2/area-wait", json={"pin": "110001", "kind": "lab"}).status_code == 200


def test_admin_setup_funnel_email_and_stuck():
    a = R.admin()
    su = a.get("/api/admin/console/setup").json()
    assert su["total"] >= 10 and any(i["key"] == "ai" for i in su["items"])
    assert [x["name"] for x in a.get("/api/admin/console/funnel").json()["steps"]][0] == "Opened lab tests"
    assert a.put("/api/admin/me/email", json={"email": "new@urbanhealth.in", "password": "bad"}).status_code == 403
    import uuid
    em = f"x{uuid.uuid4().hex[:6]}@urbanhealth.in"
    assert a.put("/api/admin/me/email", json={"email": em, "password": "Adm!n-pass-123"}).json()["email"] == em
    lab, _, _ = R.stores()
    f = R.family()
    o = f.post("/api/v1/orders", json={"store": lab, "kind": "lab", "items": [{"code": "hba1c"}], "member": "P", "memberId": "m1", "payment": "cod", "addr": FULL, "slot": slot(60)}).json()
    with R.DB.session() as db:
        x = db.get(booking.Order, o["id"])
        x.created = x.created - 3 * 86400
        x.timeline = [{"s": "placed", "t": x.created}]
    t = a.get("/api/admin/console/today").json()
    assert any("stuck" in n["title"] for n in t["needs"])
    card = next(c for c in sum(a.get("/api/admin/console/board").json()["lanes"].values(), []) if c["id"] == o["id"])
    assert card["stuck"] >= 3 and card["late"] == 0

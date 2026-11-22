"""Returns, exchanges and refunds for hospital bag orders follow the customer policy at /hospital-bag/policies:
7 days for unused items, hygiene items only while sealed, damaged or wrong within 48 hours with a photo, one free size
exchange, refunds the way the family paid or to their UPI ID, and the team works each request in Admin → Orders."""
import base64
import os

os.environ.setdefault("OTP_DEMO", "1")
os.environ.setdefault("PWNED_CHECK", "0")
os.environ["DATABASE_URL"] = "sqlite:///./data/test_bag.db"

from fastapi.testclient import TestClient  # noqa: E402

import server  # noqa: E402
from api import bagreturns, bagshop  # noqa: E402
from api import db as DB  # noqa: E402
from api.models import BagItem, Notice, Order, now  # noqa: E402
from tests.test_bag_checkout import body, family  # noqa: E402
from tests.test_round7 import admin as _admin  # noqa: E402

# the smallest real JPEG: a 1×1 white pixel
JPEG = "data:image/jpeg;base64," + base64.b64encode(bytes.fromhex(
    "ffd8ffe000104a46494600010100000100010000ffdb004300080606070605080707070909080a0c140d0c0b0b0c1912130f141d1a1f1e1d1a1c1c20242e2720"
    "222c231c1c2837292c30313434341f27393d38323c2e333432ffc0000b080001000101011100ffc4001f0000010501010101010100000000000000000102030405"
    "060708090a0bffc400b5100002010303020403050504040000017d01020300041105122131410613516107227114328191a1082342b1c11552d1f02433627282090a"
    "161718191a25262728292a3435363738393a434445464748494a535455565758595a636465666768696a737475767778797a838485868788898a92939495969798"
    "999aa2a3a4a5a6a7a8a9aab2b3b4b5b6b7b8b9bac2c3c4c5c6c7c8c9cad2d3d4d5d6d7d8d9dae1e2e3e4e5e6e7e8e9eaf1f2f3f4f5f6f7f8f9faffda0008010100"
    "003f00fbd3ffd9")).decode()


def admin():
    a = _admin()
    a.headers["x-tht"] = "1"
    return a


def bag(f, deliver_ago=86400, **kw):
    """A complete bag, delivered deliver_ago seconds ago."""
    o = f.post("/api/v1/shop/bag/order", json=body(**kw)).json()["order"]
    with DB.session() as db:
        x = db.get(Order, o["id"])
        x.status = "delivered"
        x.timeline = list(x.timeline or []) + [{"s": "delivered", "t": now() - deliver_ago}]
        x.eta = now() - deliver_ago + 3600   # on time
    return o["id"]


def ask(f, oid, **kw):
    b = {"reason": "not_needed", "lines": [{"sku": "hb-mm-towel", "qty": 1}], "unused": True, "upi": "priya@okaxis"}
    b.update(kw)
    return f.post(f"/api/v1/shop/bag/orders/{oid}/return", json=b)


def test_the_policy_page_is_public_and_filled_in():
    c = TestClient(server.app)
    c.__enter__()   # tables are created on startup
    r = c.get("/hospital-bag/policies")
    assert r.status_code == 200
    t = r.text
    assert "{{" not in t and "support@urbanhealth.in" in t
    for h in ("Returns and exchanges", "Refunds", "Cancellations", "Delivery", "Damaged, faulty or wrong items", "Warranty", "Payment", "Prices",
              "Product information", "Your information", "Questions and complaints", "Seller"):
        assert f">{h}</h2>" in t, h
    for p in ("/returns", "/refund-policy", "/cancellation-policy", "/shipping-policy"):
        r = c.get(p, follow_redirects=False)
        assert r.status_code == 301 and r.headers["location"].startswith("/hospital-bag/policies#"), p
    assert "/hospital-bag/policies" in c.get("/sitemap.xml").text
    # the same short policy everywhere: checkout, the page's questions and the API
    info = c.get("/api/v1/shop/bag").json()
    assert info["policyUrl"] == "/hospital-bag/policies" and any("7 days" in p for p in info["policy"])


def test_a_return_before_delivery_is_not_offered_but_cancelling_is():
    f = family()
    o = f.post("/api/v1/shop/bag/order", json=body()).json()["order"]
    assert o["ret"]["can"] is False
    assert f.get(f"/api/v1/shop/bag/orders/{o['id']}/return").json()["why"].startswith("You can ask for a return once")
    t = f.get(f"/api/v2/orders/{o['id']}/terms").json()
    assert t["can"] and t["free"] and t["why"] == "Free until we pack your bag."
    with DB.session() as db:
        db.get(Order, o["id"]).status = "packing"
    t = f.get(f"/api/v2/orders/{o['id']}/terms").json()
    assert not t["can"] and "packed your bag" in t["why"]
    assert f.post(f"/api/v2/orders/{o['id']}/cancel").status_code == 409


def test_return_for_a_refund_to_upi_then_the_team_refunds_it():
    f, a = family(), admin()
    oid = bag(f)
    opt = f.get(f"/api/v1/shop/bag/orders/{oid}/return").json()
    assert opt["can"] and opt["pay"] == "cod"
    assert [x["k"] for x in opt["reasons"]] == ["size", "damaged", "wrong", "not_needed"]   # on time, so no "late"
    assert all(x["sku"] != "hb-uh-card" for x in opt["lines"])   # the free card has nothing to refund
    # unused has to be confirmed, a UPI ID is needed for a pay-on-delivery refund, and only what was bought comes back
    assert ask(f, oid, unused=False).status_code == 400
    assert ask(f, oid, upi="").status_code == 400
    assert ask(f, oid, upi="9876543210").status_code == 400
    assert ask(f, oid, lines=[{"sku": "hb-mm-towel", "qty": 3}]).status_code == 400
    assert ask(f, oid, lines=[{"sku": "hb-xx", "qty": 1}]).status_code == 400
    r = ask(f, oid, lines=[{"sku": "hb-mm-towel", "qty": 2}, {"sku": "hb-mm-bag", "qty": 1}], note="Gift from family <b>")
    assert r.status_code == 200, r.text
    o = r.json()["order"]
    assert o["status"] == "return_requested"
    op = o["ret"]["open"]
    assert op["state"] == "requested" and op["refund"] == 2 * 559 + 1399 and op["to"] == "upi" and op["upi"] == "priya@okaxis"
    assert not o["ret"]["can"]
    assert ask(f, oid).status_code == 409   # one open request at a time
    # the team sees it, marks it received and records the refund; the family hears about each step
    rows = a.get("/api/admin/orders/returns").json()["returns"]
    card = next(c for c in rows if c["id"] == oid)
    assert card["req"]["refund"] == 2517 and card["req"]["upi"] == "priya@okaxis" and "<b>" not in card["req"]["note"]
    assert a.post(f"/api/admin/orders/{oid}/return/received").json()["status"] == "returned"
    r = a.post(f"/api/admin/orders/{oid}/refund", json={"amount": 2517, "reason": "Return: No longer needed", "method": "upi", "ref": "UTR 4321-77"})
    assert r.status_code == 200, r.text
    o = next(x for x in f.get("/api/v1/orders").json()["orders"] if x["id"] == oid)
    assert o["status"] == "refunded" and o["ret"]["open"]["state"] == "refunded" and o["ret"]["refunded"] == 2517
    with DB.session() as db:
        titles = [n.title for n in db.query(Notice).filter(Notice.household_id == db.get(Order, oid).household_id).all()]
        tl = db.get(Order, oid).timeline
    assert any(t.startswith("Return requested") for t in titles) and any(t.startswith("We've received your return") for t in titles)
    assert any(t.startswith("Refund of ₹2,517 sent") for t in titles)
    assert tl[-1]["ref"] == "UTR4321-77" and tl[-1]["method"] == "upi"
    # what came back can't be asked for twice, and the refunds can't add up to more than was paid
    opt = f.get(f"/api/v1/shop/bag/orders/{oid}/return").json()
    assert next(x for x in opt["lines"] if x["sku"] == "hb-mm-towel")["qty"] == 0
    assert a.post(f"/api/admin/orders/{oid}/refund", json={"amount": 11890, "reason": "too much"}).status_code == 400


def test_hygiene_items_only_sealed_and_damaged_needs_a_photo_within_48_hours():
    f = family()
    oid = bag(f)
    # an opened nursing bra can't come back as "no longer needed" without confirming it is sealed
    r = ask(f, oid, lines=[{"sku": "hb-mm-bra", "qty": 1}], unused=False)
    assert r.status_code == 400 and "sealed" in r.json()["detail"]
    # damaged: a photo is needed, and then a replacement or a refund
    assert ask(f, oid, reason="damaged", lines=[{"sku": "hb-ps-pads", "qty": 1}], unused=False).status_code == 400
    assert ask(f, oid, reason="damaged", lines=[{"sku": "hb-ps-pads", "qty": 1}], photos=["data:image/jpeg;base64,AAAA"]).status_code == 400
    r = ask(f, oid, reason="damaged", want="replace", lines=[{"sku": "hb-ps-pads", "qty": 1}], unused=False, upi="", photos=[JPEG])
    assert r.status_code == 200, r.text
    op = r.json()["order"]["ret"]["open"]
    assert op["kind"] == "replace" and op["refund"] == 0
    a = admin()
    card = next(c for c in a.get("/api/admin/orders/returns").json()["returns"] if c["id"] == oid)
    assert card["req"]["photos"] == 1
    ph = a.get(f"/api/admin/orders/{oid}/return/photo/0")
    assert ph.status_code == 200 and ph.headers["content-type"] == "image/jpeg"
    assert f.get(f"/api/admin/orders/{oid}/return/photo/0").status_code in (401, 403)
    assert a.post(f"/api/admin/orders/{oid}/return/exchange", json={}).json()["status"] == "delivered"
    # after 48 hours, damaged and wrong are no longer offered, with a kind way forward
    g = family()
    late = bag(g, deliver_ago=3 * 86400)
    opt = g.get(f"/api/v1/shop/bag/orders/{late}/return").json()
    assert "damaged" not in [x["k"] for x in opt["reasons"]]
    r = ask(g, late, reason="damaged", lines=[{"sku": "hb-ps-pads", "qty": 1}], photos=[JPEG])
    assert r.status_code == 409 and "48 hours" in r.json()["detail"]
    # after 7 days, nothing
    h = family()
    old = bag(h, deliver_ago=8 * 86400)
    assert h.get(f"/api/v1/shop/bag/orders/{old}/return").json()["can"] is False
    assert ask(h, old).status_code == 409


def test_size_exchange_once_and_only_while_in_stock_then_decline_is_explained():
    f, a = family(), admin()
    oid = bag(f)
    with DB.session() as db:
        db.get(BagItem, "mm-bra").stock = {"S": None, "M": 0, "L": None, "XL": 4}
    assert ask(f, oid, reason="size", lines=[{"sku": "hb-mm-towel", "qty": 1}]).status_code == 400   # one size
    assert ask(f, oid, reason="size", lines=[{"sku": "hb-mm-bra", "qty": 1, "to": "L"}]).status_code == 400   # already L
    r = ask(f, oid, reason="size", lines=[{"sku": "hb-mm-bra", "qty": 1, "to": "M"}])
    assert r.status_code == 409 and "out of stock" in r.json()["detail"]
    r = ask(f, oid, reason="size", lines=[{"sku": "hb-mm-bra", "qty": 1, "to": "XL"}])
    assert r.status_code == 200, r.text
    assert a.post(f"/api/admin/orders/{oid}/return/exchange", json={}).status_code == 200
    with DB.session() as db:
        assert db.get(BagItem, "mm-bra").stock["XL"] == 3
    # once only
    r = ask(f, oid, reason="size", lines=[{"sku": "hb-mm-bra", "qty": 1, "to": "XL"}])
    assert r.status_code == 400 or r.status_code == 409
    # a declined request tells the family why, and its items can be asked for again
    r = ask(f, oid, lines=[{"sku": "hb-mm-nest", "qty": 1}])
    assert r.status_code == 200
    assert a.post(f"/api/admin/orders/{oid}/return/decline", json={"why": "short"}).status_code == 400
    o = a.post(f"/api/admin/orders/{oid}/return/decline", json={"why": "The carry nest we collected had been used, so we've sent it back to you."}).json()
    assert o["status"] == "delivered" and o["ret"]["open"]["state"] == "declined" and "used" in o["ret"]["open"]["why"]
    assert next(x for x in f.get(f"/api/v1/shop/bag/orders/{oid}/return").json()["lines"] if x["sku"] == "hb-mm-nest")["qty"] == 1


def test_late_delivery_and_online_refunds_go_back_the_way_they_came():
    f = family()
    oid = bag(f)
    with DB.session() as db:
        x = db.get(Order, oid)
        x.eta = now() - 3 * 86400   # promised two days before it came
        x.payment = "online-paid"
    opt = f.get(f"/api/v1/shop/bag/orders/{oid}/return").json()
    assert "late" in [x["k"] for x in opt["reasons"]] and opt["pay"] == "online"
    r = ask(f, oid, reason="late", upi="", lines=[{"sku": "hb-mm-swad", "qty": 1}])
    assert r.status_code == 200, r.text
    assert r.json()["order"]["ret"]["open"]["to"] == "original"
    # someone else's order is not found
    assert ask(family(), oid).status_code == 404


def test_cancelled_after_paying_online_shows_as_refund_due():
    f, a = family(), admin()
    o = f.post("/api/v1/shop/bag/order", json=body()).json()["order"]
    with DB.session() as db:
        db.get(Order, o["id"]).payment = "online-paid"
    assert f.post(f"/api/v2/orders/{o['id']}/cancel").status_code == 200
    due = [c for c in a.get("/api/admin/orders/returns").json()["refunds"] if c["id"] == o["id"]]
    assert due and due[0]["due"] == 8314
    # over ₹5,000, a second admin approves it; once approved, the family is told and it leaves the list
    r = a.post(f"/api/admin/orders/{o['id']}/refund", json={"amount": 8314, "reason": "Cancelled before packing", "method": "razorpay", "ref": "rfnd_ABC123"}).json()
    assert r.get("approval")
    b = admin()
    assert b.post(f"/api/admin/approvals/{r['approval']}", json={"approve": True}).status_code == 200
    assert not [c for c in a.get("/api/admin/orders/returns").json()["refunds"] if c["id"] == o["id"]]
    with DB.session() as db:
        last = db.get(Order, o["id"]).timeline[-1]
    assert (last["s"], last["amount"], last["method"], last["ref"]) == ("refunded", 8314, "razorpay", "rfnd_ABC123")


def test_unit_refund_counts_the_bag_price_first():
    ln = {"price": 1000, "bag": 1}
    old = bagshop.BAG_RATE
    try:
        bagshop.BAG_RATE = .9
        assert bagreturns.unit_refund(ln, 1) == 900 and bagreturns.unit_refund(ln, 2) == 1900
    finally:
        bagshop.BAG_RATE = old

"""The hospital bag page orders a real bag: Urban Health sign-in, prices from the server's own list (which must match
the page), an ordinary shop order the family sees in the app, Razorpay or pay on delivery, and no double orders.
Every item is a Mee Mee, SuperBottoms or Pee Safe product at the brand's own price, plus a free emergency card."""
import json
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

os.environ.setdefault("OTP_DEMO", "1")
os.environ.setdefault("PWNED_CHECK", "0")
os.environ["DATABASE_URL"] = "sqlite:///./data/test_bag.db"

from fastapi.testclient import TestClient  # noqa: E402

import server  # noqa: E402
from api import bagshop  # noqa: E402
from api import db as DB  # noqa: E402
from api import payments as RZ  # noqa: E402
from api.models import BagItem, Order, SavedAddress  # noqa: E402
from tests.test_round7 import admin  # noqa: E402
from tests.test_round7 import family as _family  # noqa: E402

PAGE = Path(__file__).resolve().parents[1] / "site" / "home" / "bag.html"
IST = timezone(timedelta(hours=5, minutes=30))
COMPLETE = {b[0]: b[4] for b in bagshop.BAG if b[5]}
ADDR = {"name": "Priya Raman", "phone": "9876543210", "line1": "12B", "line2": "Lake View Apartments, Anna Nagar", "city": "Chennai", "state": "Tamil Nadu", "pin": "600040"}


def family():
    c = _family()
    c.headers["x-tht"] = "1"
    return c


def day(n=6):
    return (datetime.now(IST).date() + timedelta(days=n)).isoformat()


def body(**kw):
    b = {"items": dict(COMPLETE), "opts": {"sb-jhabla": "3–6 m", "mm-bra": "L"}, "twins": False, "deliverOn": day(), "addr": dict(ADDR), "payment": "cod", "token": os.urandom(6).hex()}
    b.update(kw)
    return b


def test_page_lists_the_same_items_and_prices_as_the_server():
    html = PAGE.read_text(encoding="utf-8")
    rows = re.findall(r'\["([\w-]+)","([mbd])","([^"]+)","[^"]*",(\d+),(\d+),"[^"]*","[^"]*",([01]),"[^"]*",(null|\[[^\]]*\]),"[^"]*","([^"]+)"\]', html)
    assert len(rows) == len(bagshop.BAG)
    for (iid, grp, name, price, d, inb, opts, brand), b in zip(rows, bagshop.BAG):
        assert (iid, grp, name, int(price), int(d), inb == "1", None if opts == "null" else json.loads(opts)) == b[:7], iid
        assert brand == bagshop.brand(iid), iid
    # the "from home" list on the page is the one the account keeps
    assert all(k in html for k in bagshop.HOME_ITEMS)


def test_prices():
    q = bagshop.price_bag(COMPLETE)
    # every item at least 30% below its brand's own price, rounded down to the rupee; the bag is the plain sum
    assert (q["full"], q["total"], q["save"], q["units"], q["off"]) == (11890, 8314, 3576, 23, 30)
    for ln in q["lines"]:
        lst = bagshop.BY_ID[ln["sku"][3:]][3]
        assert ln["list"] == lst and ln["price"] == lst * 70 // 100 and (lst == 0 or (lst - ln["price"]) / lst >= .30) and ln["off"] == bagshop.pct_off(lst, ln["price"])
    assert sum(ln["qty"] * ln["price"] for ln in q["lines"]) == q["total"] and sum(ln["qty"] * ln["list"] for ln in q["lines"]) == q["full"]
    assert {ln["brand"] for ln in q["lines"]} == {"Mee Mee", "SuperBottoms", "Pee Safe", "Urban Health"}
    assert any(ln["name"] == "Nursing bra (Mee Mee) · S" for ln in q["lines"])
    # an extra and an add-on are their own price; the free emergency card comes once
    assert bagshop.price_bag({**COMPLETE, "mm-bra": 3})["total"] == 8314 + 524
    assert bagshop.price_bag({**COMPLETE, "mm-belt": 1})["total"] == 8314 + 559
    card = bagshop.price_bag({"uh-card": 5})
    assert card["lines"][0]["qty"] == 1 and card["total"] == 0
    # with a bag saving switched on, baby items stay at the bag price up to twice the usual count for twins
    old = bagshop.BAG_RATE
    try:
        bagshop.BAG_RATE = .9
        twins = {k: v * 2 if bagshop.BY_ID[k][1] == "b" else v for k, v in COMPLETE.items()}
        t = bagshop.price_bag(twins, twins=True)
        assert t["total"] == round(sum(ln["qty"] * ln["price"] for ln in t["lines"]) * .9)
        assert bagshop.price_bag(twins)["total"] > t["total"]
    finally:
        bagshop.BAG_RATE = old
    # the browser can't name a size that isn't sold, or more than 20 of anything
    q = bagshop.price_bag({"mm-bra": 99}, opts={"mm-bra": "XXXL"})
    assert q["lines"][0]["qty"] == 20 and q["lines"][0]["opt"] == "S"


def test_sign_in_is_required_and_the_order_lands_in_the_family_orders():
    anon = TestClient(server.app)
    anon.__enter__()
    info = anon.get("/api/v1/shop/bag").json()
    assert info["items"][0]["id"] == "mm-bra" and info["items"][0]["brand"] == "Mee Mee" and info["rate"] == 1.0
    assert [k for k, _ in info["home"]][:4] == ["mcp", "scan", "idp", "ins"]
    assert anon.post("/api/v1/shop/bag/order", headers={"x-tht": "1"}, json=body()).status_code == 401
    f = family()
    assert f.post("/api/v1/shop/bag/order", json=body(), headers={"x-tht": ""}).status_code == 403   # CSRF header
    r = f.post("/api/v1/shop/bag/order", json=body(bill={"same": False, "name": "Ravi Raman", "line": "Plot 4, Sector 2, Chennai 600040"}))
    assert r.status_code == 200, r.text
    j = r.json()
    o = j["order"]
    assert o["kind"] == "shop" and (o["total"], o["subtotal"], o["discount"]) == (8314, 11890, 3576) and o["payment"] == "cod" and o["status"] == "placed"
    assert j["key"] == f.headers["X-DoKKo-Key"]
    assert any(ln["name"] == "Mulmul jhablas (SuperBottoms) · 3–6 m" and ln["qty"] == 6 for ln in o["items"])
    assert o["addr"]["phone"] == "+919876543210" and o["addr"]["bill"]["name"] == "Ravi Raman"
    assert [x["id"] for x in f.get("/api/v1/orders").json()["orders"]][:1] == [o["id"]]
    pdf = f.get(f"/api/v1/orders/{o['id']}/receipt.pdf")
    assert pdf.status_code == 200 and pdf.content[:4] == b"%PDF"
    # the receipt adds up: lines at the brand's price, the offer as one line, then the total
    import pymupdf
    text = "".join(pg.get_text() for pg in pymupdf.open(stream=pdf.content, filetype="pdf"))
    assert "Offer: 30% off brand prices" in text and "11,890" in text and "3,576" in text and "8,314" in text


def test_double_tap_makes_one_order_and_bad_input_is_refused():
    f = family()
    b = body()
    a1, a2 = f.post("/api/v1/shop/bag/order", json=b).json(), f.post("/api/v1/shop/bag/order", json=b).json()
    assert a1["order"]["id"] == a2["order"]["id"] and a2.get("again")
    assert f.post("/api/v1/shop/bag/order", json=body(items={})).status_code == 400
    assert f.post("/api/v1/shop/bag/order", json=body(items={"uh-card": 1})).status_code == 400   # the free card alone isn't an order
    assert f.post("/api/v1/shop/bag/order", json=body(deliverOn=day(1))).status_code == 400
    assert f.post("/api/v1/shop/bag/order", json=body(addr={**ADDR, "pin": "12345"})).status_code == 400
    assert f.post("/api/v1/shop/bag/order", json=body(addr={**ADDR, "phone": "12345"})).status_code == 400
    assert f.post("/api/v1/shop/bag/order", json=body(payment="upi")).status_code == 400
    assert f.post("/api/v1/shop/bag/order", json=body(payment="online")).status_code == 400   # Razorpay is off
    # someone else's saved address can't be used
    with DB.session() as db:
        other = SavedAddress(household_id="h_someone_else", label="Home", line1="1", line2="Street", city="Pune", pin="411001", lat=18.5, lng=73.8, name="X", phone="+919999999999")
        db.add(other)
        db.flush()
        aid = other.id
    assert f.post("/api/v1/shop/bag/order", json=body(addr={"id": aid})).status_code == 400


def test_pay_online_with_razorpay_or_switch_to_pay_on_delivery(monkeypatch):
    monkeypatch.setenv("RAZORPAY_KEY_ID", "rzp_test_abc")
    monkeypatch.setenv("RAZORPAY_KEY_SECRET", "sekret")
    monkeypatch.setattr(RZ, "create_order", lambda amount, receipt: {"keyId": "rzp_test_abc", "orderId": "order_bag1", "amount": amount * 100, "currency": "INR"})
    f = family()
    assert f.get("/api/v1/shop/bag").json()["online"] is True
    j = f.post("/api/v1/shop/bag/order", json=body(payment="online")).json()
    oid = j["order"]["id"]
    st = f.post("/api/v1/pay/online/start", json={"kind": "order", "orderId": oid}, headers={"x-dokko-key": j["key"]}).json()
    assert st["amount"] == 8314 * 100 and st["orderId"] == "order_bag1"
    # the family closes the Razorpay window and pays when the bag arrives instead
    assert f.post(f"/api/v1/shop/bag/orders/{oid}/cod").json()["order"]["payment"] == "cod"
    with DB.session() as db:
        assert db.get(Order, oid).payment == "cod"
    assert TestClient(server.app).post(f"/api/v1/shop/bag/orders/{oid}/cod", headers={"x-tht": "1"}).status_code == 401


def _reset_bag():
    with DB.session() as db:
        for x in db.query(BagItem).all():
            b = bagshop.BY_ID[x.id]
            x.price, x.active, x.stock = b[3], True, {k: None for k in bagshop._keys(b)}


def test_the_team_sets_prices_and_stock_and_the_shop_keeps_to_them():
    _reset_bag()
    a, f = admin(), family()
    items = a.get("/api/admin/products/bag/items").json()
    assert items["complete"] == {"total": 8314, "full": 11890, "off": 30} and items["rate"] == 1.0 and items["offPct"] == 30
    # a price above the offer ceiling is refused, with the ceiling in the message
    r = a.put("/api/admin/products/bag/items", json={"items": [{"id": "mm-bra", "price": 525, "active": True, "stock": {}}]})
    assert r.status_code == 400 and "₹524 or less" in r.json()["detail"]
    bra = next(x for x in items["items"] if x["id"] == "mm-bra")
    assert bra["stock"] == {"S": None, "M": None, "L": None, "XL": None}   # not counted until the team says
    r = a.put("/api/admin/products/bag/items", json={"items": [{"id": "mm-bra", "price": 249, "active": True, "stock": {"S": 5, "M": 2, "L": 0, "XL": None}},
                                                              {"id": "mm-belt", "price": 559, "active": False, "stock": {}}]})
    assert r.status_code == 200, r.text
    info = f.get("/api/v1/shop/bag").json()
    bra = next(x for x in info["items"] if x["id"] == "mm-bra")
    assert bra["price"] == 249 and bra["stock"]["L"] == 0 and bra["stock"]["XL"] is None
    assert next(x for x in info["items"] if x["id"] == "mm-belt")["active"] is False
    assert info["policy"][0].startswith("Cancel free")
    # the new price is what the order charges
    o = f.post("/api/v1/shop/bag/order", json=body(opts={"mm-bra": "M"})).json()["order"]
    assert o["total"] == bagshop.price_bag(COMPLETE, prices={"mm-bra": 249})["total"]
    with DB.session() as db:
        assert db.get(BagItem, "mm-bra").stock["M"] == 0
    # sold out, too few left, and switched off are all refused with a plain reason
    r = f.post("/api/v1/shop/bag/order", json=body(opts={"mm-bra": "M"}))
    assert r.status_code == 409 and "sold out" in r.json()["detail"]
    r = f.post("/api/v1/shop/bag/order", json=body(items={**COMPLETE, "mm-bra": 6}, opts={"mm-bra": "S"}))
    assert r.status_code == 409 and "Only 5 left" in r.json()["detail"]
    r = f.post("/api/v1/shop/bag/order", json=body(items={**COMPLETE, "mm-belt": 1}, opts={"mm-bra": "XL"}))
    assert r.status_code == 409 and "isn't available" in r.json()["detail"]
    # cancelling puts the stock back, once
    assert f.post(f"/api/v1/orders/{o['id']}/cancel").status_code == 200
    assert f.post(f"/api/v1/orders/{o['id']}/cancel").status_code in (200, 409)
    with DB.session() as db:
        assert db.get(BagItem, "mm-bra").stock["M"] == 2
    # a content admin can edit; a bad price is refused
    assert a.put("/api/admin/products/bag/items", json={"items": [{"id": "mm-bra", "price": 0, "stock": {}}]}).status_code == 400
    # the free emergency card can stay at ₹0
    assert a.put("/api/admin/products/bag/items", json={"items": [{"id": "uh-card", "price": 0, "active": True, "stock": {"": None}}]}).status_code == 200
    assert TestClient(server.app).get("/api/admin/products/bag/items").status_code == 401
    _reset_bag()


def test_packing_list_is_kept_with_the_account_and_reminds_at_weeks_34_and_36():
    from api.models import ReminderSent  # noqa: F401
    f = family()
    assert TestClient(server.app).get("/api/v1/shop/bag/checklist").status_code == 401
    o = f.post("/api/v1/shop/bag/order", json=body()).json()["order"]
    due = datetime.now(IST).date() + timedelta(days=50)
    r = f.put("/api/v1/shop/bag/checklist", json={"packed": {"mm-bra": True, "mcp": True, "h-nighty": True, "evil<script>": True}, "remind": True, "due": due.isoformat()})
    assert r.status_code == 200, r.text
    c = r.json()
    assert c["packed"] == {"mm-bra": True, "mcp": True, "h-nighty": True} and c["order"] == o["id"]
    assert [x["week"] for x in c["remind"]] == [34, 36] and c["remind"][0]["on"] == (due - timedelta(days=42)).isoformat()
    assert any(x["id"] == "sb-jhabla" and x["qty"] == 6 for x in c["items"])
    # the due date itself is not kept
    assert "due" not in json.dumps(f.get("/api/v1/shop/bag/checklist").json())
    with DB.session() as db:
        on = due - timedelta(days=42)
        assert bagshop.send_reminders(db, on - timedelta(days=1)) == 0
        sent = bagshop.send_reminders(db, on)
        assert sent >= 1
        assert bagshop.send_reminders(db, on) == 0          # once
        assert bagshop.send_reminders(db, on + timedelta(days=14)) >= 1   # week 36
    kinds = [n for n in f.get("/api/v1/inbox").json()["notices"] if n["kind"] == "bag_reminder"]
    assert any("Week 34" in n["title"] for n in kinds) and any("Week 36" in n["title"] for n in kinds)
    assert f.put("/api/v1/shop/bag/checklist", json={"packed": {}, "remind": False}).json()["remind"] == []


def test_returns_and_receipt_follow_the_shop_policy():
    f = family()
    o = f.post("/api/v1/shop/bag/order", json=body()).json()["order"]
    # opened hygiene items only come back if damaged or wrong
    r = f.post(f"/api/v1/orders/{o['id']}/return", json={"reason": "not_needed", "items": ["hb-ps-pads", "hb-ps-undies"]})
    assert r.status_code == 400 and "Hygiene" in r.json()["detail"]
    # the 7 days run from delivery: an order placed weeks earlier can still be returned after it arrives
    with DB.session() as db:
        row = db.get(Order, o["id"])
        row.created -= 40 * 86400
        row.timeline = (row.timeline or []) + [{"s": "delivered", "t": int(datetime.now().timestamp()) - 86400}]
    assert f.post(f"/api/v1/orders/{o['id']}/return", json={"reason": "not_needed", "items": ["hb-mm-towel"]}).status_code == 200
    import pymupdf
    o2 = f.post("/api/v1/shop/bag/order", json=body()).json()["order"]
    text = pymupdf.open(stream=f.get(f"/api/v1/orders/{o2['id']}/receipt.pdf").content, filetype="pdf")[0].get_text()
    assert "Sold and shipped by Urban Health" in text and "medicines" not in text
    assert "hygiene" not in f.get("/api/v1/returns/policy").json()["medicines"][0].lower()
    assert f.get("/api/v1/returns/policy").json()["shop"] == bagshop.POLICY


def test_one_bag_live_price_and_packing_slip():
    import pymupdf
    f, a = family(), admin()
    info = f.get("/api/v1/shop/bag").json()
    assert info["complete"] == {"total": 8314, "full": 11890, "units": 23, "save": 3576, "off": 30}
    # the old in-app package is off sale, and can't be ordered around the listing either
    assert all(x["sku"] != "bag-complete" for x in f.get("/api/v1/shop/products").json()["products"])
    assert f.post("/api/v1/orders", json={"store": "s_tht_shop", "kind": "medicine", "items": [{"sku": "bag-complete", "qty": 1}], "address": "12 Road, Hyderabad",
                                          "member": "P", "payment": "cod"}).status_code == 400
    # the landing page and the app point at the one bag
    root = PAGE.parents[2]
    assert 'id="bagBuy"' in (root / "site/home/index.html").read_text(encoding="utf-8") and "/api/v1/shop/bag" in (root / "site/home/index.html").read_text(encoding="utf-8")
    assert 'href="/hospital-bag#build"' in (root / "web/uh.html").read_text(encoding="utf-8")
    assert "₹" not in PAGE.read_text(encoding="utf-8").split("</head>")[0]   # no fixed price in the page's description
    # a packing slip: items with sizes, the day, the address and the cash to collect, and no prices
    o = f.post("/api/v1/shop/bag/order", json=body(opts={"sb-jhabla": "0–3 m", "ps-undies": "XL–XXL"})).json()["order"]
    r = a.get(f"/api/admin/orders/{o['id']}/slip.pdf")
    assert r.status_code == 200 and r.content[:4] == b"%PDF"
    text = "\n".join(pg.get_text() for pg in pymupdf.open(stream=r.content, filetype="pdf"))
    assert "PACKING SLIP" in text and f"UH-{o['id']}" in text and "Priya Raman" in text and "600040" in text
    assert "Mulmul jhablas (SuperBottoms) · 0-3 m" in text and "Disposable underwear (Pee Safe) · XL-XXL" in text and "Collect Rs. 8,314" in text
    assert "Rs. 749" not in text and "Packed by" in text
    assert TestClient(server.app).get(f"/api/admin/orders/{o['id']}/slip.pdf").status_code == 401

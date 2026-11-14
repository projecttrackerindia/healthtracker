"""Online payment is Razorpay only: the amount comes from our database, the signature decides, the webhook and the
redirect can both arrive without paying twice, and no personal UPI ID ships in the code or is shown by default."""
import hashlib
import hmac
import json
import os
from pathlib import Path

os.environ.setdefault("OTP_DEMO", "1")
os.environ.setdefault("PWNED_CHECK", "0")
os.environ["DATABASE_URL"] = "sqlite:///./data/test_rzp.db"

from tests.test_round7 import family as _family  # noqa: E402
from api import payments as RZ  # noqa: E402
from api import db as DB  # noqa: E402
from api.models import Order, Payment  # noqa: E402


def family():
    c = _family()
    c.headers["x-tht"] = "1"
    return c


def _on(monkeypatch):
    monkeypatch.setenv("RAZORPAY_KEY_ID", "rzp_test_abc")
    monkeypatch.setenv("RAZORPAY_KEY_SECRET", "sekret")
    monkeypatch.setenv("RAZORPAY_WEBHOOK_SECRET", "hooksekret")
    made = []

    def fake(amount, receipt):
        made.append((amount, receipt))
        return {"keyId": "rzp_test_abc", "orderId": f"order_{receipt[-10:]}{len(made)}", "amount": amount * 100, "currency": "INR"}
    monkeypatch.setattr(RZ, "create_order", fake)
    return made


def _order(f):
    sp = f.get("/api/v1/shop/products").json()["products"][0]
    return f.post("/api/v1/orders", json={"store": "s_tht_shop", "kind": "medicine", "items": [{"sku": sp["sku"], "qty": 1, "size": "M"}],
                                          "address": "4 Beach Rd, Chennai - 600021", "member": "K", "payment": "online"}).json()


def test_no_personal_upi_in_code_or_by_default(monkeypatch):
    monkeypatch.delenv("UPI_PAY", raising=False)
    monkeypatch.delenv("UPI_ACCOUNTS", raising=False)
    assert not Path("api/data/upi.json").exists()
    f = family()
    assert f.get("/api/v1/pay/upi/accounts").json() == {"enabled": False, "accounts": []}
    assert f.post("/api/v1/pay/upi/start", json={"kind": "plan", "plan": "family"}).status_code == 503
    monkeypatch.setenv("UPI_ACCOUNTS", '[{"id":"x","vpa":"biz@ybl"}]')     # accounts alone do not switch it on
    assert f.post("/api/v1/pay/upi/start", json={"kind": "plan", "plan": "family"}).status_code == 503


def test_online_refused_without_razorpay(monkeypatch):
    monkeypatch.delenv("RAZORPAY_KEY_ID", raising=False)
    f = family()
    assert f.get("/api/v1/config").json()["payments"] == "door"
    sp = f.get("/api/v1/shop/products").json()["products"][0]
    r = f.post("/api/v1/orders", json={"store": "s_tht_shop", "kind": "medicine", "items": [{"sku": sp["sku"], "qty": 1}], "address": "x", "member": "K", "payment": "online"})
    assert r.status_code == 400
    assert f.post("/api/v1/pay/online/start", json={"kind": "order", "orderId": "X"}).status_code == 503


def test_order_paid_by_signature_once(monkeypatch):
    made = _on(monkeypatch)
    f = family()
    assert f.get("/api/v1/config").json()["payments"] == "razorpay"
    o = _order(f)
    st = f.post("/api/v1/pay/online/start", json={"kind": "order", "orderId": o["id"]}).json()
    assert st["amount"] == o["total"] * 100 and made[-1][0] == o["total"] and st["orderId"].startswith("order_")
    again = f.post("/api/v1/pay/online/start", json={"kind": "order", "orderId": o["id"]}).json()
    assert again["payment"] == st["payment"] and len(made) == 1          # reused, not a second Razorpay order
    oid = st["orderId"]
    bad = f.post("/api/v1/pay/online/verify", json={"payment": st["payment"], "razorpay_order_id": oid, "razorpay_payment_id": "pay_1", "razorpay_signature": "nope"})
    assert bad.status_code == 400
    sig = hmac.new(b"sekret", f"{oid}|pay_1".encode(), hashlib.sha256).hexdigest()
    wrong_order = f.post("/api/v1/pay/online/verify", json={"payment": st["payment"], "razorpay_order_id": "order_OTHER", "razorpay_payment_id": "pay_1", "razorpay_signature": sig})
    assert wrong_order.status_code == 400
    ok = f.post("/api/v1/pay/online/verify", json={"payment": st["payment"], "razorpay_order_id": oid, "razorpay_payment_id": "pay_1", "razorpay_signature": sig}).json()
    assert ok["status"] == "confirmed"
    with DB.session() as db:
        assert db.get(Order, o["id"]).payment == "online-paid"
    assert f.post("/api/v1/pay/online/start", json={"kind": "order", "orderId": o["id"]}).status_code == 400   # already paid
    # someone else's family cannot verify or start on this order
    g = family()
    assert g.post("/api/v1/pay/online/start", json={"kind": "order", "orderId": o["id"]}).status_code == 404
    assert g.post("/api/v1/pay/online/verify", json={"payment": st["payment"], "razorpay_order_id": oid, "razorpay_payment_id": "pay_1", "razorpay_signature": sig}).status_code == 404


def test_webhook_settles_once_and_checks_amount(monkeypatch):
    _on(monkeypatch)
    f = family()
    o = _order(f)
    st = f.post("/api/v1/pay/online/start", json={"kind": "order", "orderId": o["id"]}).json()

    def hook(amount, sig=None):
        body = json.dumps({"event": "payment.captured", "payload": {"payment": {"entity": {"id": "pay_W", "order_id": st["orderId"], "amount": amount}}}}).encode()
        s = sig or hmac.new(b"hooksekret", body, hashlib.sha256).hexdigest()
        return f.post("/api/v1/pay/online/webhook", content=body, headers={"x-razorpay-signature": s, "content-type": "application/json"})
    assert hook(o["total"] * 100, sig="forged").status_code == 400
    assert hook(100).json().get("mismatch")                       # a different amount never settles
    with DB.session() as db:
        assert db.get(Order, o["id"]).payment == "online"
    assert hook(o["total"] * 100).json()["ok"]
    assert hook(o["total"] * 100).json()["ok"]                     # delivered twice: still one settlement
    with DB.session() as db:
        assert db.get(Order, o["id"]).payment == "online-paid"
        assert db.get(Payment, st["payment"]).status == "confirmed"
        tl = [t for t in db.get(Order, o["id"]).timeline if t.get("s") == "paid"]
        assert len(tl) == 1

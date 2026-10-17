"""Razorpay (India) — used only when RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET are set. Standard Checkout flow:
server creates an order → the app opens Razorpay Checkout with key_id + order_id → the app posts payment_id/signature back
→ the server verifies the HMAC. Amounts are in paise. Needs a Razorpay merchant account (KYC) before going live."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import urllib.request


def _auth():
    kid, sec = os.getenv("RAZORPAY_KEY_ID", ""), os.getenv("RAZORPAY_KEY_SECRET", "")
    return kid, sec, "Basic " + base64.b64encode(f"{kid}:{sec}".encode()).decode()


def create_order(amount_inr: int, receipt: str) -> dict:
    kid, _, auth = _auth()
    body = json.dumps({"amount": int(amount_inr * 100), "currency": "INR", "receipt": receipt[:40], "notes": {"app": "TheHealthTracker"}}).encode()
    req = urllib.request.Request("https://api.razorpay.com/v1/orders", data=body, method="POST",
                                 headers={"Authorization": auth, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=20) as r:
        o = json.loads(r.read())
    return {"keyId": kid, "orderId": o["id"], "amount": o["amount"], "currency": o["currency"]}


def verify_payment(order_id: str, payment_id: str, signature: str) -> bool:
    _, sec, _ = _auth()
    good = hmac.new(sec.encode(), f"{order_id}|{payment_id}".encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(good, signature or "")


def verify_webhook(body: bytes, signature: str) -> bool:
    sec = os.getenv("RAZORPAY_WEBHOOK_SECRET", "")
    if not sec:
        return False
    good = hmac.new(sec.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(good, signature or "")

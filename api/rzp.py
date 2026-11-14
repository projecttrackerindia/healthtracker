"""Online payments through Razorpay (/api/v1/pay/online): orders and plan upgrades.

The only way money is collected online. Nothing here ever shows a personal UPI ID: the family pays inside Razorpay
Checkout (UPI, cards, netbanking), the server checks Razorpay's signature, and only then marks the order paid or
switches the plan. The webhook settles the same payment if the family closes the app before the redirect lands, and
settling is idempotent, so a payment can never count twice.

    family taps Pay → POST /start  → Razorpay order (amount from OUR database, never from the request)
                    → Checkout     → POST /verify (HMAC over order_id|payment_id)  → settled
                    → (or) Razorpay webhook payment.captured (HMAC over the body)   → settled
"""
from __future__ import annotations

import json
import os
import time

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import payments as RZ
from .auth import csrf, current_user, limit
from .db import get_db
from .inbox import notify
from .launch import free_now
from .models import Household, Order, Payment, Plan, now
from .routes import household

r = APIRouter(prefix="/api/v1/pay/online")
ACCOUNT = "razorpay"


def enabled() -> bool:
    return bool(os.getenv("RAZORPAY_KEY_ID") and os.getenv("RAZORPAY_KEY_SECRET"))


class StartIn(BaseModel):
    kind: str            # order | plan
    orderId: str = ""
    plan: str = ""
    period: str = "month"


def _amount(db: Session, h: Household, body: StartIn) -> tuple[int, str]:
    if body.kind == "order":
        o = db.get(Order, body.orderId)
        if not o or o.household_id != h.id:
            raise HTTPException(404, "order not found")
        if o.status in ("cancelled", "refunded"):
            raise HTTPException(400, "This order is closed.")
        if (o.payment or "").endswith("paid"):
            raise HTTPException(400, "This order is already paid.")
        if (o.total or 0) <= 0:
            raise HTTPException(400, "Nothing to pay on this order.")
        return int(o.total), o.id
    if body.kind == "plan":
        if free_now():
            raise HTTPException(400, "Every feature is free for your family right now; there is nothing to pay for.")
        p = db.get(Plan, body.plan)
        if not p or not p.active:
            raise HTTPException(404, "plan not found")
        period = "year" if body.period == "year" else "month"
        amt = p.price_year if period == "year" else p.price_month
        if amt <= 0:
            raise HTTPException(400, "This plan is free; nothing to pay.")
        return int(amt), f"{p.code}:{period}"
    raise HTTPException(400, "kind must be order or plan")


@r.post("/start", dependencies=[Depends(csrf)])
def start(body: StartIn, request: Request, db: Session = Depends(get_db), x_dokko_key: str | None = Header(None)):
    if not enabled():
        raise HTTPException(503, "Online payment is not switched on yet. Pay at the door instead.")
    h = household(db, x_dokko_key)
    if not h:
        raise HTTPException(401, "Sign in to pay.")
    limit(request, f"rzpstart:{h.id}", 20, 3600)
    amount, ref = _amount(db, h, body)
    cur = db.scalar(select(Payment).where(Payment.household_id == h.id, Payment.kind == body.kind, Payment.ref == ref, Payment.account == ACCOUNT,
                                          Payment.status == "pending", Payment.amount == amount).order_by(Payment.created.desc()))
    if cur and cur.created + 3600 > now():
        rz = {"keyId": os.getenv("RAZORPAY_KEY_ID", ""), "orderId": cur.note, "amount": amount * 100, "currency": "INR"}
    else:
        try:
            rz = RZ.create_order(amount, f"{body.kind}:{ref}"[:40])
        except Exception:
            raise HTTPException(502, "Razorpay did not respond. Try again in a minute, or pay at the door.")
        u = current_user(request, db)
        cur = Payment(household_id=h.id, user_id=u.id if u else "", kind=body.kind, ref=ref, amount=amount, account=ACCOUNT, vpa="", note=rz["orderId"])
        db.add(cur)
        db.flush()
    return {"payment": cur.id, **rz, "name": "Urban Health", "description": f"Order {ref}" if body.kind == "order" else "Urban Health plan",
            "prefill": {"name": h.name or "", "contact": h.phone or ""}}


def settle(db: Session, p: Payment, payment_id: str, by: str) -> Payment:
    """Mark one Razorpay payment as received. Safe to call twice (redirect and webhook can both arrive)."""
    if p.status == "confirmed":
        return p
    h = db.get(Household, p.household_id)
    if not h:
        raise HTTPException(404)
    if p.kind == "plan":
        from .upipay import activate_plan
        code, period = p.ref.split(":")
        sub = activate_plan(db, h, code, period, p.amount, "razorpay", payment_id)
        notify(db, h.id, "payment", f"Payment received · {sub.invoice_no}", f"Your {code.title()} plan is active till {time.strftime('%d/%m/%Y', time.localtime(h.plan_until))}. Thank you.",
               {"payment": p.id, "plan": code, "invoice": sub.invoice_no}, "", "/app#page=plan")
    else:
        o = db.get(Order, p.ref)
        if o:
            o.payment = "online-paid"
            o.timeline = (o.timeline or []) + [{"s": "paid", "t": now(), "by": by, "ref": payment_id}]
            notify(db, h.id, "payment", f"Payment received for order {o.id}", f"₹{p.amount} paid online. Your receipt shows it as paid.", {"payment": p.id, "order": o.id}, o.member_id or "", "/app#page=bill")
    p.status, p.utr, p.decided_by, p.decided_at = "confirmed", payment_id[:40], by, now()
    return p


class VerifyIn(BaseModel):
    payment: str
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str


@r.post("/verify", dependencies=[Depends(csrf)])
def verify(body: VerifyIn, db: Session = Depends(get_db), x_dokko_key: str | None = Header(None)):
    h = household(db, x_dokko_key, create=False)
    p = db.get(Payment, body.payment)
    if not h or not p or p.household_id != h.id or p.account != ACCOUNT:
        raise HTTPException(404)
    if body.razorpay_order_id != p.note or not RZ.verify_payment(body.razorpay_order_id, body.razorpay_payment_id, body.razorpay_signature):
        raise HTTPException(400, "We could not confirm this payment. If money left your account, it comes back automatically within 5–7 days.")
    settle(db, p, body.razorpay_payment_id, "razorpay")
    return {"ok": True, "status": p.status, "kind": p.kind, "ref": p.ref}


@r.post("/webhook")
async def webhook(request: Request, db: Session = Depends(get_db)):
    raw = await request.body()
    if not RZ.verify_webhook(raw, request.headers.get("x-razorpay-signature", "")):
        raise HTTPException(400, "bad signature")
    ev = json.loads(raw or b"{}")
    if ev.get("event") not in ("payment.captured", "order.paid"):
        return {"ok": True, "ignored": ev.get("event")}
    ent = ((ev.get("payload") or {}).get("payment") or {}).get("entity") or {}
    p = db.scalar(select(Payment).where(Payment.account == ACCOUNT, Payment.note == (ent.get("order_id") or "")).order_by(Payment.created.desc()))
    if not p:
        return {"ok": True, "unknown": True}
    if int(ent.get("amount") or 0) != p.amount * 100:
        return {"ok": False, "mismatch": True}   # never settle a different amount than we asked for
    settle(db, p, ent.get("id") or "", "razorpay-webhook")
    return {"ok": True}

"""Pay by UPI QR (/api/v1/pay/upi, /api/admin/payments) — plan upgrades and orders until a payment gateway is live.

The family picks a plan (or chooses "Pay by UPI" for an order), the server records a pending payment with a short
reference, and shows a QR / one-tap UPI link for one of our accounts with the exact amount and the reference in the
note. The person pays in any UPI app, enters the 12-digit UTR, and an admin matches it against the bank statement in
Admin → Payments; confirming activates the plan (or marks the order paid) and tells the family. Nothing changes without
that confirmation. Accounts come from UPI_ACCOUNTS (JSON) or api/data/upi.json; the QR is generated here, so the amount
and reference are always right.
"""
from __future__ import annotations

import io
import json
import os
import re
import time
from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .admin import Admin, log
from .admin import me as admin_me
from .auth import current_user, limit
from .db import get_db
from .inbox import notify
from .models import Household, Order, Payment, Plan, Subscription, now
from .routes import household

r = APIRouter(prefix="/api/v1/pay/upi")
ar = APIRouter(prefix="/api/admin")
DATA = Path(__file__).resolve().parent / "data" / "upi.json"
EXPIRE_S = 2 * 3600
UTR_RE = re.compile(r"^[A-Za-z0-9]{12,22}$")


def accounts() -> list[dict]:
    raw = os.getenv("UPI_ACCOUNTS", "").strip()
    try:
        rows = json.loads(raw) if raw else json.loads(DATA.read_text())
    except Exception:
        rows = []
    return [a for a in rows if a.get("vpa") and a.get("id")]


def enabled() -> bool:
    return bool(accounts()) and os.getenv("UPI_PAY", "1") not in ("0", "false", "off")


def public(a: dict) -> dict:
    return {"id": a["id"], "bank": a.get("bank", ""), "last4": a.get("last4", ""), "vpa": a["vpa"]}


def upi_link(a: dict, amount: int, note: str) -> str:
    return f"upi://pay?pa={quote(a['vpa'])}&pn={quote(a.get('name') or 'TheHealthTracker')}&am={amount}.00&cu=INR&tn={quote(note)}"


def pay_json(p: Payment, base: str = "") -> dict:
    a = next((x for x in accounts() if x["id"] == p.account), None)
    return {"id": p.id, "kind": p.kind, "ref": p.ref, "amount": p.amount, "account": public(a) if a else None, "note": p.note, "status": p.status, "utr": p.utr,
            "payer": p.payer, "created": p.created, "expires": p.created + EXPIRE_S, "claimedAt": p.claimed_at, "decidedAt": p.decided_at, "adminNote": p.admin_note,
            "upiLink": upi_link(a, p.amount, p.note) if a and p.status == "pending" else "", "qr": f"/api/v1/pay/upi/{p.id}/qr.svg" if p.status == "pending" else ""}


@r.get("/accounts")
def list_accounts():
    return {"enabled": enabled(), "accounts": [public(a) for a in accounts()]}


class StartIn(BaseModel):
    kind: str            # plan | order
    plan: str = ""
    period: str = "month"
    orderId: str = ""
    account: str = ""


@r.post("/start")
def start(body: StartIn, request: Request, db: Session = Depends(get_db), x_dokko_key: str | None = Header(None)):
    if not enabled():
        raise HTTPException(503, "UPI payment is not switched on.")
    h = household(db, x_dokko_key)
    if not h:
        raise HTTPException(400, "missing household key")
    limit(request, f"upistart:{h.id}", 20, 3600)
    acc = accounts()
    a = next((x for x in acc if x["id"] == body.account), acc[0])
    if body.kind == "plan":
        p = db.get(Plan, body.plan)
        if not p or not p.active:
            raise HTTPException(404, "plan not found")
        amount = p.price_year if body.period == "year" else p.price_month
        if amount <= 0:
            raise HTTPException(400, "This plan is free; nothing to pay.")
        ref = f"{p.code}:{'year' if body.period == 'year' else 'month'}"
    elif body.kind == "order":
        o = db.get(Order, body.orderId)
        if not o or o.household_id != h.id:
            raise HTTPException(404, "order not found")
        if o.status in ("cancelled", "refunded"):
            raise HTTPException(400, "This order is closed.")
        if (o.payment or "").endswith("paid"):
            raise HTTPException(400, "This order is already paid.")
        amount, ref = o.total, o.id
    else:
        raise HTTPException(400, "kind must be plan or order")
    # one open payment per thing: reuse it instead of minting another reference
    cur = db.scalar(select(Payment).where(Payment.household_id == h.id, Payment.kind == body.kind, Payment.ref == ref, Payment.status.in_(("pending", "claimed"))).order_by(Payment.created.desc()))
    if cur and cur.created + EXPIRE_S > now():
        return pay_json(cur)
    u = current_user(request, db)
    n = (db.scalar(select(func.count(Payment.id))) or 0) + 1
    pay = Payment(household_id=h.id, user_id=u.id if u else "", kind=body.kind, ref=ref, amount=amount, account=a["id"], vpa=a["vpa"], note=f"THT{n:05d}")
    db.add(pay)
    db.flush()
    return pay_json(pay)


@r.get("/{pid}/qr.svg")
def qr(pid: str, db: Session = Depends(get_db), x_dokko_key: str | None = Header(None)):
    import qrcode
    import qrcode.image.svg

    h = household(db, x_dokko_key, create=False)
    p = db.get(Payment, pid)
    if not h or not p or p.household_id != h.id:
        raise HTTPException(404)
    a = next((x for x in accounts() if x["id"] == p.account), None)
    if not a:
        raise HTTPException(404)
    img = qrcode.make(upi_link(a, p.amount, p.note), image_factory=qrcode.image.svg.SvgPathImage, box_size=10, border=2)
    buf = io.BytesIO()
    img.save(buf)
    return Response(buf.getvalue(), media_type="image/svg+xml", headers={"Cache-Control": "private, max-age=3600"})


class ClaimIn(BaseModel):
    utr: str
    payer: str = ""


@r.post("/{pid}/claim")
def claim(pid: str, body: ClaimIn, request: Request, db: Session = Depends(get_db), x_dokko_key: str | None = Header(None)):
    """'I have paid': the UTR / transaction id from the UPI app, so the admin can match it."""
    h = household(db, x_dokko_key, create=False)
    p = db.get(Payment, pid)
    if not h or not p or p.household_id != h.id:
        raise HTTPException(404)
    if p.status not in ("pending", "claimed"):
        raise HTTPException(400, f"This payment is already {p.status}.")
    utr = re.sub(r"\s+", "", body.utr)
    if not UTR_RE.match(utr):
        raise HTTPException(400, "Enter the 12-digit UTR / transaction ID shown in your UPI app.")
    if db.scalar(select(Payment.id).where(Payment.utr == utr, Payment.id != p.id, Payment.status.in_(("claimed", "confirmed")))):
        raise HTTPException(400, "This UTR is already in use.")
    p.utr, p.payer, p.status, p.claimed_at = utr, body.payer.strip()[:80], "claimed", now()
    from . import messaging
    admin_to = os.getenv("ADMIN_ALERT_EMAIL") or os.getenv("LEGAL_EMAIL") or ""
    if admin_to:
        messaging.mail(admin_to, f"[Admin] UPI payment to confirm · ₹{p.amount} · {p.note}", f"UTR {utr} · ₹{p.amount} · {p.kind} {p.ref} · account {p.account}\nPayer: {p.payer or '—'}\n\nConfirm: https://thehealthtracker.com/admin#payments")
    return pay_json(p)


@r.get("")
def mine(db: Session = Depends(get_db), x_dokko_key: str | None = Header(None)):
    h = household(db, x_dokko_key, create=False)
    if not h:
        return {"payments": []}
    rows = db.scalars(select(Payment).where(Payment.household_id == h.id).order_by(Payment.created.desc()).limit(30)).all()
    for p in rows:
        if p.status == "pending" and p.created + EXPIRE_S < now():
            p.status = "expired"
    return {"payments": [pay_json(p) for p in rows]}


@r.get("/{pid}")
def one(pid: str, db: Session = Depends(get_db), x_dokko_key: str | None = Header(None)):
    h = household(db, x_dokko_key, create=False)
    p = db.get(Payment, pid)
    if not h or not p or p.household_id != h.id:
        raise HTTPException(404)
    if p.status == "pending" and p.created + EXPIRE_S < now():
        p.status = "expired"
    return pay_json(p)


# ---- admin: match against the bank statement ---------------------------------------------------------------------------------
@ar.get("/payments")
def admin_payments(status: str = "claimed", a: Admin = Depends(admin_me), db: Session = Depends(get_db)):
    q = select(Payment).order_by(Payment.created.desc())
    if status != "all":
        q = q.where(Payment.status == status)
    rows = db.scalars(q.limit(300)).all()
    hs = {x.id: x for x in db.scalars(select(Household).where(Household.id.in_({p.household_id for p in rows}))).all()} if rows else {}
    return {"payments": [{**pay_json(p), "household": p.household_id, "family": (hs.get(p.household_id).name if hs.get(p.household_id) else ""), "plan": (hs.get(p.household_id).plan if hs.get(p.household_id) else "")} for p in rows],
            "counts": {s: (db.scalar(select(func.count(Payment.id)).where(Payment.status == s)) or 0) for s in ("pending", "claimed", "confirmed", "rejected")}}


class DecideIn(BaseModel):
    note: str = ""


def activate_plan(db: Session, h: Household, code: str, period: str, amount: int, provider: str, ref: str) -> Subscription:
    p = db.get(Plan, code)
    days = 365 if period == "year" else 30
    start = max(now(), h.plan_until or 0) if h.plan == code else now()
    h.plan, h.plan_until = code, start + days * 86400
    n = (db.scalar(select(func.count(Subscription.id))) or 0) + 1
    sub = Subscription(household_id=h.id, plan=code, period=period, amount=amount, status="active", provider=provider, provider_ref=ref, renews=h.plan_until,
                       invoice_no=f"THT-{time.strftime('%Y%m')}-{n:05d}")
    db.add(sub)
    db.flush()
    return sub


@ar.post("/payments/{pid}/confirm")
def confirm(pid: str, body: DecideIn, a: Admin = Depends(admin_me), db: Session = Depends(get_db)):
    p = db.get(Payment, pid)
    if not p or p.status not in ("claimed", "pending"):
        raise HTTPException(404)
    h = db.get(Household, p.household_id)
    if not h:
        raise HTTPException(404)
    if p.kind == "plan":
        code, period = p.ref.split(":")
        sub = activate_plan(db, h, code, period, p.amount, "upi", p.utr or p.note)
        notify(db, h.id, "payment", f"Payment received · {sub.invoice_no}", f"Your {code.title()} plan is active till {time.strftime('%d/%m/%Y', time.localtime(h.plan_until))}. Thank you.",
               {"payment": p.id, "plan": code, "until": h.plan_until, "invoice": sub.invoice_no}, "", "/app#page=plan")
    else:
        o = db.get(Order, p.ref)
        if o:
            o.payment = "upi-paid"
            o.timeline = (o.timeline or []) + [{"s": "paid", "t": now(), "by": a.email, "utr": p.utr}]
            notify(db, h.id, "payment", f"Payment received for order {o.id}", f"₹{p.amount} by UPI (UTR {p.utr}). The receipt in Bills shows it as paid.", {"payment": p.id, "order": o.id}, o.member_id or "", "/app#page=bill")
    p.status, p.decided_by, p.decided_at, p.admin_note = "confirmed", a.email, now(), body.note[:300]
    log(db, a.email, f"payment.confirm {pid} {p.kind} {p.ref} ₹{p.amount} utr={p.utr}")
    return pay_json(p)


@ar.post("/payments/{pid}/reject")
def reject(pid: str, body: DecideIn, a: Admin = Depends(admin_me), db: Session = Depends(get_db)):
    p = db.get(Payment, pid)
    if not p or p.status not in ("claimed", "pending"):
        raise HTTPException(404)
    p.status, p.decided_by, p.decided_at, p.admin_note = "rejected", a.email, now(), body.note[:300]
    notify(db, p.household_id, "payment", "We could not match your UPI payment", (body.note or "The UTR did not match a credit in our account.") + " Reply from Bills → Payments with a screenshot, or try again.",
           {"payment": p.id}, "", "/app#page=plan")
    log(db, a.email, f"payment.reject {pid}")
    return pay_json(p)

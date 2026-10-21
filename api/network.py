"""Growing the partner network without a human in every step.

Self-serve: a lab, pharmacy or hospital applies from /partner → Apply (public, rate-limited, de-duplicated by email).
Admin: a review queue; Approve creates the store (unverified until the licence is checked), the owner's sign-in with a
one-time password, and marks the application. Settlements: what each partner is owed for a month (orders delivered /
reports ready), less the platform fee (PARTNER_FEE_PCT, default 8%), so the finance team can pay out and reconcile.
"""
from __future__ import annotations

import os
import secrets
import time
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .admin import Admin, log
from .admin import me as admin_me
from .auth import limit
from .db import get_db
from .models import Order, PartnerApplication, PartnerUser, Payout, Store, now
from .security import hash_pw

r = APIRouter(prefix="/api/v1")
ar = APIRouter(prefix="/api/admin")
IST = timezone(timedelta(hours=5, minutes=30))
KINDS = ("pharmacy", "lab", "hospital")
SETTLED = ("delivered", "ready", "returned", "refunded")


class ApplyIn(BaseModel):
    kind: str
    name: str
    contact: str = ""
    email: str
    phone: str
    address: str = ""
    area: str = ""
    city: str
    pin: str = ""
    lat: float | None = None
    lng: float | None = None
    licence: str = ""
    gstin: str = ""
    services: str = ""
    note: str = ""
    accept: bool = False


def app_json(a: PartnerApplication) -> dict:
    return {"id": a.id, "kind": a.kind, "name": a.name, "contact": a.contact, "email": a.email, "phone": a.phone, "address": a.address, "area": a.area, "city": a.city, "pin": a.pin,
            "lat": a.lat, "lng": a.lng, "licence": a.licence, "gstin": a.gstin, "services": a.services, "note": a.note, "status": a.status, "storeId": a.store_id,
            "decidedBy": a.decided_by, "decidedAt": a.decided_at, "created": a.created}


@r.post("/partner/apply")
def apply(body: ApplyIn, request: Request, db: Session = Depends(get_db)):
    limit(request, "partner-apply", 5, 3600)
    if body.kind not in KINDS:
        raise HTTPException(400, "kind must be pharmacy, lab or hospital")
    email = body.email.strip().lower()
    if "@" not in email or len(body.name.strip()) < 3 or len(body.city.strip()) < 2 or len(body.phone.strip()) < 10:
        raise HTTPException(400, "Business name, city, a working phone number and an email are needed.")
    if not body.accept:
        raise HTTPException(400, "Please accept the partner terms.")
    if not body.licence.strip():
        raise HTTPException(400, {"pharmacy": "The drug licence number is needed.", "lab": "The NABL / clinical establishment registration number is needed.",
                                  "hospital": "The clinical establishment registration number is needed."}[body.kind])
    dup = db.scalar(select(PartnerApplication).where(PartnerApplication.email == email, PartnerApplication.status == "new"))
    if dup:
        return {"ok": True, "id": dup.id, "status": "new", "message": "We already have your application; the partner team will write to you within 2 working days."}
    if db.scalar(select(PartnerUser.id).where(PartnerUser.email == email)):
        raise HTTPException(400, "This email already has a partner sign-in. Sign in at /partner, or write to partner@thehealthtracker.com.")
    a = PartnerApplication(kind=body.kind, name=body.name.strip()[:120], contact=body.contact.strip()[:80], email=email, phone=body.phone.strip()[:24], address=body.address.strip()[:240],
                           area=body.area.strip()[:80], city=body.city.strip()[:80], pin=body.pin.strip()[:12], lat=body.lat, lng=body.lng, licence=body.licence.strip()[:64],
                           gstin=body.gstin.strip().upper()[:20], services=body.services.strip()[:300], note=body.note.strip()[:2000],
                           ip=(request.headers.get("x-forwarded-for", "").split(",")[0].strip() or (request.client.host if request.client else ""))[:48])
    db.add(a)
    db.flush()
    from . import messaging
    admin_to = os.getenv("ADMIN_ALERT_EMAIL") or os.getenv("LEGAL_EMAIL") or ""
    if admin_to:
        messaging.mail(admin_to, f"[Admin] New partner application · {a.name} ({a.kind}, {a.city})", f"{a.name} · {a.kind} · {a.city}\nContact {a.contact} · {a.phone} · {a.email}\nLicence {a.licence}\n\nReview: https://thehealthtracker.com/admin#applications")
    messaging.mail(email, "We received your TheHealthTracker partner application", f"Thank you, {a.contact or a.name}.\n\nReference: {a.id}\nWe check the licence number ({a.licence}) with the regulator and write back within 2 working days. "
                   "Meanwhile, keep your price list or test menu handy; you will enter it in the portal on first sign-in.")
    return {"ok": True, "id": a.id, "status": "new", "message": "Thank you. The partner team checks the licence and writes to you within 2 working days."}


@r.get("/partner/apply/{aid}")
def apply_status(aid: str, db: Session = Depends(get_db)):
    a = db.get(PartnerApplication, aid)
    if not a:
        raise HTTPException(404)
    return {"id": a.id, "status": a.status, "name": a.name}


# ---- admin review -----------------------------------------------------------------------------------------------------------
@ar.get("/applications")
def applications(status: str = "new", a: Admin = Depends(admin_me), db: Session = Depends(get_db)):
    q = select(PartnerApplication).order_by(PartnerApplication.created.desc())
    if status != "all":
        q = q.where(PartnerApplication.status == status)
    return {"applications": [app_json(x) for x in db.scalars(q.limit(300)).all()]}


class DecideIn(BaseModel):
    verified: bool = False   # licence checked → store goes live verified
    note: str = ""


@ar.post("/applications/{aid}/approve")
def approve(aid: str, body: DecideIn, a: Admin = Depends(admin_me), db: Session = Depends(get_db)):
    ap = db.get(PartnerApplication, aid)
    if not ap or ap.status != "new":
        raise HTTPException(404)
    if ap.lat is None or ap.lng is None:
        raise HTTPException(400, "Set the store's location (lat/lng) before approving so it shows up in Nearby.")
    if db.scalar(select(PartnerUser.id).where(PartnerUser.email == ap.email)):
        raise HTTPException(400, "This email already has a partner sign-in.")
    s = Store(kind=ap.kind, name=ap.name, address=ap.address, area=ap.area, city=ap.city, pin=ap.pin, lat=ap.lat, lng=ap.lng, phone=ap.phone, licence=ap.licence,
              verified=bool(body.verified), active=True, owner_email=ap.email, notes=(f"From application {ap.id}. GSTIN {ap.gstin}. {ap.services}".strip() + (" " + body.note if body.note else ""))[:2000],
              home_collection=ap.kind == "lab", delivery=ap.kind == "pharmacy", rating=0, rating_n=0)
    db.add(s)
    db.flush()
    temp = secrets.token_urlsafe(9)
    u = PartnerUser(store_id=s.id, email=ap.email, name=ap.contact or ap.name, phone=ap.phone, role="owner", pw_hash=hash_pw(temp), must_change=True)
    db.add(u)
    ap.status, ap.store_id, ap.decided_by, ap.decided_at = "approved", s.id, a.email, now()
    log(db, a.email, f"partner.application.approve {aid} → store {s.id}")
    from . import messaging
    sent = messaging.mail(ap.email, "Welcome to the TheHealthTracker partner network",
                          f"Hello {ap.contact or ap.name},\n\n{ap.name} is now on TheHealthTracker{' as a verified partner' if s.verified else ' (verification of the licence is in progress)'}.\n\n"
                          f"Sign in at https://thehealthtracker.com/partner\nEmail: {ap.email}\nOne-time password: {temp}\n\nYou will be asked to set your own password on first sign-in. "
                          f"Then complete the store profile and price list so families near you can book.\n\nQuestions: partner@thehealthtracker.com")
    return {"ok": True, "storeId": s.id, "email": ap.email, "tempPassword": temp, "portal": "/partner", "verified": s.verified, "emailed": sent}


@ar.post("/applications/{aid}/decline")
def decline(aid: str, body: DecideIn, a: Admin = Depends(admin_me), db: Session = Depends(get_db)):
    ap = db.get(PartnerApplication, aid)
    if not ap or ap.status != "new":
        raise HTTPException(404)
    ap.status, ap.decided_by, ap.decided_at = "declined", a.email, now()
    ap.note = (ap.note + f"\n[declined] {body.note}").strip()[:2000]
    log(db, a.email, f"partner.application.decline {aid}")
    return {"ok": True}


class LocIn(BaseModel):
    lat: float
    lng: float


@ar.post("/applications/{aid}/location")
def set_location(aid: str, body: LocIn, a: Admin = Depends(admin_me), db: Session = Depends(get_db)):
    ap = db.get(PartnerApplication, aid)
    if not ap:
        raise HTTPException(404)
    ap.lat, ap.lng = body.lat, body.lng
    return app_json(ap)


# ---- settlements ------------------------------------------------------------------------------------------------------------
def fee_pct() -> float:
    """The platform default, used by any partner without a rate of their own."""
    try:
        return float(os.getenv("PARTNER_FEE_PCT", "8"))
    except ValueError:
        return 8.0


def fee_for(s: Store | None) -> float:
    """This partner's rate. Contracts differ — a launch partner may be on 0% and a referred one on 12 — so the
    rate is a property of the store, and the global figure is only the fallback. 0 is a real rate, which is
    why the column is nullable rather than defaulting to zero."""
    if s is not None and s.commission_pct is not None:
        return float(s.commission_pct)
    return fee_pct()


def month_bounds(month: str) -> tuple[int, int]:
    y, m = int(month[:4]), int(month[5:7])
    start = datetime(y, m, 1, tzinfo=IST)
    end = datetime(y + (m == 12), (m % 12) + 1, 1, tzinfo=IST)
    return int(start.timestamp()), int(end.timestamp())


def settlement_rows(db: Session, month: str) -> list[dict]:
    lo, hi = month_bounds(month)
    out = []
    paid = {p.store_id: p for p in db.scalars(select(Payout).where(Payout.month == month)).all()}
    stores = {s.id: s for s in db.scalars(select(Store)).all()}
    orders = db.scalars(select(Order).where(Order.created >= lo, Order.created < hi, Order.status.in_(SETTLED))).all()
    by: dict[str, dict] = {}
    for o in orders:
        d = by.setdefault(o.store_id, {"orders": 0, "gross": 0, "refunds": 0, "cod": 0, "online": 0, "medicine": 0, "lab": 0})
        if o.status in ("refunded",):
            d["refunds"] += o.total
            continue
        d["orders"] += 1
        d["gross"] += o.total
        d["cod" if (o.payment or "cod") == "cod" else "online"] += o.total
        d[o.kind if o.kind in ("medicine", "lab") else "medicine"] += o.total
    for sid, d in by.items():
        s = stores.get(sid)
        pct = fee_for(s)
        fee = round(d["gross"] * pct / 100)
        # cash-on-delivery money is already with the partner, so the fee on it is owed TO the platform; online money is held by us and paid out less the fee
        payable = d["online"] - round(d["online"] * pct / 100)
        due_from_partner = round(d["cod"] * pct / 100)
        p = paid.get(sid)
        out.append({"storeId": sid, "store": s.name if s else sid, "kind": s.kind if s else "", "city": s.city if s else "", **d, "feePct": pct, "fee": fee,
                    "payableToPartner": payable, "dueFromPartner": due_from_partner, "net": payable - due_from_partner,
                    # What was actually settled, if anything. The figures above are recomputed from the orders
                    # every time; this is the part that cannot be.
                    "settled": bool(p), "settledAt": p.paid_at if p else None, "settledRef": p.ref if p else "",
                    "settledNet": p.net if p else None, "settledBy": p.paid_by if p else ""})
    out.sort(key=lambda x: -x["gross"])
    return out


def payout_json(p: Payout) -> dict:
    return {"id": p.id, "storeId": p.store_id, "month": p.month, "orders": p.orders_n, "gross": p.gross,
            "feePct": p.fee_pct, "fee": p.fee, "payableToPartner": p.payable, "dueFromPartner": p.due_from,
            "net": p.net, "status": p.status, "ref": p.ref, "note": p.note, "paidAt": p.paid_at, "paidBy": p.paid_by}


@ar.get("/settlements")
def settlements(month: str = "", a: Admin = Depends(admin_me), db: Session = Depends(get_db)):
    month = month or datetime.now(IST).strftime("%Y-%m")
    if len(month) != 7:
        raise HTTPException(400, "month as YYYY-MM")
    rows = settlement_rows(db, month)
    return {"month": month, "feePct": fee_pct(), "rows": rows, "totals": {"gross": sum(r["gross"] for r in rows), "fee": sum(r["fee"] for r in rows),
            "payable": sum(r["payableToPartner"] for r in rows), "dueFromPartners": sum(r["dueFromPartner"] for r in rows), "orders": sum(r["orders"] for r in rows)}}


class PayIn(BaseModel):
    ref: str = ""
    note: str = ""
    status: str = "paid"


@ar.post("/settlements/{month}/{store_id}")
def settle(month: str, store_id: str, body: PayIn, a: Admin = Depends(admin_me), db: Session = Depends(get_db)):
    """Record that this month's account with this partner has been settled.

    The figures are taken from the live computation at the moment of settling and frozen into the row, so a
    later refund or a changed commission rate cannot quietly rewrite what was paid. A bank reference is asked
    for because a payout nobody can trace is a payout that gets made twice."""
    if len(month) != 7:
        raise HTTPException(400, "month as YYYY-MM")
    s = db.get(Store, store_id)
    if not s:
        raise HTTPException(404, "store not found")
    if db.scalar(select(Payout).where(Payout.store_id == store_id, Payout.month == month)):
        raise HTTPException(409, f"{month} is already settled for {s.name}.")
    row = next((r for r in settlement_rows(db, month) if r["storeId"] == store_id), None)
    if not row:
        raise HTTPException(400, f"{s.name} has nothing to settle in {month}.")
    if body.status not in ("paid", "written_off"):
        raise HTTPException(400, "status is paid or written_off")
    p = Payout(store_id=store_id, month=month, orders_n=row["orders"], gross=row["gross"], fee_pct=row["feePct"],
               fee=row["fee"], payable=row["payableToPartner"], due_from=row["dueFromPartner"], net=row["net"],
               status=body.status, ref=body.ref.strip()[:60], note=body.note.strip()[:300], paid_at=now(), paid_by=a.email)
    db.add(p)
    db.flush()
    log(db, a.email, f"settlement.pay {store_id} {month} net={row['net']} ref={p.ref}")
    return payout_json(p)


@ar.delete("/settlements/{month}/{store_id}")
def unsettle(month: str, store_id: str, a: Admin = Depends(admin_me), db: Session = Depends(get_db)):
    """Undo a settlement recorded in error. Logged, because unmarking a payout is how one gets made twice."""
    p = db.scalar(select(Payout).where(Payout.store_id == store_id, Payout.month == month))
    if not p:
        raise HTTPException(404)
    db.delete(p)
    log(db, a.email, f"settlement.unpay {store_id} {month}")
    return {"ok": True}


class RateIn(BaseModel):
    pct: float | None = None


@ar.post("/stores/{sid}/commission")
def set_commission(sid: str, body: RateIn, a: Admin = Depends(admin_me), db: Session = Depends(get_db)):
    """This partner's rate, or null to put them back on the platform default."""
    s = db.get(Store, sid)
    if not s:
        raise HTTPException(404)
    if body.pct is not None and not (0 <= body.pct <= 40):
        raise HTTPException(400, "A commission between 0 and 40% please.")
    s.commission_pct = body.pct
    log(db, a.email, f"store.commission {sid} {'default' if body.pct is None else body.pct}")
    return {"id": s.id, "name": s.name, "commissionPct": s.commission_pct, "effective": fee_for(s)}


@ar.get("/settlements.csv")
def settlements_csv(month: str = "", a: Admin = Depends(admin_me), db: Session = Depends(get_db)):
    from fastapi.responses import Response
    month = month or datetime.now(IST).strftime("%Y-%m")
    rows = settlement_rows(db, month)
    head = ("store_id,store,kind,city,orders,gross_inr,medicine_inr,lab_inr,cod_inr,online_inr,refunds_inr,fee_pct,"
            "fee_inr,payable_to_partner_inr,due_from_partner_inr,net_inr,settled,settled_net_inr,settled_ref,settled_by")
    cols = ("storeId", "store", "kind", "city", "orders", "gross", "medicine", "lab", "cod", "online", "refunds",
            "feePct", "fee", "payableToPartner", "dueFromPartner", "net", "settled", "settledNet", "settledRef", "settledBy")
    lines = [head] + [",".join(("" if r[k] is None else str(r[k])).replace(",", " ") for k in cols) for r in rows]
    return Response("\n".join(lines) + "\n", media_type="text/csv", headers={"Content-Disposition": f'attachment; filename="settlements-{month}.csv"'})

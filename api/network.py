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
from .models import Order, PartnerApplication, PartnerUser, Store, now
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
    return {"ok": True, "storeId": s.id, "email": ap.email, "tempPassword": temp, "portal": "/partner", "verified": s.verified}


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
    try:
        return float(os.getenv("PARTNER_FEE_PCT", "8"))
    except ValueError:
        return 8.0


def month_bounds(month: str) -> tuple[int, int]:
    y, m = int(month[:4]), int(month[5:7])
    start = datetime(y, m, 1, tzinfo=IST)
    end = datetime(y + (m == 12), (m % 12) + 1, 1, tzinfo=IST)
    return int(start.timestamp()), int(end.timestamp())


def settlement_rows(db: Session, month: str) -> list[dict]:
    lo, hi = month_bounds(month)
    pct = fee_pct()
    out = []
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
        fee = round(d["gross"] * pct / 100)
        # cash-on-delivery money is already with the partner, so the fee on it is owed TO the platform; online money is held by us and paid out less the fee
        payable = d["online"] - round(d["online"] * pct / 100)
        due_from_partner = round(d["cod"] * pct / 100)
        out.append({"storeId": sid, "store": s.name if s else sid, "kind": s.kind if s else "", "city": s.city if s else "", **d, "feePct": pct, "fee": fee,
                    "payableToPartner": payable, "dueFromPartner": due_from_partner, "net": payable - due_from_partner})
    out.sort(key=lambda x: -x["gross"])
    return out


@ar.get("/settlements")
def settlements(month: str = "", a: Admin = Depends(admin_me), db: Session = Depends(get_db)):
    month = month or datetime.now(IST).strftime("%Y-%m")
    if len(month) != 7:
        raise HTTPException(400, "month as YYYY-MM")
    rows = settlement_rows(db, month)
    return {"month": month, "feePct": fee_pct(), "rows": rows, "totals": {"gross": sum(r["gross"] for r in rows), "fee": sum(r["fee"] for r in rows),
            "payable": sum(r["payableToPartner"] for r in rows), "dueFromPartners": sum(r["dueFromPartner"] for r in rows), "orders": sum(r["orders"] for r in rows)}}


@ar.get("/settlements.csv")
def settlements_csv(month: str = "", a: Admin = Depends(admin_me), db: Session = Depends(get_db)):
    from fastapi.responses import Response
    month = month or datetime.now(IST).strftime("%Y-%m")
    rows = settlement_rows(db, month)
    head = "store_id,store,kind,city,orders,gross_inr,medicine_inr,lab_inr,cod_inr,online_inr,refunds_inr,fee_pct,fee_inr,payable_to_partner_inr,due_from_partner_inr,net_inr"
    lines = [head] + [",".join(str(r[k]).replace(",", " ") for k in ("storeId", "store", "kind", "city", "orders", "gross", "medicine", "lab", "cod", "online", "refunds", "feePct", "fee", "payableToPartner", "dueFromPartner", "net")) for r in rows]
    return Response("\n".join(lines) + "\n", media_type="text/csv", headers={"Content-Disposition": f'attachment; filename="settlements-{month}.csv"'})

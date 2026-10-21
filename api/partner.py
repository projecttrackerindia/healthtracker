"""Partner portal API (/api/partner): the lab, pharmacy or hospital side of TheHealthTracker.

A partner user signs in (signed HttpOnly cookie, like admin), sees the orders / bookings / visit requests for their store,
moves them through their statuses, uploads lab reports (encrypted into the family's document store, S3-backed), reads a
prescription the family chose to share, keeps the price list and store profile current, and messages the family.
Every change writes a Notice (and a push) to the family, so it shows up in the app within a minute.
"""
from __future__ import annotations

import os
import time

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import Response as RawResponse
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from . import storage
from .db import get_db
from .inbox import appt_json, msg_json, notify
from .models import Appointment, Household, LabTest, Message, Order, PartnerUser, Store, StoreItem, StoredFile, now
from .routes import STEPS_LAB, STEPS_MED, order_json
from .security import check_pw, hash_pw, sign, verify
from .seed import CATALOG, TESTS

r = APIRouter(prefix="/api/partner")
COOKIE = "dk_partner"
NEXT_MED = {"placed": ["checking", "cancelled"], "checking": ["packing", "cancelled"], "packing": ["out", "cancelled"], "out": ["delivered"], "delivered": [],
            "return_requested": ["returned", "refunded", "delivered"], "returned": ["refunded"], "refunded": [], "cancelled": []}
# A lab booking now has a person attached to it, so the walk from "confirmed" to "collected" is no longer one
# step. "assigned" names a technician; "en_route" is them setting off, which is what turns the family's live
# map on; "arrived" freezes it. Going straight from confirmed to collected is still allowed, because a family
# that walks into the lab never had a technician travelling to them.
NEXT_LAB = {"placed": ["confirmed", "cancelled"], "confirmed": ["assigned", "collected", "cancelled"],
            "assigned": ["en_route", "collected", "cancelled"], "en_route": ["arrived", "collected", "cancelled"],
            "arrived": ["collected", "cancelled"], "collected": ["processing"], "processing": ["ready"], "ready": [],
            "return_requested": ["processing", "refunded", "ready"], "refunded": [], "cancelled": []}
LABEL = dict(STEPS_MED + STEPS_LAB + [("cancelled", "Cancelled"), ("return_requested", "Return requested"), ("returned", "Returned"), ("refunded", "Refunded")])
ACTION = {"assigned": "Assign a technician", "en_route": "On the way", "arrived": "At the door", "checking": "Start checking", "packing": "Packed", "out": "Out for delivery", "delivered": "Delivered", "confirmed": "Confirm booking", "collected": "Sample collected",
          "processing": "In the lab", "ready": "Report ready", "cancelled": "Cancel", "returned": "Return received", "refunded": "Refund done"}


def alert_store(db: Session, store_id: str, subject: str, text: str) -> int:
    """Tell the store by email (owner address + every active sign-in) — they are not in the portal all day."""
    from . import messaging
    s = db.get(Store, store_id)
    if not s:
        return 0
    tos = {u.email for u in db.scalars(select(PartnerUser).where(PartnerUser.store_id == store_id, PartnerUser.active == True)).all()}  # noqa: E712
    if s.owner_email:
        tos.add(s.owner_email.strip().lower())
    n = 0
    for t in tos:
        if messaging.mail(t, f"[TheHealthTracker] {subject}", text + "\n\nOpen the partner portal: https://thehealthtracker.com/partner"):
            n += 1
    return n


def me(request: Request, db: Session = Depends(get_db)) -> PartnerUser:
    p = verify(request.cookies.get(COOKIE))
    if not p or p.get("k") != "partner":
        raise HTTPException(401, "login required")
    u = db.get(PartnerUser, p.get("id"))
    if not u or not u.active:
        raise HTTPException(401, "login required")
    return u


def my_store(db: Session, u: PartnerUser) -> Store:
    s = db.get(Store, u.store_id)
    if not s or not s.active:
        raise HTTPException(403, "This store is not active. Contact partner@thehealthtracker.com.")
    return s


def phone10(v: str | None) -> str:
    """The last ten digits, which is the part of an Indian mobile number that identifies it whether it was
    typed bare, with +91, with a leading 0, or with spaces in it."""
    return "".join(c for c in (v or "") if c.isdigit())[-10:]


def find_user(db: Session, ident: str) -> PartnerUser | None:
    """Who is signing in. A phlebotomist between houses remembers their phone number, not an email address the
    lab invented for them, so an identifier without an "@" is matched against the phone instead. The phone is
    kept unique among active sign-ins when one is added, so this cannot match two people."""
    ident = (ident or "").strip().lower()
    if not ident:
        return None
    if "@" in ident:
        return db.scalar(select(PartnerUser).where(PartnerUser.email == ident))
    digits = phone10(ident)
    if len(digits) < 10:
        return None
    rows = db.scalars(select(PartnerUser).where(PartnerUser.active == True,
                                                PartnerUser.phone.like(f"%{digits}")).limit(20)).all()  # noqa: E712
    hits = [u for u in rows if phone10(u.phone) == digits]
    return hits[0] if len(hits) == 1 else None


class Login(BaseModel):
    email: str
    password: str


@r.post("/login")
def login(body: Login, request: Request, response: Response, db: Session = Depends(get_db)):
    from .auth import clear as rl_clear, fail as rl_fail, guard as rl_guard

    rl_guard(request, "partner-login", 8, 900)
    u = find_user(db, body.email)
    if not u or not u.active or not check_pw(body.password, u.pw_hash):
        rl_fail(request, "partner-login", 900)
        raise HTTPException(401, "Wrong email or password.")
    rl_clear(request, "partner-login")
    u.last_login = now()
    response.set_cookie(COOKIE, sign({"id": u.id, "k": "partner"}), httponly=True, samesite="strict", secure=request.headers.get("x-forwarded-proto", request.url.scheme) == "https", max_age=12 * 3600, path="/")
    return me_json(db, u)


@r.post("/logout")
def logout(response: Response):
    response.delete_cookie(COOKIE, path="/")
    return {"ok": True}


def me_json(db: Session, u: PartnerUser) -> dict:
    s = db.get(Store, u.store_id)
    open_orders = db.scalar(select(func.count(Order.id)).where(Order.store_id == u.store_id, Order.status.notin_(("delivered", "ready", "cancelled", "refunded", "returned")))) or 0
    pending_appts = db.scalar(select(func.count(Appointment.id)).where(Appointment.store_id == u.store_id, Appointment.status == "requested")) or 0
    unread = db.scalar(select(func.count(Message.id)).where(Message.store_id == u.store_id, Message.sender == "family", Message.read_partner == False)) or 0  # noqa: E712
    return {"user": {"id": u.id, "name": u.name, "email": "" if u.email.endswith(".invalid") else u.email,
                     "phone": u.phone, "role": u.role, "mustChange": u.must_change,
                     "rating": u.rating or 0, "ratingN": u.rating_n or 0, "regNo": u.reg_no or ""},
            "store": {"id": s.id, "kind": s.kind, "name": s.name, "verified": s.verified, "active": s.active, "address": s.address, "area": s.area, "city": s.city, "phone": s.phone,
                      "hours": s.hours, "open24": s.open_24h, "licence": s.licence, "rating": s.rating, "ratingN": s.rating_n, "homeCollection": s.home_collection,
                      "collectionFee": s.collection_fee, "delivery": s.delivery, "deliveryFee": s.delivery_fee, "freeAbove": s.free_above, "etaMin": s.eta_min, "discount": s.discount_pct} if s else None,
            "counts": {"openOrders": open_orders, "pendingAppointments": pending_appts, "unreadMessages": unread}}


@r.get("/me")
def who(db: Session = Depends(get_db), u: PartnerUser = Depends(me)):
    return me_json(db, u)


class PwIn(BaseModel):
    current: str
    new: str


@r.post("/password")
def password(body: PwIn, db: Session = Depends(get_db), u: PartnerUser = Depends(me)):
    if not check_pw(body.current, u.pw_hash):
        raise HTTPException(400, "Current password is wrong.")
    if len(body.new) < 10:
        raise HTTPException(400, "Use at least 10 characters.")
    u.pw_hash, u.must_change = hash_pw(body.new), False
    return {"ok": True}


class RegIn(BaseModel):
    regNo: str


@r.post("/my-registration")
def my_registration(body: RegIn, db: Session = Depends(get_db), u: PartnerUser = Depends(me)):
    """A pharmacy owner who is themselves the registered pharmacist records their own number here. It is set
    once by the person it belongs to and is shown beside every prescription they sign off."""
    if u.role not in ("owner", "pharmacist"):
        raise HTTPException(403, "Only a pharmacist records a registration number.")
    reg = body.regNo.strip().upper()[:40]
    if len(reg) < 4:
        raise HTTPException(400, "Enter your State Pharmacy Council registration number.")
    u.reg_no = reg
    return {"ok": True, "regNo": reg}


# ---- orders and bookings ---------------------------------------------------------------------------------------------
def rx_age_days(d: str) -> int | None:
    """How old the prescription was, in days, from the date written on it. None when it was not recorded."""
    from datetime import date

    try:
        y, m, dd = (int(x) for x in (d or "").split("-"))
        return max(0, (date.today() - date(y, m, dd)).days)
    except Exception:
        return None


def _order(db: Session, u: PartnerUser, oid: str) -> Order:
    o = db.get(Order, oid)
    if not o or o.store_id != u.store_id:
        raise HTTPException(404, "order not found")
    return o


def porder(db: Session, o: Order) -> dict:
    j = order_json(o)
    h = db.get(Household, o.household_id)
    j["family"] = {"name": h.name if h else "", "city": h.city if h else ""}
    j["memberId"] = o.member_id or ""
    j["householdId"] = o.household_id
    j["rxFiles"] = [f for f in (o.rx_files or []) if db.get(StoredFile, (o.household_id, f))] if o.rx_shared else []
    # "assigned" is deliberately not a plain status button: it needs a person, so the console gets its own
    # Assign control instead and posts to /assign.
    j["next"] = [k for k in (NEXT_LAB if o.kind == "lab" else NEXT_MED).get(j["status"], []) if k != "assigned"]
    j["labels"] = {k: ACTION.get(k, LABEL.get(k, k)) for k in j["next"]}
    j["canAssign"] = o.kind == "lab" and j["status"] in ("confirmed", "assigned")
    if o.kind == "medicine":
        rx = [i for i in (o.items or []) if i.get("rx")]
        v = db.get(PartnerUser, o.verified_by) if o.verified_by else None
        j["rxItems"] = [i.get("name") for i in rx]
        j["needsVerify"] = bool(rx) and not o.verified_at
        j["verified"] = {"by": v.name or v.email if v else "", "regNo": v.reg_no if v else "",
                         "at": o.verified_at, "doctor": o.rx_doctor, "doctorReg": o.rx_reg_no,
                         "rxDate": o.rx_date, "rxAgeDays": rx_age_days(o.rx_date),
                         "note": o.verify_note} if o.verified_at else None
    j["hasReport"] = bool(db.get(StoredFile, (o.household_id, f"labrep_{o.id}")))
    if o.kind == "lab":
        a = db.get(PartnerUser, o.agent_id) if o.agent_id else None
        j["agent"] = {"id": a.id, "name": a.name or a.email, "phone": a.phone} if a else None
    return j


@r.get("/orders")
def orders(status: str = "open", db: Session = Depends(get_db), u: PartnerUser = Depends(me)):
    q = select(Order).where(Order.store_id == u.store_id)
    closed = ("delivered", "ready", "cancelled", "refunded", "returned")
    if status == "open":
        q = q.where(Order.status.notin_(closed))
    elif status == "closed":
        q = q.where(Order.status.in_(closed))
    rows = db.scalars(q.order_by(Order.created.desc()).limit(200)).all()
    return {"orders": [porder(db, o) for o in rows]}


class StatusIn(BaseModel):
    status: str
    note: str = ""


@r.post("/orders/{oid}/status")
def set_status(oid: str, body: StatusIn, db: Session = Depends(get_db), u: PartnerUser = Depends(me)):
    o = _order(db, u, oid)
    cur = order_json(o)["status"]
    allowed = (NEXT_LAB if o.kind == "lab" else NEXT_MED).get(cur, [])
    if body.status == "assigned":
        # Moving a booking to "assigned" without naming anybody is how the family's status line came to say
        # "Phlebotomist assigned" when no phlebotomist had been. Assignment happens one way: through the picker.
        raise HTTPException(400, "Choose the technician who is going — use Assign on the booking.")
    if body.status not in allowed:
        raise HTTPException(400, f"From '{LABEL.get(cur, cur)}' you can go to: {', '.join(LABEL.get(a, a) for a in allowed) or 'nothing'}.")
    if body.status == "ready" and not db.get(StoredFile, (o.household_id, f"labrep_{o.id}")):
        raise HTTPException(400, "Upload the report first; 'Report ready' sends it to the family.")
    if body.status == "packing" and o.kind == "medicine" and not o.verified_at and any(i.get("rx") for i in (o.items or [])):
        # The family's status line has said "Pharmacist checking" since the first version of this. Until a
        # registered pharmacist has actually signed the prescription off, it is a sentence we are making up.
        raise HTTPException(400, "A registered pharmacist must check the prescription before this is packed.")
    o.status = body.status
    o.timeline = (o.timeline or []) + [{"s": body.status, "t": now(), "by": u.email, "note": body.note[:200]}]
    s = my_store(db, u)
    title = f"{s.name}: {LABEL.get(body.status, body.status)}"
    bodytxt = {"out": "Your medicines are on the way.", "delivered": "Delivered. Rate the pharmacy in Orders.", "collected": "Sample collected; the report follows.",
               "ready": "Your report is in Lab results. Tap Analyse to read it in plain words.", "cancelled": body.note or "The partner cancelled this order.",
               "refunded": "Refund initiated; 5-7 working days.", "returned": "Return received."}.get(body.status, body.note or f"Order THT-{o.id}")
    notify(db, o.household_id, "order", title, bodytxt, {"order": o.id, "status": body.status, "kind": o.kind, "store": s.name}, o.member_id or "", "/app")
    return porder(db, o)


class AssignIn(BaseModel):
    agent: str


# ---- the collection team ---------------------------------------------------------------------------------------------
# A lab with a dozen phlebotomists and ordinary turnover cannot wait on our admin desk for every hire, and it is
# the lab — not us — that employs them, pays them and answers for them at a family's door. So the lab owner runs
# their own roster: we gate the store, the store gates its staff. Doctors stay with admin, because a medical
# council registration is ours to verify and nobody else's.
LIVE_JOB = ("assigned", "en_route", "arrived")


def _owner(u: PartnerUser = Depends(me)) -> PartnerUser:
    if u.role != "owner":
        raise HTTPException(403, "Only the store owner manages the team.")
    return u


def tech_json(db: Session, t: PartnerUser) -> dict:
    jobs = db.scalars(select(Order).where(Order.agent_id == t.id, Order.status.in_(LIVE_JOB))).all()
    on = next((o for o in jobs if o.status in ("en_route", "arrived")), None)
    # A technician added without an address of their own is keyed by a reserved .invalid one (RFC 2606, so it
    # can never reach anybody). It is an internal key, not an address, and is never shown or written to.
    real = "" if t.email.endswith(".invalid") else t.email
    return {"id": t.id, "name": t.name or real or t.phone, "email": real, "phone": t.phone, "active": t.active,
            "openJobs": len(jobs), "lastLogin": t.last_login, "mustChange": t.must_change,
            "rating": t.rating or 0, "ratingN": t.rating_n or 0,
            # What the owner needs to know before handing somebody another job: are they out on one already?
            "live": on.status if on else "", "liveOrder": on.id if on else ""}


# Roles a store may create for itself, and what each one needs before it can be created. A pharmacist's
# registration number is not paperwork: dispensing a prescription without a registered pharmacist is the
# offence, and the number is what makes a named person answerable for it. A technician needs a phone because
# the family is given it. Doctors are absent on purpose — a medical council registration is ours to verify.
SELF_ROLES = {
    "tech": {"kinds": ("lab",), "label": "technician", "reg": False, "team": "Collection team"},
    "pharmacist": {"kinds": ("pharmacy",), "label": "pharmacist", "reg": True, "team": "Pharmacists"},
}


def _role_spec(role: str) -> dict:
    spec = SELF_ROLES.get(role)
    if not spec:
        raise HTTPException(404, "unknown role")
    return spec


@r.get("/techs")
def techs(db: Session = Depends(get_db), u: PartnerUser = Depends(me)):
    """The collection team, for the assign picker and the roster screen."""
    rows = db.scalars(select(PartnerUser).where(PartnerUser.store_id == u.store_id,
                                                PartnerUser.role == "tech").order_by(PartnerUser.name)).all()
    return {"techs": [tech_json(db, t) for t in rows]}


@r.get("/pharmacists")
def pharmacists(db: Session = Depends(get_db), u: PartnerUser = Depends(me)):
    """Who at this pharmacy may sign off a prescription."""
    rows = db.scalars(select(PartnerUser).where(PartnerUser.store_id == u.store_id,
                                                PartnerUser.role == "pharmacist").order_by(PartnerUser.name)).all()
    return {"pharmacists": [staff_json(db, t) for t in rows]}


def staff_json(db: Session, t: PartnerUser) -> dict:
    real = "" if t.email.endswith(".invalid") else t.email
    return {"id": t.id, "name": t.name or real or t.phone, "email": real, "phone": t.phone, "role": t.role,
            "regNo": t.reg_no or "", "active": t.active, "lastLogin": t.last_login, "mustChange": t.must_change}


class TechIn(BaseModel):
    name: str
    phone: str
    email: str = ""
    regNo: str = ""
    role: str = "tech"


@r.post("/techs")
def tech_add(body: TechIn, db: Session = Depends(get_db), u: PartnerUser = Depends(_owner)):
    """Add somebody to the collection team and hand them a one-time password.

    Name and phone are both required and neither is decoration: the family is told who to expect and is given
    that number to call, which is the whole difference between a home visit and a stranger at the door."""
    import secrets

    s = my_store(db, u)
    spec = _role_spec(body.role)
    if s.kind not in spec["kinds"]:
        raise HTTPException(400, f"A {spec['label']} belongs to a {' or '.join(spec['kinds'])}.")
    name, digits = body.name.strip(), phone10(body.phone)
    if len(name) < 2:
        raise HTTPException(400, f"Enter the {spec['label']}'s full name.")
    if len(digits) != 10 or digits[0] not in "6789":
        raise HTTPException(400, "Enter a 10-digit Indian mobile number.")
    reg = body.regNo.strip().upper()[:40]
    if spec["reg"] and len(reg) < 4:
        # Not paperwork. Dispensing a prescription without a registered pharmacist is the offence, and this
        # number is what puts a named, registered person behind every order that goes out.
        raise HTTPException(400, "A pharmacist needs their State Pharmacy Council registration number.")
    # The phone is a sign-in identifier, so it has to point at one person.
    clash = [x for x in db.scalars(select(PartnerUser).where(PartnerUser.active == True,  # noqa: E712
                                                             PartnerUser.phone.like(f"%{digits}")).limit(20)).all()
             if phone10(x.phone) == digits]
    if clash:
        raise HTTPException(400, "That mobile number already signs in here.")
    email = body.email.strip().lower()
    if email:
        if "@" not in email:
            raise HTTPException(400, "That email address does not look right.")
        if db.scalar(select(PartnerUser.id).where(PartnerUser.email == email)):
            raise HTTPException(400, "That email already signs in here.")
    else:
        # No address of their own: the account is still keyed by one, because that column is the primary
        # sign-in everywhere else in the portal. They never type it — they sign in with their phone.
        email = f"{digits}@{body.role}.invalid"
    temp = secrets.token_urlsafe(6)
    t = PartnerUser(store_id=u.store_id, email=email, name=name[:80], phone=digits, role=body.role,
                    reg_no=reg, pw_hash=hash_pw(temp), must_change=True, active=True)
    db.add(t)
    db.flush()
    if not email.endswith(".invalid"):
        from . import messaging
        where = "https://thehealthtracker.com/tech" if body.role == "tech" else "https://thehealthtracker.com/partner"
        messaging.mail(email, f"Your sign-in · {s.name}",
                       f"Hello {name},\n\n{s.name} has added you as a {spec['label']}.\n\n"
                       f"Sign in: {where}\nUse your mobile {digits} or this email\n"
                       f"One-time password: {temp}\n\nYou will choose your own password the first time you sign in.")
    out = tech_json(db, t) if body.role == "tech" else staff_json(db, t)
    # Shown once, on the owner's screen, for them to pass on. It is never stored in the clear.
    out["tempPassword"] = temp
    out["signIn"] = digits
    return out


@r.post("/techs/{uid}/reset")
def tech_reset(uid: str, db: Session = Depends(get_db), u: PartnerUser = Depends(_owner)):
    """A forgotten password on a doorstep is a job that does not happen. The owner can fix it in a tap."""
    import secrets

    t = db.get(PartnerUser, uid)
    if not t or t.store_id != u.store_id or t.role not in SELF_ROLES:
        raise HTTPException(404, "Not one of your team.")
    temp = secrets.token_urlsafe(6)
    t.pw_hash, t.must_change, t.active = hash_pw(temp), True, True
    return {"id": t.id, "name": t.name, "tempPassword": temp, "signIn": t.phone}


class TechOff(BaseModel):
    active: bool


@r.post("/techs/{uid}/active")
def tech_active(uid: str, body: TechOff, db: Session = Depends(get_db), u: PartnerUser = Depends(_owner)):
    """Someone leaves, or is off sick. Turning them off stops them signing in; it does not touch work already
    in their hands, because a half-collected job still needs finishing."""
    t = db.get(PartnerUser, uid)
    if not t or t.store_id != u.store_id or t.role not in SELF_ROLES:
        raise HTTPException(404, "Not one of your team.")
    if not body.active:
        live = db.scalars(select(Order).where(Order.agent_id == t.id, Order.status.in_(("en_route", "arrived")))).all()
        if live:
            raise HTTPException(400, f"They are out on a collection right now (THT-{live[0].id}). Reassign it first.")
    t.active = bool(body.active)
    return tech_json(db, t) if t.role == "tech" else staff_json(db, t)


@r.post("/orders/{oid}/assign")
def assign(oid: str, body: AssignIn, db: Session = Depends(get_db), u: PartnerUser = Depends(me)):
    """Name the person who is going. The family is told who to expect, which is most of what a home visit
    needs — a stranger at the door with no name is the complaint every home-collection service gets."""
    o = _order(db, u, oid)
    if o.kind != "lab":
        raise HTTPException(400, "Only lab bookings have a technician.")
    t = db.get(PartnerUser, body.agent)
    if not t or t.store_id != u.store_id or t.role != "tech":
        raise HTTPException(404, "Not one of your technicians.")
    if not t.active:
        raise HTTPException(400, "That technician is not active.")
    if o.status not in ("confirmed", "assigned"):
        raise HTTPException(400, "Confirm the booking first.")
    o.agent_id = t.id
    if o.status != "assigned":
        o.status = "assigned"
    o.timeline = (o.timeline or []) + [{"s": "assigned", "t": now(), "by": u.email, "note": t.name or ""}]
    s = my_store(db, u)
    notify(db, o.household_id, "order", f"{s.name}: {t.name or 'Your technician'} is assigned",
           f"{t.name or 'A technician'} will collect your sample. You can call them from the app.",
           {"order": o.id, "status": "assigned", "kind": "lab", "agent": t.name or ""}, o.member_id or "", "/app")
    return porder(db, o)


# ---- dispensing a prescription ---------------------------------------------------------------------------------------
def _pharmacist(u: PartnerUser = Depends(me)) -> PartnerUser:
    """Who may sign a prescription off. An owner who is themselves the registered pharmacist qualifies; a
    counter assistant does not, which is the entire point of the registration number."""
    if u.role not in ("pharmacist", "owner"):
        raise HTTPException(403, "Only a registered pharmacist can check a prescription.")
    if not (u.reg_no or "").strip():
        raise HTTPException(403, "Add your State Pharmacy Council registration number before checking prescriptions.")
    if u.must_change:
        raise HTTPException(403, "Choose your own password first.")
    return u


# Doorstep delivery under MoHFW s.26B (26 March 2020) asks for a prescription no older than 30 days for a
# repeat of a chronic medicine and 7 days for an acute course. It is a flag here, never a block: the
# registered pharmacist is the professional, and software substituting its judgement for theirs is exactly
# what the Telemedicine Practice Guidelines forbid. We state the fact; they decide.
RX_AGE = {"chronicDays": 30, "acuteDays": 7,
          "note": "Doorstep delivery asks for a prescription no older than 30 days for a repeat, 7 for an acute course. "
                  "You are the registered pharmacist — this is a note, not a refusal."}


@r.get("/rx-rules")
def rx_rules(u: PartnerUser = Depends(me)):
    return RX_AGE


class VerifyIn(BaseModel):
    doctor: str = ""          # prescriber's name, as written on the prescription
    regNo: str = ""           # their medical council registration
    rxDate: str = ""          # the date on the prescription
    note: str = ""


@r.post("/orders/{oid}/verify")
def verify_rx(oid: str, body: VerifyIn, db: Session = Depends(get_db), u: PartnerUser = Depends(_pharmacist)):
    """A named, registered pharmacist signs this prescription off.

    What is recorded is who checked it, when, and the three things about the prescription that make it
    checkable afterwards: the prescriber, their registration number, and its date. Nothing about the order's
    contents is editable here, because Rule 65(11-A) forbids substitution outright — if a prescribed medicine
    cannot be supplied, the order is refused or part-supplied, never quietly swapped."""
    o = _order(db, u, oid)
    if o.kind != "medicine":
        raise HTTPException(400, "Only medicine orders carry a prescription.")
    if not any(i.get("rx") for i in (o.items or [])):
        raise HTTPException(400, "Nothing on this order needs a prescription.")
    if not o.rx_shared or not (o.rx_files or []):
        raise HTTPException(400, "The family has not shared a prescription yet. Message them to ask for it.")
    if o.verified_at:
        raise HTTPException(409, "This prescription has already been checked.")
    doctor, reg = body.doctor.strip()[:120], body.regNo.strip().upper()[:40]
    if len(doctor) < 3:
        raise HTTPException(400, "Enter the prescriber's name as written on the prescription.")
    if len(reg) < 4:
        raise HTTPException(400, "Enter the prescriber's registration number from the prescription.")
    o.verified_by, o.verified_at = u.id, now()
    o.rx_doctor, o.rx_reg_no, o.rx_date, o.verify_note = doctor, reg, body.rxDate.strip()[:10], body.note.strip()[:400]
    o.timeline = (o.timeline or []) + [{"s": "checking", "t": now(), "by": u.email,
                                        "note": f"Checked by {u.name or u.email} (Reg {u.reg_no})"}]
    s = my_store(db, u)
    notify(db, o.household_id, "order", f"{s.name}: prescription checked",
           f"{u.name or 'Our pharmacist'} has checked your prescription. Your order is being packed.",
           {"order": o.id, "status": "checking", "kind": "medicine"}, o.member_id or "", "/app")
    return porder(db, o)


class RefuseIn(BaseModel):
    reason: str


@r.post("/orders/{oid}/refuse")
def refuse_rx(oid: str, body: RefuseIn, db: Session = Depends(get_db), u: PartnerUser = Depends(_pharmacist)):
    """The pharmacist will not dispense this. The family is told plainly why, because "cancelled" with no
    reason sends them to another pharmacy to try the same prescription again."""
    o = _order(db, u, oid)
    if o.kind != "medicine":
        raise HTTPException(400, "Only medicine orders carry a prescription.")
    if o.status in ("out", "delivered", "cancelled"):
        raise HTTPException(400, "Too late to refuse this one.")
    reason = body.reason.strip()[:300]
    if len(reason) < 5:
        raise HTTPException(400, "Tell the family why — they will otherwise take the same prescription elsewhere.")
    o.status = "cancelled"
    o.timeline = (o.timeline or []) + [{"s": "cancelled", "t": now(), "by": u.email, "reason": reason,
                                        "note": f"Refused by {u.name or u.email} (Reg {u.reg_no})"}]
    s = my_store(db, u)
    notify(db, o.household_id, "order", f"{s.name}: prescription not dispensed", reason,
           {"order": o.id, "status": "cancelled", "kind": "medicine"}, o.member_id or "", "/app")
    return porder(db, o)


# ---- picking several orders at once ----------------------------------------------------------------------------------
# The list is what still needs picking, so an order leaves it the moment it is packed. Including "packing"
# here would leave every finished batch on the screen, and a list that does not shrink as you work it is one
# nobody trusts by the third batch of the morning.
PICKABLE = ("checking",)


@r.get("/picklist")
def picklist(db: Session = Depends(get_db), u: PartnerUser = Depends(me)):
    """Everything waiting to be packed, gathered by medicine rather than by order.

    A pharmacist with fifteen orders open does not walk the shelves fifteen times. They want to know that
    eighty-five strips of Amoxicillin come off one shelf, and which orders those eighty-five are for. So the
    lines come back aggregated, each carrying the orders that make it up.

    Orders whose prescription has not been checked are still listed, and said to be waiting, rather than
    quietly left out: a picker who cannot see why an order is missing will assume the list is wrong."""
    s = my_store(db, u)
    if s.kind != "pharmacy":
        raise HTTPException(400, "Pick lists are for pharmacies.")
    rows = db.scalars(select(Order).where(Order.store_id == s.id, Order.kind == "medicine",
                                          Order.status.in_(PICKABLE)).order_by(Order.created)).all()
    lines: dict[str, dict] = {}
    orders = []
    for o in rows:
        rx = [i for i in (o.items or []) if i.get("rx")]
        waiting = bool(rx) and not o.verified_at
        orders.append({"id": o.id, "member": o.member or "", "status": o.status, "created": o.created,
                       "items": len(o.items or []), "total": o.total, "waiting": waiting,
                       "ready": not waiting})
        for i in (o.items or []):
            key = i.get("sku") or i.get("name") or "?"
            ln = lines.setdefault(key, {"sku": i.get("sku", ""), "name": i.get("name") or key,
                                        "rx": bool(i.get("rx")), "qty": 0, "orders": [], "waiting": 0})
            q = int(i.get("qty") or 1)
            ln["qty"] += q
            ln["orders"].append({"id": o.id, "member": o.member or "", "qty": q, "waiting": waiting})
            if waiting:
                ln["waiting"] += q
    out = sorted(lines.values(), key=lambda x: (not x["rx"], -x["qty"], x["name"]))
    return {"lines": out, "orders": orders,
            "ready": sum(1 for o in orders if o["ready"]), "waiting": sum(1 for o in orders if o["waiting"])}


class BatchIn(BaseModel):
    orders: list[str]


@r.post("/batch/pack")
def batch_pack(body: BatchIn, db: Session = Depends(get_db), u: PartnerUser = Depends(me)):
    """Mark a picked batch packed, in one action.

    Each order is still put through the same single-order rules, and one that fails them does not stop the
    others — it comes back named, with the reason. A batch action that rolls everything back because one
    prescription is unchecked means the pharmacist does the whole batch again by hand."""
    from .routes import order_json

    s = my_store(db, u)
    done, skipped = [], []
    for oid in body.orders[:100]:
        o = db.get(Order, oid)
        if not o or o.store_id != s.id or o.kind != "medicine":
            skipped.append({"id": oid, "why": "not one of your orders"})
            continue
        cur = order_json(o)["status"]
        if cur == "packing":
            done.append(o.id)                      # already there; a second tap is a tap
            continue
        if cur != "checking":
            skipped.append({"id": o.id, "why": f"it is at '{LABEL.get(cur, cur)}', not checking"})
            continue
        if any(i.get("rx") for i in (o.items or [])) and not o.verified_at:
            skipped.append({"id": o.id, "why": "the prescription has not been checked"})
            continue
        o.status = "packing"
        o.timeline = (o.timeline or []) + [{"s": "packing", "t": now(), "by": u.email, "note": "picked in a batch"}]
        notify(db, o.household_id, "order", f"{s.name}: {LABEL.get('packing', 'Packing')}",
               "Your medicines are being packed.", {"order": o.id, "status": "packing", "kind": "medicine",
                                                    "store": s.name}, o.member_id or "", "/app")
        done.append(o.id)
    return {"packed": done, "skipped": skipped}


# ---- what the partner earned -----------------------------------------------------------------------------------------
@r.get("/earnings")
def earnings(months: int = 6, db: Session = Depends(get_db), u: PartnerUser = Depends(_owner)):
    """The store's own statement, month by month.

    A partner who cannot see what they earned will telephone to ask, every week, and will be right to. The
    figures here are the same computation the admin side settles against — not a second, friendlier one.

    Direction is spelled out rather than netted into a single number, because the two are different events: we
    transfer them what we hold, and they transfer us the fee on the cash they took at the door."""
    from datetime import datetime

    from .network import IST, fee_for, settlement_rows

    s = my_store(db, u)
    months = max(1, min(int(months or 6), 24))
    nowdt = datetime.now(IST)
    out = []
    y, m = nowdt.year, nowdt.month
    for _ in range(months):
        key = f"{y:04d}-{m:02d}"
        row = next((x for x in settlement_rows(db, key) if x["storeId"] == s.id), None)
        out.append({"month": key, "orders": row["orders"] if row else 0, "gross": row["gross"] if row else 0,
                    "lab": row["lab"] if row else 0, "medicine": row["medicine"] if row else 0,
                    "cash": row["cod"] if row else 0, "online": row["online"] if row else 0,
                    "refunds": row["refunds"] if row else 0,
                    "feePct": row["feePct"] if row else fee_for(s), "fee": row["fee"] if row else 0,
                    "weOweYou": row["payableToPartner"] if row else 0,
                    "youOweUs": row["dueFromPartner"] if row else 0,
                    "settled": bool(row and row["settled"]), "settledAt": row["settledAt"] if row else None,
                    "settledRef": row["settledRef"] if row else ""})
        m -= 1
        if m == 0:
            y, m = y - 1, 12
    return {"store": s.name, "commissionPct": fee_for(s), "months": out}


@r.get("/orders/{oid}/rx/{file_id}")
def read_rx(oid: str, file_id: str, db: Session = Depends(get_db), u: PartnerUser = Depends(me)):
    """The prescription the family chose to share with this order; nothing else in their vault is reachable."""
    o = _order(db, u, oid)
    if not o.rx_shared or file_id not in (o.rx_files or []):
        raise HTTPException(404, "not shared")
    got = storage.get(db, o.household_id, file_id)
    if not got:
        raise HTTPException(404, "not synced yet")
    row, data = got
    return RawResponse(data, media_type=row.mime, headers={"Cache-Control": "private, no-store", "Content-Disposition": f'inline; filename="{row.name or file_id}"'})


@r.put("/orders/{oid}/report")
async def upload_report(oid: str, request: Request, db: Session = Depends(get_db), u: PartnerUser = Depends(me)):
    """The lab's PDF goes straight into the family's encrypted document store under this booking."""
    o = _order(db, u, oid)
    if o.kind != "lab":
        raise HTTPException(400, "Reports belong to lab bookings.")
    data = await request.body()
    mime = (request.headers.get("content-type") or "").split(";")[0].strip()
    if not data or len(data) > storage.MAX_FILE:
        raise HTTPException(413, "PDF up to 15 MB")
    if mime not in ("application/pdf", "image/jpeg", "image/png"):
        raise HTTPException(415, "PDF or image only")
    s = my_store(db, u)
    name = request.headers.get("x-file-name", "")[:120] or f"{s.name} report {time.strftime('%d-%m-%Y')}"
    try:
        storage.put(db, o.household_id, f"labrep_{o.id}", data, mime, name, "partner:" + u.id)
        db.flush()
    except Exception as e:
        print("[partner] report store failed:", type(e).__name__, str(e)[:200], flush=True)
        raise HTTPException(502, "The report could not be stored right now; try again in a minute.")
    o.timeline = (o.timeline or []) + [{"s": "report_uploaded", "t": now(), "by": u.email}]
    if order_json(o)["status"] in ("placed", "confirmed", "collected", "processing"):
        o.status = "ready"
        o.timeline = o.timeline + [{"s": "ready", "t": now(), "by": u.email}]
    tests = ", ".join(i.get("name", "") for i in (o.items or [])[:3])
    notify(db, o.household_id, "lab_result", f"Report ready · {s.name}", f"{tests}. Open Lab results and tap Analyse to read it in plain words.",
           {"order": o.id, "fileId": f"labrep_{o.id}", "store": s.name, "name": name, "mime": mime, "size": len(data), "tests": [i.get("name", "") for i in (o.items or [])]}, o.member_id or "", "/app")
    return porder(db, o)


# ---- appointments (hospitals / clinics) -----------------------------------------------------------------------------------
@r.get("/appointments")
def appts(status: str = "open", db: Session = Depends(get_db), u: PartnerUser = Depends(me)):
    q = select(Appointment).where(Appointment.store_id == u.store_id)
    if status == "open":
        q = q.where(Appointment.status.in_(("requested", "confirmed", "rescheduled")))
    rows = db.scalars(q.order_by(Appointment.created.desc()).limit(200)).all()
    return {"appointments": [appt_json(db, a) for a in rows]}


class ApptAct(BaseModel):
    status: str
    slotDate: str = ""
    slotTime: str = ""
    doctor: str = ""
    note: str = ""


@r.post("/appointments/{aid}")
def appt_set(aid: str, body: ApptAct, db: Session = Depends(get_db), u: PartnerUser = Depends(me)):
    a = db.get(Appointment, aid)
    if not a or a.store_id != u.store_id:
        raise HTTPException(404)
    if body.status not in ("confirmed", "rescheduled", "declined", "done"):
        raise HTTPException(400, "status must be confirmed, rescheduled, declined or done")
    if body.status in ("confirmed", "rescheduled") and len(body.slotDate) != 10:
        raise HTTPException(400, "Give the confirmed date (and time).")
    a.status, a.updated, a.note = body.status, now(), body.note[:300]
    if body.slotDate:
        a.slot_date, a.slot_time = body.slotDate, body.slotTime[:8]
    if body.doctor:
        a.doctor = body.doctor[:80]
    s = my_store(db, u)
    when = f"{a.slot_date} {a.slot_time}".strip()
    msg = {"confirmed": f"Confirmed for {when}" + (f" with {a.doctor}" if a.doctor else ""), "rescheduled": f"New time offered: {when}. Open Appointments to accept or cancel.",
           "declined": body.note or "No slot available; please call the hospital.", "done": "Thank you for visiting. Add the prescription or report through the assistant."}[body.status]
    notify(db, a.household_id, "appointment", f"{s.name}: visit {body.status}", msg, {"appointment": a.id, "status": a.status, "store": s.name}, a.member_id, "/app")
    return appt_json(db, a)


# ---- price list and profile --------------------------------------------------------------------------------------------------
@r.get("/prices")
def prices(db: Session = Depends(get_db), u: PartnerUser = Depends(me)):
    s = my_store(db, u)
    if s.kind == "lab":
        have = {t.code: t for t in db.scalars(select(LabTest).where(LabTest.store_id == s.id)).all()}
        return {"kind": "lab", "tests": [{"code": c, "name": v[0], "typical": v[1], "price": have[c].price if c in have else None, "tat": have[c].tat_hours if c in have else v[2], "fasting": v[3]} for c, v in TESTS.items()]}
    have = {i.sku: i for i in db.scalars(select(StoreItem).where(StoreItem.store_id == s.id)).all()}
    return {"kind": s.kind, "items": [{"sku": x["id"], "name": x["name"], "form": x.get("form", ""), "cat": x.get("cat", ""), "mrp": x["mrp"], "rx": bool(x.get("rx")),
                                      "price": have[x["id"]].price if x["id"] in have else None, "stock": have[x["id"]].stock if x["id"] in have else 0} for x in CATALOG]}


class PricesIn(BaseModel):
    tests: list[dict] = []
    items: list[dict] = []


@r.put("/prices")
def set_prices(body: PricesIn, db: Session = Depends(get_db), u: PartnerUser = Depends(me)):
    s = my_store(db, u)
    n = 0
    if s.kind == "lab":
        have = {t.code: t for t in db.scalars(select(LabTest).where(LabTest.store_id == s.id)).all()}
        for t in body.tests:
            code = t.get("code")
            if code not in TESTS:
                continue
            price = t.get("price")
            if price in (None, "", 0):
                if code in have:
                    db.delete(have[code]); n += 1
                continue
            price = max(1, min(100000, int(price)))
            tat = max(1, min(720, int(t.get("tat") or TESTS[code][2])))
            if code in have:
                have[code].price, have[code].tat_hours = price, tat
            else:
                db.add(LabTest(store_id=s.id, code=code, name=TESTS[code][0], price=price, tat_hours=tat, fasting=TESTS[code][3]))
            n += 1
    else:
        cat = {x["id"]: x for x in CATALOG}
        have = {i.sku: i for i in db.scalars(select(StoreItem).where(StoreItem.store_id == s.id)).all()}
        for it in body.items:
            sku = it.get("sku")
            if sku not in cat:
                continue
            price = it.get("price")
            if price in (None, "", 0):
                if sku in have:
                    db.delete(have[sku]); n += 1
                continue
            price = max(1, min(100000, int(price)))
            stock = max(0, min(9999, int(it.get("stock") or 0)))
            if sku in have:
                have[sku].price, have[sku].stock = price, stock
            else:
                db.add(StoreItem(store_id=s.id, sku=sku, name=cat[sku]["name"], mrp=cat[sku]["mrp"], price=price, stock=stock))
            n += 1
    return {"ok": True, "changed": n}


class ProfileIn(BaseModel):
    phone: str = ""
    hours: str = ""
    open24: bool | None = None
    homeCollection: bool | None = None
    collectionFee: int | None = None
    delivery: bool | None = None
    deliveryFee: int | None = None
    freeAbove: int | None = None
    etaMin: int | None = None
    discount: float | None = None


@r.post("/prices/import")
async def import_prices(request: Request, db: Session = Depends(get_db), u: PartnerUser = Depends(me)):
    """CSV from the shop's own software: labs `code,price,tat_hours`; pharmacies `sku,price,mrp,stock`. Unknown codes/skus are reported, not guessed."""
    import csv
    import io
    s = my_store(db, u)
    data = (await request.body()).decode("utf-8", "ignore")
    rows = list(csv.DictReader(io.StringIO(data)))
    if not rows:
        raise HTTPException(400, "Empty CSV. First line must be the header.")
    rows = [{k.strip().lower(): (v or "").strip() for k, v in r.items() if k} for r in rows]
    n, skipped = 0, []
    if s.kind == "lab":
        have = {t.code: t for t in db.scalars(select(LabTest).where(LabTest.store_id == s.id)).all()}
        for r in rows:
            code = r.get("code", "").lower()
            if code not in TESTS:
                skipped.append(code or "?"); continue
            try:
                price = int(float(r.get("price") or 0))
            except ValueError:
                skipped.append(code); continue
            tat = int(float(r.get("tat_hours") or r.get("tat") or TESTS[code][2]))
            if code in have:
                have[code].price, have[code].tat_hours = price, max(1, min(720, tat))
            else:
                db.add(LabTest(store_id=s.id, code=code, name=TESTS[code][0], price=price, tat_hours=max(1, min(720, tat)), fasting=TESTS[code][3]))
            n += 1
    else:
        cat = {c["id"]: c for c in CATALOG}
        have = {i.sku: i for i in db.scalars(select(StoreItem).where(StoreItem.store_id == s.id)).all()}
        for r in rows:
            sku = r.get("sku", "").lower()
            if sku not in cat and sku not in have:
                skipped.append(sku or "?"); continue
            try:
                price = int(float(r.get("price") or 0)); mrp = int(float(r.get("mrp") or 0)) or price; stock = int(float(r.get("stock") or 0))
            except ValueError:
                skipped.append(sku); continue
            if price > mrp:
                skipped.append(sku + " (price > MRP)"); continue
            if sku in have:
                have[sku].price, have[sku].mrp, have[sku].stock = price, mrp, stock
            else:
                db.add(StoreItem(store_id=s.id, sku=sku, name=cat[sku]["name"], price=price, mrp=mrp, stock=stock))
            n += 1
    return {"updated": n, "skipped": skipped[:50], "skippedCount": len(skipped)}


@r.put("/profile")
def set_profile(body: ProfileIn, db: Session = Depends(get_db), u: PartnerUser = Depends(me)):
    s = my_store(db, u)
    if body.phone:
        s.phone = body.phone[:24]
    if body.hours:
        s.hours = body.hours[:80]
    for src, dst, lo, hi in (("collectionFee", "collection_fee", 0, 2000), ("deliveryFee", "delivery_fee", 0, 500), ("freeAbove", "free_above", 0, 100000), ("etaMin", "eta_min", 10, 10080)):
        v = getattr(body, src)
        if v is not None:
            setattr(s, dst, max(lo, min(hi, int(v))))
    for src, dst in (("open24", "open_24h"), ("homeCollection", "home_collection"), ("delivery", "delivery")):
        v = getattr(body, src)
        if v is not None:
            setattr(s, dst, bool(v))
    if body.discount is not None:
        s.discount_pct = max(0, min(50, float(body.discount)))
    return me_json(db, u)["store"]


# ---- messages with families -------------------------------------------------------------------------------------------------
@r.get("/threads")
def threads(db: Session = Depends(get_db), u: PartnerUser = Depends(me)):
    rows = db.scalars(select(Message).where(Message.store_id == u.store_id).order_by(Message.t.desc()).limit(600)).all()
    seen, out = {}, []
    for m in rows:
        if m.household_id in seen:
            if m.sender == "family" and not m.read_partner:
                seen[m.household_id]["unread"] += 1
            continue
        h = db.get(Household, m.household_id)
        seen[m.household_id] = {"household": m.household_id, "family": (h.name if h else "Family") or "Family", "city": h.city if h else "", "last": msg_json(m), "unread": 1 if (m.sender == "family" and not m.read_partner) else 0}
        out.append(seen[m.household_id])
    return {"threads": out}


@r.get("/threads/{hid}")
def thread(hid: str, db: Session = Depends(get_db), u: PartnerUser = Depends(me)):
    rows = db.scalars(select(Message).where(Message.store_id == u.store_id, Message.household_id == hid).order_by(Message.t.asc()).limit(300)).all()
    if not rows:
        raise HTTPException(404)
    for m in rows:
        if m.sender == "family":
            m.read_partner = True
    return {"messages": [msg_json(m) for m in rows]}


class PMsg(BaseModel):
    text: str


@r.post("/threads/{hid}")
def reply(hid: str, body: PMsg, db: Session = Depends(get_db), u: PartnerUser = Depends(me)):
    s = my_store(db, u)
    ok = db.scalar(select(Message.id).where(Message.store_id == s.id, Message.household_id == hid)) or db.scalar(select(Order.id).where(Order.store_id == s.id, Order.household_id == hid)) \
        or db.scalar(select(Appointment.id).where(Appointment.store_id == s.id, Appointment.household_id == hid))
    if not ok:
        raise HTTPException(403, "You can message families who have an order, booking or visit with you.")
    text = body.text.strip()[:2000]
    if not text:
        raise HTTPException(400, "empty")
    m = Message(household_id=hid, store_id=s.id, sender="partner", sender_name=u.name or s.name, text=text, read_partner=True)
    db.add(m)
    db.flush()
    notify(db, hid, "message", f"Message from {s.name}", text[:140], {"store": s.id, "storeName": s.name}, "", "/app")
    return msg_json(m)


@r.get("/thread-file/{hid}/{file_id}")
def thread_file(hid: str, file_id: str, db: Session = Depends(get_db), u: PartnerUser = Depends(me)):
    """A document the family attached in a message to this store."""
    m = db.scalar(select(Message).where(Message.store_id == u.store_id, Message.household_id == hid, Message.file_id == file_id, Message.sender == "family"))
    if not m:
        raise HTTPException(404)
    got = storage.get(db, hid, file_id)
    if not got:
        raise HTTPException(404, "not synced yet")
    row, data = got
    return RawResponse(data, media_type=row.mime, headers={"Cache-Control": "private, no-store"})

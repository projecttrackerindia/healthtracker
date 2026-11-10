"""Families (privacy-first support), DPDP data requests, company plans, messages & offers, the morning summary,
and practice mode."""
from __future__ import annotations

import re
import secrets
import time

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .admin import log, me as admin_me
from .db import get_db
from .models import (AccessGrant, Admin, Company, CompanyMember, Complaint, DataRequest, HealthRecord, Household, Notice, Offer, OfferUse, Order,
                     Person, Setting, Store, User, now)

ar = APIRouter(prefix="/api/admin")
fr = APIRouter(prefix="/api/v2")


def _user(request: Request, db: Session) -> User:
    from .auth import current_user
    u = current_user(request, db)
    if not u:
        raise HTTPException(401, "Sign in first")
    return u


def _mask_contact(v: str) -> str:
    if not v:
        return ""
    if "@" in v:
        a, _, d = v.partition("@")
        return a[:1] + "•••@" + d
    return v[:3] + " ••••• " + v[-4:]


# ---- families --------------------------------------------------------------------------------------------------------
@ar.get("/families")
def families(q: str = "", a: Admin = Depends(admin_me), db: Session = Depends(get_db)):
    """Find one family by a full mobile number or email. No browsing, no partial matches."""
    from .auth import norm_id
    from .console import mask
    q = (q or "").strip()
    if not q:
        return {"rows": [], "hint": "Enter a full mobile number or email."}
    try:
        kind, v = norm_id(q)
    except HTTPException:
        return {"rows": [], "hint": "Enter a full 10-digit mobile number or a complete email address."}
    u = db.scalar(select(User).where((User.email if kind == "email" else User.phone) == v))
    hh = [db.get(Household, u.household_id)] if u and u.household_id else []
    if not hh:
        hh = db.scalars(select(Household).where((Household.email if kind == "email" else Household.phone) == v)).all()
    log(db, a.email, "family.search", _mask_contact(v))
    return {"rows": [{"id": h.id, "name": mask(h.name), "city": h.city, "plan": h.plan} for h in hh if h]}


@ar.get("/families/{hid}")
def family(hid: str, a: Admin = Depends(admin_me), db: Session = Depends(get_db)):
    from .console import mask
    h = db.get(Household, hid)
    if not h:
        raise HTTPException(404)
    users = db.scalars(select(User).where(User.household_id == hid)).all()
    people = db.scalars(select(Person).where(Person.household_id == hid, Person.removed.is_(None))).all()
    orders = db.scalars(select(Order).where(Order.household_id == hid).order_by(Order.created.desc())).all()
    comps = db.scalars(select(Complaint).where(Complaint.household_id == hid).order_by(Complaint.created.desc())).all()
    g = db.scalar(select(AccessGrant).where(AccessGrant.household_id == hid).order_by(AccessGrant.created.desc()))
    t = now()
    grant = None
    if g:
        if g.status == "granted" and g.expires < t:
            g.status = "expired"
        grant = {"status": g.status, "by": g.admin_email, "expires": g.expires, "reason": g.reason}
    owner = users[0] if users else None
    log(db, a.email, "family.open", hid)
    out = {"id": h.id, "name": mask(h.name), "city": h.city, "plan": h.plan, "planUntil": h.plan_until, "created": h.created,
           "lastSeen": getattr(h, "last_seen", None), "members": len(people) or h.members,
           "people": [{"name": mask(p.name), "rel": "Has own sign-in" if p.owner_user else "Managed by the family", "managed": not p.owner_user} for p in people][:12],
           "account": {"mobile": _mask_contact(owner.phone) if owner else "", "mobileVerified": bool(owner and owner.phone_verified), "email": _mask_contact(owner.email) if owner else "",
                       "signIns": len(users)},
           "orders": len(orders), "paid": sum(o.total or 0 for o in orders if o.status not in ("cancelled", "refunded")),
           "recent": [{"id": o.id, "what": ", ".join(i.get("name", "") for i in (o.items or [])[:2]), "status": o.status, "total": o.total} for o in orders[:4]],
           "complaints": [{"id": c.id, "kind": c.kind, "status": c.status} for c in comps[:4]], "openSupport": sum(1 for c in comps if c.status != "resolved"),
           "grant": grant, "blocked": h.blocked}
    if g and g.status == "granted" and g.expires > t:
        recs = db.scalars(select(HealthRecord).where(HealthRecord.person_id.in_([p.id for p in people]), HealthRecord.kind == "report").order_by(HealthRecord.day.desc()).limit(20)).all()
        out["records"] = [{"day": r.day, "kind": r.kind} for r in recs]   # dates only: enough to see what's missing, never contents
        log(db, a.email, "family.records.view", hid)
    return out


class AskAccess(BaseModel):
    reason: str


@ar.post("/families/{hid}/ask-access")
def ask_access(hid: str, body: AskAccess, a: Admin = Depends(admin_me), db: Session = Depends(get_db)):
    from .inbox import notify
    h = db.get(Household, hid)
    if not h:
        raise HTTPException(404)
    if len(body.reason.strip()) < 8:
        raise HTTPException(400, "Tell the family why, in a sentence they'll understand.")
    g = AccessGrant(household_id=hid, admin_email=a.email, reason=body.reason.strip()[:300])
    db.add(g)
    db.flush()
    notify(db, hid, "access", "Urban Health support is asking to see your records",
           f"Reason: {g.reason}. Allow for 1 hour? You can say no. Every view is recorded.", {"grant": g.id})
    log(db, a.email, "family.access.ask", hid)
    return {"ok": True}


class GrantIn(BaseModel):
    allow: bool


@fr.post("/access/{gid}")
def answer_access(gid: str, body: GrantIn, request: Request, db: Session = Depends(get_db)):
    u = _user(request, db)
    g = db.get(AccessGrant, gid)
    if not g or g.household_id != u.household_id or g.status != "asked":
        raise HTTPException(404)
    g.status = "granted" if body.allow else "declined"
    g.expires = now() + 3600 if body.allow else 0
    return {"status": g.status}


class FamilyAct(BaseModel):
    action: str    # block | unblock


@ar.post("/families/{hid}/state")
def family_state(hid: str, body: FamilyAct, a: Admin = Depends(admin_me), db: Session = Depends(get_db)):
    h = db.get(Household, hid)
    if not h:
        raise HTTPException(404)
    if body.action not in ("block", "unblock"):
        raise HTTPException(400)
    h.blocked = body.action == "block"
    log(db, a.email, f"family.{body.action}", hid)
    return {"blocked": h.blocked}


# ---- data requests (DPDP) --------------------------------------------------------------------------------------------
DR_DAYS = 30


class DataReqIn(BaseModel):
    kind: str
    detail: str = ""


@fr.post("/data-requests")
def data_request(body: DataReqIn, request: Request, db: Session = Depends(get_db)):
    u = _user(request, db)
    if body.kind not in ("delete", "copy", "correct"):
        raise HTTPException(400, "Choose delete, copy or correct")
    if db.scalar(select(DataRequest).where(DataRequest.user_id == u.id, DataRequest.kind == body.kind, DataRequest.status == "open")):
        raise HTTPException(409, "You already have this request open. We'll tell you when it's done.")
    d = DataRequest(household_id=u.household_id or "", user_id=u.id, kind=body.kind, detail=re.sub(r"[<>\x00-\x1f]", "", body.detail)[:400], due=now() + DR_DAYS * 86400)
    db.add(d)
    return {"ok": True, "due": d.due}


@ar.get("/data-requests")
def data_requests(a: Admin = Depends(admin_me), db: Session = Depends(get_db)):
    from .console import mask
    rows = db.scalars(select(DataRequest).order_by(DataRequest.status.desc(), DataRequest.due)).all()
    out = []
    for d in rows[:200]:
        h = db.get(Household, d.household_id) if d.household_id else None
        out.append({"id": d.id, "kind": d.kind, "detail": d.detail, "via": d.via, "status": d.status, "due": d.due, "left": (d.due - now()) // 86400,
                    "who": mask(h.name if h else ""), "created": d.created, "note": d.done_note})
    return {"rows": out, "rules": {"days": DR_DAYS, "kept": "Invoices 8 years (tax law), audit log 400 days (CERT-In)"}}


class DataReqDone(BaseModel):
    note: str = ""
    erase: bool = False


@ar.post("/data-requests/{rid}")
def data_request_done(rid: str, body: DataReqDone, a: Admin = Depends(admin_me), db: Session = Depends(get_db)):
    from .auth import erase_user
    from .inbox import notify
    d = db.get(DataRequest, rid)
    if not d or d.status != "open":
        raise HTTPException(404)
    if d.kind == "delete" and body.erase:
        if a.role != "owner":
            raise HTTPException(403, "Only an owner can erase an account.")
        u = db.get(User, d.user_id)
        if u:
            erase_user(db, u)
    elif d.kind == "copy":
        notify(db, d.household_id, "data", "Your data is ready", "Open Family & Privacy → Download my data. The file is prepared on your phone and never emailed.", {}, to_user=d.user_id) if d.household_id else None
    elif d.kind == "correct":
        if len(body.note.strip()) < 5:
            raise HTTPException(400, "Say what was corrected.")
        notify(db, d.household_id, "data", "We corrected your details", body.note.strip()[:300], {}, to_user=d.user_id) if d.household_id else None
    d.status, d.done_at, d.done_note = "done", now(), body.note.strip()[:300]
    log(db, a.email, f"data_request.{d.kind}.done", rid)
    return {"ok": True}


# ---- companies -------------------------------------------------------------------------------------------------------
MIN_GROUP = 20


class CompanyIn(BaseModel):
    name: str
    hrEmail: str = ""
    plan: str = ""
    invited: int = 0
    price: int = 0


@ar.get("/companies")
def companies(a: Admin = Depends(admin_me), db: Session = Depends(get_db)):
    out = []
    for c in db.scalars(select(Company).order_by(Company.created.desc())).all():
        mem = db.scalars(select(CompanyMember).where(CompanyMember.company_id == c.id)).all()
        out.append({"id": c.id, "name": c.name, "code": c.code, "hrEmail": c.hr_email, "plan": c.plan, "invited": c.invited, "joined": len(mem),
                    "price": c.price, "invoice": c.price * len(mem), "active": c.active, "stats": company_stats(db, c, mem)})
    return {"rows": out, "minGroup": MIN_GROUP}


def company_stats(db: Session, c: Company, mem: list) -> dict | None:
    """Only totals, and only when at least MIN_GROUP people are counted: never a name or one person's report."""
    from .family import decrypt
    if len(mem) < MIN_GROUP:
        return None
    people = db.scalars(select(Person).where(Person.household_id.in_([m.household_id for m in mem]), Person.owner_user.in_([m.user_id for m in mem]))).all()
    tally = {"sugar": 0, "chol": 0, "vitd": 0}
    n = 0
    for p in people:
        r = db.scalar(select(HealthRecord).where(HealthRecord.person_id == p.id, HealthRecord.kind == "report").order_by(HealthRecord.day.desc()))
        if not r:
            continue
        try:
            fs = decrypt(r.blob).get("findings") or []
        except Exception:
            continue
        n += 1
        codes = {f.get("code"): f.get("flag") for f in fs}
        tally["sugar"] += codes.get("hba1c") == "high" or codes.get("glu_f") == "high"
        tally["chol"] += codes.get("ldl") == "high" or codes.get("tc") == "high"
        tally["vitd"] += codes.get("vitd") == "low"
    if n < MIN_GROUP:
        return None
    return {"counted": n, "sugar": round(100 * tally["sugar"] / n), "chol": round(100 * tally["chol"] / n), "vitd": round(100 * tally["vitd"] / n)}


@ar.post("/companies")
def add_company(body: CompanyIn, a: Admin = Depends(admin_me), db: Session = Depends(get_db)):
    name = re.sub(r"[<>\x00-\x1f]", "", body.name).strip()[:120]
    if len(name) < 2:
        raise HTTPException(400, "Enter the company name")
    code = re.sub(r"[^A-Z]", "", name.upper())[:5] + secrets.token_hex(2).upper()
    c = Company(name=name, code=code, hr_email=body.hrEmail.strip().lower()[:160], plan=body.plan.strip()[:160], invited=max(0, body.invited), price=max(0, body.price))
    db.add(c)
    log(db, a.email, "company.add", name)
    return {"id": c.id, "code": code}


class JoinCo(BaseModel):
    code: str


@fr.post("/company/join")
def join_company(body: JoinCo, request: Request, db: Session = Depends(get_db)):
    u = _user(request, db)
    c = db.scalar(select(Company).where(Company.code == body.code.strip().upper(), Company.active == True))  # noqa: E712
    if not c:
        raise HTTPException(404, "That company code isn't valid.")
    if db.scalar(select(CompanyMember).where(CompanyMember.company_id == c.id, CompanyMember.user_id == u.id)):
        return {"company": c.name, "plan": c.plan}
    db.add(CompanyMember(company_id=c.id, household_id=u.household_id or "", user_id=u.id))
    return {"company": c.name, "plan": c.plan, "note": "Your company sees only group totals, never your name or reports."}


# ---- messages & offers -----------------------------------------------------------------------------------------------
MESSAGES = [("otp", "Sign-in code", "SMS · email", True), ("lab_result", "Report is ready", "Push · SMS", True), ("report", "Report read", "Push", False),
            ("dose", "Medicine reminder", "Push", False), ("order", "Order updates", "Push · SMS", True), ("refill", "Refill in 5 days", "Push", False),
            ("family", "Family missed doses", "Push", False), ("complaint", "Reply to a complaint", "Push", False), ("access", "Support asks for access", "Push", False),
            ("invite", "Partner invite link", "SMS · email", True)]


def paused_kinds(db: Session) -> set[str]:
    s = db.get(Setting, "messages")
    return set((s.value or {}).get("paused", [])) if s else set()


@ar.get("/messages")
def messages(a: Admin = Depends(admin_me), db: Session = Depends(get_db)):
    t = now()
    sent = dict(db.execute(select(Notice.kind, func.count(Notice.id)).where(Notice.t > t - 86400).group_by(Notice.kind)).all())
    paused = paused_kinds(db)
    return {"rows": [{"kind": k, "name": n, "channel": ch, "sent": sent.get(k, 0), "dlt": dlt, "on": k not in paused} for k, n, ch, dlt in MESSAGES],
            "dltNote": "SMS wording must match a template registered on the Indian DLT registry (TRAI). Push and email need no registration."}


class MsgToggle(BaseModel):
    kind: str
    on: bool


@ar.post("/messages")
def toggle_message(body: MsgToggle, a: Admin = Depends(admin_me), db: Session = Depends(get_db)):
    if body.kind not in {k for k, *_ in MESSAGES}:
        raise HTTPException(400)
    if body.kind == "otp" and not body.on:
        raise HTTPException(400, "Sign-in codes can't be paused: people would be locked out.")
    s = db.get(Setting, "messages") or Setting(key="messages", value={})
    if s not in db:
        db.add(s)
    p = set((s.value or {}).get("paused", []))
    (p.discard if body.on else p.add)(body.kind)
    s.value = {**(s.value or {}), "paused": sorted(p)}
    log(db, a.email, f"message.{'on' if body.on else 'pause'} {body.kind}")
    return {"ok": True}


class OfferIn(BaseModel):
    code: str
    title: str
    applies: str = "lab"
    pct: int = 0
    flat: int = 0
    maxOff: int = 0
    budget: int
    once: bool = True
    ends: str


@ar.get("/offers")
def offers(a: Admin = Depends(admin_me), db: Session = Depends(get_db)):
    t = now()
    return {"rows": [{"code": o.code, "title": o.title, "applies": o.applies, "pct": o.pct, "flat": o.flat, "maxOff": o.max_off, "budget": o.budget, "spent": o.spent,
                      "uses": o.uses, "once": o.once, "ends": o.ends, "state": "Ended" if o.ends < t else "Budget used" if o.spent >= o.budget else "Live" if o.active else "Paused"}
                     for o in db.scalars(select(Offer).order_by(Offer.created.desc())).all()]}


@ar.post("/offers")
def add_offer(body: OfferIn, a: Admin = Depends(admin_me), db: Session = Depends(get_db)):
    code = body.code.strip().upper()
    if not re.fullmatch(r"[A-Z0-9]{4,20}", code):
        raise HTTPException(400, "Code: 4–20 letters or digits")
    if db.get(Offer, code):
        raise HTTPException(409, "That code exists")
    if body.applies not in ("lab", "package", "visit"):
        raise HTTPException(400, "Offers are for lab tests, packages or home visits only. Never prescription medicines.")
    if not (0 < body.pct <= 50) and not (0 < body.flat <= 2000):
        raise HTTPException(400, "Either a % off (up to 50) or a flat amount (up to ₹2,000)")
    if body.budget <= 0 or body.budget > 1000000:
        raise HTTPException(400, "Every offer needs a total budget (up to ₹10 L)")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", body.ends):
        raise HTTPException(400, "Every offer needs an end date")
    ends = int(time.mktime(time.strptime(body.ends, "%Y-%m-%d"))) + 86399
    if ends < now() or ends > now() + 180 * 86400:
        raise HTTPException(400, "End date must be within the next 6 months")
    db.add(Offer(code=code, title=re.sub(r"[<>]", "", body.title)[:160], applies=body.applies, pct=body.pct, flat=body.flat, max_off=max(0, body.maxOff),
                 budget=body.budget, once=body.once, ends=ends))
    log(db, a.email, "offer.add", code)
    return {"ok": True}


@ar.post("/offers/{code}/toggle")
def toggle_offer(code: str, a: Admin = Depends(admin_me), db: Session = Depends(get_db)):
    o = db.get(Offer, code)
    if not o:
        raise HTTPException(404)
    o.active = not o.active
    log(db, a.email, f"offer.{'on' if o.active else 'pause'}", code)
    return {"active": o.active}


def apply_offer(db: Session, code: str, household_id: str, kind: str, items: list, subtotal: int) -> int:
    """How much an offer takes off. Refuses prescription items outright, respects budget, end date and once-per-family."""
    o = db.get(Offer, (code or "").strip().upper())
    t = now()
    if not o or not o.active or o.ends < t or o.spent >= o.budget:
        raise HTTPException(400, "This offer has ended.")
    if any(i.get("rx") for i in items) or kind == "medicine":
        raise HTTPException(400, "Offers can't be used on medicines.")
    if o.once and db.scalar(select(OfferUse).where(OfferUse.code == o.code, OfferUse.household_id == household_id)):
        raise HTTPException(400, "Your family has already used this offer.")
    off = round(subtotal * o.pct / 100) if o.pct else o.flat
    if o.max_off:
        off = min(off, o.max_off)
    return max(0, min(off, subtotal, o.budget - o.spent))


@fr.post("/offers/check")
def check_offer(body: dict, request: Request, db: Session = Depends(get_db)):
    u = _user(request, db)
    off = apply_offer(db, str(body.get("code", "")), u.household_id or "", str(body.get("kind", "lab")), body.get("items") or [], int(body.get("subtotal") or 0))
    return {"off": off}


# ---- morning summary -------------------------------------------------------------------------------------------------
def summary_text(db: Session) -> str:
    from .console import today as console_today
    owner = db.scalar(select(Admin).where(Admin.role == "owner"))
    d = console_today(days=1, a=owner, db=db)
    k = {x["label"]: x["value"] for x in d["kpi"]}
    lines = [f"Yesterday · {time.strftime('%a %d %b', time.gmtime(now() + 19800 - 86400))}", "",
             f"Orders completed: {k.get('Orders completed', 0)} · ₹{k.get('Gross value', 0):,}",
             f"On-time home visits: {k.get('On-time home visits') if k.get('On-time home visits') is not None else '—'}%",
             f"Reports read: {k.get('Reports read', 0)}", ""]
    lines += ["Needs you today:"] + [f"• {n['title']}" for n in d["needs"][:6]] if d["needs"] else ["Nothing needs you today."]
    return "\n".join(lines)


def send_morning_summary(db: Session) -> int:
    """Called by the scheduler at 8 am IST. Email only: WhatsApp needs a business account and approved templates."""
    from . import messaging
    if not messaging.email_ready():
        return 0
    s = db.get(Setting, "summary_sent")
    day = time.strftime("%Y-%m-%d", time.gmtime(now() + 19800))
    if s and (s.value or {}).get("day") == day:
        return 0
    text = summary_text(db)
    n = 0
    for a in db.scalars(select(Admin).where(Admin.role.in_(("owner", "ops")), Admin.summary == True)).all():  # noqa: E712
        try:
            messaging.send_mail(a.email, "Urban Health · your morning summary", f"Good morning,\n\n{text}\n\nOpen admin: https://urbanhealth.in/admin")
            n += 1
        except Exception as e:
            print("[summary] failed:", str(e)[:120], flush=True)
    s = s or Setting(key="summary_sent", value={})
    if s not in db:
        db.add(s)
    s.value = {"day": day, "sent": n}
    return n


@ar.get("/summary")
def summary_preview(a: Admin = Depends(admin_me), db: Session = Depends(get_db)):
    from . import messaging
    return {"text": summary_text(db), "on": a.summary, "emailReady": messaging.email_ready()}


@ar.post("/summary")
def summary_toggle(a: Admin = Depends(admin_me), db: Session = Depends(get_db)):
    a.summary = not a.summary
    return {"on": a.summary}


# ---- practice mode ---------------------------------------------------------------------------------------------------
PRACTICE = "Practice"


def practice_store(db: Session) -> Store | None:
    return db.scalar(select(Store).where(Store.notes == "practice"))


@ar.post("/practice/{what}")
def practice(what: str, a: Admin = Depends(admin_me), db: Session = Depends(get_db)):
    """Fake orders on a fake partner and a fake family, never shown to real families or in the public pages.
    'clear' removes all of it."""
    s = practice_store(db)
    if what == "clear":
        if s:
            for o in db.scalars(select(Order).where(Order.store_id == s.id)).all():
                db.delete(o)
            h = db.scalar(select(Household).where(Household.key == "practice-family"))
            if h:
                for c in db.scalars(select(Complaint).where(Complaint.household_id == h.id)).all():
                    db.delete(c)
            s.active = False
        log(db, a.email, "practice.clear")
        return {"ok": True}
    if not s:
        s = Store(kind="lab", name="Practice Lab (not real)", area="Practice", city="Practice", lat=0.0, lng=0.0, verified=False, active=True, notes="practice")
        db.add(s)
        db.flush()
    s.active = True
    h = db.scalar(select(Household).where(Household.key == "practice-family")) or Household(key="practice-family", name="Practice Family", city="Practice")
    if h not in db:
        db.add(h)
        db.flush()
    t = now()
    if what == "order":
        o = Order(household_id=h.id, store_id=s.id, kind="lab", items=[{"name": "CBC (practice)"}], total=299, member="Practice", status="placed", timeline=[{"s": "placed", "t": t}], slot="7:00–8:00 am")
        db.add(o)
    elif what == "late":
        o = Order(household_id=h.id, store_id=s.id, kind="lab", items=[{"name": "Thyroid (practice)"}], total=449, member="Practice", status="en_route",
                  timeline=[{"s": "placed", "t": t - 7200}, {"s": "en_route", "t": t - 3600}], created=t - 7200, slot="7:00–8:00 am")
        db.add(o)
    elif what == "complaint":
        o = Order(household_id=h.id, store_id=s.id, kind="lab", items=[{"name": "HbA1c (practice)"}], total=399, member="Practice", status="ready", timeline=[{"s": "ready", "t": t}])
        db.add(o)
        db.flush()
        db.add(Complaint(household_id=h.id, order_id=o.id, kind="missed_visit", text="(Practice) The technician did not come.", lang="te", due=t + 6 * 3600,
                         thread=[{"by": "family", "text": "(Practice) The technician did not come.", "t": t}]))
    else:
        raise HTTPException(400)
    log(db, a.email, f"practice.{what}")
    return {"ok": True}

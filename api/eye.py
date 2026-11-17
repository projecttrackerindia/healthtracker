"""Eye exams from partner eye hospitals (/api/partner/eye).

A verified doctor at the hospital opens a confirmed or finished visit, enters the readings for each eye, marks findings on
the 3D eye and writes a few plain words for the patient. Saving does three things:

* keeps the exam on the visit (Appointment.eye), so the hospital sees this patient's earlier exams at the next visit;
* writes it into the patient's own encrypted records as kind "eye" (read at the "summary" level, like reports), which is
  what the app's Eyes page shows, pinned on the 3D eye;
* tells the family, with a link straight to the Eyes page.

Families cannot create or edit "eye" records themselves (people.py refuses the kind): an exam always comes from a doctor.
Numbers are checked against what an eye can actually measure, so a slip of the keyboard never reaches a patient's phone.
"""
from __future__ import annotations

import datetime as _dt
import re

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from .consult import _doctor, _store_appt
from .db import get_db
from .family import encrypt
from .inbox import notify
from .models import Appointment, HealthRecord, PartnerUser, Person, now
from .partner import me as partner_me
from .partner import my_store

pr = APIRouter(prefix="/api/partner")

OPEN = ("confirmed", "rescheduled", "done")
TONES = ("ok", "watch", "alert")
# where a finding may be pinned: the eyeball parts of the 3D eye and the socket / pathway parts of the body model
PART = re.compile(r"^(cornea|iris|pupil|lens|nucleus|zonules|ciliary|anterior chamber|posterior chamber|trabecular|schlemm|conjunctiva|sclera|choroid|retina|vitreous|macula|disc|vessels|optic nerve|ganglion|optic radiation|(Right|Left) [A-Za-z ()-]{3,60})$")
RANGES = {"iop": (0, 80), "cct": (300, 800), "cd": (0, 1), "oct": (100, 900)}


class EyeSide(BaseModel):
    vision: str = Field("", max_length=12)    # 6/6, 6/9, CF 2m, HM, PL ...
    sph: str = Field("", max_length=8)
    cyl: str = Field("", max_length=8)
    axis: str = Field("", max_length=4)
    add: str = Field("", max_length=8)
    near: str = Field("", max_length=8)       # near vision, N6, N8 ...
    iop: float | None = None                  # mmHg
    cct: float | None = None                  # µm
    cd: float | None = None                   # cup-to-disc ratio
    oct: float | None = None                  # central macular thickness, µm
    angle: str = Field("", max_length=40)
    lens: str = Field("", max_length=60)
    retina: str = Field("", max_length=80)


class Finding(BaseModel):
    part: str = Field(..., max_length=70)
    side: str = "R"
    label: str = Field(..., max_length=80)
    tone: str = "watch"


class Glasses(BaseModel):
    """A glasses quote from this optical counter: what is made, what it costs, when it is ready. The family
    replies to order; nothing is charged from here."""
    lens: str = Field("", max_length=60)
    lensPrice: int = Field(0, ge=0, le=200000)
    frame: str = Field("", max_length=60)
    framePrice: int = Field(0, ge=0, le=200000)
    ready: str = Field("", max_length=40)
    delivery: str = Field("", max_length=20)   # "home" | "pickup"
    inStock: bool = False


class ExamIn(BaseModel):
    R: EyeSide = EyeSide()
    L: EyeSide = EyeSide()
    findings: list[Finding] = []
    note: str = Field("", max_length=600)     # plain words for the patient
    dx: str = Field("", max_length=160)       # diagnosis, for the hospital's own record
    colour: str = Field("", max_length=24)    # colour vision, e.g. "Ishihara 14 of 14"
    squint: str = Field("", max_length=40)    # cover test result, e.g. "None"
    glasses: Glasses | None = None             # the quote sent to the family with the prescription


POWER = re.compile(r"^[+-]?\d{1,2}(\.\d{1,2})?$")


def _side(s: EyeSide, which: str) -> dict:
    out = {}
    for k in ("vision", "near", "angle", "lens", "retina"):
        v = re.sub(r"\s+", " ", getattr(s, k) or "").strip()
        if v:
            out[k] = v
    for k in ("sph", "cyl", "add"):
        v = (getattr(s, k) or "").strip().replace("−", "-")
        if v:
            if not POWER.fullmatch(v) or abs(float(v)) > 30:
                raise HTTPException(400, f"{which} eye: {k.upper()} should look like -2.25 or +1.50.")
            out[k] = ("+" if float(v) > 0 and not v.startswith("+") else "") + v
    if s.axis.strip():
        if not s.axis.strip().isdigit() or not 0 <= int(s.axis) <= 180:
            raise HTTPException(400, f"{which} eye: axis is 0 to 180.")
        out["axis"] = s.axis.strip()
    for k, (lo, hi) in RANGES.items():
        v = getattr(s, k)
        if v is None:
            continue
        if not lo <= v <= hi:
            names = {"iop": "Eye pressure", "cct": "Cornea thickness", "cd": "Cup-to-disc ratio", "oct": "Macula thickness"}
            raise HTTPException(400, f"{which} eye: {names[k]} should be between {lo} and {hi}.")
        out[k] = round(v, 2) if k == "cd" else round(v)
    return out


def exam_json(a: Appointment) -> dict:
    return {"id": a.id, "memberName": a.member_name or "", "memberId": a.member_id or "", "date": a.slot_date or a.date or "", "time": a.slot_time or a.time or "",
            "why": a.why or "", "doctor": a.doctor or "", "status": a.status, "kind": a.kind, "exam": a.eye or None}


def _mine(u: PartnerUser, a: Appointment) -> bool:
    if u.role != "doctor" or not a.doctor:
        return True
    d = a.doctor.lower().replace("dr.", "").replace("dr ", "").strip()
    return d == u.name.lower().replace("dr.", "").replace("dr ", "").strip()


@pr.get("/eye/visits")
def visits(db: Session = Depends(get_db), u: PartnerUser = Depends(partner_me)):
    """Visits a doctor can examine: confirmed, rescheduled and recently finished ones at this hospital, newest first."""
    rows = db.scalars(select(Appointment).where(Appointment.store_id == u.store_id, Appointment.status.in_(OPEN))
                      .order_by(Appointment.updated.desc()).limit(150)).all()
    return {"visits": [exam_json(a) for a in rows if _mine(u, a)]}


@pr.get("/eye/visits/{aid}")
def visit(aid: str, db: Session = Depends(get_db), u: PartnerUser = Depends(partner_me)):
    """One visit, its exam if written, and this patient's earlier exams at this hospital (for the trend)."""
    a = _store_appt(db, u, aid)
    hist = []
    if a.member_id:
        for b in db.scalars(select(Appointment).where(Appointment.store_id == u.store_id, Appointment.household_id == a.household_id,
                                                      Appointment.member_id == a.member_id, Appointment.id != a.id)
                            .order_by(Appointment.updated.desc()).limit(20)):
            if b.eye:
                hist.append(b.eye)
    return {"visit": exam_json(a), "history": hist[:8]}


@pr.put("/eye/visits/{aid}")
def save(aid: str, body: ExamIn, db: Session = Depends(get_db), u: PartnerUser = Depends(partner_me)):
    _doctor(db, u)
    a = _store_appt(db, u, aid)
    if a.status not in OPEN:
        raise HTTPException(400, "Examine a confirmed or finished visit.")
    if not a.member_id:
        raise HTTPException(400, "This visit is not linked to a family member, so it cannot be sent to their app.")
    p = db.get(Person, a.member_id)
    if not p or p.household_id != a.household_id or p.removed:
        raise HTTPException(400, "This patient's profile is no longer in their family app.")
    R, L = _side(body.R, "Right"), _side(body.L, "Left")
    if not (R or L or body.findings or body.note.strip() or body.colour.strip() or body.squint.strip()):
        raise HTTPException(400, "Enter a reading, a finding or a note.")
    if len(body.findings) > 12:
        raise HTTPException(400, "Up to 12 findings.")
    fs = []
    for f in body.findings:
        part, label = f.part.strip(), re.sub(r"\s+", " ", f.label).strip()
        if not PART.fullmatch(part):
            raise HTTPException(400, "Pick the part on the 3D eye.")
        if not label:
            raise HTTPException(400, "Every finding needs a few words.")
        fs.append({"part": part, "side": f.side if f.side in ("R", "L", "B") else "R", "label": label, "tone": f.tone if f.tone in TONES else "watch"})
    s = my_store(db, u)
    day = _dt.date.today().isoformat()
    exam = {"date": day, "store": s.name, "doctor": u.name, "specialty": u.specialty or "", "R": R, "L": L, "findings": fs,
            "note": body.note.strip(), "appt": a.id, "t": now()}
    if body.dx.strip():
        exam["dx"] = body.dx.strip()
    for k in ("colour", "squint"):
        v = re.sub(r"\s+", " ", getattr(body, k) or "").strip()
        if v:
            exam[k] = v
    g = body.glasses
    if g and (g.lens.strip() or g.frame.strip()):
        exam["glasses"] = {"lens": g.lens.strip(), "lensPrice": g.lensPrice, "frame": g.frame.strip(), "framePrice": g.framePrice,
                           "total": g.lensPrice + g.framePrice, "ready": g.ready.strip(), "delivery": g.delivery if g.delivery in ("home", "pickup") else "",
                           "inStock": bool(g.inStock)}
        prev = (a.eye or {}).get("glasses") or {}
        for k in ("status", "pay", "paid", "payRef", "orderedAt"):     # an edited exam never forgets the order or the payment
            if k in prev:
                exam["glasses"][k] = prev[k]
    first = not a.eye
    rid = (a.eye or {}).get("rid", "")
    x = db.get(HealthRecord, rid) if rid else None
    if x and x.person_id == p.id and x.kind == "eye":
        x.blob, x.day = encrypt(exam), day
    else:
        x = HealthRecord(person_id=p.id, kind="eye", blob=encrypt(exam), day=day, by_user=("partner:" + u.id)[:32])
        db.add(x)
        db.flush()
    a.eye = {**exam, "rid": x.id}
    a.updated = now()
    watch = [f["label"] for f in fs if f["tone"] != "ok"]
    notify(db, a.household_id, "eye", f"Dr {u.name} sent {'your' if first else 'an update to your'} eye check",
           ((watch[0] + (" · " + str(len(watch) - 1) + " more" if len(watch) > 1 else "") if watch else "Readings and notes, shown on your eye in 3D.")
            + (f" Glasses ₹{exam['glasses']['total']:,}{' · ready ' + exam['glasses']['ready'] if exam['glasses']['ready'] else ''}: reply to order." if exam.get("glasses") else ""))[:200],
           {"appointment": a.id, "person": p.id, "store": s.name, "doctor": u.name, "glasses": exam.get("glasses")}, a.member_id, "/app#eye=" + p.id)
    db.commit()
    return {"visit": exam_json(a)}


# ---- glasses: the family orders the quote and pays online or at the counter ------------------------------------------------

from .auth import need_user  # noqa: E402
from .models import User  # noqa: E402

fr = APIRouter(prefix="/api/v2/glasses")
GSTEP = ("quoted", "ordered", "ready", "delivered")


def glasses_json(a: Appointment, store_name: str = "") -> dict:
    g = (a.eye or {}).get("glasses") or {}
    return {"id": a.id, "member": a.member_name or "", "memberId": a.member_id or "", "store": store_name, "doctor": a.doctor or "",
            "lens": g.get("lens", ""), "lensPrice": g.get("lensPrice", 0), "frame": g.get("frame", ""), "framePrice": g.get("framePrice", 0),
            "total": g.get("total", 0), "ready": g.get("ready", ""), "delivery": g.get("delivery", ""), "inStock": g.get("inStock", False),
            "status": g.get("status", "quoted"), "pay": g.get("pay", ""), "paid": bool(g.get("paid")), "orderedAt": g.get("orderedAt")}


@fr.get("")
def family_glasses(db: Session = Depends(get_db), u: User = Depends(need_user)):
    if not u.household_id:
        return {"glasses": []}
    from .models import Store
    rows = db.scalars(select(Appointment).where(Appointment.household_id == u.household_id).order_by(Appointment.updated.desc()).limit(60)).all()
    out = []
    for a in rows:
        if (a.eye or {}).get("glasses"):
            st = db.get(Store, a.store_id) if getattr(a, "store_id", None) else None
            out.append(glasses_json(a, st.name if st else ""))
    return {"glasses": out}


class GOrder(BaseModel):
    pay: str = "counter"     # counter | online (online is settled by Razorpay, see rzp.py kind "glasses")


@fr.post("/{aid}/order")
def family_order(aid: str, body: GOrder, db: Session = Depends(get_db), u: User = Depends(need_user)):
    a = db.get(Appointment, aid)
    if not a or not u.household_id or a.household_id != u.household_id or not (a.eye or {}).get("glasses"):
        raise HTTPException(404)
    g = dict(a.eye["glasses"])
    if g.get("status", "quoted") == "quoted":
        g.update({"status": "ordered", "pay": "online" if body.pay == "online" else "counter", "orderedAt": now()})
        a.eye = {**a.eye, "glasses": g}
        a.updated = now()
    return glasses_json(a)


class GStep(BaseModel):
    status: str


@pr.post("/eye/{aid}/glasses")
def partner_glasses_step(aid: str, body: GStep, db: Session = Depends(get_db), u: PartnerUser = Depends(partner_me)):
    """The optical counter moves the order on: ready (for pickup or on its way), then delivered."""
    s = my_store(db, u)
    a = db.get(Appointment, aid)
    if not a or getattr(a, "store_id", None) != s.id or not (a.eye or {}).get("glasses"):
        raise HTTPException(404)
    if body.status not in ("ready", "delivered"):
        raise HTTPException(400, "Choose ready or delivered")
    g = dict(a.eye["glasses"])
    if g.get("status") not in ("ordered", "ready"):
        raise HTTPException(400, "The family has not ordered these glasses yet.")
    g["status"] = body.status
    a.eye = {**a.eye, "glasses": g}
    a.updated = now()
    who = (a.member_name or "").split(" ")[0] or "Your"
    if body.status == "ready":
        notify(db, a.household_id, "order", "Your glasses are ready",
               (f"{s.name} is sending them to you." if g.get("delivery") == "home" else f"Collect them from {s.name}.")
               + ("" if g.get("paid") else f" ₹{g.get('total', 0):,} to pay."), {"appointment": a.id, "glasses": True}, a.member_id or "", "/app")
    return glasses_json(a, s.name)

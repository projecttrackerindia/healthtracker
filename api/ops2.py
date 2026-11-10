"""Phase 2 of the admin console: the prescription check, two-person approvals, and complaints with deadlines."""
from __future__ import annotations

import csv
import io
import re
import secrets
import time

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response as RawResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import storage
from .admin import log, me as admin_me
from .db import get_db
from .models import Admin, Approval, Complaint, Order, now

ar = APIRouter(prefix="/api/admin")
fr = APIRouter(prefix="/api/v2")

REFUND_LIMIT = 5000
# Habit-forming medicines (Schedule H1 / X and NDPS) that must never be dispensed without a careful look.
HABIT = re.compile(r"(?i)alprazolam|clonazepam|lorazepam|diazepam|nitrazepam|zolpidem|codeine|tramadol|tapentadol|pregabalin|"
                   r"buprenorphine|morphine|fentanyl|pentazocine|phenobarbit|methylphenid|ketamine|cough syrup.*codeine")


# ---- prescription check ----------------------------------------------------------------------------------------------
def _rx_orders(db: Session):
    return [o for o in db.scalars(select(Order).where(Order.kind == "medicine", Order.status.in_(("placed", "checking"))).order_by(Order.created)).all()
            if any(i.get("rx") for i in (o.items or []))]


def rx_checks(o: Order) -> list[dict]:
    items = o.items or []
    out = [{"ok": bool(o.rx_shared and o.rx_files), "text": "Prescription shared by the family" if o.rx_shared and o.rx_files else "No prescription shared yet"}]
    habit = [i.get("name", "") for i in items if HABIT.search(i.get("name", ""))]
    out.append({"ok": not habit, "text": "No habit-forming (Schedule H1/X) medicines" if not habit else "Habit-forming: " + ", ".join(habit) + ". Check quantity and date carefully"})
    big = [i for i in items if (i.get("qty") or 1) > 3]
    out.append({"ok": not big, "text": "Quantities look normal" if not big else "Large quantity: " + ", ".join(f"{i.get('name')} ×{i.get('qty')}" for i in big)})
    return out


@ar.get("/rx")
def rx_queue(a: Admin = Depends(admin_me), db: Session = Depends(get_db)):
    t = now()
    rows = []
    for o in _rx_orders(db):
        ck = rx_checks(o)
        rows.append({"id": o.id, "store": o.store.name if o.store else "", "items": o.items or [], "wait": (t - (o.created or t)) // 60,
                     "verified": bool(o.verified_at), "doctor": o.rx_doctor, "regNo": o.rx_reg_no, "rxDate": o.rx_date,
                     "files": list(o.rx_files or []) if o.rx_shared else [], "checks": ck, "flag": not all(c["ok"] for c in ck)})
    rows.sort(key=lambda r: (r["verified"], not r["flag"], -r["wait"]))
    return {"rows": rows, "waiting": sum(1 for r in rows if not r["verified"])}


@ar.get("/rx/{oid}/file/{fid}")
def rx_file(oid: str, fid: str, a: Admin = Depends(admin_me), db: Session = Depends(get_db)):
    o = db.get(Order, oid)
    if not o or not o.rx_shared or fid not in (o.rx_files or []):
        raise HTTPException(404, "Not shared")
    got = storage.get(db, o.household_id, fid) or (storage.get(db, o.member_id, fid) if o.member_id else None)
    if not got:
        raise HTTPException(404, "Not available")
    log(db, a.email, f"rx.view {oid}")       # a prescription is health data: every look is recorded
    row, data = got
    return RawResponse(data, media_type=row.mime, headers={"Cache-Control": "private, no-store"})


class RxDecision(BaseModel):
    decision: str            # approve | reject
    doctor: str = ""
    regNo: str = ""
    rxDate: str = ""
    pharmacist: str = ""
    pharmacistReg: str = ""
    note: str = ""


@ar.post("/rx/{oid}")
def rx_decide(oid: str, body: RxDecision, a: Admin = Depends(admin_me), db: Session = Depends(get_db)):
    o = db.get(Order, oid)
    if not o or o.kind != "medicine":
        raise HTTPException(404, "No such order")
    if o.verified_at:
        raise HTTPException(409, "Already checked")
    t = now()
    if body.decision == "reject":
        if len(body.note.strip()) < 5:
            raise HTTPException(400, "Tell the family why, in a sentence.")
        o.status = "cancelled"
        o.verify_note = body.note.strip()[:400]
        o.timeline = (o.timeline or []) + [{"s": "cancelled", "t": t, "by": a.email, "why": "prescription"}]
        log(db, a.email, f"rx.reject {oid}", body.note[:300])
        return {"ok": True}
    if not (o.rx_shared and o.rx_files):
        raise HTTPException(400, "There is no prescription on this order yet. Ask the family for it.")
    doctor, reg = body.doctor.strip()[:120], body.regNo.strip().upper()[:40]
    if len(doctor) < 3 or len(reg) < 4:
        raise HTTPException(400, "Enter the doctor's name and registration number as written on the prescription.")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", body.rxDate or ""):
        raise HTTPException(400, "Enter the date on the prescription.")
    age = (t - int(time.mktime(time.strptime(body.rxDate, "%Y-%m-%d")))) // 86400
    if age < -1:
        raise HTTPException(400, "The prescription date is in the future.")
    if age > 180:
        raise HTTPException(400, "This prescription is more than 6 months old. Ask the family for a current one.")
    if any(HABIT.search(i.get("name", "")) for i in (o.items or [])) and age > 30:
        raise HTTPException(400, "Habit-forming medicines need a prescription from the last 30 days.")
    if len(body.pharmacist.strip()) < 3 or len(body.pharmacistReg.strip()) < 4:
        raise HTTPException(400, "Your name and pharmacy council registration number are recorded with every approval.")
    o.verified_by, o.verified_at = "admin:" + a.email, t
    o.rx_doctor, o.rx_reg_no, o.rx_date = doctor, reg, body.rxDate
    o.verify_note = f"Checked by {body.pharmacist.strip()[:60]} (Reg {body.pharmacistReg.strip()[:30]}). {body.note.strip()[:200]}".strip()
    o.timeline = (o.timeline or []) + [{"s": "checking", "t": t, "by": a.email, "rx": "approved"}]
    log(db, a.email, f"rx.approve {oid}", o.verify_note)
    return {"ok": True}


# ---- approvals -------------------------------------------------------------------------------------------------------
class AskIn(BaseModel):
    kind: str
    ref: str = ""
    amount: int = 0
    reason: str
    payload: dict | None = None


def _title(kind: str, ref: str, amount: int, payload: dict | None) -> str:
    if kind == "refund":
        return f"Refund ₹{amount:,} · order #{ref}"
    if kind == "export":
        return f"Export: {(payload or {}).get('what', 'orders')} ({(payload or {}).get('month', 'all')})"
    if kind == "role":
        return f"Make {ref} {(payload or {}).get('role', '')}"
    return f"{kind} {ref}"


@ar.post("/approvals")
def ask(body: AskIn, a: Admin = Depends(admin_me), db: Session = Depends(get_db)):
    if body.kind not in ("refund", "export", "role"):
        raise HTTPException(400, "Unknown kind")
    if len(body.reason.strip()) < 5:
        raise HTTPException(400, "Give a reason the other admin can check.")
    if body.kind == "refund":
        o = db.get(Order, body.ref)
        if not o:
            raise HTTPException(404, "No such order")
        if body.amount <= 0 or body.amount > (o.total or 0):
            raise HTTPException(400, f"Refund must be between ₹1 and the order total ₹{o.total}.")
    if db.scalar(select(Approval).where(Approval.kind == body.kind, Approval.ref == body.ref, Approval.status == "waiting")):
        raise HTTPException(409, "This is already waiting for approval.")
    x = Approval(kind=body.kind, ref=body.ref[:64], amount=max(0, body.amount), payload=body.payload or {}, reason=body.reason.strip()[:400],
                 asked_by=a.email, title=_title(body.kind, body.ref, body.amount, body.payload))
    db.add(x)
    log(db, a.email, f"approval.ask {x.kind} {x.ref}", x.reason)
    db.flush()
    return {"id": x.id, "title": x.title}


def _json(x: Approval) -> dict:
    return {"id": x.id, "kind": x.kind, "ref": x.ref, "amount": x.amount, "title": x.title, "reason": x.reason, "askedBy": x.asked_by,
            "status": x.status, "decidedBy": x.decided_by, "decidedAt": x.decided_at, "note": x.note, "created": x.created, "expires": x.expires,
            "payload": {k: v for k, v in (x.payload or {}).items() if k != "token"}}


@ar.get("/approvals")
def approvals(a: Admin = Depends(admin_me), db: Session = Depends(get_db)):
    t = now()
    for x in db.scalars(select(Approval).where(Approval.status == "waiting", Approval.expires < t)).all():
        x.status = "expired"
    rows = db.scalars(select(Approval).order_by(Approval.created.desc()).limit(80)).all()
    return {"waiting": [_json(x) for x in rows if x.status == "waiting"], "recent": [_json(x) for x in rows if x.status != "waiting"][:20],
            "me": a.email, "rules": {"refundAbove": REFUND_LIMIT}}


class DecideIn(BaseModel):
    approve: bool
    note: str = ""


@ar.post("/approvals/{aid}")
def decide(aid: str, body: DecideIn, a: Admin = Depends(admin_me), db: Session = Depends(get_db)):
    x = db.get(Approval, aid)
    if not x or x.status != "waiting":
        raise HTTPException(404, "Not waiting")
    if x.asked_by == a.email:
        raise HTTPException(403, "You asked for this, so another admin has to decide it.")
    if x.kind == "role" and a.role != "owner":
        raise HTTPException(403, "Only an owner can approve role changes.")
    if x.expires < now():
        x.status = "expired"
        raise HTTPException(410, "This request expired. Ask again.")
    x.decided_by, x.decided_at, x.note = a.email, now(), body.note.strip()[:400]
    if not body.approve:
        x.status = "declined"
        log(db, a.email, f"approval.decline {x.kind} {x.ref}", x.note)
        return _json(x)
    x.status = "approved"
    if x.kind == "refund":
        o = db.get(Order, x.ref)
        if o:
            o.status = "refunded"
            o.timeline = (o.timeline or []) + [{"s": "refunded", "t": now(), "by": a.email, "amount": x.amount}]
    elif x.kind == "role":
        t = db.scalar(select(Admin).where(Admin.email == x.ref))
        if t:
            t.role = (x.payload or {}).get("role", t.role)
    elif x.kind == "export":
        x.payload = {**(x.payload or {}), "token": secrets.token_urlsafe(18), "used": False}
    log(db, a.email, f"approval.approve {x.kind} {x.ref}", x.title)
    return _json(x)


@ar.get("/approvals/{aid}/download")
def export_download(aid: str, a: Admin = Depends(admin_me), db: Session = Depends(get_db)):
    """An approved export downloads once, by the person who asked, with masked contact details."""
    x = db.get(Approval, aid)
    if not x or x.kind != "export" or x.status != "approved" or (x.payload or {}).get("used"):
        raise HTTPException(404, "Not available")
    if a.email != x.asked_by:
        raise HTTPException(403, "Only the person who asked can download it.")
    x.payload = {**(x.payload or {}), "used": True}
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["order", "created", "kind", "partner", "status", "total", "payment"])
    for o in db.scalars(select(Order).order_by(Order.created.desc()).limit(20000)).all():
        w.writerow([o.id, time.strftime("%Y-%m-%d", time.gmtime((o.created or 0) + 19800)), o.kind, o.store.name if o.store else "", o.status, o.total, o.payment])
    w.writerow([])
    w.writerow([f"Exported by {x.asked_by}, approved by {x.decided_by}. Confidential."])
    log(db, a.email, f"export.download {x.id}")
    return RawResponse(buf.getvalue(), media_type="text/csv", headers={"Content-Disposition": f'attachment; filename="orders-{x.id}.csv"', "Cache-Control": "no-store"})


class RefundIn(BaseModel):
    amount: int
    reason: str


@ar.post("/orders/{oid}/refund")
def refund(oid: str, body: RefundIn, a: Admin = Depends(admin_me), db: Session = Depends(get_db)):
    """Small refunds go straight through; above the limit they become an approval request for a second admin."""
    o = db.get(Order, oid)
    if not o:
        raise HTTPException(404, "No such order")
    if o.status == "refunded":
        raise HTTPException(409, "Already refunded")
    if body.amount <= 0 or body.amount > (o.total or 0):
        raise HTTPException(400, f"Refund must be between ₹1 and the order total ₹{o.total}.")
    if len(body.reason.strip()) < 5:
        raise HTTPException(400, "Give a reason in a few words.")
    if body.amount > REFUND_LIMIT:
        r = ask(AskIn(kind="refund", ref=oid, amount=body.amount, reason=body.reason), a, db)
        return {"approval": r["id"], "message": f"Over ₹{REFUND_LIMIT:,}: sent to another admin to approve."}
    o.status = "refunded"
    o.timeline = (o.timeline or []) + [{"s": "refunded", "t": now(), "by": a.email, "amount": body.amount}]
    log(db, a.email, f"order.refund {oid} ₹{body.amount}", body.reason[:300])
    return {"ok": True, "message": f"₹{body.amount:,} refunded."}


# ---- complaints ------------------------------------------------------------------------------------------------------
DEADLINE_H = {"wrong_medicine": 2, "unsafe": 2, "missed_visit": 6, "late": 6, "report": 24, "refund": 72, "behaviour": 72, "other": 72}
KIND_TEXT = {"wrong_medicine": "Wrong medicine delivered", "unsafe": "Safety concern", "missed_visit": "Technician didn't come", "late": "Very late",
             "report": "Report not showing or wrong", "refund": "Refund not received", "behaviour": "Rude or unprofessional", "other": "Something else"}
REPLIES = {
    "wrong_medicine": {"en": "We're very sorry. Please don't take the wrong medicine. A replacement is on its way within 60 minutes at no cost, and the wrong pack will be collected.",
                       "te": "క్షమించండి. దయచేసి తప్పు మందు వేసుకోకండి. సరైన మందు 60 నిమిషాల్లో ఉచితంగా పంపుతున్నాము, తప్పు ప్యాక్‌ను తీసుకెళ్తాము.",
                       "hi": "हमें बहुत खेद है। कृपया गलत दवा न लें। सही दवा 60 मिनट में मुफ़्त भेजी जा रही है, और गलत पैक वापस ले लिया जाएगा।"},
    "missed_visit": {"en": "We're sorry the technician didn't arrive. We've booked the earliest slot for you at no extra cost and will call you to confirm.",
                     "te": "టెక్నీషియన్ రాకపోవడం పట్ల క్షమించండి. మీకు అదనపు ఖర్చు లేకుండా త్వరిత స్లాట్ బుక్ చేశాము, నిర్ధారించడానికి కాల్ చేస్తాము.",
                     "hi": "तकनीशियन के न आने के लिए खेद है। हमने बिना अतिरिक्त शुल्क के सबसे जल्दी का स्लॉट बुक किया है और पुष्टि के लिए कॉल करेंगे।"},
    "report": {"en": "Thank you for telling us. We've asked the lab to check your report and will update you within 24 hours.",
               "te": "తెలియజేసినందుకు ధన్యవాదాలు. మీ రిపోర్ట్‌ను తనిఖీ చేయమని ల్యాబ్‌ను అడిగాము, 24 గంటల్లో తెలియజేస్తాము.",
               "hi": "बताने के लिए धन्यवाद। हमने लैब से आपकी रिपोर्ट जाँचने को कहा है और 24 घंटे में जानकारी देंगे।"},
    "refund": {"en": "Your refund has been sent. Banks usually take 3–5 working days to show it. We'll share the reference number here.",
               "te": "మీ రీఫండ్ పంపబడింది. బ్యాంక్‌లో కనిపించడానికి 3–5 పని దినాలు పట్టవచ్చు. రిఫరెన్స్ నంబర్ ఇక్కడ పంపుతాము.",
               "hi": "आपका रिफ़ंड भेज दिया गया है। बैंक में दिखने में 3–5 कार्यदिवस लग सकते हैं। रेफ़रेंस नंबर यहाँ साझा करेंगे।"},
    "other": {"en": "Thank you for telling us. We're looking into it and will reply here soon.",
              "te": "తెలియజేసినందుకు ధన్యవాదాలు. పరిశీలిస్తున్నాము, త్వరలో ఇక్కడ సమాధానం ఇస్తాము.",
              "hi": "बताने के लिए धन्यवाद। हम इसे देख रहे हैं और जल्द ही यहाँ जवाब देंगे।"},
}


def complaint_json(c: Complaint, admin: bool = False) -> dict:
    t = now()
    j = {"id": c.id, "orderId": c.order_id, "kind": c.kind, "kindText": KIND_TEXT.get(c.kind, c.kind), "status": c.status, "due": c.due,
         "left": (c.due - t) // 60, "lang": c.lang, "thread": c.thread or [], "created": c.created}
    if admin:
        j["replies"] = REPLIES.get(c.kind, REPLIES["other"])
        j["text"] = c.text
    return j


class ComplaintIn(BaseModel):
    orderId: str = ""
    kind: str
    text: str
    lang: str = "en"


@fr.post("/complaints")
def raise_complaint(body: ComplaintIn, request: Request, db: Session = Depends(get_db)):
    from .auth import current_user, limit
    from .models import Household
    limit(request, "complaint", 8, 3600)
    u = current_user(request, db)
    if not u:
        raise HTTPException(401, "Sign in first")
    if body.kind not in KIND_TEXT:
        raise HTTPException(400, "Choose what went wrong")
    text = re.sub(r"[<>\x00-\x1f]", "", body.text or "").strip()
    if len(text) < 5:
        raise HTTPException(400, "Tell us a little more, in a sentence.")
    if body.orderId:
        o = db.get(Order, body.orderId)
        if not o or o.household_id != u.household_id:
            raise HTTPException(404, "No such order")
    c = Complaint(household_id=u.household_id, user_id=u.id, order_id=body.orderId[:32], kind=body.kind, text=text[:2000],
                  lang=body.lang if body.lang in ("en", "te", "hi") else "en", due=now() + DEADLINE_H[body.kind] * 3600,
                  thread=[{"by": "family", "text": text[:2000], "t": now()}])
    db.add(c)
    db.flush()
    return complaint_json(c)


@fr.get("/complaints")
def my_complaints(request: Request, db: Session = Depends(get_db)):
    from .auth import current_user
    u = current_user(request, db)
    if not u:
        raise HTTPException(401, "Sign in first")
    return {"rows": [complaint_json(c) for c in db.scalars(select(Complaint).where(Complaint.household_id == u.household_id).order_by(Complaint.created.desc()).limit(30)).all()]}


@ar.get("/complaints")
def complaints(status: str = "open", a: Admin = Depends(admin_me), db: Session = Depends(get_db)):
    from .console import mask
    from .models import Household
    q = select(Complaint).order_by(Complaint.due)
    if status == "open":
        q = q.where(Complaint.status != "resolved")
    else:
        q = q.where(Complaint.status == "resolved").order_by(Complaint.resolved_at.desc())
    out = []
    for c in db.scalars(q.limit(200)).all():
        j = complaint_json(c, True)
        h = db.get(Household, c.household_id)
        j["who"] = mask(h.name if h else "")
        o = db.get(Order, c.order_id) if c.order_id else None
        if o:
            j["order"] = {"id": o.id, "store": o.store.name if o.store else "", "what": ", ".join(i.get("name", "") for i in (o.items or [])[:3]), "total": o.total, "status": o.status,
                          "rxBy": o.verify_note[:80] if o.verify_note else ""}
        out.append(j)
    return {"rows": out}


class ReplyIn(BaseModel):
    text: str
    resolve: bool = False


@ar.post("/complaints/{cid}")
def reply(cid: str, body: ReplyIn, a: Admin = Depends(admin_me), db: Session = Depends(get_db)):
    from .inbox import notify
    c = db.get(Complaint, cid)
    if not c:
        raise HTTPException(404, "No such complaint")
    text = (body.text or "").strip()
    if text:
        c.thread = (c.thread or []) + [{"by": "urban health", "text": text[:2000], "t": now()}]
        c.status = "answered"
        notify(db, c.household_id, "complaint", "Reply to your complaint", text[:300], {"complaint": c.id}, to_user=c.user_id)
    if body.resolve:
        c.status, c.resolved_at = "resolved", now()
    if not text and not body.resolve:
        raise HTTPException(400, "Write a reply or mark it resolved.")
    log(db, a.email, f"complaint.{'resolve' if body.resolve else 'reply'} {cid}")
    return complaint_json(c, True)


# ---- for Today -------------------------------------------------------------------------------------------------------
def open_counts(db: Session, t: int) -> list[dict]:
    out = []
    waiting = db.scalars(select(Approval).where(Approval.status == "waiting", Approval.expires > t)).all()
    if waiting:
        out.append({"sev": "warn", "tag": "Approvals", "icon": "✓", "title": f"{len(waiting)} request{'s' if len(waiting) > 1 else ''} waiting for a second admin",
                    "sub": waiting[0].title, "act": "Review", "go": "approvals"})
    cs = db.scalars(select(Complaint).where(Complaint.status != "resolved")).all()
    due = [c for c in cs if c.due - t < 3 * 3600]
    if due:
        late = [c for c in due if c.due < t]
        out.append({"sev": "urgent" if late or any(c.kind in ("wrong_medicine", "unsafe") for c in due) else "warn", "tag": "Complaints", "icon": "!",
                    "title": f"{len(due)} complaint{'s' if len(due) > 1 else ''} {'past' if late else 'near'} the deadline",
                    "sub": KIND_TEXT.get(due[0].kind, "") + (" · overdue" if late else f" · {(due[0].due - t) // 60} min left"), "act": "Reply", "go": "complaints"})
    return out

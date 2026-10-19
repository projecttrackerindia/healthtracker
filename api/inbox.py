"""The family's server-side inbox: notices (order status, report ready, visit confirmed, new message), appointment
requests at partner hospitals, and messages with partner stores. Everything here is a Postgres row; the app polls
/inbox and merges it into its notification centre, Lab results and Appointments."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from . import push as PUSH
from .auth import limit
from .db import get_db
from .models import Appointment, Household, Message, Notice, PushSub, Store, StoredFile, now
from .routes import household

r = APIRouter(prefix="/api/v1")


def notify(db: Session, household_id: str, kind: str, title: str, body: str = "", ref: dict | None = None, member_id: str = "", url: str = "/app") -> Notice:
    """One notice row + a push to every phone in the family (when push is configured)."""
    n = Notice(household_id=household_id, member_id=member_id or "", kind=kind, title=title[:160], body=body[:400], ref=ref or {})
    db.add(n)
    if PUSH.ready():
        for s in db.scalars(select(PushSub).where(PushSub.household_id == household_id)).all():
            try:
                ok, status, _ = PUSH.send(s.sub, {"title": title[:80], "body": body[:160], "url": url, "tag": kind})
                if not ok and status in (404, 410):
                    db.delete(s)
            except Exception:
                pass
    return n


def notice_json(n: Notice) -> dict:
    return {"id": n.id, "kind": n.kind, "title": n.title, "body": n.body, "ref": n.ref or {}, "t": n.t, "read": n.read, "member": n.member_id}


@r.get("/inbox")
def inbox(since: int = 0, db: Session = Depends(get_db), x_dokko_key: str | None = Header(None)):
    h = household(db, x_dokko_key, create=False)
    if not h:
        return {"notices": [], "appointments": [], "unreadMessages": 0, "t": now()}
    rows = db.scalars(select(Notice).where(Notice.household_id == h.id, Notice.t > since).order_by(Notice.t.desc(), Notice.id.desc()).limit(100)).all()
    ap = db.scalars(select(Appointment).where(Appointment.household_id == h.id).order_by(Appointment.created.desc()).limit(60)).all()
    unread = db.scalar(select(func.count(Message.id)).where(Message.household_id == h.id, Message.sender == "partner", Message.read_family == False)) or 0  # noqa: E712
    return {"notices": [notice_json(n) for n in rows], "appointments": [appt_json(db, a) for a in ap], "unreadMessages": unread, "t": now()}


class ReadIn(BaseModel):
    ids: list[int] = []


@r.post("/inbox/read")
def inbox_read(body: ReadIn, db: Session = Depends(get_db), x_dokko_key: str | None = Header(None)):
    h = household(db, x_dokko_key, create=False)
    if not h:
        return {"ok": True}
    for n in db.scalars(select(Notice).where(Notice.household_id == h.id, Notice.id.in_(body.ids[:200]))).all():
        n.read = True
    return {"ok": True}


# ---- appointments at partner hospitals / clinics ---------------------------------------------------------------------------
def appt_json(db: Session, a: Appointment) -> dict:
    s = db.get(Store, a.store_id)
    return {"id": a.id, "store": {"id": s.id, "name": s.name, "phone": s.phone, "address": ", ".join(x for x in (s.address, s.area, s.city) if x), "lat": s.lat, "lng": s.lng} if s else None,
            "member": a.member_id, "memberName": a.member_name, "kind": a.kind, "date": a.date, "time": a.time, "why": a.why, "doctor": a.doctor,
            "status": a.status, "slotDate": a.slot_date, "slotTime": a.slot_time, "note": a.note, "created": a.created, "updated": a.updated,
            "live": bool(a.call_started and not a.call_ended), "hasRx": bool(a.rx), "hasSummary": bool(a.summary)}


class ApptIn(BaseModel):
    store: str
    member: str = ""
    memberName: str = ""
    kind: str = "visit"
    date: str
    time: str = ""
    why: str = ""
    doctor: str = ""


@r.post("/appointments")
def appt_request(body: ApptIn, request: Request, db: Session = Depends(get_db), x_dokko_key: str | None = Header(None)):
    h = household(db, x_dokko_key)
    if not h:
        raise HTTPException(400, "missing household key")
    limit(request, f"appt:{h.id}", 20, 3600)
    s = db.get(Store, body.store)
    if not s or not s.active or s.kind != "hospital":
        raise HTTPException(404, "This hospital is not a partner yet. Call them, then add the visit to your appointments.")
    if len(body.date) != 10:
        raise HTTPException(400, "choose a date")
    a = Appointment(household_id=h.id, member_id=body.member[:32], member_name=body.memberName[:80], store_id=s.id, kind="video" if body.kind == "video" else "visit",
                    date=body.date, time=body.time[:8], why=body.why[:160], doctor=body.doctor[:80])
    db.add(a)
    db.flush()
    return appt_json(db, a)


@r.get("/appointments")
def appt_list(db: Session = Depends(get_db), x_dokko_key: str | None = Header(None)):
    h = household(db, x_dokko_key, create=False)
    if not h:
        return {"appointments": []}
    rows = db.scalars(select(Appointment).where(Appointment.household_id == h.id).order_by(Appointment.created.desc()).limit(100)).all()
    return {"appointments": [appt_json(db, a) for a in rows]}


@r.post("/appointments/{aid}/cancel")
def appt_cancel(aid: str, db: Session = Depends(get_db), x_dokko_key: str | None = Header(None)):
    h = household(db, x_dokko_key, create=False)
    a = db.get(Appointment, aid)
    if not h or not a or a.household_id != h.id:
        raise HTTPException(404)
    if a.status in ("done", "cancelled"):
        raise HTTPException(400, "This visit is already closed.")
    a.status, a.updated = "cancelled", now()
    return appt_json(db, a)


# ---- messages with a partner store ----------------------------------------------------------------------------------------
def msg_json(m: Message) -> dict:
    return {"id": m.id, "sender": m.sender, "name": m.sender_name, "text": m.text, "fileId": m.file_id, "t": m.t}


@r.get("/messages/threads")
def threads(db: Session = Depends(get_db), x_dokko_key: str | None = Header(None)):
    h = household(db, x_dokko_key, create=False)
    if not h:
        return {"threads": []}
    rows = db.scalars(select(Message).where(Message.household_id == h.id).order_by(Message.t.desc()).limit(500)).all()
    seen, out = {}, []
    for m in rows:
        if m.store_id in seen:
            if m.sender == "partner" and not m.read_family:
                seen[m.store_id]["unread"] += 1
            continue
        s = db.get(Store, m.store_id)
        seen[m.store_id] = {"store": {"id": m.store_id, "name": s.name if s else "Partner", "kind": s.kind if s else ""}, "last": msg_json(m), "unread": 1 if (m.sender == "partner" and not m.read_family) else 0}
        out.append(seen[m.store_id])
    return {"threads": out}


@r.get("/messages")
def messages(store: str, db: Session = Depends(get_db), x_dokko_key: str | None = Header(None)):
    h = household(db, x_dokko_key, create=False)
    if not h:
        return {"messages": []}
    rows = db.scalars(select(Message).where(Message.household_id == h.id, Message.store_id == store).order_by(Message.t.asc()).limit(300)).all()
    for m in rows:
        if m.sender == "partner":
            m.read_family = True
    s = db.get(Store, store)
    return {"store": {"id": store, "name": s.name if s else "Partner", "kind": s.kind if s else "", "phone": s.phone if s else ""}, "messages": [msg_json(m) for m in rows]}


class MsgIn(BaseModel):
    store: str
    text: str = ""
    fileId: str = ""
    name: str = ""


@r.post("/messages")
def send_message(body: MsgIn, request: Request, db: Session = Depends(get_db), x_dokko_key: str | None = Header(None)):
    h = household(db, x_dokko_key)
    if not h:
        raise HTTPException(400, "missing household key")
    limit(request, f"msg:{h.id}", 120, 3600)
    s = db.get(Store, body.store)
    if not s or not s.active:
        raise HTTPException(404, "partner not found")
    text, fid = body.text.strip()[:2000], body.fileId.strip()[:48]
    if not text and not fid:
        raise HTTPException(400, "Write a message or attach a document.")
    if fid and not db.get(StoredFile, (h.id, fid)):
        raise HTTPException(400, "That document has not synced yet; try again in a moment.")
    m = Message(household_id=h.id, store_id=s.id, sender="family", sender_name=body.name[:80], text=text, file_id=fid, read_family=True)
    db.add(m)
    db.flush()
    return msg_json(m)

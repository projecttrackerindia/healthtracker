"""Video consults with verified doctors at partner hospitals (/api/v1/consults, /api/partner/consults, /ws/call).

A family requests a video visit (Appointments → Book → Video), the hospital confirms a slot and a doctor, and at the
time the doctor presses Start: the family gets a notice, both sides open the call page and this module relays the
WebRTC signalling (offer / answer / ICE candidates / live captions) over one WebSocket room per appointment. Media flows
peer to peer (STUN by default; a TURN server when TURN_URL is set) — the server never sees audio or video.

What persists in Postgres, on the appointment row: when the call started and ended, the caption transcript both sides
agreed to keep, the doctor's e-prescription (also written as a signed PDF into the family's encrypted document store,
so it can be used to order medicines) and a plain-words visit summary written by the health assistant for the family.
"""
from __future__ import annotations

import asyncio
import io
import json
import os
import time
from pathlib import Path

from fastapi import APIRouter, Depends, Header, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import ai as AI
from . import storage
from .db import get_db, session
from .inbox import appt_json, notify
from .models import Appointment, Household, PartnerUser, Store, now
from .partner import COOKIE as PARTNER_COOKIE
from .partner import me as partner_me
from .partner import my_store
from .routes import household
from .security import valid_key
from .security import verify

r = APIRouter(prefix="/api/v1")
pr = APIRouter(prefix="/api/partner")
ws = APIRouter()
ROOT = Path(__file__).resolve().parents[1]
LOGO = ROOT / "web" / "brand" / "png" / "user-logo.png"
INK, MUTE, BLUE, LINE = (0.07, 0.09, 0.15), (0.42, 0.45, 0.52), (0.18, 0.36, 1.0), (0.88, 0.9, 0.93)
MAX_TRANSCRIPT = 400
FREQ = {"od": "once a day", "bd": "twice a day", "tds": "three times a day", "qid": "four times a day", "sos": "when needed", "hs": "at bedtime", "weekly": "once a week"}


# ---- doctors ----------------------------------------------------------------------------------------------------------------
def doctor_json(u: PartnerUser) -> dict:
    return {"id": u.id, "name": u.name, "specialty": u.specialty or "", "regNo": u.reg_no or "", "verified": bool(u.verified)}


@r.get("/doctors")
def doctors(store: str, db: Session = Depends(get_db)):
    """Verified doctors who consult at a partner hospital — what the family sees when booking a video visit."""
    s = db.get(Store, store)
    if not s or not s.active:
        return {"doctors": [], "video": False}
    rows = db.scalars(select(PartnerUser).where(PartnerUser.store_id == store, PartnerUser.role == "doctor", PartnerUser.active == True, PartnerUser.verified == True)  # noqa: E712
                      .order_by(PartnerUser.name)).all()
    return {"doctors": [doctor_json(u) for u in rows], "video": bool(rows)}


# ---- ICE configuration ------------------------------------------------------------------------------------------------------
def ice_servers() -> list[dict]:
    out = [{"urls": ["stun:stun.l.google.com:19302", "stun:stun1.l.google.com:19302"]}]
    turn = (os.getenv("TURN_URL") or "").strip()
    if turn:
        out.append({"urls": [u.strip() for u in turn.split(",") if u.strip()], "username": os.getenv("TURN_USER", ""), "credential": os.getenv("TURN_PASS", "")})
    return out


@r.get("/consults/ice")
def ice():
    return {"iceServers": ice_servers(), "turn": bool(os.getenv("TURN_URL"))}


# ---- the appointment as a consult ------------------------------------------------------------------------------------------
def consult_json(db: Session, a: Appointment, for_partner: bool = False) -> dict:
    j = appt_json(db, a)
    j.update({"callStarted": a.call_started, "callEnded": a.call_ended, "rx": a.rx, "summary": a.summary or "",
              "transcript": a.transcript or [] if for_partner or a.call_ended else [], "live": bool(a.call_started and not a.call_ended),
              "rxFileId": f"erx_{a.id}" if a.rx else ""})
    return j


def _family_appt(db: Session, aid: str, key: str | None) -> Appointment:
    h = household(db, key, create=False)
    a = db.get(Appointment, aid)
    if not h or not a or a.household_id != h.id:
        raise HTTPException(404)
    return a


@r.get("/consults/{aid}")
def consult(aid: str, db: Session = Depends(get_db), x_dokko_key: str | None = Header(None)):
    return consult_json(db, _family_appt(db, aid, x_dokko_key))


class EndIn(BaseModel):
    transcript: list[dict] = []
    keep: bool = True


def _clean_transcript(items: list[dict]) -> list[dict]:
    out = []
    for x in items[-MAX_TRANSCRIPT:]:
        text = str(x.get("text", "")).strip()[:400]
        if text:
            out.append({"who": "doctor" if x.get("who") == "doctor" else "family", "t": int(x.get("t") or now()), "text": text})
    return out


def _summarise(a: Appointment, db: Session) -> str:
    """Plain-words visit summary for the family, from the transcript and the e-prescription. Not a diagnosis."""
    if not AI.available() or not (a.transcript or a.rx):
        return ""
    s = db.get(Store, a.store_id)
    ctx = {"hospital": s.name if s else "", "doctor": a.doctor, "reason": a.why, "when": f"{a.slot_date} {a.slot_time}".strip(),
           "transcript": [f"{x['who']}: {x['text']}" for x in (a.transcript or [])][-120:], "prescription": a.rx}
    system = ("You write the after-visit summary for a family inside TheHealthTracker, an Indian family health app, from a video consult "
              "transcript (speech captions, so expect errors) and the doctor's e-prescription. Write for the patient's family in plain English, "
              "120-220 words, in this shape with these exact headings on their own lines: 'What we discussed', 'What the doctor advised', "
              "'Medicines' (name, how to take, for how long — exactly as prescribed, never change a dose), 'Watch for' (warning signs that need "
              "urgent care), 'Next steps' (follow-up, tests). Only use what is in the transcript or prescription; never add a diagnosis the doctor "
              "did not state; never mention AI, vendors or model names. Output plain text, no markdown symbols.")
    try:
        res = AI.create(max_tokens=900, system=system, messages=[{"role": "user", "content": json.dumps(ctx, ensure_ascii=False)[:14000]}])
        return "".join(b.text for b in res.content if getattr(b, "type", "") == "text").strip()[:4000]
    except Exception as e:  # the visit is saved either way; the summary can be retried
        AI._fail("visit summary", e)
        return ""


@r.post("/consults/{aid}/end")
def family_end(aid: str, body: EndIn, db: Session = Depends(get_db), x_dokko_key: str | None = Header(None)):
    """The family's side hangs up: keep (or discard) the captions, then write the summary."""
    a = _family_appt(db, aid, x_dokko_key)
    if not a.call_started:
        raise HTTPException(400, "This consult has not started.")
    if body.keep and body.transcript:
        mine = _clean_transcript(body.transcript)
        have = {(x["t"], x["text"]) for x in (a.transcript or [])}
        a.transcript = sorted((a.transcript or []) + [x for x in mine if (x["t"], x["text"]) not in have], key=lambda x: x["t"])[-MAX_TRANSCRIPT:]
    if not a.call_ended:
        a.call_ended = now()
    if not a.summary:
        a.summary = _summarise(a, db)
        _count(db, a, bool(a.summary))
    a.updated = now()
    return consult_json(db, a)


def _count(db: Session, a: Appointment, ok: bool) -> None:
    """Tokens of a visit summary count against the family's daily allowance like any other smart reading."""
    from .routes import _job
    h = db.get(Household, a.household_id) if a.household_id else None
    if h:
        db.add(_job(h, "summary", "claude" if ok else "error", ok=ok))


@r.post("/consults/{aid}/summary")
def family_summary(aid: str, db: Session = Depends(get_db), x_dokko_key: str | None = Header(None)):
    a = _family_appt(db, aid, x_dokko_key)
    if not a.call_ended:
        raise HTTPException(400, "The summary is written after the call ends.")
    a.summary = _summarise(a, db) or a.summary
    _count(db, a, bool(a.summary))
    if not a.summary:
        raise HTTPException(502, "The summary could not be written right now; the transcript and prescription are saved.")
    return consult_json(db, a)


# ---- the doctor's side ------------------------------------------------------------------------------------------------------
def _doctor(db: Session, u: PartnerUser) -> PartnerUser:
    if u.role != "doctor":
        raise HTTPException(403, "Only doctors run consults.")
    if not u.verified:
        raise HTTPException(403, "Your registration is being verified by TheHealthTracker; consults open once it is confirmed.")
    return u


def _store_appt(db: Session, u: PartnerUser, aid: str) -> Appointment:
    a = db.get(Appointment, aid)
    if not a or a.store_id != u.store_id:
        raise HTTPException(404)
    return a


@pr.get("/consults")
def partner_consults(db: Session = Depends(get_db), u: PartnerUser = Depends(partner_me)):
    """Video visits for this hospital: confirmed and due, live, and the recently finished ones."""
    rows = db.scalars(select(Appointment).where(Appointment.store_id == u.store_id, Appointment.kind == "video",
                                                Appointment.status.in_(("confirmed", "rescheduled", "done"))).order_by(Appointment.updated.desc()).limit(100)).all()
    if u.role == "doctor":  # a doctor sees the visits assigned to them (by name) and the unassigned ones
        rows = [a for a in rows if not a.doctor or a.doctor.lower().strip() in (u.name.lower().strip(), ("dr " + u.name).lower().strip(), ("dr. " + u.name).lower().strip())]
    return {"consults": [consult_json(db, a, True) for a in rows], "me": doctor_json(u) if u.role == "doctor" else None}


@pr.post("/consults/{aid}/start")
def partner_start(aid: str, db: Session = Depends(get_db), u: PartnerUser = Depends(partner_me)):
    _doctor(db, u)
    a = _store_appt(db, u, aid)
    if a.kind != "video" or a.status not in ("confirmed", "rescheduled"):
        raise HTTPException(400, "Only a confirmed video visit can be started.")
    s = my_store(db, u)
    a.doctor = a.doctor or u.name
    a.call_started, a.call_ended, a.updated = now(), None, now()
    notify(db, a.household_id, "consult", f"Dr {u.name} is ready for your video visit", f"{s.name} · tap to join the call now.",
           {"appointment": a.id, "store": s.name, "doctor": u.name, "join": True}, a.member_id, "/app#call=" + a.id)
    return consult_json(db, a, True)


class DocEndIn(BaseModel):
    transcript: list[dict] = []


@pr.post("/consults/{aid}/end")
def partner_end(aid: str, body: DocEndIn, db: Session = Depends(get_db), u: PartnerUser = Depends(partner_me)):
    _doctor(db, u)
    a = _store_appt(db, u, aid)
    if not a.call_started:
        raise HTTPException(400, "This consult has not started.")
    if body.transcript:
        mine = _clean_transcript(body.transcript)
        have = {(x["t"], x["text"]) for x in (a.transcript or [])}
        a.transcript = sorted((a.transcript or []) + [x for x in mine if (x["t"], x["text"]) not in have], key=lambda x: x["t"])[-MAX_TRANSCRIPT:]
    a.call_ended = a.call_ended or now()
    a.status, a.updated = "done", now()
    return consult_json(db, a, True)


class RxItem(BaseModel):
    name: str
    strength: str = ""
    form: str = ""          # tablet | capsule | syrup | drops | injection | cream | inhaler | other
    frequency: str = "od"   # od | bd | tds | qid | sos | hs | weekly
    duration: str = ""      # e.g. "5 days"
    instructions: str = ""  # e.g. "after food"
    rx: bool = True


class RxIn(BaseModel):
    items: list[RxItem]
    advice: str = ""
    followUp: str = ""      # e.g. "2 weeks" or a date
    diagnosis: str = ""     # the doctor's words, shown as the doctor's note


def rx_pdf(a: Appointment, s: Store, u: PartnerUser, rx: dict) -> bytes:
    try:
        import pymupdf  # type: ignore
    except ImportError:  # pragma: no cover
        import fitz as pymupdf  # type: ignore
    doc = pymupdf.open()
    page = doc.new_page(width=595, height=842)
    W, M = 595, 44
    y = 46
    if LOGO.exists():
        page.insert_image(pymupdf.Rect(M, y - 6, M + 150, y + 34), filename=str(LOGO), keep_proportion=True)
    page.insert_text((W - M - 190, y + 6), "E-PRESCRIPTION", fontsize=9, fontname="helv", color=MUTE)
    page.insert_text((W - M - 190, y + 24), f"THT-RX-{a.id[-8:].upper()}", fontsize=16, fontname="hebo", color=INK)
    y += 56
    page.draw_line((M, y), (W - M, y), color=LINE, width=1)
    y += 20
    col2 = W / 2 + 10
    page.insert_text((M, y), "PATIENT", fontsize=8, fontname="helv", color=MUTE)
    page.insert_text((col2, y), "DOCTOR", fontsize=8, fontname="helv", color=MUTE)
    y += 14
    page.insert_text((M, y), (a.member_name or "Family member")[:48], fontsize=11, fontname="hebo", color=INK)
    page.insert_text((col2, y), f"Dr {u.name}"[:48], fontsize=11, fontname="hebo", color=INK)
    y += 14
    left = [f"Video consult on {time.strftime('%d/%m/%Y %H:%M', time.localtime(rx['t']))} IST", f"Reason: {a.why or '—'}"[:70]]
    right = [(u.specialty or "General practice")[:60], f"Reg. no. {u.reg_no}", s.name[:60], ", ".join(x for x in (s.address, s.area, s.city) if x)[:70]]
    y2 = y
    for line in left:
        page.insert_text((M, y), line, fontsize=9, fontname="helv", color=MUTE); y += 12
    for line in right:
        page.insert_text((col2, y2), line, fontsize=9, fontname="helv", color=MUTE); y2 += 12
    y = max(y, y2) + 14
    if rx.get("diagnosis"):
        page.insert_text((M, y), "DOCTOR'S NOTE", fontsize=8, fontname="helv", color=MUTE); y += 13
        page.insert_text((M, y), rx["diagnosis"][:110], fontsize=10, fontname="helv", color=INK); y += 18
    page.insert_text((M, y + 8), "Rx", fontsize=18, fontname="hebo", color=BLUE)
    y += 22
    page.draw_rect(pymupdf.Rect(M, y, W - M, y + 22), color=None, fill=(0.95, 0.96, 0.98))
    for x, label in ((M + 8, "MEDICINE"), (M + 250, "HOW TO TAKE"), (W - M - 110, "FOR")):
        page.insert_text((x, y + 15), label, fontsize=8, fontname="hebo", color=MUTE)
    y += 22
    for i, it in enumerate(rx["items"], 1):
        y += 18
        name = f"{i}. {it['name']} {it.get('strength', '')}".strip()
        page.insert_text((M + 8, y), name[:40] + (f" · {it['form']}" if it.get("form") else ""), fontsize=10, fontname="hebo", color=INK)
        how = FREQ.get(it.get("frequency", ""), it.get("frequency", "")) + (f", {it['instructions']}" if it.get("instructions") else "")
        page.insert_text((M + 250, y), how[:42], fontsize=10, fontname="helv", color=INK)
        page.insert_text((W - M - 110, y), (it.get("duration") or "—")[:16], fontsize=10, fontname="helv", color=INK)
        page.draw_line((M, y + 6), (W - M, y + 6), color=LINE, width=0.5)
    y += 26
    if rx.get("advice"):
        page.insert_text((M, y), "ADVICE", fontsize=8, fontname="helv", color=MUTE); y += 13
        words, line = rx["advice"].split(), ""
        for w in words:
            if len(line) + len(w) > 95:
                page.insert_text((M, y), line, fontsize=9.5, fontname="helv", color=INK); y += 13; line = ""
            line += (" " if line else "") + w
        if line:
            page.insert_text((M, y), line, fontsize=9.5, fontname="helv", color=INK); y += 13
        y += 6
    if rx.get("followUp"):
        page.insert_text((M, y), f"Follow-up: {rx['followUp'][:60]}", fontsize=9.5, fontname="helv", color=INK); y += 18
    y = max(y + 20, 700)
    page.insert_text((W - M - 200, y), f"Dr {u.name}"[:40], fontsize=11, fontname="hebo", color=INK)
    page.insert_text((W - M - 200, y + 13), f"Reg. no. {u.reg_no} · signed electronically", fontsize=8, fontname="helv", color=MUTE)
    page.insert_text((W - M - 200, y + 24), f"Issued through TheHealthTracker · {time.strftime('%d/%m/%Y %H:%M', time.localtime(rx['t']))} IST", fontsize=8, fontname="helv", color=MUTE)
    foot = ["This e-prescription was issued after a video consult, in line with the Telemedicine Practice Guidelines, 2020 (Board of Governors, MCI).",
            "It is valid for dispensing by a licensed pharmacy. Verify the doctor's registration on the NMC Indian Medical Register if needed."]
    yy = 842 - 46
    for line in foot:
        page.insert_text((M, yy), line, fontsize=7.5, fontname="helv", color=MUTE); yy += 10
    buf = io.BytesIO()
    doc.save(buf, garbage=3, deflate=True)
    doc.close()
    return buf.getvalue()


@pr.put("/consults/{aid}/rx")
def partner_rx(aid: str, body: RxIn, db: Session = Depends(get_db), u: PartnerUser = Depends(partner_me)):
    """The doctor's e-prescription: saved on the visit, written as a signed PDF into the family's documents, and the family is told."""
    _doctor(db, u)
    a = _store_appt(db, u, aid)
    if not a.call_started:
        raise HTTPException(400, "Prescribe during or after the consult.")
    if not body.items or len(body.items) > 15:
        raise HTTPException(400, "1 to 15 medicines.")
    items = []
    for it in body.items:
        if not it.name.strip():
            raise HTTPException(400, "Every medicine needs a name.")
        items.append({"name": it.name.strip()[:80], "strength": it.strength.strip()[:30], "form": it.form.strip()[:20], "frequency": it.frequency.strip()[:12],
                      "duration": it.duration.strip()[:30], "instructions": it.instructions.strip()[:80], "rx": bool(it.rx)})
    s = my_store(db, u)
    rx = {"items": items, "advice": body.advice.strip()[:800], "followUp": body.followUp.strip()[:60], "diagnosis": body.diagnosis.strip()[:160],
          "doctor": u.name, "regNo": u.reg_no, "specialty": u.specialty, "store": s.name, "t": now()}
    try:
        pdf = rx_pdf(a, s, u, rx)
        storage.put(db, a.household_id, f"erx_{a.id}", pdf, "application/pdf", f"Prescription · Dr {u.name} · {time.strftime('%d-%m-%Y')}", "partner:" + u.id)
        db.flush()
    except Exception as e:
        print("[consult] rx store failed:", type(e).__name__, str(e)[:200], flush=True)
        raise HTTPException(502, "The prescription could not be stored right now; try again in a minute.")
    a.rx, a.updated = rx, now()
    names = ", ".join(i["name"] for i in items[:3]) + (" …" if len(items) > 3 else "")
    notify(db, a.household_id, "prescription", f"Prescription from Dr {u.name}", f"{names}. Open Medicines to order, or Lab results → Prescriptions to read it.",
           {"appointment": a.id, "fileId": f"erx_{a.id}", "store": s.name, "doctor": u.name, "items": items, "mime": "application/pdf", "name": f"Prescription · Dr {u.name}", "diagnosis": rx["diagnosis"]},
           a.member_id, "/app")
    return consult_json(db, a, True)


@pr.get("/consults/{aid}/rx.pdf")
def partner_rx_pdf(aid: str, db: Session = Depends(get_db), u: PartnerUser = Depends(partner_me)):
    a = _store_appt(db, u, aid)
    if not a.rx:
        raise HTTPException(404)
    f = storage.get(db, a.household_id, f"erx_{a.id}")
    if not f:
        raise HTTPException(404)
    row, data = f
    return Response(data, media_type=row.mime, headers={"Content-Disposition": 'inline; filename="prescription.pdf"', "Cache-Control": "private, no-store"})


# ---- signalling -------------------------------------------------------------------------------------------------------------
class Room:
    def __init__(self) -> None:
        self.peers: dict[str, WebSocket] = {}


ROOMS: dict[str, Room] = {}
RELAY = {"offer", "answer", "ice", "caption", "hangup", "context", "mute", "ping"}


def _auth_ws(aid: str, key: str | None, cookie: str | None) -> str | None:
    """Who is this socket? 'family' (household key owns the appointment) or 'doctor' (partner cookie for the store)."""
    with session() as db:
        a = db.get(Appointment, aid)
        if not a or a.kind != "video":
            return None
        k = valid_key(key)
        if k:
            h = household(db, k, create=False)
            return "family" if h and h.id == a.household_id else None
        p = verify(cookie)
        if p and p.get("k") == "partner":
            u = db.get(PartnerUser, p.get("id"))
            if u and u.active and u.store_id == a.store_id and u.role == "doctor" and u.verified:
                return "doctor"
    return None


@ws.websocket("/ws/call/{aid}")
async def call_socket(socket: WebSocket, aid: str):
    role = _auth_ws(aid, socket.query_params.get("key"), socket.cookies.get(PARTNER_COOKIE))
    if not role:
        await socket.close(code=4401)
        return
    await socket.accept()
    room = ROOMS.setdefault(aid, Room())
    old = room.peers.get(role)
    room.peers[role] = socket
    if old is not None:
        try:
            await old.close(code=4409)
        except Exception:
            pass
    other = "doctor" if role == "family" else "family"
    await socket.send_text(json.dumps({"type": "hello", "you": role, "peerPresent": other in room.peers, "ice": ice_servers()}))
    if other in room.peers:
        try:
            await room.peers[other].send_text(json.dumps({"type": "peer", "present": True, "who": role}))
        except Exception:
            pass
    try:
        while True:
            raw = await socket.receive_text()
            if len(raw) > 60000:
                continue
            try:
                msg = json.loads(raw)
            except Exception:
                continue
            t = msg.get("type")
            if t not in RELAY:
                continue
            if t == "ping":
                await socket.send_text('{"type":"pong"}')
                continue
            peer = room.peers.get(other)
            if peer is None:
                await socket.send_text(json.dumps({"type": "peer", "present": False, "who": other}))
                continue
            msg["from"] = role
            try:
                await peer.send_text(json.dumps(msg))
            except Exception:
                room.peers.pop(other, None)
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        if room.peers.get(role) is socket:
            room.peers.pop(role, None)
            peer = room.peers.get(other)
            if peer is not None:
                try:
                    await peer.send_text(json.dumps({"type": "peer", "present": False, "who": role}))
                except Exception:
                    pass
        if not room.peers:
            ROOMS.pop(aid, None)

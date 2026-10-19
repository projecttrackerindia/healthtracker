"""Take-your-data export (/api/v1/export) — the DPDP Act 2023 right to access and portability, done properly.

One ZIP: the family's whole record as readable JSON (profiles, readings, results, medicines, cards, trackers — the same
record the app keeps, decrypted for the family that owns it), every document in the vault with its original name,
orders, lab bookings, appointments, consult summaries, messages with partners and notices, plus a README that says
what each file is. Built in memory and streamed once; nothing is left on the server.
"""
from __future__ import annotations

import io
import json
import re
import time
import zipfile

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import storage
from .auth import limit
from .db import get_db
from .family import decrypt
from .inbox import msg_json, notice_json
from .models import Appointment, HouseholdState, Message, Notice, Order, StoredFile, User
from .routes import household, order_json

r = APIRouter(prefix="/api/v1")
MAX_ZIP = 400 * 1024 * 1024
EXT = {"application/pdf": ".pdf", "image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp", "text/plain": ".txt", "audio/webm": ".webm", "audio/mp4": ".m4a"}


def _safe(name: str) -> str:
    return re.sub(r"[^\w\-. ()]+", "_", name or "").strip()[:80] or "file"


@r.get("/export")
def export(request: Request, db: Session = Depends(get_db), x_dokko_key: str | None = Header(None)):
    h = household(db, x_dokko_key, create=False)
    if not h:
        raise HTTPException(400, "missing household key")
    limit(request, f"export:{h.id}", 3, 86400)
    buf = io.BytesIO()
    total = 0
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        st = db.get(HouseholdState, h.id)
        state = {}
        if st:
            try:
                state = decrypt(st.blob)
            except Exception:
                state = {"error": "the record could not be decrypted with the current key"}
        z.writestr("record.json", json.dumps(state, ensure_ascii=False, indent=1))
        users = db.scalars(select(User).where(User.household_id == h.id)).all()
        z.writestr("accounts.json", json.dumps([{"name": u.name, "email": u.email, "phone": u.phone, "emailVerified": u.email_verified, "phoneVerified": u.phone_verified,
                                                 "profile": u.member_id, "created": getattr(u, "created", None)} for u in users], ensure_ascii=False, indent=1))
        orders = db.scalars(select(Order).where(Order.household_id == h.id).order_by(Order.created)).all()
        z.writestr("orders.json", json.dumps([order_json(o) for o in orders], ensure_ascii=False, indent=1))
        appts = db.scalars(select(Appointment).where(Appointment.household_id == h.id).order_by(Appointment.created)).all()
        z.writestr("appointments.json", json.dumps([{"id": a.id, "store": a.store_id, "member": a.member_name, "kind": a.kind, "date": a.date, "time": a.time, "why": a.why, "doctor": a.doctor,
                                                     "status": a.status, "slot": f"{a.slot_date} {a.slot_time}".strip(), "note": a.note, "transcript": a.transcript, "prescription": a.rx,
                                                     "summary": a.summary, "created": a.created} for a in appts], ensure_ascii=False, indent=1))
        msgs = db.scalars(select(Message).where(Message.household_id == h.id).order_by(Message.t)).all()
        z.writestr("messages.json", json.dumps([{**msg_json(m), "store": m.store_id} for m in msgs], ensure_ascii=False, indent=1))
        notices = db.scalars(select(Notice).where(Notice.household_id == h.id).order_by(Notice.t)).all()
        z.writestr("notices.json", json.dumps([notice_json(n) for n in notices], ensure_ascii=False, indent=1))
        files = db.scalars(select(StoredFile).where(StoredFile.household_id == h.id).order_by(StoredFile.created)).all()
        index, skipped = [], []
        for f in files:
            if total + f.size > MAX_ZIP:
                skipped.append(f.file_id)
                continue
            try:
                got = storage.get(db, h.id, f.file_id)
            except Exception:
                got = None
            if not got:
                skipped.append(f.file_id)
                continue
            row, data = got
            base = _safe(row.name) or row.file_id
            ext = EXT.get(row.mime, "")
            if ext and not base.lower().endswith(ext):
                base += ext
            path = f"documents/{row.file_id}_{base}"
            z.writestr(path, data)
            total += len(data)
            index.append({"id": row.file_id, "file": path, "name": row.name, "mime": row.mime, "size": row.size, "added": row.created})
        z.writestr("documents/index.json", json.dumps({"files": index, "notIncluded": skipped}, ensure_ascii=False, indent=1))
        z.writestr("README.txt", f"""TheHealthTracker — your family's data export
Generated {time.strftime('%d/%m/%Y %H:%M')} IST for household {h.id}.

record.json         Everything the app keeps for your family: profiles, readings, lab results, medicines and doses, cards,
                    trackers (pregnancy, cycle, growth), care plans, consents and the audit ledger. This is the same record
                    that is stored encrypted on our servers; here it is decrypted for you.
documents/          Every report, prescription, card scan and voice note in your vault, with the original file name.
                    documents/index.json maps each file to its record entry (the id matches `doc` / `file` fields in record.json).
orders.json         Medicine orders and lab bookings with their status timelines.
appointments.json   Visits requested at partner hospitals, including video-consult transcripts, e-prescriptions and summaries.
messages.json       Your conversations with partner labs, pharmacies and hospitals.
notices.json        Notifications you received (order updates, reports ready, nudges).
accounts.json       The sign-ins attached to this family (no passwords).

This export is provided under the Digital Personal Data Protection Act, 2023 (right to access and portability).
To erase everything, use Family & Privacy → Delete family data in the app, or write to privacy@thehealthtracker.com.
""")
    buf.seek(0)
    name = f"thehealthtracker-export-{time.strftime('%Y%m%d')}.zip"
    return StreamingResponse(buf, media_type="application/zip", headers={"Content-Disposition": f'attachment; filename="{name}"', "Cache-Control": "private, no-store"})

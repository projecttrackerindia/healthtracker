"""Backups the family can see (/api/v1/backup/*).

The record already lives encrypted on the server with 30 days of history, and the vault's documents are in object
storage. What families miss is proof: this module sends a copy of the record (ZIP, documents left out so it stays small)
to the family's verified email on the first morning of every month, lets them ask for one now, and tells the app when the
last copy went and where to.
"""
from __future__ import annotations

import time
from datetime import date

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import messaging
from .auth import csrf, limit, need_user
from .db import get_db
from .export import build_zip
from .family import my_household
from .models import Household, HouseholdState, ReminderSent, User, now
from .routes import household as household_by_key

r = APIRouter(prefix="/api/v1/backup")
MAX_ATTACH = 12 * 1024 * 1024


def recipients(db: Session, hid: str) -> list[User]:
    """Verified-email accounts of the family, owners first."""
    rows = db.scalars(select(User).where(User.household_id == hid, User.email_verified == True)).all()  # noqa: E712
    return [u for u in rows if u.email]


def send_backup(db: Session, h: Household, state: dict | None = None, why: str = "monthly") -> dict:
    """Build the record ZIP and mail it to every verified address. Returns what happened (never raises for a mail failure)."""
    to = recipients(db, h.id)
    if not to:
        return {"sent": 0, "reason": "no verified email"}
    if not messaging.email_ready():
        return {"sent": 0, "reason": "email is not configured"}
    data = build_zip(db, h, include_files=False)
    if len(data) > MAX_ATTACH:
        return {"sent": 0, "reason": "record too large to attach"}
    stamp = time.strftime("%Y-%m-%d")
    name = f"urbanhealth-backup-{stamp}.zip"
    text = (f"Your family's Urban Health record, as of {time.strftime('%d %b %Y, %H:%M')} IST.\n\n"
            "Inside: record.json (profiles, readings, results, medicines, cards, trackers, consents), orders, appointments, messages, notices and a README. "
            "Documents are not attached — they stay safe in your vault; a full copy with every file is one tap away in the app: Family & Privacy → My data → Download a copy.\n\n"
            f"This copy was sent because {'it is the first of the month' if why == 'monthly' else 'you asked for it'}. Keep it somewhere safe; anyone with the file can read it.\n\n"
            "— Urban Health")
    sent = 0
    for u in to:
        try:
            messaging.send_mail_attachment(u.email, f"Your family's health record — backup {stamp}", text, name, data)
            sent += 1
        except Exception as e:
            print("[backup] mail failed:", str(e)[:160], flush=True)
    if sent:
        h.backup_at = now()
        h.backup_to = ", ".join(u.email for u in to[:3])
    return {"sent": sent, "size": len(data), "to": [u.email for u in to]}


def monthly(db: Session, today: date) -> int:
    """Called by the morning job: on the 1st, one backup per household that has a verified email. Idempotent per month."""
    if today.day != 1:
        return 0
    n = 0
    for h in db.scalars(select(Household)).all():
        key = f"backup:{h.id}:{today.strftime('%Y-%m')}"
        if db.get(ReminderSent, key) or getattr(h, "blocked", False):
            continue
        if not db.get(HouseholdState, h.id) or not recipients(db, h.id):
            continue
        db.add(ReminderSent(key=key))
        if send_backup(db, h, why="monthly").get("sent"):
            n += 1
    return n


def _status(db: Session, h: Household) -> dict:
    st = db.get(HouseholdState, h.id)
    to = recipients(db, h.id)
    nxt = date.today().replace(day=1)
    nxt = (nxt.replace(month=nxt.month + 1) if nxt.month < 12 else nxt.replace(year=nxt.year + 1, month=1))
    return {"synced": bool(st), "version": st.version if st else 0, "lastEmail": h.backup_at, "emailTo": h.backup_to or "", "willEmail": [u.email for u in to],
            "nextEmail": nxt.isoformat(), "email": messaging.email_ready()}


@r.get("/status")
def status(db: Session = Depends(get_db), x_dokko_key: str | None = Header(None)):
    h = household_by_key(db, x_dokko_key, create=False)
    if not h:
        raise HTTPException(400, "missing household key")
    return _status(db, h)


@r.post("/send", dependencies=[Depends(csrf)])
def send_now(request: Request, db: Session = Depends(get_db), u: User = Depends(need_user)):
    h = my_household(db, u)
    limit(request, f"backup:{h.id}", 2, 86400)
    res = send_backup(db, h, why="asked")
    if not res.get("sent"):
        raise HTTPException(409, {"no verified email": "Verify your email address first (Family & Privacy → Accounts).", "email is not configured": "Email is not set up on this server.",
                                  "record too large to attach": "The record is too large to email; download it from My data instead."}.get(res.get("reason", ""), "Could not send the backup."))
    return {"ok": True, **res, **_status(db, h)}

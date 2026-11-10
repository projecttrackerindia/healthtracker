"""Operations: security events, crash reports with alerts, privacy-safe screen counts, and the admin view of them."""
from __future__ import annotations

import datetime as _dt
import hashlib
import os
import re
import traceback

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from . import messaging
from .db import get_db
from .models import ErrorEvent, SecurityEvent, UsageDay, now

r = APIRouter(prefix="/api/v2")
ALERT_EVERY = 3600          # one email per kind of error per hour, however often it happens
SCREENS = re.compile(r"^[a-z][a-z0-9-]{1,31}$")


def _ip_hash(request: Request | None) -> str:
    ip = (request.client.host if request and request.client else "") or ""
    return hashlib.sha256(("uh-ip:" + ip).encode()).hexdigest()[:24] if ip else ""


def security(db: Session, kind: str, user_id: str = "", request: Request | None = None) -> None:
    from .auth import device_of
    try:
        db.add(SecurityEvent(user_id=user_id or "", kind=kind[:24], ip_hash=_ip_hash(request), device=device_of(request) if request else ""))
    except Exception:
        pass


def record_error(db: Session, side: str, where: str, message: str) -> None:
    message = re.sub(r"[\w.+-]+@[\w-]+\.[\w.]+|\+?\d{10,13}", "•", message or "")[:300]   # no emails or phone numbers
    sig = hashlib.sha1(f"{side}|{where}|{message[:120]}".encode()).hexdigest()
    e = db.scalar(select(ErrorEvent).where(ErrorEvent.sig == sig))
    if e:
        e.count, e.last = e.count + 1, now()
    else:
        e = ErrorEvent(sig=sig, side=side, where=where[:120], message=message)
        db.add(e)
    if now() - (e.alerted or 0) > ALERT_EVERY:
        e.alerted = now()
        to = os.getenv("ADMIN_ALERT_EMAIL") or os.getenv("LEGAL_EMAIL") or ""
        if to:
            try:
                messaging.mail(to, f"Urban Health {side} error: {where[:60]}", f"{message}\n\nSeen {e.count} time(s). Version {os.getenv('APP_VERSION', 'dev')}.")
            except Exception:
                pass


class ClientError(BaseModel):
    where: str = ""
    message: str = ""


@r.post("/client-error", status_code=204)
def client_error(body: ClientError, request: Request, db: Session = Depends(get_db)):
    from .auth import limit
    limit(request, "clienterr", 20, 600)
    record_error(db, "web", body.where, body.message)
    db.commit()


class Seen(BaseModel):
    screen: str


@r.post("/usage", status_code=204)
def usage(body: Seen, request: Request, db: Session = Depends(get_db)):
    from .auth import limit
    limit(request, "usage", 120, 600)
    if not SCREENS.match(body.screen or ""):
        return
    day = _dt.date.today().isoformat()
    row = db.get(UsageDay, (day, body.screen))
    if row:
        row.n += 1
    else:
        db.add(UsageDay(day=day, screen=body.screen, n=1))
    db.commit()


@r.get("/ops/summary")
def summary(request: Request, db: Session = Depends(get_db)):
    from .auth import need_user
    u = need_user(request, db)
    if (u.role or "") != "admin" and (u.email or "").lower() != os.getenv("ADMIN_EMAIL", "admin@urbanhealth.in").lower():
        raise HTTPException(403, "Admins only")
    since = (_dt.date.today() - _dt.timedelta(days=30)).isoformat()
    screens = db.execute(select(UsageDay.screen, func.sum(UsageDay.n)).where(UsageDay.day >= since).group_by(UsageDay.screen).order_by(func.sum(UsageDay.n).desc())).all()
    errs = db.scalars(select(ErrorEvent).order_by(ErrorEvent.last.desc()).limit(30)).all()
    sec = db.execute(select(SecurityEvent.kind, func.count()).where(SecurityEvent.t > now() - 30 * 86400).group_by(SecurityEvent.kind)).all()
    return {"screens": [{"screen": a, "opens": int(b)} for a, b in screens], "errors": [{"side": e.side, "where": e.where, "message": e.message, "count": e.count, "last": e.last} for e in errs],
            "security": {k: int(n) for k, n in sec}}


def purge(db: Session) -> dict:
    a = db.query(SecurityEvent).filter(SecurityEvent.t < now() - 400 * 86400).delete(synchronize_session=False)
    b = db.query(ErrorEvent).filter(ErrorEvent.last < now() - 90 * 86400).delete(synchronize_session=False)
    c = db.query(UsageDay).filter(UsageDay.day < (_dt.date.today() - _dt.timedelta(days=400)).isoformat()).delete(synchronize_session=False)
    return {"security": a, "errors": b, "usage": c}


def server_error(request: Request, exc: Exception) -> None:
    from .db import session
    try:
        with session() as db:
            tb = traceback.extract_tb(exc.__traceback__)
            last = tb[-1] if tb else None
            record_error(db, "server", f"{request.method} {re.sub(r'/[a-zA-Z0-9_-]{16,}', '/…', request.url.path)}", f"{type(exc).__name__}: {str(exc)[:160]}" + (f" @ {os.path.basename(last.filename)}:{last.lineno}" if last else ""))
            db.commit()
    except Exception:
        pass

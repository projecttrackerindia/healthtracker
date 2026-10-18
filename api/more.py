"""Round 4 endpoints: document sync, share links, push subscriptions, client error reports, public settings."""
from __future__ import annotations

import hashlib
import os
import secrets
import time

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from . import push as PUSH, storage
from .auth import csrf, current_user, limit, need_user
from .db import get_db
from .family import my_household
from .models import ClientError, PushSub, Setting, ShareLink, StoredFile, User, now

r = APIRouter(prefix="/api/v1")
SAFE_MIME = ("application/pdf", "image/jpeg", "image/png", "image/webp", "image/heic", "image/heif")


def hlimit(request: Request, key: str, hid: str, n: int, per: int):
    """Rate limit per household (families share Wi-Fi, so per-IP limits would trip)."""
    limit(request, f"{key}:{hid}", n, per)


# ---- documents ------------------------------------------------------------------------------------------------------
@r.get("/files")
def files_list(db: Session = Depends(get_db), u: User = Depends(need_user)):
    h = my_household(db, u)
    rows = db.scalars(select(StoredFile).where(StoredFile.household_id == h.id)).all()
    return {"backend": storage.backend(), "files": [{"id": f.file_id, "size": f.size, "mime": f.mime, "name": f.name, "updated": f.updated} for f in rows],
            "bytes": sum(f.size for f in rows)}


@r.put("/files/{file_id}", dependencies=[Depends(csrf)])
async def file_put(file_id: str, request: Request, db: Session = Depends(get_db), u: User = Depends(need_user)):
    h = my_household(db, u)
    hlimit(request, "fileput", h.id, 120, 3600)
    if not (1 <= len(file_id) <= 48) or not file_id.replace(":", "").replace("_", "").replace("-", "").isalnum():
        raise HTTPException(400, "bad file id")
    data = await request.body()
    if not data or len(data) > storage.MAX_FILE:
        raise HTTPException(413, "File must be between 1 byte and 15 MB")
    mime = (request.headers.get("content-type") or "application/octet-stream").split(";")[0].strip()
    if mime not in SAFE_MIME:
        raise HTTPException(415, "PDF or image only")
    used = db.scalar(select(func.coalesce(func.sum(StoredFile.size), 0)).where(StoredFile.household_id == h.id)) or 0
    cap = int(os.getenv("FILES_CAP_MB", "2048")) * 1024 * 1024
    if used + len(data) > cap:
        raise HTTPException(507, "Your family's document storage is full. Delete old documents or contact support.")
    name = request.headers.get("x-file-name", "")[:160]
    try:
        n = storage.put(db, h.id, file_id, data, mime, name, u.id)
    except Exception as e:
        print("[storage] put failed:", type(e).__name__, str(e)[:200], flush=True)
        raise HTTPException(502, "The document could not be stored right now. It stays on this device; we will retry.")
    return {"id": file_id, "size": n, "sha": hashlib.sha256(data).hexdigest()[:16]}


@r.get("/files/{file_id}")
def file_get(file_id: str, db: Session = Depends(get_db), u: User = Depends(need_user)):
    h = my_household(db, u)
    try:
        got = storage.get(db, h.id, file_id)
    except Exception as e:
        print("[storage] get failed:", type(e).__name__, str(e)[:200], flush=True)
        raise HTTPException(502, "The document could not be fetched right now.")
    if not got:
        raise HTTPException(404, "not stored")
    row, data = got
    return Response(data, media_type=row.mime, headers={"Cache-Control": "private, max-age=3600", "X-File-Name": row.name or file_id})


@r.delete("/files/{file_id}", dependencies=[Depends(csrf)])
def file_delete(file_id: str, db: Session = Depends(get_db), u: User = Depends(need_user)):
    h = my_household(db, u)
    for s in db.scalars(select(ShareLink).where(ShareLink.household_id == h.id, ShareLink.file_id == file_id)).all():
        db.delete(s)
    return {"deleted": storage.delete(db, h.id, file_id)}


# ---- share a document with a doctor ----------------------------------------------------------------------------------
class ShareIn(BaseModel):
    file_id: str
    label: str = ""
    hours: int = 72


@r.post("/share", dependencies=[Depends(csrf)])
def share_make(body: ShareIn, request: Request, db: Session = Depends(get_db), u: User = Depends(need_user)):
    h = my_household(db, u)
    hlimit(request, "share", h.id, 60, 3600)
    if not db.get(StoredFile, (h.id, body.file_id)):
        raise HTTPException(404, "Upload the document first (it syncs when you are online).")
    hours = max(1, min(24 * 30, body.hours))
    s = ShareLink(token=secrets.token_urlsafe(24), household_id=h.id, file_id=body.file_id, label=body.label[:160], by_user=u.id, expires=now() + hours * 3600)
    db.add(s)
    origin = (os.getenv("APP_ORIGIN") or "").split(",")[0].strip().rstrip("/") or f"{request.headers.get('x-forwarded-proto', request.url.scheme)}://{request.headers.get('x-forwarded-host') or request.headers.get('host')}"
    return {"token": s.token, "url": f"{origin}/d/{s.token}", "expires": s.expires}


@r.get("/share")
def share_list(db: Session = Depends(get_db), u: User = Depends(need_user)):
    h = my_household(db, u)
    rows = db.scalars(select(ShareLink).where(ShareLink.household_id == h.id, ShareLink.revoked == False, ShareLink.expires > now())).all()  # noqa: E712
    return [{"token": s.token, "fileId": s.file_id, "label": s.label, "expires": s.expires, "views": s.views} for s in rows]


@r.delete("/share/{token}", dependencies=[Depends(csrf)])
def share_revoke(token: str, db: Session = Depends(get_db), u: User = Depends(need_user)):
    h = my_household(db, u)
    s = db.get(ShareLink, token)
    if s and s.household_id == h.id:
        s.revoked = True
    return {"revoked": bool(s)}


def shared_file(token: str, db: Session):
    s = db.get(ShareLink, token)
    if not s or s.revoked or s.expires < now():
        return None, None
    try:
        got = storage.get(db, s.household_id, s.file_id)
    except Exception:
        got = None
    if not got:
        return None, None
    return s, got


# ---- web push ---------------------------------------------------------------------------------------------------------
@r.get("/push/key")
def push_key():
    return {"enabled": PUSH.ready(), "key": PUSH.public_key()}


class SubIn(BaseModel):
    subscription: dict


@r.post("/push/subscribe", dependencies=[Depends(csrf)])
def push_subscribe(body: SubIn, request: Request, db: Session = Depends(get_db), u: User = Depends(need_user)):
    if not PUSH.ready():
        raise HTTPException(503, "Push is not set up on this server yet.")
    h = my_household(db, u)
    sub = body.subscription
    if not isinstance(sub, dict) or not sub.get("endpoint") or not isinstance(sub.get("keys"), dict):
        raise HTTPException(400, "bad subscription")
    row = db.scalar(select(PushSub).where(PushSub.endpoint == sub["endpoint"]))
    if row:
        row.user_id, row.household_id, row.sub, row.failures = u.id, h.id, sub, 0
    else:
        db.add(PushSub(user_id=u.id, household_id=h.id, endpoint=sub["endpoint"], sub=sub, ua=request.headers.get("user-agent", "")[:200]))
    return {"ok": True}


@r.post("/push/unsubscribe", dependencies=[Depends(csrf)])
def push_unsubscribe(body: SubIn, db: Session = Depends(get_db), u: User = Depends(need_user)):
    ep = (body.subscription or {}).get("endpoint", "")
    n = db.query(PushSub).filter(PushSub.endpoint == ep, PushSub.user_id == u.id).delete()
    return {"removed": n}


@r.post("/push/test", dependencies=[Depends(csrf)])
def push_test(request: Request, db: Session = Depends(get_db), u: User = Depends(need_user)):
    limit(request, "pushtest", 6, 600)
    subs = db.scalars(select(PushSub).where(PushSub.user_id == u.id)).all()
    sent = 0
    for s in subs:
        ok, status, note = PUSH.send(s.sub, {"title": "TheHealthTracker", "body": "Phone notifications are on. Medicine reminders will arrive like this.", "url": "/app", "tag": "test"})
        if ok:
            sent += 1
        elif status in (404, 410):
            db.delete(s)
    return {"sent": sent, "subscriptions": len(subs)}


# ---- client error reports ----------------------------------------------------------------------------------------------
class ErrIn(BaseModel):
    message: str
    stack: str = ""
    page: str = ""
    version: str = ""


@r.post("/client-error")
def client_error(body: ErrIn, request: Request, db: Session = Depends(get_db)):
    limit(request, "cerr", 30, 600)
    msg = body.message.strip()[:400]
    if not msg:
        return {"ok": True}
    recent = db.scalar(select(ClientError).where(ClientError.message == msg, ClientError.t > now() - 86400))
    if recent:
        recent.count += 1
    else:
        db.add(ClientError(message=msg, stack=body.stack[:4000], page=body.page[:80], ua=request.headers.get("user-agent", "")[:200], version=body.version[:16]))
    return {"ok": True}


# ---- public settings (clinical reviewer, environment) --------------------------------------------------------------------
@r.get("/settings")
def public_settings(db: Session = Depends(get_db)):
    rv = db.get(Setting, "reviewer")
    return {"env": os.getenv("APP_ENV", "production"), "reviewer": (rv.value if rv else None), "push": PUSH.ready(), "files": storage.backend()}

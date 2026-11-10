"""Partner sign-ins by invite link, the partner scorecard, report-quality checks, and coverage.

Sign-ins: an admin invites a person by mobile (and email if they have one) with a role. They get a one-time
link that works for 48 hours; they set their own password. Nobody at Urban Health ever sees or sends it.
"""
from __future__ import annotations

import hashlib
import os
import random
import re
import secrets
import time

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .admin import log, me as admin_me
from .db import get_db
from .models import Admin, Complaint, Household, Order, PartnerUser, QualityFlag, Store, now
from .security import hash_pw

ar = APIRouter(prefix="/api/admin")
pr = APIRouter(prefix="/api/partner")

INVITE_H = 48
ROLES = {"owner": "Owner", "staff": "Staff", "technician": "Technician", "doctor": "Doctor", "pathologist": "Pathologist", "pharmacist": "Pharmacist"}
PROMISE = {"visit": 95, "report": 95, "cancel": 3, "corrections": 5}


def _h(tok: str) -> str:
    return hashlib.sha256(tok.encode()).hexdigest()


def _origin(request: Request) -> str:
    return os.getenv("PUBLIC_URL") or f"{request.headers.get('x-forwarded-proto', request.url.scheme)}://{request.headers.get('host', 'urbanhealth.in')}"


def _send_invite(request: Request, u: PartnerUser, s: Store, tok: str) -> list[str]:
    from . import messaging
    link = f"{_origin(request)}/partner/join/{tok}"
    sent = []
    first = (u.name or "").split(" ")[0] or "there"
    text = f"Hi {first}, Urban Health has invited you to {s.name}. Set up your sign-in (works once, {INVITE_H} h): {link}"
    try:
        if u.phone and (messaging.alert_sms_ready() or messaging.demo()) and messaging.send_text_sms(u.phone, text):
            sent.append("sms")
    except Exception as e:
        print("[invite] sms failed:", str(e)[:120], flush=True)
    try:
        if u.email and not u.email.endswith(".invalid") and (messaging.email_ready() or messaging.demo()):
            messaging.send_mail(u.email, f"Your Urban Health sign-in for {s.name}", text + "\n\nIf you weren't expecting this, ignore it.")
            sent.append("email")
    except Exception as e:
        print("[invite] email failed:", str(e)[:120], flush=True)
    return sent


def signin_json(u: PartnerUser) -> dict:
    t = now()
    if not u.active:
        st, tag = "removed", "Access removed"
    elif (u.locked_until or 0) > t:
        st, tag = "locked", f"Locked · {u.fails} wrong tries"
    elif u.invite_hash and not u.pw_hash:
        st, tag = ("invited", f"Invite sent · expires in {max(0, (u.invite_exp - t) // 3600)} h") if u.invite_exp > t else ("expired", "Invite expired")
    else:
        st, tag = "active", "Active"
    ph = u.phone or ""
    return {"id": u.id, "name": u.name, "role": u.role, "roleText": ROLES.get(u.role, u.role.title()), "status": st, "tag": tag,
            "phone": (ph[:3] + "•••• " + ph[-4:]) if len(ph) >= 8 else ph, "email": "" if u.email.endswith(".invalid") else u.email,
            "lastLogin": u.last_login, "device": u.last_device, "regNo": u.reg_no, "verified": u.verified}


class InviteIn(BaseModel):
    name: str
    phone: str = ""
    email: str = ""
    role: str = "staff"
    regNo: str = ""


@ar.get("/stores/{sid}/signins")
def signins(sid: str, a: Admin = Depends(admin_me), db: Session = Depends(get_db)):
    s = db.get(Store, sid)
    if not s:
        raise HTTPException(404)
    rows = db.scalars(select(PartnerUser).where(PartnerUser.store_id == sid).order_by(PartnerUser.created)).all()
    return {"store": s.name, "rows": [signin_json(u) for u in rows], "portal": "/partner",
            "rules": {"lockAfter": 10, "session": "12 h", "inviteHours": INVITE_H, "max": 25}}


@ar.post("/stores/{sid}/invite")
def invite(sid: str, body: InviteIn, request: Request, a: Admin = Depends(admin_me), db: Session = Depends(get_db)):
    from .auth import norm_id
    s = db.get(Store, sid)
    if not s:
        raise HTTPException(404)
    name = re.sub(r"[<>\x00-\x1f]", "", body.name).strip()[:80]
    if len(name) < 2:
        raise HTTPException(400, "Enter their full name.")
    if body.role not in ROLES:
        raise HTTPException(400, "Choose a role.")
    if body.role == "doctor" and s.kind != "hospital":
        raise HTTPException(400, "Doctors belong to hospitals and clinics.")
    phone = ""
    if body.phone.strip():
        kind, phone = norm_id(body.phone)
        if kind != "phone":
            raise HTTPException(400, "Enter a mobile number.")
    email = body.email.strip().lower()
    if email and not re.fullmatch(r"[^@\s]{1,64}@[^@\s]+\.[a-z]{2,}", email):
        raise HTTPException(400, "That email doesn't look right.")
    if not phone and not email:
        raise HTTPException(400, "Enter a mobile number (or an email).")
    if db.scalar(select(func.count(PartnerUser.id)).where(PartnerUser.store_id == sid, PartnerUser.active == True)) >= 25:  # noqa: E712
        raise HTTPException(400, "A partner can have up to 25 sign-ins. Remove someone first.")
    if body.role == "owner" and db.scalar(select(PartnerUser).where(PartnerUser.store_id == sid, PartnerUser.role == "owner", PartnerUser.active == True)):  # noqa: E712
        raise HTTPException(409, "This partner already has an owner. Change their role first.")
    if phone and db.scalar(select(PartnerUser).where(PartnerUser.phone == phone, PartnerUser.active == True)):  # noqa: E712
        raise HTTPException(409, "This mobile number already signs in for a partner.")
    if email and db.scalar(select(PartnerUser).where(PartnerUser.email == email)):
        raise HTTPException(409, "This email already signs in for a partner.")
    tok = secrets.token_urlsafe(24)
    u = PartnerUser(store_id=sid, name=name, phone=phone, email=email or f"p{phone.lstrip('+')}@phone.invalid", role=body.role, pw_hash="",
                    must_change=False, reg_no=body.regNo.strip()[:40], invite_hash=_h(tok), invite_exp=now() + INVITE_H * 3600)
    db.add(u)
    db.flush()
    sent = _send_invite(request, u, s, tok)
    log(db, a.email, f"partner.invite {s.name} {body.role}", name)
    from . import messaging
    return {**signin_json(u), "sent": sent, **({"demoLink": f"/partner/join/{tok}"} if messaging.demo() else {})}


class SigninAct(BaseModel):
    action: str        # resend | reset | role | signout | unlock | remove
    role: str = ""


@ar.post("/partner-users/{uid}")
def signin_action(uid: str, body: SigninAct, request: Request, a: Admin = Depends(admin_me), db: Session = Depends(get_db)):
    u = db.get(PartnerUser, uid)
    if not u:
        raise HTTPException(404)
    s = db.get(Store, u.store_id)
    out: dict = {}
    if body.action in ("resend", "reset"):
        if not u.active:
            raise HTTPException(400, "Access was removed. Invite them again.")
        tok = secrets.token_urlsafe(24)
        u.invite_hash, u.invite_exp = _h(tok), now() + INVITE_H * 3600
        if body.action == "reset":
            u.pw_hash = ""
            u.session_epoch = (u.session_epoch or 0) + 1
        out["sent"] = _send_invite(request, u, s, tok)
        from . import messaging
        if messaging.demo():
            out["demoLink"] = f"/partner/join/{tok}"
    elif body.action == "role":
        if body.role not in ROLES:
            raise HTTPException(400, "Choose a role.")
        if body.role == "owner" and db.scalar(select(PartnerUser).where(PartnerUser.store_id == u.store_id, PartnerUser.role == "owner", PartnerUser.active == True, PartnerUser.id != u.id)):  # noqa: E712
            raise HTTPException(409, "There is already an owner. Change their role first.")
        u.role = body.role
        u.session_epoch = (u.session_epoch or 0) + 1
    elif body.action == "signout":
        u.session_epoch = (u.session_epoch or 0) + 1
    elif body.action == "unlock":
        u.locked_until, u.fails = 0, 0
    elif body.action == "remove":
        u.active = False
        u.invite_hash = ""
        u.session_epoch = (u.session_epoch or 0) + 1
    else:
        raise HTTPException(400, "Unknown action")
    log(db, a.email, f"partner.signin.{body.action} {s.name if s else ''}", u.name)
    return {**signin_json(u), **out}


# ---- the person's side of the link -----------------------------------------------------------------------------------
def _by_token(db: Session, tok: str) -> PartnerUser:
    if not tok or len(tok) > 80:
        raise HTTPException(404, "This link isn't valid.")
    u = db.scalar(select(PartnerUser).where(PartnerUser.invite_hash == _h(tok)))
    if not u or not u.active:
        raise HTTPException(404, "This link isn't valid. Ask Urban Health to send a new one.")
    if u.invite_exp < now():
        raise HTTPException(410, "This link has expired. Ask Urban Health to send a new one.")
    return u


@pr.get("/join/{tok}")
def join_info(tok: str, request: Request, db: Session = Depends(get_db)):
    from .auth import limit
    limit(request, "partner-join", 20, 600)
    u = _by_token(db, tok)
    s = db.get(Store, u.store_id)
    return {"name": u.name, "role": ROLES.get(u.role, u.role), "store": s.name if s else "", "area": s.area if s else "",
            "phone": (u.phone[:3] + "•••• " + u.phone[-4:]) if u.phone else "", "email": "" if u.email.endswith(".invalid") else u.email}


class JoinIn(BaseModel):
    token: str
    password: str


@pr.post("/join")
def join(body: JoinIn, request: Request, db: Session = Depends(get_db)):
    from .auth import limit
    from .passwords import check
    limit(request, "partner-join", 20, 600)
    u = _by_token(db, body.token)
    bad = check(body.password or "", name=u.name, email=u.email, phone=u.phone)
    if bad:
        raise HTTPException(400, "Password: " + "; ".join(bad).lower() + ".")
    u.pw_hash = hash_pw(body.password)
    u.invite_hash, u.invite_exp, u.must_change, u.fails, u.locked_until = "", 0, False, 0, 0
    db.add(__import__("api.models", fromlist=["Audit"]).Audit(who="partner:" + u.email, what=f"partner.join {u.store_id}"))
    return {"ok": True, "signIn": u.phone or u.email}


# ---- scorecard -------------------------------------------------------------------------------------------------------
@ar.get("/stores/{sid}/scorecard")
def scorecard(sid: str, days: int = 30, a: Admin = Depends(admin_me), db: Session = Depends(get_db)):
    from .console import late_by, _ist
    s = db.get(Store, sid)
    if not s:
        raise HTTPException(404)
    days = 7 if days <= 7 else 90 if days >= 90 else 30
    t = now()
    lo = t - days * 86400
    os_ = db.scalars(select(Order).where(Order.store_id == sid, Order.created > lo)).all()
    done = [o for o in os_ if o.status in ("ready", "delivered", "completed")]
    lab = s.kind == "lab"

    def ts(o, st):
        return next((x.get("t") for x in (o.timeline or []) if x.get("s") == st), None)
    visits = [o for o in done if lab]
    v_ok = sum(1 for o in visits if not late_by(o, ts(o, "collected") or ts(o, "arrived") or o.done_at or t))
    rep = [o for o in done if lab and ts(o, "ready") and ts(o, "collected")]
    tat = max(6, int((s.eta_min or 1440) / 60)) if s.eta_min and s.eta_min > 90 else 24
    r_ok = sum(1 for o in rep if ts(o, "ready") - ts(o, "collected") <= tat * 3600)
    cancelled = sum(1 for o in os_ if o.status == "cancelled" and any((x.get("by") or "").startswith("partner") or x.get("why") == "store" for x in (o.timeline or [])))
    corrections = db.scalar(select(func.count(QualityFlag.id)).where(QualityFlag.store_id == sid, QualityFlag.created > lo, QualityFlag.serious == True)) or 0  # noqa: E712
    ratings = [o.rating for o in done if o.rating]
    pct = lambda a_, b_: round(100 * a_ / b_) if b_ else None  # noqa: E731
    days_series = []
    for d in range(min(days, 30) - 1, -1, -1):
        dlo = t - (d + 1) * 86400
        day_rep = [o for o in rep if dlo < (ts(o, "ready") or 0) <= dlo + 86400]
        day_vis = [o for o in visits if dlo < (o.created or 0) <= dlo + 86400]
        val = pct(sum(1 for o in day_rep if ts(o, "ready") - ts(o, "collected") <= tat * 3600), len(day_rep)) if lab else pct(sum(1 for o in day_vis if not late_by(o, o.done_at or t)), len(day_vis))
        days_series.append({"day": time.strftime("%d %b", _ist(dlo + 86400)), "pct": val})
    m = {"visit": pct(v_ok, len(visits)), "report": pct(r_ok, len(rep)), "rating": round(sum(ratings) / len(ratings), 1) if ratings else None,
         "ratingN": len(ratings), "cancel": pct(cancelled, len(os_)) if os_ else None, "corrections": corrections, "orders": len(os_)}
    below = [k for k in ("visit", "report") if m[k] is not None and m[k] < PROMISE[k]] + [k for k in ("cancel",) if m[k] is not None and m[k] > PROMISE[k]] + (["corrections"] if corrections > PROMISE["corrections"] else [])
    peers = [x for x in db.scalars(select(Store).where(Store.kind == s.kind, Store.verified == True, Store.city == s.city)).all()]  # noqa: E712
    rank = sorted(peers, key=lambda x: (-(x.rating or 0) * (x.rating_n or 0) ** .5))
    stand = next((i + 1 for i, x in enumerate(rank) if x.id == s.id), None)
    voices = [{"stars": o.rating, "text": o.rating_note} for o in sorted(done, key=lambda o: -(o.created or 0)) if o.rating and o.rating_note][:4]
    return {"store": s.name, "kind": s.kind, "days": days, "m": m, "promise": PROMISE, "below": below, "series": days_series,
            "standing": {"rank": stand, "of": len(peers), "city": s.city}, "voices": voices,
            "status": "Hidden from new bookings" if len(below) >= 2 else "Warning sent" if below else "Keeping its promises"}


# ---- report quality --------------------------------------------------------------------------------------------------
def check_report(db: Session, o: Order, s: Store, data: bytes, mime: str) -> list[QualityFlag]:
    """Called when a lab uploads a report. Raises flags; never blocks the family from getting their report."""
    flags = []
    hsh = hashlib.sha256(data).hexdigest()
    same = db.scalar(select(QualityFlag).where(QualityFlag.file_hash == hsh, QualityFlag.order_id != o.id))
    if same or db.scalar(select(func.count(QualityFlag.id)).where(QualityFlag.file_hash == hsh, QualityFlag.order_id != o.id)):
        flags.append(QualityFlag(store_id=s.id, order_id=o.id, kind="copied", serious=True, text="Exactly the same file was uploaded for a different person"))
    text = ""
    if mime == "application/pdf":
        try:
            from . import ai
            text = ai.text_from(data, mime) or ""
        except Exception:
            text = ""
        if len(text) > 200:
            from .storage import looks_medical
            if not looks_medical(text):
                flags.append(QualityFlag(store_id=s.id, order_id=o.id, kind="not_medical", serious=True, text="The file doesn't read like a lab report"))
            if not re.search(r"(?i)patholog|\bMD\b|\bDCP\b|\bDNB\b|consultant|authori[sz]ed|reg\.?\s*no", text):
                flags.append(QualityFlag(store_id=s.id, order_id=o.id, kind="unsigned", serious=True, text="No pathologist name or registration found on the report"))
            if not re.search(r"(?i)reference|ref\.?\s*range|normal range|biological", text):
                flags.append(QualityFlag(store_id=s.id, order_id=o.id, kind="no_range", text="Reference ranges are missing"))
    col = next((x.get("t") for x in (o.timeline or []) if x.get("s") == "collected"), None)
    if col and now() - col > 36 * 3600:
        flags.append(QualityFlag(store_id=s.id, order_id=o.id, kind="late", text=f"Report came {(now() - col) // 3600} h after the sample was collected"))
    if random.random() < 0.02:
        flags.append(QualityFlag(store_id=s.id, order_id=o.id, kind="sample", text="Random check: a person should review this report"))
    marker = QualityFlag(store_id=s.id, order_id=o.id, kind="received", text="", file_hash=hsh, status="resolved")
    for f in flags + [marker]:
        db.add(f)
    return flags


KIND_TITLE = {"copied": "Same report for different people", "not_medical": "Doesn't look like a lab report", "unsigned": "No pathologist signature",
              "no_range": "Reference range missing", "late": "Uploaded late", "sample": "Random check · 2% sample"}


@ar.get("/quality")
def quality(a: Admin = Depends(admin_me), db: Session = Depends(get_db)):
    t = now()
    wk = t - 7 * 86400
    rec = db.scalar(select(func.count(QualityFlag.id)).where(QualityFlag.kind == "received", QualityFlag.created > wk)) or 0
    flags = db.scalars(select(QualityFlag).where(QualityFlag.kind != "received", QualityFlag.created > t - 30 * 86400).order_by(QualityFlag.created.desc())).all()
    wk_flags = [f for f in flags if f.created > wk]
    stores = {s.id: s for s in db.scalars(select(Store)).all()}
    serious = {}
    for f in wk_flags:
        if f.serious:
            serious[f.store_id] = serious.get(f.store_id, 0) + 1
    watch = [{"id": sid, "name": stores[sid].name if sid in stores else sid, "serious": n, "paused": not stores[sid].active if sid in stores else False}
             for sid, n in sorted(serious.items(), key=lambda x: -x[1]) if n >= 3]
    return {"received": rec, "flagged": len({f.order_id for f in wk_flags}), "passed": max(0, rec - len({f.order_id for f in wk_flags})), "watch": watch,
            "rows": [{"id": f.id, "kind": f.kind, "title": KIND_TITLE.get(f.kind, f.kind), "text": f.text, "serious": f.serious, "status": f.status,
                      "store": stores[f.store_id].name if f.store_id in stores else "", "storeId": f.store_id, "order": f.order_id, "t": f.created} for f in flags if f.status == "open"][:200]}


@ar.post("/quality/{fid}/resolve")
def quality_resolve(fid: int, a: Admin = Depends(admin_me), db: Session = Depends(get_db)):
    f = db.get(QualityFlag, fid)
    if not f:
        raise HTTPException(404)
    f.status = "resolved"
    log(db, a.email, f"quality.resolve {fid} {f.kind}")
    return {"ok": True}


# ---- coverage --------------------------------------------------------------------------------------------------------
@ar.get("/coverage")
def coverage(kind: str = "lab", a: Admin = Depends(admin_me), db: Session = Depends(get_db)):
    t = now()
    pins: dict[str, dict] = {}

    def P(pin):
        return pins.setdefault(pin, {"pin": pin, "area": "", "families": 0, "orders": 0, "partners": 0})
    for s in db.scalars(select(Store).where(Store.kind == kind, Store.verified == True, Store.active == True)).all():  # noqa: E712
        cov = set(re.findall(r"\b\d{6}\b", ((s.profile or {}).get("pins") or "") + " " + (s.pin or "")))
        for p in cov:
            x = P(p)
            x["partners"] += 1
            x["area"] = x["area"] or (s.area if p == s.pin else "")
    for o in db.scalars(select(Order).where(Order.kind == ("medicine" if kind == "pharmacy" else kind), Order.created > t - 30 * 86400)).all():
        pin = str((o.addr or {}).get("pin") or "") or (re.findall(r"\b\d{6}\b", o.address or "") or [""])[-1]
        if pin:
            x = P(pin)
            x["orders"] += 1
            x["area"] = x["area"] or (o.addr or {}).get("area", "")
    for h in db.scalars(select(Household).where(Household.last_seen > t - 30 * 86400)).all() if hasattr(Household, "last_seen") else []:
        pin = getattr(h, "pin", "") or ""
        if pin:
            P(pin)["families"] += 1
    rows = list(pins.values())
    for x in rows:
        x["state"] = "none" if not x["orders"] and not x["families"] and not x["partners"] else "gap" if x["partners"] == 0 else "thin" if x["partners"] == 1 else "good"
    gaps = sorted([x for x in rows if x["state"] == "gap"], key=lambda x: -(x["orders"] + x["families"]))
    return {"rows": sorted(rows, key=lambda x: x["pin"]), "gaps": gaps[:8],
            "summary": {"covered": sum(1 for x in rows if x["partners"]), "total": len(rows), "gapOrders": sum(x["orders"] for x in gaps)}}

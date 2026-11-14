"""Admin API (/api/admin): login, dashboard, partners (pharmacies, labs, hospitals), price lists, orders, households,
plans & subscriptions, seasonal advisories, first-aid videos, admins and the audit log. Session = signed HttpOnly cookie."""
from __future__ import annotations

import csv
import io
import time
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, Response, UploadFile, File
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from . import ai as AI
from .ai import LAST_ERROR as AI_LAST_ERROR
from .db import get_db
from .models import Admin, AiJob, Audit, Household, HouseholdState, HouseholdStateHistory, LabTest, PartnerUser, Order, Plan, Seasonal, Store, StoreItem, Subscription, Video, now
from .security import check_pw, hash_pw, sign, verify
from .seed import CATALOG, TESTS

r = APIRouter(prefix="/api/admin")
COOKIE = "dk_admin"


# ---- who may do what ---------------------------------------------------------------------------------------------------
# Checked here, once, for every admin route in every module, so a new route is covered the day it is added.
#   owner    everything
#   ops      runs the business day to day: partners, orders, families' accounts, privacy queue. Not money settings,
#            other admins, platform settings, deleting partners or rewriting a family's record.
#   content  first-aid videos, seasonal tips, the medicine and test catalogue, products and offers. Nothing about people.
import re as _re

_OWNER_ONLY = [
    (None, r"/admins(/.*)?"), ("PUT", r"/plans/.+"), ("POST", r"/settings/.+"), ("POST", r"/storage/test"), ("POST", r"/ai/test"),
    ("DELETE", r"/client-errors"), ("POST", r"/stores/import"), ("DELETE", r"/stores/[^/]+"), ("POST", r"/stores/[^/]+/purge"), ("POST", r"/stores/[^/]+/commission"),
    ("POST", r"/households/[^/]+/restore/.+"), ("POST", r"/families/[^/]+/state"), ("PUT", r"/messaging/.+"), ("PUT", r"/app/.+"),
    ("PUT", r"/services/.+"), ("POST", r"/settlements/.+"), ("DELETE", r"/settlements/.+"), ("POST", r"/payments/[^/]+/(confirm|reject)"),
]
_EVERYONE = r"/(me(/.*)?|devices(/.*)?|signout-everywhere|logout|login|totp(/.*)?)"
_CONTENT = r"/(seasonal|videos|catalog|products|offers)(/.*)?"
ROLE_LABEL = {"owner": "Owner", "ops": "Operations", "content": "Content"}


def allowed(role: str, method: str, path: str) -> bool:
    sub = path.split("/api/admin", 1)[-1] or "/"
    if role == "owner" or _re.fullmatch(_EVERYONE, sub):
        return True
    if role == "content":
        return bool(_re.fullmatch(_CONTENT, sub))
    if role == "ops":
        return not any((m is None or m == method) and _re.fullmatch(rx, sub) for m, rx in _OWNER_ONLY)
    return False


def me(request: Request, db: Session = Depends(get_db)) -> Admin:
    p = verify(request.cookies.get(COOKIE))
    if not p:
        raise HTTPException(401, "login required")
    a = db.get(Admin, p.get("id"))
    if not a or int(p.get("ep") or 0) != int(a.session_epoch or 0):
        raise HTTPException(401, "login required")
    if request.url.path.startswith("/api/admin") and not allowed(a.role, request.method, request.url.path):
        log(db, a.email, "denied", f"{request.method} {request.url.path}")
        db.commit()
        raise HTTPException(403, f"Your role ({ROLE_LABEL.get(a.role, a.role)}) can't do this. Ask the owner.")
    return a


def owner(a: Admin = Depends(me)) -> Admin:
    if a.role != "owner":
        raise HTTPException(403, "owner only")
    return a


def log(db: Session, who: str, what: str, detail: str = ""):
    db.add(Audit(who=who, what=what[:200], detail=detail[:4000]))


class Login(BaseModel):
    email: str
    password: str
    code: str = ""
    totp: str = ""     # 6-digit code from the authenticator app
    enrol: str = ""    # signed set-up token from the first sign-in, sent back with the first code


def _totp_step(db: Session, a: Admin, body: "Login") -> bool:
    """Authenticator app on every sign-in. Returns True when it was used (it then replaces the new-device code).
    First sign-in after it is switched on: we hand out a secret to scan, and the account is enrolled only once a
    correct code comes back, so a half-finished set-up can't lock anyone out or leave a known secret behind."""
    from . import totp
    if not totp.required() and not a.totp_secret:
        return False
    if a.totp_secret:
        if not body.totp:
            raise HTTPException(428, {"needTotp": True})
        st = totp.verify(totp.unseal(a.totp_secret), body.totp, a.totp_step or 0)
        if not st:
            log(db, a.email, "login.totp_fail")
            db.commit()
            raise HTTPException(401, "That code didn't match. Use the newest code in your authenticator app.")
        a.totp_step = st
        return True
    if body.enrol and body.totp:
        d = verify(body.enrol)
        if not d or d.get("t") != "totp-enrol" or d.get("id") != a.id or now() - int(d.get("at") or 0) > 900:
            raise HTTPException(400, "That set-up expired. Sign in again to get a new code to scan.")
        sec = totp.unseal(d["s"])
        st = totp.verify(sec, body.totp)
        if not st:
            raise HTTPException(401, "That code didn't match. Check the time on your phone is set automatically, then try the newest code.")
        a.totp_secret, a.totp_step = totp.seal(sec), st
        log(db, a.email, "totp.enrolled")
        return True
    sec = totp.new_secret()
    raise HTTPException(428, {"enrolTotp": True, "secret": sec, "qr": totp.qr_svg(totp.uri(sec, a.email)), "uri": totp.uri(sec, a.email),
                              "enrol": sign({"t": "totp-enrol", "id": a.id, "s": totp.seal(sec), "at": now()})})


DEV_COOKIE = "dk_adev"


def _device_check(db: Session, a: Admin, body: "Login", request: Request, response: Response):
    """A device this admin hasn't used before must enter a code sent to them, unless it's their very first device
    or no way to send a code is set up (then it's let in, recorded and shown in Your devices)."""
    import hashlib
    import secrets
    from . import messaging
    from .auth import check_code, send_code
    from .models import AdminDevice
    raw = request.cookies.get(DEV_COOKIE) or ""
    key = hashlib.sha256(raw.encode()).hexdigest() if raw else ""
    known = db.scalar(select(AdminDevice).where(AdminDevice.admin_id == a.id, AdminDevice.key == key, AdminDevice.trusted == True)) if key else None  # noqa: E712
    ua = (request.headers.get("user-agent") or "")
    label = ("iPhone" if "iPhone" in ua else "Android" if "Android" in ua else "Mac" if "Mac OS" in ua else "Windows" if "Windows" in ua else "Device") + \
            (" · Chrome" if "Chrome" in ua and "Edg" not in ua else " · Safari" if "Safari" in ua and "Chrome" not in ua else " · Edge" if "Edg" in ua else " · Firefox" if "Firefox" in ua else "")
    if known:
        known.last = now()
        return known
    has_trusted = db.scalar(select(AdminDevice).where(AdminDevice.admin_id == a.id, AdminDevice.trusted == True))  # noqa: E712
    target, kind = (a.phone, "phone") if a.phone and messaging.sms_mode() in ("msg91", "twilio") else (a.email, "email")
    can_send = (messaging.email_ready() if kind == "email" else True) or messaging.demo()
    if has_trusted and can_send:
        if not body.code:
            out = send_code(request, db, target, kind, "step")
            db.commit()
            raise HTTPException(428, {"needCode": True, "sentTo": (target[:2] + "•••" + target[target.find("@"):]) if kind == "email" else target[:3] + " ••••• " + target[-3:], **({"demo": out.get("demo")} if out.get("demo") else {})})
        check_code(db, target, "step", body.code)
    raw = secrets.token_urlsafe(24)
    response.set_cookie(DEV_COOKIE, raw, httponly=True, samesite="strict", secure=request.url.scheme == "https", max_age=400 * 86400, path="/")
    d = AdminDevice(admin_id=a.id, key=hashlib.sha256(raw.encode()).hexdigest(), label=label[:80], trusted=True)
    db.add(d)
    if has_trusted:
        log(db, a.email, "admin.new_device" + ("" if can_send else ".unverified"), label)
    return d


def _remember_device(db: Session, a: Admin, request: Request, response: Response):
    import hashlib
    import secrets
    from .models import AdminDevice
    raw = request.cookies.get(DEV_COOKIE) or ""
    key = hashlib.sha256(raw.encode()).hexdigest() if raw else ""
    d = db.scalar(select(AdminDevice).where(AdminDevice.admin_id == a.id, AdminDevice.key == key)) if key else None
    if d:
        d.last = now()
        return d
    ua = request.headers.get("user-agent") or ""
    label = ("iPhone" if "iPhone" in ua else "Android" if "Android" in ua else "Mac" if "Mac OS" in ua else "Windows" if "Windows" in ua else "Device")
    raw = secrets.token_urlsafe(24)
    response.set_cookie(DEV_COOKIE, raw, httponly=True, samesite="strict", secure=request.url.scheme == "https", max_age=400 * 86400, path="/")
    d = AdminDevice(admin_id=a.id, key=hashlib.sha256(raw.encode()).hexdigest(), label=label, trusted=True)
    db.add(d)
    log(db, a.email, "admin.new_device", label)
    return d


@r.get("/devices")
def devices(request: Request, a: Admin = Depends(me), db: Session = Depends(get_db)):
    import hashlib
    from .models import AdminDevice
    raw = request.cookies.get(DEV_COOKIE) or ""
    mine = hashlib.sha256(raw.encode()).hexdigest() if raw else ""
    rows = db.scalars(select(AdminDevice).where(AdminDevice.admin_id == a.id).order_by(AdminDevice.last.desc())).all()
    return {"rows": [{"id": d.id, "label": d.label, "first": d.first, "last": d.last, "this": d.key == mine, "trusted": d.trusted} for d in rows]}


@r.post("/devices/{did}/forget")
def forget_device(did: int, a: Admin = Depends(me), db: Session = Depends(get_db)):
    from .models import AdminDevice
    d = db.get(AdminDevice, did)
    if not d or d.admin_id != a.id:
        raise HTTPException(404)
    db.delete(d)
    a.session_epoch = (a.session_epoch or 0) + 1      # every session ends; this device needs a code next time
    log(db, a.email, "admin.device.forget", d.label)
    return {"ok": True}


@r.post("/signout-everywhere")
def signout_everywhere(response: Response, a: Admin = Depends(me), db: Session = Depends(get_db)):
    a.session_epoch = (a.session_epoch or 0) + 1
    log(db, a.email, "admin.signout_everywhere")
    response.delete_cookie(COOKIE, path="/")
    return {"ok": True}


def _alert_owner(a: Admin) -> None:
    try:
        from . import messaging
        if messaging.email_ready():
            messaging.send_mail(a.email, "Urban Health admin: sign-in locked", "Your Urban Health admin account was locked after 5 wrong passwords in a row. If this wasn't you, reset your password now and check Team & audit.")
    except Exception as e:
        print("[admin] lock alert failed:", str(e)[:120], flush=True)


@r.post("/login")
def login(body: Login, request: Request, response: Response, db: Session = Depends(get_db)):
    from .auth import clear as rl_clear, fail as rl_fail, guard as rl_guard

    try:
        rl_guard(request, "admin-login", 8, 900)
    except HTTPException:
        raise HTTPException(429, "Too many wrong attempts from this network. Wait 15 minutes and try again.")
    ident = (body.email or "").strip().lower()
    if not ident or not body.password:
        raise HTTPException(400, "Enter your email or mobile number, and your password.")
    if len(body.password) > 128 or len(ident) > 160:
        raise HTTPException(400, "That is too long to be a sign-in.")
    a = None
    if "@" in ident:
        a = db.scalar(select(Admin).where(Admin.email == ident))
    else:
        from .auth import norm_id
        try:
            kind, ph = norm_id(ident)
        except HTTPException:
            raise HTTPException(400, "Enter a valid email address or a 10-digit mobile number.")
        a = db.scalar(select(Admin).where(Admin.phone == ph)) if kind == "phone" else None
    t = now()
    if a and (a.locked_until or 0) > t:
        mins = max(1, ((a.locked_until or 0) - t + 59) // 60)
        raise HTTPException(423, f"This admin account is locked after too many wrong passwords. Try again in {mins} min, or ask the owner to reset it.")
    if not a or not check_pw(body.password, a.pw_hash):
        rl_fail(request, "admin-login", 900)
        if a:
            a.fails = (a.fails or 0) + 1
            if a.fails >= 10:
                # across every network: 15 min, then 1 h, then 24 h
                a.locked_until = t + (900 if a.fails < 15 else 3600 if a.fails < 20 else 86400)
                log(db, a.email, "login.locked", f"{a.fails} wrong passwords in a row")
                _alert_owner(a)
            else:
                log(db, a.email, "login.fail", f"{a.fails} in a row")
            db.commit()
            if a.fails >= 10:
                raise HTTPException(423, "Too many wrong passwords. This admin account is locked for 15 minutes and you have been emailed.")
            left = 8 - a.fails
            raise HTTPException(401, "Wrong email, mobile number or password." + (f" {left} attempt{'s' if left != 1 else ''} left, then sign-in pauses for 15 minutes." if 0 < left <= 3 else ""))
        raise HTTPException(401, "Wrong email, mobile number or password.")
    a.fails, a.locked_until = 0, 0
    if _totp_step(db, a, body):
        body.code = body.code or "totp"   # the authenticator already proved it's them: no extra emailed code
        dev = _remember_device(db, a, request, response)
    else:
        dev = _device_check(db, a, body, request, response)
    rl_clear(request, "admin-login")
    a.last_login = now()
    log(db, a.email, "login")
    response.set_cookie(COOKIE, sign({"id": a.id, "e": a.email, "ep": int(a.session_epoch or 0)}), httponly=True, samesite="strict", secure=request.url.scheme == "https", max_age=12 * 3600, path="/")
    return {"ok": True, "email": a.email, "role": a.role, "phone": a.phone or ""}


@r.post("/logout")
def logout(response: Response):
    response.delete_cookie(COOKIE, path="/")
    return {"ok": True}


@r.get("/me")
def whoami(a: Admin = Depends(me)):
    return {"email": a.email, "role": a.role, "roleLabel": ROLE_LABEL.get(a.role, a.role), "phone": a.phone or "", "totp": bool(a.totp_secret)}


class PhoneIn(BaseModel):
    phone: str = ""
    password: str


@r.put("/me/phone")
def my_phone(body: PhoneIn, a: Admin = Depends(me), db: Session = Depends(get_db)):
    """Sign in with a mobile number too. Asks for the password again: whoever holds the number can sign in with it."""
    if not check_pw(body.password, a.pw_hash):
        raise HTTPException(403, "That password is not right.")
    ph = ""
    if body.phone.strip():
        from .auth import norm_id
        kind, ph = norm_id(body.phone)
        if kind != "phone":
            raise HTTPException(400, "Enter a mobile number")
        if db.scalar(select(Admin).where(Admin.phone == ph, Admin.id != a.id)):
            raise HTTPException(409, "Another admin already uses this mobile number.")
    a.phone = ph
    log(db, a.email, "admin.phone " + ("set" if ph else "removed"))
    return {"ok": True, "phone": ph}


class EmailIn(BaseModel):
    email: str
    password: str


@r.put("/me/email")
def my_email(body: EmailIn, a: Admin = Depends(me), db: Session = Depends(get_db)):
    """Move a sign-in email (e.g. off the previous domain). Asks for the password again."""
    import re as _re
    if not check_pw(body.password, a.pw_hash):
        raise HTTPException(403, "That password is not right.")
    em = body.email.strip().lower()
    if not _re.fullmatch(r"[^@\s]+@[^@\s]+\.[a-z]{2,}", em):
        raise HTTPException(400, "Enter a valid email.")
    if db.scalar(select(Admin).where(Admin.email == em, Admin.id != a.id)):
        raise HTTPException(409, "Another admin already uses this email.")
    old, a.email = a.email, em
    log(db, em, "admin.email", f"{old} → {em}")
    return {"ok": True, "email": em}


# ---- settings and client errors -------------------------------------------------------------------------------------
class ReviewerIn(BaseModel):
    name: str = ""
    qualification: str = ""
    registration: str = ""
    date: str = ""
    scope: str = ""


@r.get("/settings")
def settings_get(a: Admin = Depends(me), db: Session = Depends(get_db)):
    from .models import Setting
    rv = db.get(Setting, "reviewer")
    return {"reviewer": rv.value if rv else {}}


@r.post("/settings/reviewer")
def settings_reviewer(body: ReviewerIn, a: Admin = Depends(me), db: Session = Depends(get_db)):
    from .models import Setting
    val = {k: v.strip()[:120] for k, v in body.model_dump().items()}
    if not val["name"]:
        val = {}
    rv = db.get(Setting, "reviewer")
    if rv:
        rv.value = val
    else:
        db.add(Setting(key="reviewer", value=val))
    log(db, a.email, "reviewer", str(val)[:200])
    return {"reviewer": val}


@r.get("/client-errors")
def client_errors(a: Admin = Depends(me), db: Session = Depends(get_db)):
    from .models import ClientError
    rows = db.scalars(select(ClientError).order_by(ClientError.t.desc()).limit(100)).all()
    return [{"id": e.id, "t": e.t, "message": e.message, "stack": e.stack[:600], "page": e.page, "ua": e.ua, "version": e.version, "count": e.count} for e in rows]


@r.delete("/client-errors")
def client_errors_clear(a: Admin = Depends(me), db: Session = Depends(get_db)):
    from .models import ClientError
    n = db.query(ClientError).delete()
    return {"cleared": n}


# ---- dashboard ------------------------------------------------------------------------------------------------------
@r.post("/storage/test")
def storage_test(a: Admin = Depends(me), db: Session = Depends(get_db)):
    """Can documents actually be stored? Writes, reads back and deletes one tiny object with the live credentials."""
    import time as _t
    from . import storage
    t0 = _t.time()
    try:
        storage.put(db, "admin-selftest", "probe", b"ok", "image/png", "probe", "admin")
        db.flush()
        got = storage.get(db, "admin-selftest", "probe")
        storage.delete(db, "admin-selftest", "probe")
        if not got or got[1] != b"ok":
            return {"ok": False, "backend": storage.backend(), "error": "stored object did not read back"}
        return {"ok": True, "backend": storage.backend(), "ms": int((_t.time() - t0) * 1000)}
    except Exception as e:
        return {"ok": False, "backend": storage.backend(), "error": f"{type(e).__name__}: {str(e)[:300]}"}


@r.post("/ai/test")
def ai_test(a: Admin = Depends(me)):
    """Why is smart reading off? Calls the model once and returns the exact error (admins only)."""
    from . import ai as AI
    return AI.test_connection()


@r.get("/stats")
def stats(a: Admin = Depends(me), db: Session = Depends(get_db)):
    t = now()
    day, week, month = t - 86400, t - 7 * 86400, t - 30 * 86400
    cnt = lambda q: db.scalar(select(func.count()).select_from(q.subquery())) or 0  # noqa: E731
    orders = db.scalars(select(Order).where(Order.created > month)).all()
    rev = sum(o.total for o in orders if o.status != "cancelled")
    rated = [o.rating for o in orders if o.rating]
    subs = db.scalars(select(Subscription).where(Subscription.started > month)).all()
    byday = {}
    for o in orders:
        d = datetime.fromtimestamp(o.created).strftime("%d %b")
        byday[d] = byday.get(d, 0) + 1
    ai = db.scalars(select(AiJob).where(AiJob.t > month)).all()
    from .models import Appointment as _Ap, Payment as _Pay, PartnerApplication as _PA
    attention = {"payments": db.scalar(select(func.count(_Pay.id)).where(_Pay.status == "claimed")) or 0,
                 "applications": db.scalar(select(func.count(_PA.id)).where(_PA.status == "new")) or 0,
                 "doctors": db.scalar(select(func.count(PartnerUser.id)).where(PartnerUser.role == "doctor", PartnerUser.verified == False, PartnerUser.active == True)) or 0,  # noqa: E712
                 "stores": db.scalar(select(func.count(Store.id)).where(Store.verified == False, Store.active == True)) or 0,  # noqa: E712
                 "visits": db.scalar(select(func.count(_Ap.id)).where(_Ap.status == "requested", _Ap.created < t - 86400)) or 0,
                 "orders": db.scalar(select(func.count(Order.id)).where(Order.status == "placed", Order.created < t - 4 * 3600)) or 0}
    return {"attention": attention, 
        "households": {"total": cnt(select(Household.id)), "new7": cnt(select(Household.id).where(Household.created > week)), "active1": cnt(select(Household.id).where(Household.last_seen > day)),
                       "paid": cnt(select(Household.id).where(Household.plan != "free"))},
        "partners": {k: cnt(select(Store.id).where(Store.kind == k, Store.active == True)) for k in ("pharmacy", "lab", "hospital")},  # noqa: E712
        "pending": cnt(select(Store.id).where(Store.verified == False)),  # noqa: E712
        "orders": {"month": len(orders), "revenue": rev, "avgRating": round(sum(rated) / len(rated), 2) if rated else None, "open": cnt(select(Order.id).where(Order.status.in_(("placed", "checking", "packing", "out", "confirmed", "collected", "processing")))),
                   "byDay": sorted(byday.items(), key=lambda kv: datetime.strptime(kv[0] + " " + str(datetime.now().year), "%d %b %Y"))},
        "subscriptions": {"month": len(subs), "mrr": sum(s.amount if s.period == "month" else round(s.amount / 12) for s in subs if s.status == "active")},
        "ai": {"month": len(ai), "claude": sum(1 for j in ai if j.engine == "claude"), "local": sum(1 for j in ai if j.engine == "local"), "errors": sum(1 for j in ai if not j.ok),
               "avgMs": round(sum(j.ms for j in ai) / len(ai)) if ai else 0, **_ai_spend(ai, day)},
        "perf": _perf(db, week),
        "engine": ("ai:" + AI.provider_order()[0]) if AI.available() else "local",
        "aiLastError": AI_LAST_ERROR,
    }


def _ai_spend(jobs, day: int) -> dict:
    """Token totals and an estimated bill (list prices from env, so the dashboard never names a vendor or model)."""
    import os
    pin, pout = float(os.getenv("AI_USD_PER_MTOK_IN", "3")), float(os.getenv("AI_USD_PER_MTOK_OUT", "15"))
    fx = float(os.getenv("USD_INR", "84"))
    cost = lambda js: sum(j.tin for j in js) / 1e6 * pin + sum(j.tout for j in js) / 1e6 * pout  # noqa: E731
    today = [j for j in jobs if j.t > day]
    byh: dict[str, int] = {}
    for j in today:
        byh[j.household_id] = byh.get(j.household_id, 0) + j.tin + j.tout
    top = sorted(byh.items(), key=lambda kv: -kv[1])[:5]
    return {"tokensMonth": sum(j.tin + j.tout for j in jobs), "tokensToday": sum(j.tin + j.tout for j in today),
            "inrMonth": round(cost(jobs) * fx), "inrToday": round(cost(today) * fx), "topToday": [{"household": h, "tokens": n} for h, n in top],
            "dayCap": {k: v for k, v in __import__("api.routes", fromlist=["AI_DAY_TOKENS"]).AI_DAY_TOKENS.items()}}


def _perf(db: Session, since: int) -> dict:
    """Real-device speed over the last 7 days: medians and p90 for phones and desktops, separately."""
    from .models import PerfSample
    rows = db.scalars(select(PerfSample).where(PerfSample.t > since)).all()
    def pct(xs, q):
        xs = sorted(x for x in xs if x > 0)
        return xs[min(len(xs) - 1, int(len(xs) * q))] if xs else 0
    def block(rs):
        return {"n": len(rs), "ready50": pct([r.ready for r in rs], .5), "ready90": pct([r.ready for r in rs], .9), "lcp50": pct([r.lcp for r in rs], .5), "lcp90": pct([r.lcp for r in rs], .9),
                "ttfb50": pct([r.ttfb for r in rs], .5), "swHit": round(100 * sum(1 for r in rs if r.sw) / len(rs)) if rs else 0}
    return {"phone": block([r for r in rows if r.phone]), "desktop": block([r for r in rows if not r.phone])}


# ---- partners -------------------------------------------------------------------------------------------------------
class StoreIn(BaseModel):
    kind: str = "pharmacy"
    name: str
    brand: str = ""
    address: str = ""
    area: str = ""
    city: str = ""
    pin: str = ""
    lat: float
    lng: float
    phone: str = ""
    hours: str = "8 am – 10 pm"
    open_24h: bool = False
    licence: str = ""
    discount_pct: float = 0
    delivery: bool = True
    delivery_fee: int = 30
    free_above: int = 499
    eta_min: int = 60
    home_collection: bool = False
    collection_fee: int = 0
    verified: bool = False
    active: bool = True
    owner_email: str = ""
    notes: str = ""


def sj(s: Store):
    return {c.name: getattr(s, c.name) for c in Store.__table__.columns}


@r.get("/stores")
def admin_stores(kind: str = "", q: str = "", pending: int = 0, a: Admin = Depends(me), db: Session = Depends(get_db)):
    st = select(Store).where(Store.kind != "shop").order_by(Store.created.desc())   # our own shop is not a partner
    if kind:
        st = st.where(Store.kind == kind)
    if pending:
        st = st.where(Store.verified == False)  # noqa: E712
    rows = db.scalars(st).all()
    if q:
        ql = q.lower()
        rows = [s for s in rows if ql in (s.name + s.city + s.area + s.brand + s.owner_email).lower()]
    counts = dict(db.execute(select(Order.store_id, func.count(Order.id)).group_by(Order.store_id)).all())
    return {"stores": [{**sj(s), "orders": counts.get(s.id, 0), "items": len(s.items) if s.kind == "pharmacy" else len(s.tests)} for s in rows[:500]]}


@r.post("/stores")
def add_store(body: StoreIn, a: Admin = Depends(me), db: Session = Depends(get_db)):
    # going live is the checked onboarding step (photos, licence, bank, agreement), never a box ticked at creation
    s = Store(**{**body.model_dump(), "verified": False})
    db.add(s)
    db.flush()
    if s.kind == "pharmacy":  # start with the full catalogue at the store's discount; edit later
        for m in CATALOG:
            db.add(StoreItem(store_id=s.id, sku=m["id"], name=m["name"], mrp=m["mrp"], price=max(1, round(m["mrp"] * (1 - s.discount_pct / 100))), stock=20))
    elif s.kind == "lab":
        for code, (name, price, tat, fast) in TESTS.items():
            db.add(LabTest(store_id=s.id, code=code, name=name, price=max(50, round(price * (1 - s.discount_pct / 100) / 10) * 10), tat_hours=tat, fasting=fast))
    log(db, a.email, f"store.add {s.kind} {s.name}")
    return sj(s)


@r.put("/stores/{sid}")
def edit_store(sid: str, body: dict, a: Admin = Depends(me), db: Session = Depends(get_db)):
    s = db.get(Store, sid)
    if not s:
        raise HTTPException(404)
    allowed = {c.name for c in Store.__table__.columns} - {"id", "created", "verified"}   # going live is a checked step in onboarding
    for k, v in body.items():
        if k in allowed:
            setattr(s, k, v)
    log(db, a.email, f"store.edit {s.name}", str({k: v for k, v in body.items() if k in allowed})[:1000])
    return sj(s)


@r.delete("/stores/{sid}")
def del_store(sid: str, a: Admin = Depends(owner), db: Session = Depends(get_db)):
    s = db.get(Store, sid)
    if not s:
        raise HTTPException(404)
    s.active = False
    log(db, a.email, f"store.deactivate {s.name}")
    return {"ok": True}


@r.post("/stores/{sid}/purge")
def purge_store(sid: str, body: dict, a: Admin = Depends(owner), db: Session = Depends(get_db)):
    """Remove a partner for good: test partners, duplicates, shops that never started. Only a paused partner, only when
    the owner types its exact name, and never once real money moved through it (a confirmed family payment or a paid
    payout): those stay paused so the books still add up."""
    from sqlalchemy import delete as _del
    from .models import Appointment, BloodRequest, Message, Payment, Payout, QualityFlag, Token, TrackPing
    s = db.get(Store, sid)
    if not s:
        raise HTTPException(404)
    if s.active:
        raise HTTPException(409, "Pause this partner first, then delete it.")
    if (body.get("confirm") or "").strip() != s.name.strip():
        raise HTTPException(400, "Type the partner's name exactly to delete it.")
    oids = list(db.scalars(select(Order.id).where(Order.store_id == sid)))
    paid = db.scalar(select(func.count(Payment.id)).where(Payment.kind == "order", Payment.ref.in_(oids or [""]), Payment.status == "confirmed")) or 0
    paid += db.scalar(select(func.count(Payout.id)).where(Payout.store_id == sid)) or 0
    if paid:
        raise HTTPException(409, "Money has moved through this partner, so it stays paused for the accounts instead of being deleted.")
    if db.scalar(select(func.count(BloodRequest.id)).where(BloodRequest.store_id == sid)):
        raise HTTPException(409, "Families have blood requests at this partner, so it stays paused.")
    n = {"orders": len(oids)}
    if oids:
        db.execute(_del(TrackPing).where(TrackPing.order_id.in_(oids)))
        db.execute(_del(Payment).where(Payment.kind == "order", Payment.ref.in_(oids)))
    for M in (Order, Appointment, Message, QualityFlag, Token, Payout, StoreItem, LabTest, PartnerUser):
        db.execute(_del(M).where(M.store_id == sid))
    db.delete(s)
    log(db, a.email, f"store.purge {s.name}", str(n))
    return {"ok": True, **n}


# ---- partner users: who can sign in to /partner for a store ----------------------------------------------------------
class PartnerUserIn(BaseModel):
    email: str = ""
    name: str = ""
    phone: str = ""
    role: str = "staff"       # owner | staff | doctor | tech | pharmacist
    regNo: str = ""           # doctors only: medical council registration number
    specialty: str = ""


def pu_json(u: PartnerUser, db: Session | None = None) -> dict:
    flag = ""
    if db is not None and u.reg_doc:
        from .models import StoredFile
        f = db.get(StoredFile, ("pcred_" + u.store_id, u.reg_doc))
        flag = (f.name or "").split("possibly edited: ", 1)[1] if f and "possibly edited: " in (f.name or "") else ""
    return {"regEdited": flag, "id": u.id, "email": "" if (u.email or "").endswith(".invalid") else u.email, "name": u.name, "phone": u.phone, "role": u.role, "active": u.active,
            "lastLogin": u.last_login, "mustChange": u.must_change, "regNo": u.reg_no or "", "specialty": u.specialty or "", "verified": bool(u.verified),
            "regDoc": bool(u.reg_doc), "regExpiry": u.reg_expiry or "", "approvedBy": u.verify_by or "", "totp": bool(u.totp_secret),
            "invited": bool(u.invite_hash and not u.pw_hash)}


@r.get("/stores/{sid}/users")
def partner_users(sid: str, a: Admin = Depends(me), db: Session = Depends(get_db)):
    rows = db.scalars(select(PartnerUser).where(PartnerUser.store_id == sid).order_by(PartnerUser.created)).all()
    return {"users": [pu_json(u, db) for u in rows]}


@r.post("/stores/{sid}/users")
def partner_user_add(sid: str, body: PartnerUserIn, request: Request, a: Admin = Depends(me), db: Session = Depends(get_db)):
    """Adds a sign-in by sending a one-time set-up link (SMS or email). No password is ever made up, shown or emailed:
    the person chooses their own and sets up their authenticator app when they open the link."""
    from .partners2 import InviteIn, invite
    out = invite(sid, InviteIn(name=body.name, phone=body.phone, email=body.email, role=body.role, regNo=body.regNo), request, a, db)
    u = db.get(PartnerUser, out["id"])
    if u and body.specialty:
        u.specialty = body.specialty.strip()[:60]
    return {**out, **(pu_json(u) if u else {}), "setupLink": True}


class DoctorVerifyIn(BaseModel):
    verified: bool = True


def _cred_ok(u: PartnerUser) -> str:
    """Why this registration can't be approved yet, or '' when it can."""
    import time as _t
    if len((u.reg_no or "").strip()) < 4:
        return "Their registration number is missing."
    if not u.reg_doc:
        return "Their registration certificate hasn't been uploaded yet. They add it from the partner portal."
    if not u.reg_expiry:
        return "Add the date the registration is valid until."
    if u.reg_expiry < _t.strftime("%Y-%m-%d"):
        return "This registration has expired."
    return ""


@r.post("/stores/{sid}/users/{uid}/verify")
def partner_user_verify(sid: str, uid: str, body: DoctorVerifyIn, a: Admin = Depends(me), db: Session = Depends(get_db)):
    """Doctors and pharmacists are approved by two different admins (maker-checker) after checking the certificate
    against the NMC / State Medical or Pharmacy Council register. Either admin can withdraw approval alone."""
    u = db.get(PartnerUser, uid)
    if not u or u.store_id != sid or u.role not in ("doctor", "pharmacist"):
        raise HTTPException(404)
    if not body.verified:
        u.verified, u.verify_by = False, ""
        log(db, a.email, f"partner.{u.role}.unverify {uid}", u.name)
        return pu_json(u)
    why = _cred_ok(u)
    if why:
        raise HTTPException(400, why)
    if not u.verify_by:
        u.verify_by = a.email
        log(db, a.email, f"partner.{u.role}.approve1 {uid}", u.name)
    elif u.verify_by == a.email:
        raise HTTPException(409, "You've already approved this. A second admin needs to check and approve it.")
    else:
        u.verified = True
        log(db, a.email, f"partner.{u.role}.approve2 {uid}", f"{u.name} · first: {u.verify_by}")
    return pu_json(u)


class CredIn(BaseModel):
    regExpiry: str = ""


@r.put("/stores/{sid}/users/{uid}/credential")
def partner_user_cred(sid: str, uid: str, body: CredIn, a: Admin = Depends(me), db: Session = Depends(get_db)):
    import re as _r
    u = db.get(PartnerUser, uid)
    if not u or u.store_id != sid:
        raise HTTPException(404)
    if body.regExpiry and not _r.fullmatch(r"20\d\d-\d\d-\d\d", body.regExpiry):
        raise HTTPException(400, "Use a date like 2028-03-31.")
    u.reg_expiry, u.verified, u.verify_by = body.regExpiry, False, ""   # a changed date needs checking again
    log(db, a.email, f"partner.credential {uid}", body.regExpiry)
    return pu_json(u)


@r.get("/stores/{sid}/users/{uid}/certificate")
def partner_user_cert(sid: str, uid: str, a: Admin = Depends(me), db: Session = Depends(get_db)):
    from fastapi.responses import Response as Raw
    from . import storage
    u = db.get(PartnerUser, uid)
    if not u or u.store_id != sid or not u.reg_doc:
        raise HTTPException(404)
    got = storage.get(db, "pcred_" + u.store_id, u.reg_doc)
    if not got:
        raise HTTPException(404)
    row, data = got
    mime = row.mime
    log(db, a.email, f"partner.certificate.view {uid}")
    db.commit()
    return Raw(data, media_type=mime, headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff",
                                               "Content-Security-Policy": "sandbox; default-src 'none'; img-src 'self' data:; object-src 'self'"})


@r.post("/stores/{sid}/users/{uid}/reset")
def partner_user_reset(sid: str, uid: str, request: Request, a: Admin = Depends(me), db: Session = Depends(get_db)):
    """Sends a fresh set-up link and signs them out everywhere; no temporary password."""
    from .partners2 import SigninAct, signin_action
    u = db.get(PartnerUser, uid)
    if not u or u.store_id != sid:
        raise HTTPException(404)
    return signin_action(uid, SigninAct(action="reset"), request, a, db)


@r.delete("/stores/{sid}/users/{uid}")
def partner_user_off(sid: str, uid: str, a: Admin = Depends(me), db: Session = Depends(get_db)):
    u = db.get(PartnerUser, uid)
    if not u or u.store_id != sid:
        raise HTTPException(404)
    u.active = False
    log(db, a.email, f"partner.user.disable {uid}")
    return {"ok": True}


@r.get("/stores/{sid}/prices")
def prices(sid: str, a: Admin = Depends(me), db: Session = Depends(get_db)):
    s = db.get(Store, sid)
    if not s:
        raise HTTPException(404)
    if s.kind == "lab":
        return {"kind": "lab", "rows": [{"id": t.id, "code": t.code, "name": t.name, "price": t.price, "tat_hours": t.tat_hours, "fasting": t.fasting} for t in sorted(s.tests, key=lambda t: t.name)]}
    return {"kind": "pharmacy", "rows": [{"id": i.id, "sku": i.sku, "name": i.name, "mrp": i.mrp, "price": i.price, "stock": i.stock} for i in sorted(s.items, key=lambda i: i.name)]}


@r.put("/stores/{sid}/prices")
def set_prices(sid: str, body: dict, a: Admin = Depends(me), db: Session = Depends(get_db)):
    """body.rows: [{id, price, stock|tat_hours}] ; body.add: [{sku|code, name, price, ...}] ; body.remove: [ids]"""
    s = db.get(Store, sid)
    if not s:
        raise HTTPException(404)
    M = LabTest if s.kind == "lab" else StoreItem
    for row in body.get("rows", []):
        o = db.get(M, row.get("id"))
        if not o or o.store_id != s.id:
            continue
        for k in ("price", "stock", "tat_hours", "fasting", "name", "mrp"):
            if k in row and hasattr(o, k):
                setattr(o, k, row[k])
    for row in body.get("add", []):
        if s.kind == "lab":
            db.add(LabTest(store_id=s.id, code=row.get("code", "custom")[:40], name=row.get("name", "")[:120], price=int(row.get("price", 0)), tat_hours=int(row.get("tat_hours", 24)), fasting=bool(row.get("fasting"))))
        else:
            db.add(StoreItem(store_id=s.id, sku=row.get("sku", "custom")[:40], name=row.get("name", "")[:120], mrp=int(row.get("mrp", row.get("price", 0))), price=int(row.get("price", 0)), stock=int(row.get("stock", 20))))
    for rid in body.get("remove", []):
        o = db.get(M, rid)
        if o and o.store_id == s.id:
            db.delete(o)
    log(db, a.email, f"prices.edit {s.name}", f"{len(body.get('rows', []))} rows, +{len(body.get('add', []))}, -{len(body.get('remove', []))}")
    return {"ok": True}


@r.post("/stores/import")
async def import_stores(file: UploadFile = File(...), a: Admin = Depends(owner), db: Session = Depends(get_db)):
    """CSV columns: kind,name,brand,address,area,city,pin,lat,lng,phone,hours,licence,discount_pct,delivery_fee,free_above,eta_min,home_collection,collection_fee,owner_email"""
    txt = (await file.read()).decode("utf-8", "ignore")
    n = 0
    for row in csv.DictReader(io.StringIO(txt)):
        try:
            body = StoreIn(**{k: (v if v != "" else StoreIn.model_fields[k].default) for k, v in row.items() if k in StoreIn.model_fields})
        except Exception:
            continue
        add_store(body, a, db)
        n += 1
    log(db, a.email, f"stores.import {n}")
    return {"imported": n}


# ---- orders ---------------------------------------------------------------------------------------------------------
@r.get("/orders")
def admin_orders(status: str = "", store: str = "", limit: int = 200, a: Admin = Depends(me), db: Session = Depends(get_db)):
    from .routes import order_json
    st = select(Order).order_by(Order.created.desc()).limit(limit)
    if status:
        st = st.where(Order.status == status)
    if store:
        st = st.where(Order.store_id == store)
    rows = db.scalars(st).all()
    return {"orders": [{**order_json(o), "household": o.household.name or o.household.key[:8] + "…", "householdId": o.household_id} for o in rows]}


class Advance(BaseModel):
    status: str


@r.post("/orders/{oid}/status")
def set_status(oid: str, body: Advance, a: Admin = Depends(me), db: Session = Depends(get_db)):
    from .routes import STEPS_LAB, STEPS_MED, order_json
    o = db.get(Order, oid)
    if not o:
        raise HTTPException(404)
    steps = STEPS_LAB if o.kind == "lab" else STEPS_MED
    if body.status != "cancelled" and body.status not in [k for k, _ in steps]:
        raise HTTPException(400, "unknown status")
    o.status = body.status
    o.timeline = (o.timeline or []) + [{"s": body.status, "t": now(), "by": a.email}]
    log(db, a.email, f"order.status {oid} → {body.status}")
    return order_json(o)


# ---- households -----------------------------------------------------------------------------------------------------
@r.get("/households")
def households(q: str = "", page: int = 1, size: int = 50, a: Admin = Depends(me), db: Session = Depends(get_db)):
    from sqlalchemy import or_
    size, page = max(10, min(int(size or 50), 200)), max(1, int(page or 1))
    qry = select(Household)
    if q.strip():
        like = f"%{q.strip().lower()[:80]}%"
        qry = qry.where(or_(func.lower(Household.name).like(like), func.lower(Household.city).like(like), func.lower(Household.email).like(like), Household.phone.like(like)))
    total = db.scalar(select(func.count()).select_from(qry.subquery())) or 0
    rows = db.scalars(qry.order_by(Household.last_seen.desc()).offset((page - 1) * size).limit(size)).all()
    ids = [h.id for h in rows]
    oc = dict(db.execute(select(Order.household_id, func.count(Order.id)).where(Order.household_id.in_(ids)).group_by(Order.household_id)).all()) if ids else {}
    ac = dict(db.execute(select(AiJob.household_id, func.count(AiJob.id)).where(AiJob.household_id.in_(ids)).group_by(AiJob.household_id)).all()) if ids else {}
    log(db, a.email, "view.households", f"q={q[:60]} page={page} n={len(rows)}")
    return {"total": total, "page": page, "size": size, "pages": max(1, -(-total // size)),
            "households": [{"id": h.id, "key": h.key[:6] + "…", "name": h.name, "city": h.city, "plan": h.plan, "planUntil": h.plan_until, "members": h.members, "blocked": h.blocked,
                            "created": h.created, "lastSeen": h.last_seen, "orders": oc.get(h.id, 0), "ai": ac.get(h.id, 0), "phone": h.phone, "email": h.email, "notes": h.notes} for h in rows]}


@r.get("/households/{hid}/history")
def household_history(hid: str, a: Admin = Depends(me), db: Session = Depends(get_db)):
    """Previous versions of the family's record (contents stay encrypted; only sizes, times and who saved are shown)."""
    cur = db.get(HouseholdState, hid)
    rows = db.scalars(select(HouseholdStateHistory).where(HouseholdStateHistory.household_id == hid).order_by(HouseholdStateHistory.version.desc()).limit(60)).all()
    return {"current": {"version": cur.version, "size": cur.size, "updatedBy": cur.updated_by} if cur else None,
            "history": [{"id": x.id, "version": x.version, "size": x.size, "t": x.t, "updatedBy": x.updated_by, "sections": len(x.sect or {})} for x in rows]}


@r.post("/households/{hid}/restore/{hist_id}")
def household_restore(hid: str, hist_id: int, a: Admin = Depends(me), db: Session = Depends(get_db)):
    """Put an earlier version back as the live record. The replaced one is itself kept in history, so a restore can be undone."""
    x = db.get(HouseholdStateHistory, hist_id)
    cur = db.get(HouseholdState, hid)
    if not x or x.household_id != hid or not cur:
        raise HTTPException(404)
    db.add(HouseholdStateHistory(household_id=hid, version=cur.version, blob=cur.blob, sect=cur.sect or {}, size=cur.size, updated_by=cur.updated_by or ""))
    cur.version, cur.blob, cur.sect, cur.size, cur.updated_by = cur.version + 1, x.blob, x.sect or {}, x.size, "restore:" + a.email
    log(db, a.email, f"household.restore {hid}", f"from version {x.version}")
    return {"ok": True, "version": cur.version}


@r.put("/households/{hid}")
def edit_household(hid: str, body: dict, a: Admin = Depends(me), db: Session = Depends(get_db)):
    h = db.get(Household, hid)
    if not h:
        raise HTTPException(404)
    for k in ("plan", "plan_until", "blocked", "notes", "name"):
        if k in body:
            setattr(h, k, body[k])
    if "plan" in body:
        db.add(Subscription(household_id=h.id, plan=h.plan, period="admin", amount=0, status="active", provider="admin", renews=h.plan_until, invoice_no=""))
    log(db, a.email, f"household.edit {hid}", str(body)[:500])
    return {"ok": True}


# ---- plans & billing ------------------------------------------------------------------------------------------------
@r.get("/plans")
def admin_plans(a: Admin = Depends(me), db: Session = Depends(get_db)):
    rows = db.scalars(select(Plan).order_by(Plan.sort)).all()
    subs = db.scalars(select(Subscription).order_by(Subscription.started.desc()).limit(300)).all()
    names = {h.id: (h.name or h.key[:8] + "…") for h in db.scalars(select(Household).where(Household.id.in_({s.household_id for s in subs}))).all()} if subs else {}
    return {"plans": [{c.name: getattr(p, c.name) for c in Plan.__table__.columns} for p in rows],
            "subscriptions": [{"id": s.id, "household": names.get(s.household_id, "?"), "plan": s.plan, "period": s.period, "amount": s.amount, "status": s.status, "provider": s.provider,
                               "ref": s.provider_ref, "started": s.started, "renews": s.renews, "invoice": s.invoice_no} for s in subs],
            "provider": "razorpay" if __import__("os").getenv("RAZORPAY_KEY_ID") else "demo"}


@r.put("/plans/{code}")
def edit_plan(code: str, body: dict, a: Admin = Depends(owner), db: Session = Depends(get_db)):
    p = db.get(Plan, code)
    if not p:
        p = Plan(code=code[:24], name=body.get("name", code))
        db.add(p)
    for k in ("name", "price_month", "price_year", "members", "features", "active", "sort"):
        if k in body:
            setattr(p, k, body[k])
    log(db, a.email, f"plan.edit {code}", str(body)[:500])
    return {"ok": True}


# ---- content: seasonal + videos -------------------------------------------------------------------------------------
@r.get("/seasonal")
def admin_seasonal(a: Admin = Depends(me), db: Session = Depends(get_db)):
    return {"items": [{c.name: getattr(x, c.name) for c in Seasonal.__table__.columns} for x in db.scalars(select(Seasonal).order_by(Seasonal.disease)).all()]}


@r.post("/seasonal")
def save_seasonal(body: dict, a: Admin = Depends(me), db: Session = Depends(get_db)):
    x = db.get(Seasonal, body.get("id")) if body.get("id") else None
    if x is None:
        x = Seasonal(disease=body.get("disease", "New advisory"))
        db.add(x)
    for k in ("region", "months", "disease", "emoji", "risk", "summary", "symptoms", "prevention", "see_doctor", "source", "active"):
        if k in body:
            setattr(x, k, body[k])
    x.updated = now()
    db.flush()
    log(db, a.email, f"seasonal.save {x.disease}")
    return {"id": x.id}


@r.delete("/seasonal/{sid}")
def del_seasonal(sid: str, a: Admin = Depends(me), db: Session = Depends(get_db)):
    x = db.get(Seasonal, sid)
    if x:
        db.delete(x)
        log(db, a.email, f"seasonal.delete {x.disease}")
    return {"ok": True}


@r.get("/videos")
def admin_videos(a: Admin = Depends(me), db: Session = Depends(get_db)):
    return {"videos": [{c.name: getattr(v, c.name) for c in Video.__table__.columns} for v in db.scalars(select(Video).order_by(Video.sort)).all()]}


@r.post("/videos")
def save_video(body: dict, a: Admin = Depends(me), db: Session = Depends(get_db)):
    v = db.get(Video, body.get("id")) if body.get("id") else None
    yt = str(body.get("yt", "")).strip()
    if "youtube.com" in yt or "youtu.be" in yt:
        import re
        m = re.search(r"(?:v=|youtu\.be/|embed/)([A-Za-z0-9_-]{11})", yt)
        yt = m.group(1) if m else yt
    if v is None:
        v = Video(topic=body.get("topic", "other"), title=body.get("title", ""), channel=body.get("channel", ""), yt=yt)
        db.add(v)
    for k in ("topic", "title", "channel", "lang", "minutes", "source", "verified", "active", "sort"):
        if k in body:
            setattr(v, k, body[k])
    if yt:
        v.yt = yt[:16]
    db.flush()
    log(db, a.email, f"video.save {v.title}")
    return {"id": v.id}


@r.delete("/videos/{vid}")
def del_video(vid: str, a: Admin = Depends(me), db: Session = Depends(get_db)):
    v = db.get(Video, vid)
    if v:
        db.delete(v)
    return {"ok": True}


# ---- admins + audit -------------------------------------------------------------------------------------------------
def _strong(pw: str, email: str) -> None:
    from .passwords import check
    bad = check(pw or "", email=email)
    if bad:
        raise HTTPException(400, "Password: " + "; ".join(bad).lower() + ".")


class AdminIn(BaseModel):
    email: str
    password: str = ""
    role: str = "ops"
    phone: str | None = None


@r.get("/admins")
def admins(a: Admin = Depends(owner), db: Session = Depends(get_db)):
    return {"admins": [{"id": x.id, "email": x.email, "role": x.role, "phone": x.phone or "", "created": x.created, "lastLogin": x.last_login,
                        "totp": bool(x.totp_secret)} for x in db.scalars(select(Admin)).all()]}


@r.post("/admins/{aid}/reset-totp")
def reset_admin_totp(aid: int, a: Admin = Depends(owner), db: Session = Depends(get_db)):
    """A lost phone: clear their authenticator and sign them out; they set it up again at their next sign-in."""
    x = db.get(Admin, aid)
    if not x:
        raise HTTPException(404)
    x.totp_secret, x.totp_step, x.session_epoch = "", 0, (x.session_epoch or 0) + 1
    log(db, a.email, f"admin.totp_reset {x.email}")
    return {"ok": True}


@r.post("/admins")
def add_admin(body: AdminIn, a: Admin = Depends(owner), db: Session = Depends(get_db)):
    e = body.email.strip().lower()
    x = db.scalar(select(Admin).where(Admin.email == e))
    if x is None:
        _strong(body.password, e)
        x = Admin(email=e, pw_hash=hash_pw(body.password), role=body.role if body.role in ("owner", "ops", "content") else "ops")
        db.add(x)
    else:
        if body.password:
            _strong(body.password, e)
            x.pw_hash = hash_pw(body.password)
            x.fails, x.locked_until = 0, 0
        x.role = body.role if body.role in ("owner", "ops", "content") else x.role
    if body.phone is not None:
        ph = ""
        if body.phone.strip():
            from .auth import norm_id
            kind, ph = norm_id(body.phone)
            if kind != "phone":
                raise HTTPException(400, "Enter a mobile number")
            if db.scalar(select(Admin).where(Admin.phone == ph, Admin.email != e)):
                raise HTTPException(409, "Another admin already uses this mobile number.")
        x.phone = ph
    log(db, a.email, f"admin.save {e} {x.role}")
    return {"ok": True}


@r.delete("/admins/{aid}")
def del_admin(aid: int, a: Admin = Depends(owner), db: Session = Depends(get_db)):
    if aid == a.id:
        raise HTTPException(400, "cannot delete yourself")
    x = db.get(Admin, aid)
    if x:
        db.delete(x)
        log(db, a.email, f"admin.delete {x.email}")
    return {"ok": True}


@r.get("/audit")
def audit(limit: int = 200, a: Admin = Depends(me), db: Session = Depends(get_db)):
    return {"rows": [{"t": x.t, "who": x.who, "what": x.what, "detail": x.detail} for x in db.scalars(select(Audit).order_by(Audit.t.desc()).limit(limit)).all()]}


# ---- accounts (sign-in identities) -----------------------------------------------------------------------------------
@r.get("/users")
def users(q: str = "", page: int = 1, size: int = 50, a: Admin = Depends(me), db: Session = Depends(get_db)):
    """Searched and paged in the database, so it stays fast and complete at any number of accounts.
    Viewing people's contact details is itself recorded in the audit log."""
    from sqlalchemy import or_
    from .models import AuthSession, Passkey, User
    size, page = max(10, min(int(size or 50), 200)), max(1, int(page or 1))
    qry = select(User)
    if q.strip():
        like = f"%{q.strip().lower()[:80]}%"
        qry = qry.where(or_(func.lower(User.name).like(like), func.lower(User.email).like(like), User.phone.like(like)))
    total = db.scalar(select(func.count()).select_from(qry.subquery())) or 0
    rows = db.scalars(qry.order_by(User.created.desc()).offset((page - 1) * size).limit(size)).all()
    ids = [u.id for u in rows]
    pk = dict(db.execute(select(Passkey.user_id, func.count(Passkey.id)).where(Passkey.user_id.in_(ids)).group_by(Passkey.user_id)).all()) if ids else {}
    ss = dict(db.execute(select(AuthSession.user_id, func.count(AuthSession.id)).where(AuthSession.user_id.in_(ids), AuthSession.expires > now()).group_by(AuthSession.user_id)).all()) if ids else {}
    plans = {h.id: h.plan for h in db.scalars(select(Household).where(Household.id.in_({u.household_id for u in rows if u.household_id}))).all()} if rows else {}
    log(db, a.email, "view.users", f"q={q[:60]} page={page} n={len(rows)}")
    return {"total": total, "page": page, "size": size, "pages": max(1, -(-total // size)),
            "users": [{"id": u.id, "name": u.name, "email": u.email, "phone": u.phone, "emailVerified": u.email_verified, "phoneVerified": u.phone_verified,
                       "passkeys": pk.get(u.id, 0), "sessions": ss.get(u.id, 0), "twoStep": u.two_step, "hasPassword": bool(u.pw_hash),
                       "locked": bool(u.locked_until and u.locked_until > now()), "disabled": u.disabled, "plan": plans.get(u.household_id, "free"),
                       "created": u.created, "lastLogin": u.last_login} for u in rows]}


@r.post("/users/{uid}")
def user_action(uid: str, body: dict, a: Admin = Depends(me), db: Session = Depends(get_db)):
    from .models import AuthSession, User
    u = db.get(User, uid)
    if not u:
        raise HTTPException(404)
    act = body.get("action")
    if act == "unlock":
        u.locked_until, u.failed = None, 0
    elif act == "disable":
        u.disabled = True
        db.query(AuthSession).filter(AuthSession.user_id == u.id).delete()
    elif act == "enable":
        u.disabled = False
    elif act == "signout":
        db.query(AuthSession).filter(AuthSession.user_id == u.id).delete()
    else:
        raise HTTPException(400, "unknown action")
    log(db, a.email, f"user.{act} {u.email or u.phone}")
    return {"ok": True}

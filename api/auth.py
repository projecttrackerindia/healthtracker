"""Accounts: sign up, sign in with a passkey, a password (+ optional two-step code) or a one-time code; recovery; sessions.

Security model
* Sessions: random 256-bit token in an HttpOnly, SameSite=Lax cookie (Secure on HTTPS); only its SHA-256 is stored.
* CSRF: every state-changing call must carry the header `X-THT: 1` (a cross-site form cannot set it) and JSON.
* Passwords: policy in passwords.py, scrypt hashes, breach check, 5 failures → 15-minute lock.
* One-time codes: 6 digits, HMAC-hashed, 10-minute expiry, 5 attempts, 45 s resend gap, 6 per hour per address.
* Passkeys: WebAuthn (FIDO2) with discoverable credentials and user verification; the RP ID is the site's host name.
* Answers never reveal whether an address has an account, except at sign-up (to offer "sign in instead").
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import secrets
import time
from collections import defaultdict, deque

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from webauthn import (generate_authentication_options, generate_registration_options, options_to_json,
                      verify_authentication_response, verify_registration_response)
from webauthn.helpers import base64url_to_bytes, bytes_to_base64url
from webauthn.helpers.structs import (AuthenticatorSelectionCriteria, PublicKeyCredentialDescriptor, ResidentKeyRequirement,
                                      UserVerificationRequirement)

from . import messaging, passwords
from .db import get_db
from .models import AuthFlow, AuthSession, OtpCode, Passkey, User, now
from .security import SECRET

r = APIRouter(prefix="/api/v1/auth")
COOKIE = "tht_s"
SESSION_DAYS = 30
RP_NAME = "TheHealthTracker"

# ---------------------------------------------------------------------------------------------------------------------
_HITS: dict[str, deque] = defaultdict(deque)


def limit(request: Request, key: str, n: int, per: int):
    ip = (request.headers.get("x-forwarded-for", "").split(",")[0].strip() or (request.client.host if request.client else "?"))
    k = f"{key}:{ip}"
    q, t = _HITS[k], time.time()
    while q and q[0] < t - per:
        q.popleft()
    if len(q) >= n:
        raise HTTPException(429, "Too many attempts. Please wait a few minutes and try again.")
    q.append(t)
    return ip


def csrf(request: Request):
    if request.method in ("POST", "PUT", "DELETE", "PATCH") and request.headers.get("x-tht") != "1":
        raise HTTPException(403, "missing request header")


def norm_id(s: str) -> tuple[str, str]:
    """('email'|'phone', normalised) or raises."""
    s = (s or "").strip()
    if "@" in s:
        e = s.lower()
        if not re.fullmatch(r"[^@\s]{1,64}@[^@\s]+\.[a-z]{2,}", e):
            raise HTTPException(400, "Enter a valid email address")
        return "email", e
    d = re.sub(r"[\s()-]", "", s)
    if d.startswith("00"):
        d = "+" + d[2:]
    if re.fullmatch(r"[6-9]\d{9}", d):
        d = "+91" + d
    elif re.fullmatch(r"0[6-9]\d{9}", d):
        d = "+91" + d[1:]
    if not re.fullmatch(r"\+\d{10,15}", d):
        raise HTTPException(400, "Enter a valid email or mobile number")
    return "phone", d


def find_user(db: Session, ident: str) -> User | None:
    kind, v = norm_id(ident)
    return db.scalar(select(User).where((User.email if kind == "email" else User.phone) == v))


def rp(request: Request) -> tuple[str, str]:
    host = os.getenv("RP_ID") or (request.headers.get("x-forwarded-host") or request.headers.get("host") or "localhost").split(":")[0]
    if os.getenv("APP_ORIGIN"):  # comma-separated list allowed, e.g. https://thehealthtracker.com,https://www.thehealthtracker.com
        return host, [o.strip() for o in os.getenv("APP_ORIGIN").split(",") if o.strip()]
    origin = request.headers.get("origin") or ""
    if not origin:
        proto = request.headers.get("x-forwarded-proto", request.url.scheme)
        origin = f"{proto}://{request.headers.get('host', host)}"
    return host, origin


def code_hash(target: str, code: str) -> str:
    return hmac.new(SECRET.encode(), f"{target}|{code}".encode(), hashlib.sha256).hexdigest()


def tok_hash(t: str) -> str:
    return hashlib.sha256(t.encode()).hexdigest()


def secure(request: Request) -> bool:
    return request.headers.get("x-forwarded-proto", request.url.scheme) == "https"


# ---------------------------------------------------------------------------------------------------------------------
def current_user(request: Request, db: Session) -> User | None:
    t = request.cookies.get(COOKIE)
    if not t:
        return None
    s = db.get(AuthSession, tok_hash(t))
    if not s or s.expires < now():
        return None
    u = db.get(User, s.user_id)
    if not u or u.disabled:
        return None
    if now() - s.last_seen > 600:
        s.last_seen = now()
    return u


def need_user(request: Request, db: Session = Depends(get_db)) -> User:
    u = current_user(request, db)
    if not u:
        raise HTTPException(401, "Please sign in")
    return u


def start_session(request: Request, response: Response, db: Session, u: User, method: str) -> dict:
    t = secrets.token_urlsafe(32)
    db.add(AuthSession(id=tok_hash(t), user_id=u.id, expires=now() + SESSION_DAYS * 86400, method=method,
                       ua=request.headers.get("user-agent", "")[:200], ip=(request.client.host if request.client else "")[:64]))
    u.last_login, u.failed, u.locked_until = now(), 0, None
    response.set_cookie(COOKIE, t, max_age=SESSION_DAYS * 86400, httponly=True, secure=secure(request), samesite="lax", path="/")
    return me_json(u)


def me_json(u: User) -> dict:
    return {"user": {"id": u.id, "name": u.name, "email": u.email, "phone": u.phone, "emailVerified": u.email_verified, "phoneVerified": u.phone_verified,
                     "hasPassword": bool(u.pw_hash), "twoStep": u.two_step, "passkeys": len(u.passkeys), "created": u.created}}


def new_flow(db: Session, kind: str, minutes: int = 10, **kw) -> AuthFlow:
    db.query(AuthFlow).filter(AuthFlow.expires < now()).delete()
    f = AuthFlow(id=secrets.token_urlsafe(24), kind=kind, expires=now() + minutes * 60, **kw)
    db.add(f)
    return f


def get_flow(db: Session, fid: str, kind: str) -> AuthFlow:
    f = db.get(AuthFlow, fid or "")
    if not f or f.kind != kind or f.expires < now():
        raise HTTPException(400, "This step has expired. Please start again.")
    return f


def send_code(request: Request, db: Session, target: str, kind: str, purpose: str) -> dict:
    """Create and deliver a code. Returns {'demo': code} only when OTP_DEMO=1."""
    hour = db.scalar(select(func.count(OtpCode.id)).where(OtpCode.target == target, OtpCode.created > now() - 3600)) or 0
    last = db.scalar(select(func.max(OtpCode.created)).where(OtpCode.target == target)) or 0
    if now() - last < 45:
        raise HTTPException(429, f"Please wait {45 - (now() - last)} seconds before asking for another code.")
    if hour >= 6:
        raise HTTPException(429, "Too many codes requested for this address. Try again in an hour.")
    ready = messaging.email_ready() if kind == "email" else messaging.sms_ready()
    if not ready and not messaging.demo():
        raise HTTPException(503, ("Email" if kind == "email" else "SMS") + " codes are not set up on this server yet. Use a passkey or password.")
    code = f"{secrets.randbelow(10 ** 6):06d}"
    db.query(OtpCode).filter(OtpCode.target == target, OtpCode.purpose == purpose, OtpCode.used == False).update({"used": True})  # noqa: E712
    db.add(OtpCode(target=target, purpose=purpose, code_hash=code_hash(target, code), expires=now() + 600, ip=(request.client.host if request.client else "")[:64]))
    if ready:
        try:
            (messaging.send_email(target, code, purpose) if kind == "email" else messaging.send_sms(target, code))
        except Exception as e:
            print("[auth] delivery failed:", str(e)[:200], flush=True)
            if not messaging.demo():
                raise HTTPException(502, "We could not send the code right now. Please try again shortly.")
    return {"demo": code} if messaging.demo() else {}


def check_code(db: Session, target: str, purpose: str, code: str) -> bool:
    c = db.scalar(select(OtpCode).where(OtpCode.target == target, OtpCode.purpose == purpose, OtpCode.used == False).order_by(OtpCode.created.desc()))  # noqa: E712
    if not c or c.expires < now():
        raise HTTPException(400, "The code has expired. Ask for a new one.")
    if c.attempts >= 5:
        c.used = True
        db.commit()  # failed attempts must persist although the request ends in an error
        raise HTTPException(400, "Too many wrong codes. Ask for a new one.")
    c.attempts += 1
    if not hmac.compare_digest(c.code_hash, code_hash(target, re.sub(r"\D", "", code or ""))):
        left = 5 - c.attempts
        db.commit()
        raise HTTPException(400, f"That code is not right. {left} attempt{'s' if left != 1 else ''} left.")
    c.used = True
    return True


def masked(kind: str, v: str) -> str:
    if kind == "email":
        a, _, d = v.partition("@")
        return a[:2] + "•" * max(1, len(a) - 2) + "@" + d
    return v[:3] + " ••••• " + v[-3:]


# ---------------------------------------------------------------------------------------------------------------------
@r.get("/config")
def config(request: Request):
    host, origin = rp(request)
    return {"passkeys": True, "email": messaging.email_ready(), "sms": messaging.sms_ready(), "demo": messaging.demo(), "rpId": host,
            "policy": {"min": 12, "max": 128}}


@r.get("/me")
def me(request: Request, db: Session = Depends(get_db)):
    u = current_user(request, db)
    return me_json(u) if u else {"user": None}


class PwCheck(BaseModel):
    password: str
    name: str = ""
    email: str = ""
    phone: str = ""


@r.post("/password/check", dependencies=[Depends(csrf)])
def password_check(body: PwCheck, request: Request):
    limit(request, "pwcheck", 40, 60)
    issues = passwords.check(body.password, body.name, body.email, body.phone)
    n = passwords.pwned(body.password) if not issues else 0
    if n:
        issues.append(f"This password has appeared in {n:,} data breaches. Choose another.")
    return {"ok": not issues, "issues": issues, "breached": n}


# ---- sign up ---------------------------------------------------------------------------------------------------------
class Signup(BaseModel):
    name: str
    email: str = ""
    phone: str = ""
    password: str
    terms: bool = False


@r.post("/signup/start", dependencies=[Depends(csrf)])
def signup_start(body: Signup, request: Request, db: Session = Depends(get_db)):
    limit(request, "signup", 8, 600)
    name = re.sub(r"\s+", " ", body.name).strip()[:80]
    if len(name) < 2:
        raise HTTPException(400, "Please enter your name")
    if not body.terms:
        raise HTTPException(400, "Please accept the terms and privacy policy")
    email = norm_id(body.email)[1] if body.email.strip() else None
    phone = norm_id(body.phone)[1] if body.phone.strip() else None
    if email and "@" not in email or phone and "@" in phone:
        raise HTTPException(400, "Check the email and mobile fields")
    if not email and not phone:
        raise HTTPException(400, "Enter an email address or a mobile number")
    if email and db.scalar(select(User.id).where(User.email == email)) or phone and db.scalar(select(User.id).where(User.phone == phone)):
        raise HTTPException(409, "An account with this email or mobile already exists. Sign in instead.")
    issues = passwords.check(body.password, name, email or "", phone or "")
    n = passwords.pwned(body.password) if not issues else 0
    if n:
        issues.append(f"This password has appeared in {n:,} data breaches. Choose another.")
    if issues:
        raise HTTPException(400, issues[0])
    kind, target = ("email", email) if email and (messaging.email_ready() or messaging.demo() or not phone) else ("phone", phone)
    f = new_flow(db, "signup", 15, data={"name": name, "email": email, "phone": phone, "pw": passwords.hash_pw(body.password), "kind": kind, "target": target})
    out = send_code(request, db, target, kind, "signup")
    return {"flow": f.id, "sentTo": masked(kind, target), "channel": kind, **out}


class FlowCode(BaseModel):
    flow: str
    code: str


@r.post("/signup/verify", dependencies=[Depends(csrf)])
def signup_verify(body: FlowCode, request: Request, response: Response, db: Session = Depends(get_db)):
    limit(request, "verify", 20, 600)
    f = get_flow(db, body.flow, "signup")
    d = f.data
    check_code(db, d["target"], "signup", body.code)
    if d["email"] and db.scalar(select(User.id).where(User.email == d["email"])) or d["phone"] and db.scalar(select(User.id).where(User.phone == d["phone"])):
        raise HTTPException(409, "This account already exists. Sign in instead.")
    u = User(name=d["name"], email=d["email"], phone=d["phone"], pw_hash=d["pw"], pw_changed=now(),
             email_verified=d["kind"] == "email", phone_verified=d["kind"] == "phone")
    db.add(u)
    db.delete(f)
    db.flush()
    return start_session(request, response, db, u, "otp")


# ---- password sign-in (+ optional two-step) --------------------------------------------------------------------------
class PwLogin(BaseModel):
    id: str
    password: str


@r.post("/password/login", dependencies=[Depends(csrf)])
def password_login(body: PwLogin, request: Request, response: Response, db: Session = Depends(get_db)):
    limit(request, "pwlogin", 20, 600)
    u = find_user(db, body.id)
    bad = HTTPException(400, "Wrong email/mobile or password.")
    if not u or not u.pw_hash:
        passwords.verify_pw(body.password, "scrypt$15$8$1$AAAAAAAAAAAAAAAAAAAAAA==$AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=")  # equal timing
        raise bad
    if u.disabled:
        raise HTTPException(403, "This account is disabled. Contact support.")
    if u.locked_until and u.locked_until > now():
        raise HTTPException(429, f"Too many wrong passwords. Try again in {max(1, (u.locked_until - now()) // 60)} min, or sign in with a code or passkey.")
    if not passwords.verify_pw(body.password, u.pw_hash):
        u.failed += 1
        if u.failed >= 5:
            u.locked_until, u.failed = now() + 900, 0
        db.commit()
        raise bad
    if u.two_step:
        kind, target = ("email", u.email) if u.email else ("phone", u.phone)
        f = new_flow(db, "step", 10, user_id=u.id, data={"kind": kind, "target": target})
        out = send_code(request, db, target, kind, "step")
        return {"step": f.id, "sentTo": masked(kind, target), **out}
    return start_session(request, response, db, u, "password")


@r.post("/step/verify", dependencies=[Depends(csrf)])
def step_verify(body: FlowCode, request: Request, response: Response, db: Session = Depends(get_db)):
    limit(request, "verify", 20, 600)
    f = get_flow(db, body.flow, "step")
    check_code(db, f.data["target"], "step", body.code)
    u = db.get(User, f.user_id)
    db.delete(f)
    return start_session(request, response, db, u, "password+otp")


# ---- one-time code sign-in and password reset ------------------------------------------------------------------------
class OtpStart(BaseModel):
    id: str
    purpose: str = "signin"  # signin | reset


@r.post("/otp/start", dependencies=[Depends(csrf)])
def otp_start(body: OtpStart, request: Request, db: Session = Depends(get_db)):
    limit(request, "otp", 10, 600)
    kind, target = norm_id(body.id)
    purpose = "reset" if body.purpose == "reset" else "signin"
    u = find_user(db, body.id)
    f = new_flow(db, "otp", 10, user_id=u.id if u else "", data={"kind": kind, "target": target, "purpose": purpose})
    out = {}
    if u and not u.disabled:
        out = send_code(request, db, target, kind, purpose)
    elif not (messaging.email_ready() if kind == "email" else messaging.sms_ready()) and not messaging.demo():
        raise HTTPException(503, ("Email" if kind == "email" else "SMS") + " codes are not set up on this server yet. Use a passkey or password.")
    # same answer whether or not the account exists
    return {"flow": f.id, "sentTo": masked(kind, target), "channel": kind, **out}


@r.post("/otp/verify", dependencies=[Depends(csrf)])
def otp_verify(body: FlowCode, request: Request, response: Response, db: Session = Depends(get_db)):
    limit(request, "verify", 20, 600)
    f = get_flow(db, body.flow, "otp")
    if not f.user_id:
        raise HTTPException(400, "That code is not right. 4 attempts left.")
    d = f.data
    check_code(db, d["target"], d["purpose"], body.code)
    u = db.get(User, f.user_id)
    if d["kind"] == "email":
        u.email_verified = True
    else:
        u.phone_verified = True
    if d["purpose"] == "reset":
        f.kind, f.expires = "reset", now() + 600
        return {"reset": f.id}
    db.delete(f)
    return start_session(request, response, db, u, "otp")


class Reset(BaseModel):
    flow: str
    password: str


@r.post("/password/reset", dependencies=[Depends(csrf)])
def password_reset(body: Reset, request: Request, response: Response, db: Session = Depends(get_db)):
    f = get_flow(db, body.flow, "reset")
    u = db.get(User, f.user_id)
    issues = passwords.check(body.password, u.name, u.email or "", u.phone or "")
    n = passwords.pwned(body.password) if not issues else 0
    if n:
        issues.append(f"This password has appeared in {n:,} data breaches. Choose another.")
    if issues:
        raise HTTPException(400, issues[0])
    u.pw_hash, u.pw_changed = passwords.hash_pw(body.password), now()
    db.query(AuthSession).filter(AuthSession.user_id == u.id).delete()  # sign out everywhere else
    db.delete(f)
    return start_session(request, response, db, u, "otp")


# ---- passkeys --------------------------------------------------------------------------------------------------------
@r.post("/passkey/register/options", dependencies=[Depends(csrf)])
def pk_reg_options(request: Request, u: User = Depends(need_user), db: Session = Depends(get_db)):
    host, _ = rp(request)
    opts = generate_registration_options(
        rp_id=host, rp_name=RP_NAME, user_id=u.webauthn_id.encode(), user_name=u.email or u.phone or u.id, user_display_name=u.name or (u.email or u.phone),
        authenticator_selection=AuthenticatorSelectionCriteria(resident_key=ResidentKeyRequirement.REQUIRED, user_verification=UserVerificationRequirement.REQUIRED),
        exclude_credentials=[PublicKeyCredentialDescriptor(id=base64url_to_bytes(p.id)) for p in u.passkeys], timeout=120000)
    f = new_flow(db, "reg", 5, user_id=u.id, challenge=bytes_to_base64url(opts.challenge))
    return {"flow": f.id, "options": json.loads(options_to_json(opts))}


class PkVerify(BaseModel):
    flow: str
    credential: dict
    name: str = ""


def device_name(request: Request) -> str:
    ua = request.headers.get("user-agent", "")
    for k, n in (("iPhone", "iPhone"), ("iPad", "iPad"), ("Android", "Android phone"), ("Macintosh", "Mac"), ("Windows", "Windows PC"), ("Linux", "Linux")):
        if k in ua:
            return n
    return "This device"


@r.post("/passkey/register/verify", dependencies=[Depends(csrf)])
def pk_reg_verify(body: PkVerify, request: Request, u: User = Depends(need_user), db: Session = Depends(get_db)):
    host, origin = rp(request)
    f = get_flow(db, body.flow, "reg")
    if f.user_id != u.id:
        raise HTTPException(400, "This step has expired. Please start again.")
    try:
        v = verify_registration_response(credential=body.credential, expected_challenge=base64url_to_bytes(f.challenge), expected_rp_id=host,
                                         expected_origin=origin, require_user_verification=True)
    except Exception as e:
        raise HTTPException(400, "The passkey could not be verified: " + str(e)[:120])
    cid = bytes_to_base64url(v.credential_id)
    if db.get(Passkey, cid):
        raise HTTPException(409, "This passkey is already registered.")
    tr = (body.credential.get("response") or {}).get("transports") or []
    db.add(Passkey(id=cid, user_id=u.id, public_key=bytes_to_base64url(v.credential_public_key), sign_count=v.sign_count, transports=tr[:6],
                   name=(body.name or device_name(request))[:80], backed_up=bool(getattr(v, "credential_backed_up", False))))
    db.delete(f)
    db.flush()
    return {"ok": True, **me_json(u)}


class PkStart(BaseModel):
    id: str = ""


@r.post("/passkey/login/options", dependencies=[Depends(csrf)])
def pk_login_options(body: PkStart, request: Request, db: Session = Depends(get_db)):
    limit(request, "pklogin", 30, 600)
    host, _ = rp(request)
    allow = []
    if body.id.strip():
        try:
            u = find_user(db, body.id)
        except HTTPException:
            u = None
        if u:
            allow = [PublicKeyCredentialDescriptor(id=base64url_to_bytes(p.id)) for p in u.passkeys]
    opts = generate_authentication_options(rp_id=host, allow_credentials=allow, user_verification=UserVerificationRequirement.REQUIRED, timeout=120000)
    f = new_flow(db, "auth", 5, challenge=bytes_to_base64url(opts.challenge))
    return {"flow": f.id, "options": json.loads(options_to_json(opts))}


@r.post("/passkey/login/verify", dependencies=[Depends(csrf)])
def pk_login_verify(body: PkVerify, request: Request, response: Response, db: Session = Depends(get_db)):
    limit(request, "pklogin", 30, 600)
    host, origin = rp(request)
    f = get_flow(db, body.flow, "auth")
    pk = db.get(Passkey, body.credential.get("id") or body.credential.get("rawId") or "")
    if not pk:
        raise HTTPException(400, "This passkey is not registered here. It may have been removed; sign in another way.")
    try:
        v = verify_authentication_response(credential=body.credential, expected_challenge=base64url_to_bytes(f.challenge), expected_rp_id=host,
                                           expected_origin=origin, credential_public_key=base64url_to_bytes(pk.public_key),
                                           credential_current_sign_count=pk.sign_count, require_user_verification=True)
    except Exception as e:
        raise HTTPException(400, "The passkey could not be verified: " + str(e)[:120])
    pk.sign_count, pk.last_used = v.new_sign_count, now()
    u = pk.user
    if u.disabled:
        raise HTTPException(403, "This account is disabled. Contact support.")
    db.delete(f)
    return start_session(request, response, db, u, "passkey")


@r.get("/passkeys")
def pk_list(u: User = Depends(need_user)):
    return {"passkeys": [{"id": p.id, "name": p.name, "created": p.created, "lastUsed": p.last_used, "synced": p.backed_up} for p in u.passkeys]}


class Rename(BaseModel):
    name: str


@r.post("/passkeys/{pid}", dependencies=[Depends(csrf)])
def pk_rename(pid: str, body: Rename, u: User = Depends(need_user), db: Session = Depends(get_db)):
    p = db.get(Passkey, pid)
    if not p or p.user_id != u.id:
        raise HTTPException(404)
    p.name = body.name.strip()[:80] or p.name
    return {"ok": True}


@r.delete("/passkeys/{pid}", dependencies=[Depends(csrf)])
def pk_delete(pid: str, u: User = Depends(need_user), db: Session = Depends(get_db)):
    p = db.get(Passkey, pid)
    if not p or p.user_id != u.id:
        raise HTTPException(404)
    if len(u.passkeys) == 1 and not u.pw_hash:
        raise HTTPException(400, "This is your only way to sign in. Set a password first.")
    db.delete(p)
    return {"ok": True}


# ---- account settings ------------------------------------------------------------------------------------------------
class PwChange(BaseModel):
    current: str = ""
    new: str


@r.post("/password/change", dependencies=[Depends(csrf)])
def password_change(body: PwChange, request: Request, u: User = Depends(need_user), db: Session = Depends(get_db)):
    limit(request, "pwchange", 10, 600)
    if u.pw_hash and not passwords.verify_pw(body.current, u.pw_hash):
        raise HTTPException(400, "Your current password is not right.")
    issues = passwords.check(body.new, u.name, u.email or "", u.phone or "")
    n = passwords.pwned(body.new) if not issues else 0
    if n:
        issues.append(f"This password has appeared in {n:,} data breaches. Choose another.")
    if issues:
        raise HTTPException(400, issues[0])
    u.pw_hash, u.pw_changed = passwords.hash_pw(body.new), now()
    cur = tok_hash(request.cookies.get(COOKIE, ""))
    db.query(AuthSession).filter(AuthSession.user_id == u.id, AuthSession.id != cur).delete()
    return {"ok": True}


class Toggle(BaseModel):
    on: bool


@r.post("/two-step", dependencies=[Depends(csrf)])
def two_step(body: Toggle, u: User = Depends(need_user)):
    if body.on and not ((u.email and messaging.email_ready()) or (u.phone and messaging.sms_ready()) or messaging.demo()):
        raise HTTPException(400, "Codes cannot be sent from this server yet, so two-step sign-in cannot be switched on.")
    u.two_step = body.on
    return me_json(u)


@r.get("/sessions")
def sessions(request: Request, u: User = Depends(need_user), db: Session = Depends(get_db)):
    cur = tok_hash(request.cookies.get(COOKIE, ""))
    rows = db.scalars(select(AuthSession).where(AuthSession.user_id == u.id, AuthSession.expires > now()).order_by(AuthSession.last_seen.desc())).all()
    return {"sessions": [{"id": s.id[:12], "current": s.id == cur, "method": s.method, "ua": s.ua, "created": s.created, "lastSeen": s.last_seen} for s in rows]}


@r.post("/logout", dependencies=[Depends(csrf)])
def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    t = request.cookies.get(COOKIE)
    if t:
        db.query(AuthSession).filter(AuthSession.id == tok_hash(t)).delete()
    response.delete_cookie(COOKIE, path="/")
    return {"ok": True}


@r.post("/logout-all", dependencies=[Depends(csrf)])
def logout_all(response: Response, u: User = Depends(need_user), db: Session = Depends(get_db)):
    db.query(AuthSession).filter(AuthSession.user_id == u.id).delete()
    response.delete_cookie(COOKIE, path="/")
    return {"ok": True}


class Profile(BaseModel):
    name: str


@r.post("/profile", dependencies=[Depends(csrf)])
def profile(body: Profile, u: User = Depends(need_user)):
    n = re.sub(r"\s+", " ", body.name).strip()[:80]
    if len(n) >= 2:
        u.name = n
    return me_json(u)

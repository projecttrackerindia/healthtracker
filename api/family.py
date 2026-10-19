"""Family accounts: encrypted household sync and invitations.

* /api/v1/sync         GET returns the household's app state; PUT stores it with optimistic locking (409 returns the
                       current server copy with per-section timestamps so the client can merge and retry).
* /api/v1/family/...   invite a profile's owner to create their own account; join with the token.

The state is encrypted at rest with AES-GCM. Set DATA_KEY (64 hex characters) in production; without it a key is
derived from SECRET_KEY, which works but means one secret protects both sessions and data.
"""
from __future__ import annotations

import hashlib
import json
import os
import secrets
import zlib

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import messaging
from .auth import COOKIE, csrf, current_user, limit, need_user, norm_id  # noqa: F401
from .db import get_db
from .models import AuthSession, Household, HouseholdState, HouseholdStateHistory, Invite, User, now
from .security import SECRET

r = APIRouter(prefix="/api/v1")
if not os.getenv("DATA_KEY"):
    print("[family] WARNING: DATA_KEY is not set; family health data is encrypted with a key derived from SECRET_KEY. Set DATA_KEY before launch and never change it.", flush=True)
MAX_STATE = 3 * 1024 * 1024
INVITE_DAYS = 7


# ---- encryption ------------------------------------------------------------------------------------------------------
def _key() -> bytes:
    k = os.getenv("DATA_KEY", "").strip()
    if k:
        try:
            b = bytes.fromhex(k)
            if len(b) == 32:
                return b
        except ValueError:
            pass
        print("[family] DATA_KEY is not 64 hex characters; deriving a key from SECRET_KEY instead", flush=True)
    return _legacy_key()


def encrypt(obj: dict) -> bytes:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    raw = zlib.compress(json.dumps(obj, separators=(",", ":"), ensure_ascii=False).encode(), 6)
    nonce = secrets.token_bytes(12)
    return b"v1" + nonce + AESGCM(_key()).encrypt(nonce, raw, b"tht-state-v1")


def _legacy_key() -> bytes:
    return hashlib.sha256(("tht-data|" + SECRET).encode()).digest()


def keys() -> list[bytes]:
    """Current key first, then the SECRET_KEY-derived one (what was used before DATA_KEY was set) and DATA_KEY_PREV
    (for a planned rotation). Reads try each; writes always use the current key, so data re-encrypts as it is saved."""
    out = [_key()]
    prev = os.getenv("DATA_KEY_PREV", "").strip()
    if prev:
        try:
            b = bytes.fromhex(prev)
            if len(b) == 32:
                out.append(b)
        except ValueError:
            pass
    if _legacy_key() not in out:
        out.append(_legacy_key())
    return out


def open_with_keys(blob: bytes, nonce: bytes, aad: bytes) -> bytes:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    last = None
    for k in keys():
        try:
            return AESGCM(k).decrypt(nonce, blob, aad)
        except Exception as e:  # wrong key: try the next
            last = e
    raise last or ValueError("cannot decrypt")


def decrypt(blob: bytes) -> dict:
    if blob[:2] != b"v1":
        raise ValueError("unknown blob version")
    raw = open_with_keys(blob[14:], blob[2:14], b"tht-state-v1")
    return json.loads(zlib.decompress(raw).decode())


# ---- helpers ---------------------------------------------------------------------------------------------------------
def my_household(db: Session, u: User) -> Household:
    if not u.household_id:
        raise HTTPException(409, "Open the app once so your account gets a household.")
    h = db.get(Household, u.household_id)
    if not h:
        raise HTTPException(409, "Household not found.")
    return h


def state_json(st: HouseholdState | None) -> dict:
    if not st:
        return {"version": 0, "state": None, "sect": {}, "updated": None}
    try:
        state = decrypt(st.blob)
    except Exception as e:
        print("[family] cannot decrypt household state:", type(e).__name__, flush=True)
        raise HTTPException(500, "Stored data could not be read. The DATA_KEY may have changed.")
    return {"version": st.version, "state": state, "sect": st.sect or {}, "updated": st.updated}


# ---- sync ------------------------------------------------------------------------------------------------------------
@r.get("/sync")
def sync_get(db: Session = Depends(get_db), u: User = Depends(need_user)):
    h = my_household(db, u)
    st = db.get(HouseholdState, h.id)
    out = state_json(st)
    out["memberId"] = u.member_id
    return out


class SyncIn(BaseModel):
    base: int
    state: dict
    sect: dict = {}


# what each role may change. Roles are per sign-in (not per profile): the first account in a family is its admin.
ROLES = ("admin", "member", "caregiver")
CAREGIVER_LOCKED = ("members", "mid", "cards", "consent", "results", "vault", "meds", "preg", "cycle", "claims", "perm", "contacts", "care", "growth", "vax")
ROLE_LABEL = {"admin": "Family admin", "member": "Family member", "caregiver": "Caregiver"}


def role_of(db: Session, u: User) -> str:
    r = u.role if u.role in ROLES else "member"
    if r != "admin" and u.household_id:
        # a family with no admin yet (accounts created before roles existed): its first account is the admin
        first = db.scalar(select(User).where(User.household_id == u.household_id).order_by(User.created).limit(1))
        admins = db.scalar(select(User.id).where(User.household_id == u.household_id, User.role == "admin"))
        if not admins and first and first.id == u.id:
            u.role = r = "admin"
    return r


def _same(a, b) -> bool:
    return json.dumps(a, sort_keys=True, ensure_ascii=False) == json.dumps(b, sort_keys=True, ensure_ascii=False)


@r.put("/sync", dependencies=[Depends(csrf)])
def sync_put(body: SyncIn, request: Request, db: Session = Depends(get_db), u: User = Depends(need_user)):
    h = my_household(db, u)
    limit(request, f"sync:{h.id}", 240, 600)
    st = db.get(HouseholdState, h.id)
    cur = st.version if st else 0
    if body.base != cur:
        out = state_json(st)
        raise HTTPException(409, out)
    members = body.state.get("members")
    if not isinstance(members, list) or not members:
        raise HTTPException(400, "state must contain at least one member")
    if role_of(db, u) == "caregiver" and st:
        try:
            before = decrypt(st.blob)
        except Exception:
            before = {}
        changed = [k for k in CAREGIVER_LOCKED if not _same(before.get(k), body.state.get(k))]
        if changed:
            raise HTTPException(403, f"Caregivers can add readings, doses, visits and notes, but cannot change {', '.join(changed[:3])}. Ask the family admin.")
    blob = encrypt(body.state)
    if len(blob) > MAX_STATE:
        raise HTTPException(413, "Your family's data is too large to sync (3 MB). Remove old items or contact support.")
    sect = {k: int(v) for k, v in (body.sect or {}).items() if isinstance(v, (int, float))}
    if st:
        # never lose data: the version being replaced is kept for 30 days and can be restored by support
        db.add(HouseholdStateHistory(household_id=h.id, version=st.version, blob=st.blob, sect=st.sect or {}, size=st.size or len(st.blob), updated_by=st.updated_by or ""))
        db.query(HouseholdStateHistory).filter(HouseholdStateHistory.household_id == h.id, HouseholdStateHistory.t < now() - 30 * 86400).delete()
        st.version, st.blob, st.sect, st.size, st.updated_by = cur + 1, blob, sect, len(blob), u.id
    else:
        db.add(HouseholdState(household_id=h.id, version=1, blob=blob, sect=sect, size=len(blob), updated_by=u.id))
    h.members = max(1, min(30, len(members)))
    return {"version": cur + 1, "size": len(blob)}


@r.delete("/sync", dependencies=[Depends(csrf)])
def sync_delete(db: Session = Depends(get_db), u: User = Depends(need_user)):
    if role_of(db, u) != "admin":
        raise HTTPException(403, "Only the family admin can delete the family's data.")
    """Right to erasure: remove the family's stored data from the server (the person also deletes it on each device)."""
    h = my_household(db, u)
    st = db.get(HouseholdState, h.id)
    if st:
        db.delete(st)
    return {"deleted": bool(st)}


# ---- invitations -----------------------------------------------------------------------------------------------------
class InviteIn(BaseModel):
    member_id: str
    name: str = ""
    contact: str = ""
    role: str = "member"   # member | caregiver (admin is granted later from Family → Accounts)


def invite_json(i: Invite) -> dict:
    return {"token": i.token, "memberId": i.member_id, "name": i.name, "contact": i.contact, "created": i.created, "expires": i.expires, "role": getattr(i, "role", "member") or "member",
            "status": "joined" if i.used else ("expired" if i.expires < now() else "pending")}


def _origin(request: Request) -> str:
    o = (os.getenv("APP_ORIGIN") or "").split(",")[0].strip()
    if o:
        return o.rstrip("/")
    proto = request.headers.get("x-forwarded-proto", request.url.scheme)
    return f"{proto}://{request.headers.get('x-forwarded-host') or request.headers.get('host')}"


@r.post("/family/invite", dependencies=[Depends(csrf)])
def family_invite(body: InviteIn, request: Request, db: Session = Depends(get_db), u: User = Depends(need_user)):
    limit(request, "invite", 20, 3600)
    h = my_household(db, u)
    if u.member_id and body.member_id == u.member_id:
        raise HTTPException(400, "That is your own profile.")
    contact = body.contact.strip()
    kind = ""
    if contact:
        kind, contact = norm_id(contact)
        if db.scalar(select(User.id).where((User.email if kind == "email" else User.phone) == contact, User.household_id == h.id)):
            raise HTTPException(409, "This person already has an account in your family.")
    # one live invite per profile
    for old in db.scalars(select(Invite).where(Invite.household_id == h.id, Invite.member_id == body.member_id, Invite.used == None)).all():  # noqa: E711
        db.delete(old)
    if body.role == "caregiver" and role_of(db, u) != "admin":
        raise HTTPException(403, "Only the family admin can invite a caregiver.")
    inv = Invite(token=secrets.token_urlsafe(24), household_id=h.id, member_id=body.member_id[:32], name=body.name.strip()[:80], contact=contact[:160],
                 by_user=u.id, expires=now() + INVITE_DAYS * 86400, role="caregiver" if body.role == "caregiver" else "member")
    db.add(inv)
    link = f"{_origin(request)}/join/{inv.token}"
    sent = False
    if kind == "email" and messaging.email_ready():
        try:
            messaging.send_invite_email(contact, u.name or "A family member", inv.name, link)
            sent = True
        except Exception as e:
            print("[family] invite email failed:", str(e)[:200], flush=True)
    return {**invite_json(inv), "link": link, "sent": sent, "channel": kind}


@r.get("/family/invites")
def family_invites(db: Session = Depends(get_db), u: User = Depends(need_user)):
    h = my_household(db, u)
    rows = db.scalars(select(Invite).where(Invite.household_id == h.id)).all()
    members = db.scalars(select(User).where(User.household_id == h.id)).all()
    role_of(db, u)
    return {"invites": [invite_json(i) for i in rows], "myRole": u.role,
            "accounts": [{"id": m.id, "memberId": m.member_id, "name": m.name, "phone": m.phone, "email": m.email, "me": m.id == u.id, "role": m.role if m.role in ROLES else "member",
                          "roleLabel": ROLE_LABEL.get(m.role, "Family member"), "lastSeen": getattr(m, "last_login", None)} for m in members]}


class RoleIn(BaseModel):
    role: str


@r.post("/family/accounts/{uid}/role", dependencies=[Depends(csrf)])
def set_role(uid: str, body: RoleIn, db: Session = Depends(get_db), u: User = Depends(need_user)):
    """The family admin decides what each sign-in may change. There is always at least one admin."""
    h = my_household(db, u)
    if role_of(db, u) != "admin":
        raise HTTPException(403, "Only the family admin can change roles.")
    if body.role not in ROLES:
        raise HTTPException(400, "role must be admin, member or caregiver")
    t = db.get(User, uid)
    if not t or t.household_id != h.id:
        raise HTTPException(404)
    if t.id == u.id and body.role != "admin":
        others = db.scalar(select(User.id).where(User.household_id == h.id, User.role == "admin", User.id != u.id))
        if not others:
            raise HTTPException(400, "Make someone else the admin first.")
    t.role = body.role
    return {"id": t.id, "role": t.role}


@r.delete("/family/accounts/{uid}", dependencies=[Depends(csrf)])
def remove_account(uid: str, db: Session = Depends(get_db), u: User = Depends(need_user)):
    """Detach a sign-in from the family (a caregiver whose work is done, a lost phone). Their own account survives, empty."""
    h = my_household(db, u)
    if role_of(db, u) != "admin":
        raise HTTPException(403, "Only the family admin can remove a sign-in.")
    t = db.get(User, uid)
    if not t or t.household_id != h.id:
        raise HTTPException(404)
    if t.id == u.id:
        raise HTTPException(400, "You cannot remove yourself; make someone else admin and ask them.")
    t.household_id, t.member_id = None, None
    for s in db.scalars(select(AuthSession).where(AuthSession.user_id == t.id)).all():
        db.delete(s)
    return {"removed": True}


@r.get("/family/invite/{token}")
def invite_peek(token: str, db: Session = Depends(get_db)):
    """What the invited person sees before signing up: who invited them and for which profile. No health data."""
    inv = db.get(Invite, token)
    if not inv or inv.used or inv.expires < now():
        raise HTTPException(404, "This invitation is no longer valid. Ask your family member to send a new one.")
    by = db.get(User, inv.by_user)
    return {"name": inv.name, "by": (by.name if by else "") or "A family member", "expires": inv.expires}


class JoinIn(BaseModel):
    token: str


@r.post("/family/join", dependencies=[Depends(csrf)])
def family_join(body: JoinIn, db: Session = Depends(get_db), u: User = Depends(need_user)):
    inv = db.get(Invite, body.token)
    if not inv or inv.used or inv.expires < now():
        raise HTTPException(404, "This invitation is no longer valid. Ask your family member to send a new one.")
    if u.household_id and u.household_id != inv.household_id and db.get(HouseholdState, u.household_id):
        raise HTTPException(409, "This account already belongs to another family. Sign in with a different account to join this one.")
    u.household_id = inv.household_id
    u.member_id = inv.member_id
    u.role = "caregiver" if getattr(inv, "role", "") == "caregiver" else "member"
    inv.used, inv.used_by = now(), u.id
    h = db.get(Household, inv.household_id)
    return {"joined": True, "memberId": inv.member_id, "householdKey": h.key if h else None}


class ClaimIn(BaseModel):
    member_id: str


@r.post("/family/me", dependencies=[Depends(csrf)])
def family_me(body: ClaimIn, db: Session = Depends(get_db), u: User = Depends(need_user)):
    """The account owner says which profile is theirs (normally the 'You' profile)."""
    u.member_id = body.member_id[:32]
    return {"memberId": u.member_id}

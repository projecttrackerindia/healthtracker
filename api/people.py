"""Phase 0 API (/api/v2): one record per person, and the server decides who may read it.

Rules (each one is enforced here, never in the app):
* Every adult signs in with their own account and owns their own profile. Others in the household see only what the
  owner grants: Medical ID (default) < Summary (profile, reports) < Everything (also medicines and doses).
* Women's health (cycle, pregnancy, kick counts) has its own switch per person granted to. Without it the data is not
  returned at all, at any level.
* Dependents (children, elders without a phone) have no login. Their guardians read and write everything; other
  household members get Medical ID unless a guardian grants more.
* Everyone in the household can always see everyone's Medical ID (blood group, allergies, emergency contacts):
  that is what makes SOS and a stranger's help work.
* Each read of somebody else's data is written to the access log the owner can see.
* Leaving takes your records with you. An owner cannot leave while they are the only guardian of a dependent.
"""
from __future__ import annotations

import datetime as _dt
import os
import re
import secrets

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from . import messaging
from .auth import csrf, limit, need_user
from .db import get_db
from .family import decrypt, encrypt
import hashlib

from .models import (SearchToken, ProfileChange, AccessLog, Grant, Guardian, HealthRecord, Household, HouseholdInvite, Notice, NoticeMark, NoticePref, Person, User, new_id, now)

r = APIRouter(prefix="/api/v2", dependencies=[Depends(csrf)])

RANK = {"none": 0, "medid": 1, "summary": 2, "all": 3, "guardian": 4, "owner": 5}
# which level reads which kind of record; womens kinds also need the womens switch
KIND_LEVEL = {"contact": "medid", "report": "summary", "vital": "summary", "med": "all", "dose": "all",
              "preg": "summary", "kick": "summary", "cycle": "summary"}
WOMENS = {"preg", "kick", "cycle"}
RELATIONS = ("Wife", "Husband", "Father", "Mother", "Son", "Daughter", "Brother", "Sister", "Grandfather", "Grandmother",
             "Grandson", "Granddaughter", "Father-in-law", "Mother-in-law", "Son-in-law", "Daughter-in-law", "Brother-in-law",
             "Sister-in-law", "Uncle", "Aunt", "Nephew", "Niece", "Cousin", "Friend", "Caregiver", "Other")
_REL_ALIAS = {"spouse": "Wife", "wfie": "Wife", "wief": "Wife", "husbund": "Husband", "hubby": "Husband", "dad": "Father",
              "papa": "Father", "mom": "Mother", "mum": "Mother", "amma": "Mother", "nanna": "Father", "bro": "Brother", "sis": "Sister"}
ONE_ONLY = {"Wife", "Husband", "Father", "Mother"}
ID_KEYS = ("legalName", "dob", "phone")   # the Aadhaar name, birth date and mobile: once a week, with an emailed code
ID_WEEK, ID_FIX = 7 * 86400, 86400


def norm_relation(r: str) -> str:
    """'WIFE', 'wife ', 'Wfie' -> 'Wife'. Anything unknown -> 'Other' (never free text)."""
    k = re.sub(r"[^a-z-]", "", (r or "").lower())
    if not k:
        return ""
    for x in RELATIONS:
        if x.lower() == k:
            return x
    if k in _REL_ALIAS:
        return _REL_ALIAS[k]
    import difflib
    m = difflib.get_close_matches(k, [x.lower() for x in RELATIONS], n=1, cutoff=0.75)
    return next((x for x in RELATIONS if m and x.lower() == m[0]), "Other")


def norm_name(n: str) -> str:
    """Collapse spaces; fix ALL CAPS / all lower to Title Case. Mixed case the person typed is kept."""
    n = re.sub(r"\s+", " ", (n or "").strip())[:80]
    if n and (n.isupper() or n.islower()):
        n = " ".join(w[:1].upper() + w[1:].lower() for w in n.split(" "))
    return n


def norm_contact(c: str) -> tuple[str, str]:
    c = (c or "").strip()
    if "@" in c:
        c = c.lower()
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[a-z]{2,}", c):
            raise HTTPException(400, "Enter a valid email address")
        return "email", c
    d = re.sub(r"\D", "", c)
    if len(d) == 12 and d.startswith("91"):
        d = d[2:]
    elif len(d) == 11 and d.startswith("0"):
        d = d[1:]
    if not re.fullmatch(r"[6-9]\d{9}", d):
        raise HTTPException(400, "Enter a 10-digit mobile number")
    return "phone", "+91" + d


def _name_key(n: str) -> str:
    return re.sub(r"[^a-z]", "", (n or "").lower())


PROFILE_KEYS = ("dob", "sex", "blood", "height", "weight", "donated", "allergies", "conditions", "organDonor", "phone", "legalName", "abha")
COLORS = ["#0A84FF", "#30B0C7", "#BF5AF2", "#FF9F0A", "#34C759", "#FF375F", "#5E5CE6", "#A2845E"]
INVITE_DAYS = 7


# ---- access -------------------------------------------------------------------------------------------------------------
class Access:
    def __init__(self, level: str, womens: bool):
        self.level, self.womens = level, womens

    def can(self, level: str) -> bool:
        return RANK[self.level] >= RANK[level]

    def can_kind(self, kind: str) -> bool:
        if kind not in KIND_LEVEL:
            return False
        if kind in WOMENS and not self.womens:
            return False
        return self.can(KIND_LEVEL[kind])

    @property
    def writer(self) -> bool:
        return self.level in ("owner", "guardian")


def access(db: Session, u: User, p: Person) -> Access:
    if p.removed or not u.household_id or p.household_id != u.household_id:
        return Access("none", False)
    if p.owner_user == u.id:
        return Access("owner", True)
    if db.get(Guardian, (p.id, u.id)):
        return Access("guardian", True)
    g = db.get(Grant, (p.id, u.id))
    if g:
        return Access(g.level if g.level in ("medid", "summary", "all") else "medid", bool(g.womens))
    return Access("medid", False)


def person_or_404(db: Session, u: User, pid: str, need: str = "medid") -> tuple[Person, Access]:
    p = db.get(Person, pid)
    if not p:
        raise HTTPException(404, "Not found")
    a = access(db, u, p)
    if not a.can(need):
        # the same answer whether the person exists elsewhere or is simply private: no probing other families
        raise HTTPException(404 if a.level == "none" else 403, "Not found" if a.level == "none" else "Not shared with you")
    return p, a


def log(db: Session, p: Person, u: User, a: Access, what: str):
    if a.level != "owner":
        db.add(AccessLog(person_id=p.id, user_id=u.id, what=what[:60]))


def profile(p: Person) -> dict:
    try:
        return decrypt(p.blob) if p.blob else {}
    except Exception:
        return {}


def age(dob: str) -> int | None:
    try:
        d = _dt.date.fromisoformat(dob)
    except (TypeError, ValueError):
        return None
    t = _dt.date.today()
    return t.year - d.year - ((t.month, t.day) < (d.month, d.day))


def contacts(db: Session, pid: str) -> list[dict]:
    rows = db.scalars(select(HealthRecord).where(HealthRecord.person_id == pid, HealthRecord.kind == "contact").order_by(HealthRecord.created)).all()
    out = []
    for r_ in rows:
        d = decrypt(r_.blob)
        out.append({"id": r_.id, **d})
    out.sort(key=lambda c: c.get("order", 99))
    return out


def medical_id(db: Session, p: Person, a: Access) -> dict:
    pr = profile(p)
    mid = {"blood": pr.get("blood", ""), "age": age(pr.get("dob", "")), "sex": pr.get("sex", ""), "height": pr.get("height", ""),
           "weight": pr.get("weight", ""), "donated": pr.get("donated", ""), "allergies": pr.get("allergies", ""),
           "conditions": pr.get("conditions", ""), "organDonor": pr.get("organDonor", ""), "contacts": contacts(db, p.id)}
    # emergency responders need to know about a pregnancy; the household does not, unless she shares it
    preg = active_pregnancy(db, p.id)
    if preg and a.womens:
        mid["pregnancy"] = preg
    return mid


def active_pregnancy(db: Session, pid: str) -> dict | None:
    row = db.scalar(select(HealthRecord).where(HealthRecord.person_id == pid, HealthRecord.kind == "preg").order_by(HealthRecord.updated.desc()))
    if not row:
        return None
    d = decrypt(row.blob)
    if d.get("stage") != "pregnant":
        return {"id": row.id, **d}
    lmp = d.get("lmp")
    try:
        days = (_dt.date.today() - _dt.date.fromisoformat(lmp)).days
        d["week"] = max(1, min(42, days // 7))
        d["due"] = d.get("due") or (_dt.date.fromisoformat(lmp) + _dt.timedelta(days=280)).isoformat()
    except (TypeError, ValueError):
        pass
    return {"id": row.id, **d}


IN_LAW = {"Father": "Father-in-law", "Mother": "Mother-in-law", "Brother": "Brother-in-law", "Sister": "Sister-in-law",
          "Son-in-law": "Son-in-law", "Daughter-in-law": "Daughter-in-law"}


def rel_for(db: Session, u: User, iv: HouseholdInvite) -> str:
    """A relation as the viewer would say it: your wife's mother is your mother-in-law."""
    if iv.by_user == u.id or not iv.relation:
        return iv.relation
    spouse = db.scalar(select(HouseholdInvite.token).where(
        HouseholdInvite.relation.in_(("Wife", "Husband")),
        ((HouseholdInvite.by_user == u.id) & (HouseholdInvite.used_by == iv.by_user)) | ((HouseholdInvite.by_user == iv.by_user) & (HouseholdInvite.used_by == u.id))))
    if spouse and iv.relation in IN_LAW:
        return IN_LAW[iv.relation]
    return ""


def person_json(db: Session, u: User, p: Person, a: Access) -> dict:
    pr = profile(p)
    out = {"id": p.id, "name": p.name, "color": p.color, "self": p.owner_user == u.id,
           "dependent": p.owner_user is None, "access": a.level, "womens": a.womens,
           "sex": pr.get("sex", ""), "age": age(pr.get("dob", "")), "medicalId": medical_id(db, p, a)}
    if a.can("summary"):
        out["profile"] = {k: pr.get(k, "") for k in PROFILE_KEYS}
        out["profile"]["legalName"] = pr.get("legalName") or p.name
    if p.owner_user == u.id:
        out["idLock"] = id_lock(pr)
    if a.womens:
        out["pregnancy"] = active_pregnancy(db, p.id)
    if p.owner_user and p.owner_user != u.id:
        iv = db.scalar(select(HouseholdInvite).where(HouseholdInvite.used_by == p.owner_user, HouseholdInvite.household_id == p.household_id))
        if iv:
            out["relation"], out["relationOk"] = rel_for(db, u, iv), bool(iv.rel_ok)
    out["guardians"] = [g for g in db.scalars(select(Guardian.user_id).where(Guardian.person_id == p.id))] if p.owner_user is None else []
    return out


def ensure_household(db: Session, u: User) -> Household:
    h = db.get(Household, u.household_id) if u.household_id else None
    if not h:
        h = Household(key=secrets.token_hex(16), name=(u.name.split(" ")[0] + "'s family") if u.name else "Family")
        db.add(h)
        db.flush()
        u.household_id = h.id
        u.role = "admin"
    return h


def my_person(db: Session, u: User) -> Person | None:
    return db.scalar(select(Person).where(Person.owner_user == u.id, Person.removed.is_(None)))


def clean_profile(d: dict) -> dict:
    out = {}
    for k in PROFILE_KEYS:
        v = d.get(k, "")
        if isinstance(v, str):
            v = v.strip()[:120]
        out[k] = v
    if out.get("dob"):
        try:
            if _dt.date.fromisoformat(out["dob"]) > _dt.date.today():
                raise HTTPException(400, "Date of birth is in the future")
        except ValueError:
            raise HTTPException(400, "Date of birth must be YYYY-MM-DD")
    if out.get("blood") and out["blood"] not in ("A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-", "Unknown"):
        raise HTTPException(400, "Choose a blood group")
    if out.get("sex") and out["sex"] not in ("male", "female", "other"):
        raise HTTPException(400, "Choose male, female or other")
    if out.get("legalName"):
        out["legalName"] = norm_name(out["legalName"])
    if out.get("abha"):
        d = re.sub(r"\D", "", str(out["abha"]))
        if len(d) != 14:
            raise HTTPException(400, "Health ID (ABHA) number has 14 digits")
        out["abha"] = f"{d[:2]}-{d[2:6]}-{d[6:10]}-{d[10:]}"
    return out


def abha_hash(v: str) -> str:
    d = re.sub(r"\D", "", v or "")
    return hashlib.sha256(("uh-abha:" + d).encode()).hexdigest() if d else ""


def set_abha(db: Session, p: Person, v: str):
    h = abha_hash(v)
    if h and db.scalar(select(Person.id).where(Person.abha_hash == h, Person.id != p.id, Person.removed.is_(None))):
        raise HTTPException(409, "This Health ID (ABHA) is already linked to another profile on Urban Health. If it is yours, write to support@urbanhealth.in.")
    p.abha_hash = h


# ---- me ---------------------------------------------------------------------------------------------------------------
@r.get("/me")
def me(u: User = Depends(need_user), db: Session = Depends(get_db)):
    people = []
    if u.household_id:
        for p in db.scalars(select(Person).where(Person.household_id == u.household_id, Person.removed.is_(None)).order_by(Person.created)):
            a = access(db, u, p)
            people.append(person_json(db, u, p, a))
    mine = my_person(db, u)
    members = []
    if u.household_id:
        for m in db.scalars(select(User).where(User.household_id == u.household_id)):
            members.append({"id": m.id, "name": m.name, "role": m.role, "you": m.id == u.id})
    invites = []
    if u.household_id:
        for i in db.scalars(select(HouseholdInvite).where(HouseholdInvite.household_id == u.household_id, HouseholdInvite.used_by.is_(None),
                                                          HouseholdInvite.expires > now() - 30 * 86400).order_by(HouseholdInvite.created.desc())):
            invites.append(invite_view(i))
    h = db.get(Household, u.household_id) if u.household_id else None
    return {"user": {"id": u.id, "name": u.name, "email": u.email, "phone": u.phone, "role": u.role},
            "household": u.household_id, "hkey": h.key if h else None, "me": mine.id if mine else None, "people": people, "members": members,
            "invites": invites, "onboarded": bool(mine and contacts(db, mine.id))}


# ---- people -----------------------------------------------------------------------------------------------------------
class PersonIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    profile: dict = Field(default_factory=dict)
    dependent: bool = False
    same_ok: bool = False


@r.post("/people")
def create_person(body: PersonIn, request: Request, u: User = Depends(need_user), db: Session = Depends(get_db)):
    limit(request, "v2people", 30, 600)
    h = ensure_household(db, u)
    n = len(db.scalars(select(Person.id).where(Person.household_id == h.id)).all())
    body.name = norm_name(body.name)
    if not body.name:
        raise HTTPException(400, "Enter the full name")
    if body.dependent and not body.same_ok:
        k = _name_key(body.name)
        import difflib
        for q in db.scalars(select(Person).where(Person.household_id == h.id, Person.removed.is_(None))):
            r_ = difflib.SequenceMatcher(None, _name_key(q.name), k).ratio()
            same_dob = bool(body.profile.get("dob")) and profile(q).get("dob") == body.profile.get("dob")
            if _name_key(q.name) == k or r_ > 0.88 or (same_dob and (r_ > 0.6 or k[:5] == _name_key(q.name)[:5])):
                raise HTTPException(409, f"SAME:{q.id}:{q.name} is already in your family. Is this the same person?")
    if body.dependent:
        p = Person(household_id=h.id, owner_user=None, name=body.name.strip(), color=COLORS[n % len(COLORS)], blob=encrypt(clean_profile(body.profile)))
        db.add(p)
        db.flush()
        db.add(Guardian(person_id=p.id, user_id=u.id))
    else:
        if my_person(db, u):
            raise HTTPException(409, "You already have a profile")
        p = Person(household_id=h.id, owner_user=u.id, name=body.name.strip(), color=COLORS[n % len(COLORS)], blob=encrypt(clean_profile(body.profile)))
        db.add(p)
        db.flush()
    set_abha(db, p, profile(p).get("abha", ""))
    db.commit()
    return person_json(db, u, p, access(db, u, p))


@r.get("/people/{pid}")
def get_person(pid: str, u: User = Depends(need_user), db: Session = Depends(get_db)):
    p, a = person_or_404(db, u, pid)
    log(db, p, u, a, "profile" if a.can("summary") else "Medical ID")
    db.commit()
    return person_json(db, u, p, a)


class PersonEdit(BaseModel):
    name: str | None = None
    profile: dict | None = None
    code: str | None = None


def id_lock(pr: dict) -> dict:
    """When identity details (name, date of birth, mobile) may next change. One free correction within 24 hours."""
    last = int(pr.get("_idAt") or 0)
    fix = bool(last and now() - last < ID_FIX and not pr.get("_idFix"))
    return {"last": last, "next": last + ID_WEEK if last else 0, "locked": bool(last and now() < last + ID_WEEK and not fix), "fix": fix}


def _id_target(u: User) -> tuple[str, str]:
    return ("email", u.email) if u.email else ("phone", u.phone or "")


@r.post("/people/{pid}/idcode")
def id_code(pid: str, request: Request, u: User = Depends(need_user), db: Session = Depends(get_db)):
    from .auth import send_code
    p, a = person_or_404(db, u, pid)
    if p.owner_user != u.id:
        raise HTTPException(403, "Only they can change their own details")
    lk = id_lock(profile(p))
    if lk["locked"]:
        raise HTTPException(423, "Next change allowed " + _when(lk["next"]))
    kind, tgt = _id_target(u)
    if not tgt:
        raise HTTPException(400, "Add an email to your account first")
    out = send_code(request, db, tgt, kind, "idchange")
    db.commit()
    masked = re.sub(r"^(.{2}).*(@.*)$", r"\1•••\2", tgt) if kind == "email" else tgt[:3] + " •••• " + tgt[-3:]
    return {"ok": True, "to": masked, "kind": kind, **out}


def _when(t: int) -> str:
    d = _dt.datetime.fromtimestamp(t, _dt.timezone(_dt.timedelta(hours=5, minutes=30)))
    return d.strftime("%a %-d %b, %-I:%M %p")


@r.put("/people/{pid}")
def edit_person(pid: str, body: PersonEdit, request: Request, u: User = Depends(need_user), db: Session = Depends(get_db)):
    p, a = person_or_404(db, u, pid)
    if not a.writer:
        raise HTTPException(403, "Only they can change their profile")
    cur = profile(p)
    name = norm_name(body.name) if body.name is not None and body.name.strip() else p.name
    newp = clean_profile({**cur, **(body.profile or {})}) if body.profile is not None else {k: cur.get(k, "") for k in PROFILE_KEYS}
    if newp.get("phone"):
        newp["phone"] = norm_contact(newp["phone"])[1]
    cur.setdefault("legalName", p.name)
    if not newp.get("legalName"):
        newp["legalName"] = cur["legalName"]
    changed = [k for k in ID_KEYS if (newp.get(k) or "") != (cur.get(k) or "")]
    if p.owner_user == u.id and changed and (cur.get("_idAt") or any(cur.get(k) for k in ID_KEYS)):
        lk = id_lock(cur)
        if lk["locked"]:
            raise HTTPException(423, f"Name, date of birth and mobile can change once a week. Next change allowed {_when(lk['next'])}.")
        if not body.code:
            raise HTTPException(428, "Confirm with the code we send to your email")
        from .auth import check_code
        kind, tgt = _id_target(u)
        check_code(db, tgt, "idchange", body.code)
        if lk["fix"]:
            cur["_idFix"] = 1                       # the one correction; the weekly clock does not restart
        else:
            cur["_idAt"], cur["_idFix"] = now(), 0
        old_phone = cur.get("phone") or ""
        if "phone" in changed and old_phone:
            try:
                messaging.send_text_sms(old_phone, "Urban Health: the mobile number on your profile was changed. If this was not you, sign in and lock your account, or write to support@urbanhealth.in.")
            except Exception:
                pass
        from .auth import device_of
        db.add(ProfileChange(user_id=u.id, person_id=p.id, fields=",".join(changed), device=device_of(request)))
        _note(db, p.household_id, "safety", "Your details were changed", "Changed: " + ", ".join({"dob": "date of birth", "phone": "mobile", "legalName": "name as on Aadhaar"}.get(k, k) for k in changed) + ". Not you? Change your password now.", {"user": u.id}, to_user=u.id)
    if (newp.get("abha") or "") != (cur.get("abha") or ""):
        set_abha(db, p, newp.get("abha", ""))
    p.name = name
    cur.update(newp)
    p.blob = encrypt(cur)
    db.commit()
    return person_json(db, u, p, a)


# ---- sharing ----------------------------------------------------------------------------------------------------------
class GrantIn(BaseModel):
    user_id: str
    level: str = "medid"
    womens: bool = False


@r.get("/people/{pid}/sharing")
def get_sharing(pid: str, u: User = Depends(need_user), db: Session = Depends(get_db)):
    p, a = person_or_404(db, u, pid)
    if not a.writer:
        raise HTTPException(403, "Only they can see this")
    out = []
    for m in db.scalars(select(User).where(User.household_id == p.household_id, User.id != (p.owner_user or ""))):
        if db.get(Guardian, (p.id, m.id)):
            out.append({"userId": m.id, "name": m.name, "level": "guardian", "womens": True})
            continue
        g = db.get(Grant, (p.id, m.id))
        out.append({"userId": m.id, "name": m.name, "level": g.level if g else "medid", "womens": bool(g and g.womens)})
    return out


@r.put("/people/{pid}/sharing")
def set_sharing(pid: str, body: GrantIn, u: User = Depends(need_user), db: Session = Depends(get_db)):
    p, a = person_or_404(db, u, pid)
    if not a.writer:
        raise HTTPException(403, "Only they can change who sees their health")
    if body.level not in ("medid", "summary", "all"):
        raise HTTPException(400, "Choose Medical ID, Summary or Everything")
    other = db.get(User, body.user_id)
    if not other or other.household_id != p.household_id or other.id == p.owner_user:
        raise HTTPException(400, "Not in this household")
    g = db.get(Grant, (p.id, other.id)) or Grant(person_id=p.id, user_id=other.id)
    before = (g.level, g.womens) if g.updated else ("medid", False)
    g.level, g.womens = body.level, bool(body.womens)
    db.merge(g)
    if before != (g.level, g.womens):
        what = {"medid": "only the Medical ID", "summary": "the summary and reports", "all": "everything"}[g.level]
        _note(db, p.household_id, "sharing", f"{p.name} now shares {what} with you" + (", including women's health" if g.womens else ""),
              "", {"person": p.id}, to_user=other.id)
    db.commit()
    return {"ok": True}


@r.get("/people/{pid}/access-log")
def access_log(pid: str, u: User = Depends(need_user), db: Session = Depends(get_db)):
    p, a = person_or_404(db, u, pid)
    if not a.writer:
        raise HTTPException(403, "Only they can see this")
    names = {m.id: m.name for m in db.scalars(select(User).where(User.household_id == p.household_id))}
    rows = db.scalars(select(AccessLog).where(AccessLog.person_id == p.id).order_by(AccessLog.t.desc()).limit(50)).all()
    return [{"who": names.get(x.user_id, "Someone"), "what": x.what, "t": x.t} for x in rows]


# ---- records ----------------------------------------------------------------------------------------------------------
class RecordIn(BaseModel):
    kind: str
    data: dict = Field(default_factory=dict)
    day: str = ""


def rec_json(x: HealthRecord) -> dict:
    return {"id": x.id, "kind": x.kind, "day": x.day, "file": x.file_id, "created": x.created, "updated": x.updated, **decrypt(x.blob)}


def _check_record(kind: str, data: dict, day: str):
    if kind not in KIND_LEVEL:
        raise HTTPException(400, "Unknown kind")
    if day and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", day):
        raise HTTPException(400, "day must be YYYY-MM-DD")
    if len(repr(data)) > 20000:
        raise HTTPException(413, "Too large")
    if kind == "contact":
        if not str(data.get("name", "")).strip() or not re.fullmatch(r"\+?[0-9 ]{8,16}", str(data.get("phone", "")).strip()):
            raise HTTPException(400, "An emergency contact needs a name and a phone number")
    if kind == "med" and not str(data.get("name", "")).strip():
        raise HTTPException(400, "Medicine name is required")
    if kind == "preg" and data.get("stage") not in ("trying", "pregnant", "after"):
        raise HTTPException(400, "Choose a stage")


@r.get("/people/{pid}/records")
def list_records(pid: str, kind: str = "", since: str = "", u: User = Depends(need_user), db: Session = Depends(get_db)):
    p, a = person_or_404(db, u, pid)
    kinds = [k for k in (kind.split(",") if kind else KIND_LEVEL.keys()) if a.can_kind(k)]
    if kind and not kinds:
        raise HTTPException(403, "Not shared with you")
    q = select(HealthRecord).where(HealthRecord.person_id == p.id, HealthRecord.kind.in_(kinds))
    if since:
        q = q.where(HealthRecord.day >= since)
    rows = db.scalars(q.order_by(HealthRecord.created.desc()).limit(500)).all()
    if kinds and rows:
        log(db, p, u, a, "records: " + ",".join(sorted({x.kind for x in rows})))
        db.commit()
    return [rec_json(x) for x in rows]


@r.post("/people/{pid}/records")
def add_record(pid: str, body: RecordIn, request: Request, u: User = Depends(need_user), db: Session = Depends(get_db)):
    limit(request, "v2rec", 300, 600)
    p, a = person_or_404(db, u, pid)
    _check_record(body.kind, body.data, body.day)
    # a dose may be marked by anyone allowed to see medicines (a son ticking Amma's tablet); everything else by owner/guardian
    if not (a.writer or (body.kind == "dose" and a.can_kind("dose"))):
        raise HTTPException(403, "Only they can add this")
    if body.kind == "med":
        body.data["name"] = med_name(body.data.get("name", ""))
        k = med_key(body.data["name"])
        for m in db.scalars(select(HealthRecord).where(HealthRecord.person_id == p.id, HealthRecord.kind == "med")):
            d = decrypt(m.blob) or {}
            if d.get("active") is not False and med_key(d.get("name")) == k:
                raise HTTPException(409, f"{d.get('name')} is already in the medicines list. Edit it instead of adding it again.")
    x = HealthRecord(person_id=p.id, kind=body.kind, blob=encrypt(body.data), day=body.day, by_user=u.id)
    db.add(x)
    db.flush()
    index_record(db, x, body.data)
    db.commit()
    return rec_json(x)


# ---- search: a blind index (HMAC of word prefixes) so the server finds records without reading them ----------------
SEARCH_KINDS = ("report", "med", "vital", "contact")


def _skey() -> bytes:
    import hmac as _h
    from .security import SECRET
    k = os.getenv("DATA_KEY") or SECRET
    return _h.new(k.encode() if isinstance(k, str) else k, b"uh-search-v1", hashlib.sha256).digest()


def _tok(w: str) -> str:
    import hmac as _h
    return _h.new(_skey(), w.encode(), hashlib.sha256).hexdigest()[:24]


def _words(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]+", (text or "").lower()) if len(w) >= 2}


def _prefixes(words: set[str]) -> set[str]:
    out = set()
    for w in words:
        for n in range(2, min(len(w), 12) + 1):
            out.add(w[:n])
    return out


def index_record(db: Session, x: HealthRecord, d: dict | None = None):
    db.execute(delete(SearchToken).where(SearchToken.record_id == x.id))
    if x.kind not in SEARCH_KINDS:
        return
    d = d if d is not None else (decrypt(x.blob) or {})
    parts = [x.kind, "lab" if d.get("doc") == "report" else "", "prescription rx" if d.get("doc") == "prescription" else "",
             d.get("title"), d.get("doctor"), d.get("lab"), d.get("name"), d.get("summary", "")[:400], d.get("relation"), d.get("type")]
    parts += [f.get("test", "") for f in d.get("findings", []) or []]
    parts += [m.get("name", "") for m in d.get("medicines", []) or []]
    for t in _prefixes(_words(" ".join(str(v) for v in parts if v))):
        db.add(SearchToken(person_id=x.person_id, record_id=x.id, tok=_tok(t)))


def _ensure_index(db: Session, pid: str):
    if db.scalar(select(SearchToken.id).where(SearchToken.person_id == pid).limit(1)):
        return
    for x in db.scalars(select(HealthRecord).where(HealthRecord.person_id == pid, HealthRecord.kind.in_(SEARCH_KINDS))):
        index_record(db, x)
    db.commit()


@r.get("/search")
def search(q: str = "", page: int = 0, u: User = Depends(need_user), db: Session = Depends(get_db)):
    from sqlalchemy import func
    words = [w[:12] for w in _words(q)][:6]
    if not words or not u.household_id:
        return {"items": [], "more": False}
    people = {}
    for p in db.scalars(select(Person).where(Person.household_id == u.household_id, Person.removed.is_(None))):
        a = access(db, u, p)
        if a.can("summary"):
            people[p.id] = (p, a)
            _ensure_index(db, p.id)
    if not people:
        return {"items": [], "more": False}
    toks = [_tok(w) for w in words]
    hits = db.execute(select(SearchToken.record_id).where(SearchToken.person_id.in_(list(people)), SearchToken.tok.in_(toks))
                      .group_by(SearchToken.record_id).having(func.count(func.distinct(SearchToken.tok)) == len(set(toks)))).scalars().all()
    recs = [x for x in (db.get(HealthRecord, i) for i in hits) if x and people[x.person_id][1].can_kind(x.kind)]
    recs.sort(key=lambda x: (x.day or "", x.created), reverse=True)
    size = 20
    chunk = recs[page * size:(page + 1) * size]
    return {"items": [{**rec_json(x), "person": x.person_id, "personName": people[x.person_id][0].name} for x in chunk], "more": len(recs) > (page + 1) * size}


@r.put("/records/{rid}")
def edit_record(rid: str, body: RecordIn, u: User = Depends(need_user), db: Session = Depends(get_db)):
    x = db.get(HealthRecord, rid)
    if not x:
        raise HTTPException(404, "Not found")
    p, a = person_or_404(db, u, x.person_id)
    if not a.writer or body.kind != x.kind:
        raise HTTPException(403 if not a.writer else 400, "Only they can change this" if not a.writer else "Kind cannot change")
    _check_record(body.kind, body.data, body.day)
    x.blob, x.day = encrypt(body.data), body.day or x.day
    index_record(db, x, body.data)
    db.commit()
    return rec_json(x)


@r.delete("/records/{rid}")
def delete_record(rid: str, u: User = Depends(need_user), db: Session = Depends(get_db)):
    x = db.get(HealthRecord, rid)
    if not x:
        raise HTTPException(404, "Not found")
    p, a = person_or_404(db, u, x.person_id)
    if not (a.writer or (x.kind == "dose" and a.can_kind("dose") and x.by_user == u.id)):
        raise HTTPException(403, "Only they can delete this")
    if x.file_id:
        from . import storage
        try:
            storage.delete(db, p.id, x.file_id)
        except Exception:
            pass
    db.execute(delete(SearchToken).where(SearchToken.record_id == x.id))
    db.delete(x)
    db.commit()
    return {"ok": True}


# ---- reports: file to S3, read by AI, values stored ------------------------------------------------------------------
# ---- what a report can teach the profile, and how it compares with the last time -------------------------------------
def _norm_blood(v: str) -> str:
    m = re.search(r"(?i)\b(AB|A|B|O)\b\s*(?:rh\s*)?(\+|pos(?:itive)?|-|neg(?:ative)?|\u2212)", str(v or ""))
    return (m.group(1).upper() + ("+" if m.group(2)[0] in "+pP" else "-")) if m else ""


def _patient_from_text(reading: dict) -> dict:
    out = {}
    tests = {(f.get("test") or "").lower(): str(f.get("value") or "") for f in reading.get("findings") or []}
    abo = next((v for k, v in tests.items() if "abo" in k or "blood group" in k), "")
    rh = next((v for k, v in tests.items() if re.search(r"\brh\b", k)), "")
    if abo:
        b = _norm_blood(abo + " " + rh) or (abo.strip().upper()[:2] + ("+" if "pos" in rh.lower() else "-" if "neg" in rh.lower() else "") if re.fullmatch(r"(?i)\s*(ab|a|b|o)\s*", abo) else "")
        if b and b[-1] in "+-":
            out["blood_group"] = b
    return out


def suggestions(db: Session, p: Person, rec: dict, reading: dict) -> list[dict]:
    pr, pt, out = profile(p), rec.get("patient") or {}, []
    b = _norm_blood(pt.get("blood_group", ""))
    if b and b != pr.get("blood"):
        out.append({"key": "blood", "label": "Blood group", "old": pr.get("blood", ""), "new": b, "on": True})
    try:
        w = float(pt.get("weight_kg") or 0)
        if 2 < w < 300 and abs(w - float(pr.get("weight") or 0)) >= 1:
            out.append({"key": "weight", "label": "Weight", "old": pr.get("weight", ""), "new": f"{w:g}", "unit": "kg", "on": True})
        h = float(pt.get("height_cm") or 0)
        if 40 < h < 250 and abs(h - float(pr.get("height") or 0)) >= 2:
            out.append({"key": "height", "label": "Height", "old": pr.get("height", ""), "new": f"{h:g}", "unit": "cm", "on": True})
    except (TypeError, ValueError):
        pass
    dob = str(pt.get("dob") or "")
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", dob) and dob != pr.get("dob"):
        out.append({"key": "dob", "label": "Date of birth", "old": pr.get("dob", ""), "new": dob, "lock": True, "on": False})
    elif pt.get("age_years") and pr.get("dob"):
        try:
            if abs(int(pt["age_years"]) - (age(pr["dob"]) or 0)) >= 2:
                out.append({"key": "dob", "label": "Date of birth", "old": pr.get("dob", ""), "new": "", "note": f"Report says age {int(pt['age_years'])}", "lock": True, "on": False})
        except (TypeError, ValueError):
            pass
    mob = re.sub(r"\D", "", str(pt.get("mobile") or ""))[-10:]
    if re.fullmatch(r"[6-9]\d{9}", mob) and mob != re.sub(r"\D", "", pr.get("phone", ""))[-10:]:
        out.append({"key": "phone", "label": "Mobile", "old": pr.get("phone", ""), "new": "+91" + mob, "lock": True, "on": False, "note": "May be the number of whoever booked the test"})
    have = (pr.get("allergies") or "").lower()
    new_al = [a for a in reading.get("allergies_found") or [] if a and a.lower() not in have]
    if new_al:
        out.append({"key": "allergies", "label": "Allergies", "old": pr.get("allergies", ""), "new": ", ".join([x for x in [pr.get("allergies", "")] if x and x.lower() != "none"] + new_al), "on": True})
    havec = (pr.get("conditions") or "").lower()
    new_c = [c for c in reading.get("conditions_found") or [] if c and c.lower() not in havec]
    if new_c:
        out.append({"key": "conditions", "label": "Conditions", "old": pr.get("conditions", ""), "new": ", ".join([x for x in [pr.get("conditions", "")] if x and x.lower() != "none"] + new_c), "on": True})
    return out


BETTER_HIGH = ("hdl", "egfr", "hb", "alb", "vitd", "b12", "spo2", "ferr")


def _num(v):
    try:
        return float(str(v).replace(",", "").strip())
    except (TypeError, ValueError):
        return None


def compare_findings(db: Session, pid: str, findings: list, day: str) -> list[dict]:
    prev = {}
    for x in db.scalars(select(HealthRecord).where(HealthRecord.person_id == pid, HealthRecord.kind == "report").order_by(HealthRecord.day.desc())):
        if (x.day or "") > day[:10]:
            continue
        d = decrypt(x.blob) or {}
        for f in d.get("findings") or []:
            k = (f.get("code") or re.sub(r"[^a-z0-9]", "", (f.get("test") or "").lower()))
            if k and k not in prev:
                prev[k] = (f, x.day)
    out = []
    for f in findings or []:
        k = f.get("code") or re.sub(r"[^a-z0-9]", "", (f.get("test") or "").lower())
        if k not in prev:
            out.append({"test": f.get("test"), "now": f.get("value"), "unit": f.get("unit", ""), "dir": "first", "flag": f.get("flag", "")})
            continue
        pf, pday = prev[k]
        a, b = _num(pf.get("value")), _num(f.get("value"))
        if a is None or b is None or (pf.get("unit") or "").lower() != (f.get("unit") or "").lower() and pf.get("unit") and f.get("unit"):
            out.append({"test": f.get("test"), "prev": pf.get("value"), "prevDay": pday, "now": f.get("value"), "unit": f.get("unit", ""), "dir": "same" if str(pf.get("value")).lower() == str(f.get("value")).lower() else "changed", "flag": f.get("flag", "")})
            continue
        if abs(b - a) <= max(abs(a) * 0.02, 1e-9):
            d = "same"
        else:
            pfl, nfl = pf.get("flag") or "normal", f.get("flag") or "normal"
            if pfl != "normal" and nfl == "normal":
                d = "better"
            elif pfl == "normal" and nfl != "normal":
                d = "worse"
            elif nfl == "high" or (nfl == "normal" and k not in BETTER_HIGH and pfl == "high"):
                d = "better" if b < a else "worse"
            elif nfl == "low":
                d = "better" if b > a else "worse"
            else:
                d = ("better" if b > a else "worse") if k in BETTER_HIGH else "changed"
        out.append({"test": f.get("test"), "prev": pf.get("value"), "prevDay": pday, "now": f.get("value"), "unit": f.get("unit", ""), "dir": d, "flag": f.get("flag", "")})
    return out


def _compare_line(cmp: list) -> str:
    b = [c for c in cmp if c["dir"] == "better"]
    w = [c for c in cmp if c["dir"] == "worse"]
    if not b and not w:
        return ""
    parts = []
    if b:
        parts.append(f"{b[0]['test']} improved to {b[0]['now']} {b[0].get('unit') or ''}".strip() + (f" and {len(b) - 1} more" if len(b) > 1 else ""))
    if w:
        parts.append(f"{w[0]['test']} went the wrong way" + (f" with {len(w) - 1} more" if len(w) > 1 else "") + "; worth a word with your doctor")
    return ". ".join(parts) + "."


def other_person(db: Session, u: User, p: Person, pt: dict):
    """A report printed with someone else's name: which family member it probably belongs to."""
    import difflib
    n = _name_key(pt.get("name", ""))
    if len(n) < 3:
        return None
    mine = max(difflib.SequenceMatcher(None, n, _name_key(x)).ratio() for x in (p.name, profile(p).get("legalName") or p.name))
    if mine > 0.6 or any(_name_key(w) in n for w in p.name.split() if len(w) > 3):
        return None
    best, score = None, 0.0
    for q in db.scalars(select(Person).where(Person.household_id == p.household_id, Person.id != p.id, Person.removed.is_(None))):
        if not access(db, u, q).writer:
            continue
        r_ = max(difflib.SequenceMatcher(None, n, _name_key(q.name)).ratio(), max((1.0 if len(w) > 3 and _name_key(w) in n else 0) for w in q.name.split()))
        if r_ > score:
            best, score = q, r_
    return {"name": pt.get("name"), "to": best.id, "toName": best.name} if best and score > 0.6 else {"name": pt.get("name")}


def med_changes(db: Session, pid: str, meds: list) -> list[dict]:
    cur = {}
    for m in db.scalars(select(HealthRecord).where(HealthRecord.person_id == pid, HealthRecord.kind == "med")):
        d = decrypt(m.blob) or {}
        if d.get("active") is not False:
            cur[re.sub(r"[^a-z]", "", (d.get("name") or "").split(" ")[0].lower())] = (m.id, d)
    out = []
    for m in meds or []:
        k = re.sub(r"[^a-z]", "", (m.get("name") or "").split(" ")[0].lower())
        if k in cur:
            mid, d = cur[k]
            old = (d.get("name") or "").strip()
            new = ((m.get("name") or "") + " " + (m.get("strength") or "")).strip()
            if med_key(old) != med_key(new):
                out.append({"id": mid, "old": old, "new": new, "freq": m.get("frequency", "")})
    return out


class MoveIn(BaseModel):
    to: str


@r.post("/records/{rid}/move")
def move_record(rid: str, body: MoveIn, u: User = Depends(need_user), db: Session = Depends(get_db)):
    x = db.get(HealthRecord, rid)
    if not x or x.kind != "report":
        raise HTTPException(404, "Not found")
    p, a = person_or_404(db, u, x.person_id)
    q, b = person_or_404(db, u, body.to)
    if not (a.writer and b.writer) or p.household_id != q.household_id:
        raise HTTPException(403, "You can move it only between people you manage")
    d = decrypt(x.blob) or {}
    d["other"], d["suggest"] = None, []
    d["compare"] = compare_findings(db, q.id, d.get("findings") or [], x.day or "")
    x.person_id, x.blob = q.id, encrypt(d)
    index_record(db, x, d)
    db.commit()
    return rec_json(x)


@r.post("/records/{rid}/seen")
def seen_suggest(rid: str, u: User = Depends(need_user), db: Session = Depends(get_db)):
    x = db.get(HealthRecord, rid)
    if not x:
        raise HTTPException(404, "Not found")
    p, a = person_or_404(db, u, x.person_id)
    if not a.writer:
        raise HTTPException(403, "Not yours")
    d = decrypt(x.blob) or {}
    d["suggestDone"] = True
    x.blob = encrypt(d)
    db.commit()
    return {"ok": True}


@r.post("/people/{pid}/reports")
async def upload_report(pid: str, request: Request, file: UploadFile = File(...), read: str = Form("1"), doc: str = Form("report"),
                        u: User = Depends(need_user), db: Session = Depends(get_db)):
    limit(request, "v2upload", 30, 600)
    p, a = person_or_404(db, u, pid)
    if not a.writer:
        raise HTTPException(403, "Only they can add reports")
    data = await file.read()
    if not data or len(data) > 15 * 1024 * 1024:
        raise HTTPException(413, "Files up to 15 MB")
    mime = file.content_type or "application/octet-stream"
    if not (mime.startswith("image/") or mime == "application/pdf"):
        raise HTTPException(415, "PDF or photo only")
    from . import storage
    fid = new_id("f")
    mime, fname = storage.checked(data, file.filename or "report")
    data = storage.safe_document(data, mime)
    if mime not in ("application/pdf", "image/heic"):
        mime = "image/jpeg"
    storage.virus_scan(data)
    if mime == "application/pdf":
        try:
            from . import ai
            txt = ai.text_from(data, mime)
        except Exception:
            txt = ""
        if txt and len(txt) > 200 and not storage.looks_medical(txt):
            raise HTTPException(422, "This doesn't look like a medical report or prescription, so it was not saved.")
    storage.put(db, p.id, fid, data, mime, fname, u.id)
    reading = {}
    if read == "1":
        try:
            from . import ai
            pr = profile(p)
            preg = active_pregnancy(db, p.id)
            reading = ai.analyze("prescription" if doc == "prescription" else "report", data, mime, "", {"age": age(pr.get("dob", "")), "sex": pr.get("sex", ""), "allergies": pr.get("allergies", ""), "pregnant": bool(preg and preg.get("stage") == "pregnant")})
        except Exception as e:                            # the file is safe in storage; the person can enter values by hand
            reading = {"engine": "none", "warnings": ["The report was saved but could not be read automatically. Add the values yourself."], "error": type(e).__name__}
    if reading.get("not_medical") and not reading.get("findings") and not reading.get("medicines"):
        from .models import StoredFile
        f0 = db.get(StoredFile, (p.id, fid))
        if f0:
            db.delete(f0)
        db.commit()
        raise HTTPException(422, "This doesn't look like a medical report or prescription, so it was not saved.")
    first = (reading.get("findings") or [{}])[0] if reading.get("findings") else {}
    stem = re.sub(r"[_-]+", " ", (file.filename or "").rsplit(".", 1)[0]).strip()
    generic = not stem or re.fullmatch(r"(?i)(img|image|scan|document|doc|photo|pxl|file|report|download)?[\s\d()]*", stem)
    title = reading.get("title") or ("Prescription" if doc == "prescription" else (stem.title() if not generic else ("Lab report" if len(reading.get("findings") or []) > 1 else first.get("test") or "Lab report")))
    rec = {"title": str(title).strip()[:80],
           "doc": "prescription" if doc == "prescription" else "report", "doctor": reading.get("doctor", ""), "date": reading.get("date", ""),
           "findings": reading.get("findings", []), "medicines": reading.get("medicines", []), "summary": reading.get("summary", ""),
           "focus": reading.get("focus", []), "followups": reading.get("followups", []) + reading.get("tests_needed", []),
           "questions": reading.get("questions_for_doctor", []), "warnings": reading.get("warnings", []),
           "engine": reading.get("engine", ""), "mime": mime, "name": (file.filename or "")[:120], "checked": False}
    rec.update({"patient": reading.get("patient") or {}, "lab": reading.get("lab", ""), "recheck": reading.get("recheck", []),
                "doctorPhone": reading.get("doctor_phone", "")})
    rec["patient"].update({k: v for k, v in _patient_from_text(reading).items() if not rec["patient"].get(k)})
    for f in rec["findings"]:
        f["sure"] = f.get("sure") is not False
    rec["unreadable"] = reading.get("readable") is False or (read == "1" and reading.get("engine") == "none")
    rec["suggest"] = suggestions(db, p, rec, reading)
    rec["compare"] = compare_findings(db, p.id, rec["findings"], rec["date"] or _dt.date.today().isoformat())
    rec["other"] = other_person(db, u, p, rec["patient"])
    if doc == "prescription":
        rec["medChanges"] = med_changes(db, p.id, rec["medicines"])
    flagged = [f for f in rec["findings"] if (f.get("flag") or "normal") not in ("normal", "unknown")]
    _note(db, p.household_id, "report", f"{p.name}: {rec['title']} read" if p.owner_user != u.id else f"Your {rec['title']} is read",
          ("Couldn't read it clearly. Retake the photo in good light." if rec["unreadable"] and not rec["findings"] else
           (_compare_line(rec["compare"]) or (f"{len(flagged)} value{'s' if len(flagged) != 1 else ''} need attention" if flagged else "Everything is in range"))
           + (f" · check {sum(1 for f in rec['findings'] if not f['sure'])} value(s) we weren't sure of" if any(not f["sure"] for f in rec["findings"]) else "")) if rec["findings"] or rec["unreadable"] else "Saved. Add the values if needed.",
          {"person": p.id}, member_id=p.id)
    x = HealthRecord(person_id=p.id, kind="report", blob=encrypt(rec), file_id=fid, day=(rec["date"] or "")[:10] if re.fullmatch(r"\d{4}-\d{2}-\d{2}.*", rec["date"] or "") else _dt.date.today().isoformat(), by_user=u.id)
    db.add(x)
    db.flush()
    index_record(db, x, rec)
    db.commit()
    return rec_json(x)


def flag_from_ref(value, ref: str, old: str) -> str:
    """Re-decide high / low / normal after a person corrects a number, using the lab's own printed range."""
    try:
        v = float(value)
    except (TypeError, ValueError):
        return old or "unknown"
    t = (ref or "").replace(",", "").replace("–", "-").replace(" to ", "-")
    m = re.search(r"(-?\d+(?:\.\d+)?)\s*-\s*(-?\d+(?:\.\d+)?)", t)
    if m:
        lo, hi = float(m.group(1)), float(m.group(2))
        return "low" if v < lo else "high" if v > hi else "normal"
    m = re.search(r"(<|≤|up to|upto|below)\s*(\d+(?:\.\d+)?)", t, re.I)
    if m:
        return "high" if v > float(m.group(2)) else "normal"
    m = re.search(r"(>|≥|above)\s*(\d+(?:\.\d+)?)", t, re.I)
    if m:
        return "low" if v < float(m.group(2)) else "normal"
    return old or "unknown"


class FindingFix(BaseModel):
    i: int
    value: str | float | None = None   # None = "the value we read is right"


@r.post("/records/{rid}/finding")
def fix_finding(rid: str, body: FindingFix, u: User = Depends(need_user), db: Session = Depends(get_db)):
    x = db.get(HealthRecord, rid)
    if not x or x.kind != "report":
        raise HTTPException(404, "Not found")
    p, a = person_or_404(db, u, x.person_id)
    if not a.writer:
        raise HTTPException(403, "Only they can change this report")
    rec = decrypt(x.blob)
    fs = rec.get("findings") or []
    if not 0 <= body.i < len(fs):
        raise HTTPException(400, "No such value")
    f = fs[body.i]
    if body.value is not None and str(body.value).strip() != "":
        raw = str(body.value).strip().replace(",", "")
        if len(raw) > 20 or not re.fullmatch(r"-?\d+(\.\d+)?|[A-Za-z +/-]{1,20}", raw):
            raise HTTPException(400, "Enter the number exactly as printed, e.g. 7.2")
        try:
            num = float(raw)
            if num < 0 or num > 1_000_000:
                raise HTTPException(400, "That number is out of range for a lab value")
            f["value"] = num
        except ValueError:
            f["value"] = raw
        f["flag"] = flag_from_ref(f["value"], f.get("ref", ""), f.get("flag", ""))
        f["edited"] = True
    f["sure"] = True
    rec["checked"] = all(z.get("sure", True) for z in fs)
    rec["compare"] = compare_findings(db, p.id, fs, rec.get("date") or x.day)
    x.blob = encrypt(rec)
    db.flush()
    index_record(db, x, rec)
    db.commit()
    return rec_json(x)


@r.get("/records/{rid}/file")
def report_file(rid: str, u: User = Depends(need_user), db: Session = Depends(get_db)):
    x = db.get(HealthRecord, rid)
    if not x or not x.file_id:
        raise HTTPException(404, "Not found")
    p, a = person_or_404(db, u, x.person_id)
    if not a.can_kind(x.kind):
        raise HTTPException(403, "Not shared with you")
    from . import storage
    got = storage.get(db, p.id, x.file_id)
    if not got:
        raise HTTPException(404, "File missing")
    row, data = got
    mime = row.mime or "application/octet-stream"
    log(db, p, u, a, "report file")
    db.commit()
    return Response(data, media_type=mime, headers={"Cache-Control": "private, no-store"})


# ---- household: invite, join, guardians, leave, remove ---------------------------------------------------------------
class InviteIn(BaseModel):
    contact: str
    relation: str = ""
    name: str = ""


INVITE_GAP, INVITE_MAX = 120, 5


def invite_view(i: HouseholdInvite) -> dict:
    st = "joined" if i.used_by else "expired" if i.expires < now() else "opened" if i.opened else "sent"
    return {"ref": i.token[:10], "token": i.token[:6], "contact": i.contact, "relation": i.relation, "name": i.name,
            "sent": i.sent_at or i.created, "sends": i.sends or 1, "status": st, "expires": i.expires,
            "link": f"/app/join/{i.token}", "canResend": (now() - (i.sent_at or i.created)) >= INVITE_GAP and (i.sends or 1) < INVITE_MAX}


def _deliver(request: Request, u: User, i: HouseholdInvite) -> bool:
    link = f"{str(request.base_url).rstrip('/')}/app/join/{i.token}"
    text = f"{u.name or 'Your family'} invited you to their family on Urban Health. Join with your own account: {link}"
    try:
        if "@" in i.contact and (messaging.email_ready() or messaging.demo()):
            messaging.send_invite_email(i.contact, u.name or "Your family", i.relation or "", link)
            return True
        if "@" not in i.contact and (messaging.alert_sms_ready() or messaging.demo()):
            return bool(messaging.send_text_sms(i.contact, text))
    except Exception:
        pass
    return False


def _my_invite(db: Session, u: User, ref: str) -> HouseholdInvite:
    ref = (ref or "")[:10]
    i = db.scalar(select(HouseholdInvite).where(HouseholdInvite.household_id == (u.household_id or "-"), HouseholdInvite.token.like(ref + "%"))) if len(ref) >= 6 else None
    if not i or i.used_by:
        raise HTTPException(404, "This invite is no longer there")
    return i


@r.post("/household/invite")
def invite(body: InviteIn, request: Request, u: User = Depends(need_user), db: Session = Depends(get_db)):
    limit(request, "v2invite", 20, 3600)
    h = ensure_household(db, u)
    kind, c = norm_contact(body.contact)
    rel, name = norm_relation(body.relation), norm_name(body.name)
    if c in ((u.phone or ""), (u.email or "").lower()):
        raise HTTPException(400, "That is your own " + ("email" if kind == "email" else "number"))
    member = db.scalar(select(User).where(User.household_id == h.id, (User.email == c) if kind == "email" else (User.phone == c)))
    if member:
        raise HTTPException(409, f"{member.name or 'This person'} is already in your family")
    live = db.scalars(select(HouseholdInvite).where(HouseholdInvite.household_id == h.id, HouseholdInvite.used_by.is_(None))).all()
    dup = next((i for i in live if i.contact == c), None)
    if dup:                                   # never a second row: the caller offers Resend instead
        return {"ok": True, "duplicate": True, "invite": invite_view(dup)}
    if rel in ONE_ONLY:
        taken = db.scalar(select(HouseholdInvite).where(HouseholdInvite.household_id == h.id, HouseholdInvite.relation == rel,
                                                         (HouseholdInvite.used_by.is_not(None)) | (HouseholdInvite.expires > now())))
        if taken:
            raise HTTPException(409, f"You already have a {rel.lower()} in your family ({taken.name or taken.contact}). Cancel that invite first if it was a mistake.")
    t = secrets.token_urlsafe(24)
    i = HouseholdInvite(token=t, household_id=h.id, contact=c, relation=rel, name=name, by_user=u.id, expires=now() + INVITE_DAYS * 86400, sent_at=now(), sends=1)
    db.add(i)
    db.commit()
    sent = _deliver(request, u, i)
    return {"ok": True, "sent": sent, "link": f"{str(request.base_url).rstrip('/')}/app/join/{t}", "invite": invite_view(i)}


@r.post("/household/invites/{ref}/resend")
def invite_resend(ref: str, request: Request, u: User = Depends(need_user), db: Session = Depends(get_db)):
    limit(request, "v2resend", 20, 3600)
    i = _my_invite(db, u, ref)
    wait = INVITE_GAP - (now() - (i.sent_at or i.created))
    if wait > 0:
        raise HTTPException(429, f"Sent just now. You can resend in {wait} seconds.")
    if (i.sends or 1) >= INVITE_MAX:
        raise HTTPException(429, "Sent 5 times already. Share the link on WhatsApp instead.")
    i.sends, i.sent_at, i.expires = (i.sends or 1) + 1, now(), now() + INVITE_DAYS * 86400
    db.commit()
    return {"ok": True, "sent": _deliver(request, u, i), "invite": invite_view(i)}


class InviteEdit(BaseModel):
    name: str = ""
    relation: str = ""


@r.put("/household/invites/{ref}")
def invite_edit(ref: str, body: InviteEdit, u: User = Depends(need_user), db: Session = Depends(get_db)):
    i = _my_invite(db, u, ref)
    i.name, i.relation = norm_name(body.name) or i.name, norm_relation(body.relation) or i.relation
    db.commit()
    return invite_view(i)


@r.delete("/household/invites/{ref}")
def invite_cancel(ref: str, u: User = Depends(need_user), db: Session = Depends(get_db)):
    i = _my_invite(db, u, ref)
    db.delete(i)                              # the link stops working at once
    db.commit()
    return {"ok": True}


@r.get("/household/invite/{token}")
def invite_open(token: str, db: Session = Depends(get_db)):
    """The invited person opened the link: mark it, and say who invited them. No health data."""
    i = db.get(HouseholdInvite, token)
    if not i or i.used_by or i.expires < now():
        raise HTTPException(404, "This invite has expired. Ask for a new one.")
    if not i.opened:
        i.opened = now()
        db.commit()
    by = db.get(User, i.by_user)
    return {"by": (by.name if by else "") or "Your family", "relation": i.relation}


class JoinIn(BaseModel):
    token: str


@r.post("/household/join")
def join(body: JoinIn, u: User = Depends(need_user), db: Session = Depends(get_db)):
    i = db.get(HouseholdInvite, body.token)
    if not i or i.used_by or i.expires < now():
        raise HTTPException(400, "This invite has expired. Ask for a new one.")
    by = db.get(User, i.by_user)
    out = {"ok": True, "by": (by.name if by else "") or "Your family", "relation": i.relation}
    if i.person_id:                                   # a dependent receiving their own login, records intact
        p = db.get(Person, i.person_id)
        if not p or p.owner_user or p.removed:
            raise HTTPException(400, "This profile was already handed over.")
        if my_person(db, u):
            raise HTTPException(409, "You already have your own profile. Sign up with a new account to receive this one.")
        if u.household_id and u.household_id != p.household_id:
            _move_out(db, u)
        u.household_id, u.role = p.household_id, "member"
        p.owner_user = u.id
        for g in db.scalars(select(Guardian).where(Guardian.person_id == p.id)):
            db.merge(Grant(person_id=p.id, user_id=g.user_id, level="summary", womens=False))
            db.delete(g)
        i.used_by = u.id
        _note(db, p.household_id, "family", f"{p.name} now has their own login", "Their records came with them. They decide what you can see now.", {"user": u.id})
        db.commit()
        return {**out, "handover": True}
    if u.household_id == i.household_id:
        return out
    if u.household_id and db.scalar(select(Guardian.person_id).join(Person, Person.id == Guardian.person_id).where(Guardian.user_id == u.id, Person.household_id == u.household_id)):
        raise HTTPException(409, "Hand over the people you look after before joining another family.")
    _move_out(db, u)
    u.household_id, u.role = i.household_id, "member"
    mine = my_person(db, u)
    if mine:
        mine.household_id = i.household_id
    i.used_by = u.id
    _note(db, i.household_id, "family", f"{u.name or 'Someone'} joined the family", "They chose what to share from their own Settings.", {"user": u.id})
    db.commit()
    return out


class RelIn(BaseModel):
    relation: str = ""
    related: bool = True


@r.post("/household/relation")
def confirm_relation(body: RelIn, u: User = Depends(need_user), db: Session = Depends(get_db)):
    """The person who joined says how they are related. A wrong relation is corrected and the inviter told."""
    i = db.scalar(select(HouseholdInvite).where(HouseholdInvite.used_by == u.id, HouseholdInvite.household_id == (u.household_id or "-")))
    if not i:
        raise HTTPException(404, "Nothing to confirm")
    rel = norm_relation(body.relation) if body.related else "Other"
    if rel and rel != i.relation:
        old = i.relation
        i.relation = rel
        _note(db, i.household_id, "family", f"{u.name or 'Someone'} corrected the relation", f"You added them as {old or 'family'}; they say {rel}.", {"user": u.id}, to_user=i.by_user)
    i.rel_ok = 1
    db.commit()
    return {"ok": True, "relation": i.relation}


class HandIn(BaseModel):
    contact: str


@r.post("/people/{pid}/handover")
def handover(pid: str, body: HandIn, request: Request, u: User = Depends(need_user), db: Session = Depends(get_db)):
    """A dependent turning 18 gets their own login. One invite, their records move with them, nothing is copied."""
    limit(request, "v2invite", 20, 3600)
    p, a = person_or_404(db, u, pid)
    if p.owner_user or not db.get(Guardian, (p.id, u.id)):
        raise HTTPException(403, "Only a guardian can hand over a profile")
    yrs = age(profile(p).get("dob", ""))
    if not isinstance(yrs, int) or yrs < 18:
        raise HTTPException(400, "Profiles can be handed over from 18 years of age")
    kind, c = norm_contact(body.contact)
    db.execute(delete(HouseholdInvite).where(HouseholdInvite.person_id == p.id, HouseholdInvite.used_by.is_(None)))
    i = HouseholdInvite(token=secrets.token_urlsafe(24), household_id=p.household_id, contact=c, relation="", name=p.name,
                        by_user=u.id, expires=now() + INVITE_DAYS * 86400, sent_at=now(), sends=1, person_id=p.id)
    db.add(i)
    db.commit()
    return {"ok": True, "sent": _deliver(request, u, i), "invite": invite_view(i)}


@r.get("/household/invites/{ref}/qr.svg")
def invite_qr(ref: str, request: Request, u: User = Depends(need_user), db: Session = Depends(get_db)):
    import io
    import qrcode
    import qrcode.image.svg
    i = _my_invite(db, u, ref)
    img = qrcode.make(f"{str(request.base_url).rstrip('/')}/app/join/{i.token}", image_factory=qrcode.image.svg.SvgPathImage, box_size=12, border=2)
    b = io.BytesIO()
    img.save(b)
    return Response(b.getvalue(), media_type="image/svg+xml", headers={"Cache-Control": "private, no-store"})


@r.get("/changes")
def my_changes(u: User = Depends(need_user), db: Session = Depends(get_db)):
    rows = db.scalars(select(ProfileChange).where(ProfileChange.user_id == u.id).order_by(ProfileChange.t.desc()).limit(100))
    return [{"fields": x.fields.split(","), "device": x.device, "t": x.t} for x in rows]


# ---- duplicates: find and merge ----------------------------------------------------------------------------------------
def med_key(n: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (n or "").lower())


def med_name(n: str) -> str:
    """'DOLO-650', 'dolo650', 'Dolo 650' -> 'Dolo 650'."""
    n = re.sub(r"[-_]+", " ", (n or "").strip())
    n = re.sub(r"(?<=[A-Za-z])(?=\d)", " ", n)
    n = re.sub(r"\s+", " ", n)
    return " ".join(w if any(ch.isdigit() for ch in w) or (len(w) <= 3 and w.isupper()) else w[:1].upper() + w[1:].lower() for w in n.split(" "))[:80]


@r.get("/household/duplicates")
def duplicates(u: User = Depends(need_user), db: Session = Depends(get_db)):
    import difflib
    out = []
    if not u.household_id:
        return out
    ppl = [p for p in db.scalars(select(Person).where(Person.household_id == u.household_id, Person.removed.is_(None))) if access(db, u, p).writer]
    allp = list(db.scalars(select(Person).where(Person.household_id == u.household_id, Person.removed.is_(None))))
    for x in range(len(allp)):
        for y in range(x + 1, len(allp)):
            a, b = allp[x], allp[y]
            if a.owner_user and b.owner_user:
                continue
            r_ = difflib.SequenceMatcher(None, _name_key(a.name), _name_key(b.name)).ratio()
            same_dob = profile(a).get("dob") and profile(a).get("dob") == profile(b).get("dob")
            if r_ > 0.88 or (same_dob and r_ > 0.6):
                keep, drop = (a, b) if a.owner_user or a.created <= b.created else (b, a)
                if not drop.owner_user and db.get(Guardian, (drop.id, u.id)):
                    out.append({"kind": "person", "keep": keep.id, "drop": drop.id, "a": keep.name, "b": drop.name})
    seen = {}
    for i in db.scalars(select(HouseholdInvite).where(HouseholdInvite.household_id == u.household_id, HouseholdInvite.used_by.is_(None)).order_by(HouseholdInvite.created.desc())):
        try:
            c = norm_contact(i.contact)[1]
        except HTTPException:
            c = i.contact
        if c in seen:
            out.append({"kind": "invite", "keep": seen[c].token[:10], "drop": i.token[:10], "a": seen[c].name or seen[c].contact, "b": i.name or i.contact})
        else:
            seen[c] = i
    for p in ppl:
        meds = {}
        for m in db.scalars(select(HealthRecord).where(HealthRecord.person_id == p.id, HealthRecord.kind == "med").order_by(HealthRecord.created)):
            d = decrypt(m.blob) or {}
            if d.get("active") is False:
                continue
            k = med_key(d.get("name"))
            if k in meds:
                out.append({"kind": "med", "keep": meds[k][0], "drop": m.id, "a": meds[k][1], "b": d.get("name", ""), "who": p.name})
            else:
                meds[k] = (m.id, d.get("name", ""))
    return out


class MergeIn(BaseModel):
    kind: str
    keep: str
    drop: str


@r.post("/household/merge")
def merge(body: MergeIn, u: User = Depends(need_user), db: Session = Depends(get_db)):
    if body.kind == "invite":
        _my_invite(db, u, body.keep)
        db.delete(_my_invite(db, u, body.drop))
    elif body.kind == "med":
        a, b = db.get(HealthRecord, body.keep), db.get(HealthRecord, body.drop)
        if not a or not b or a.kind != "med" or b.kind != "med" or a.person_id != b.person_id or not person_or_404(db, u, a.person_id)[1].writer:
            raise HTTPException(404, "Not found")
        for d in db.scalars(select(HealthRecord).where(HealthRecord.person_id == a.person_id, HealthRecord.kind == "dose")):
            dd = decrypt(d.blob) or {}
            if dd.get("med") == b.id:
                dd["med"] = a.id
                d.blob = encrypt(dd)
        db.delete(b)
    elif body.kind == "person":
        keep, ka = person_or_404(db, u, body.keep)
        drop, da = person_or_404(db, u, body.drop)
        if drop.owner_user or not db.get(Guardian, (drop.id, u.id)) or keep.household_id != drop.household_id:
            raise HTTPException(403, "Only a dependent you look after can be merged")
        for rec in db.scalars(select(HealthRecord).where(HealthRecord.person_id == drop.id)):
            rec.person_id = keep.id
        kp, dp = profile(keep), profile(drop)
        for k in PROFILE_KEYS:
            if not kp.get(k) and dp.get(k):
                kp[k] = dp[k]
        keep.blob = encrypt(kp)
        drop.removed = now()
        db.execute(delete(Guardian).where(Guardian.person_id == drop.id))
    else:
        raise HTTPException(400, "Unknown")
    db.commit()
    return {"ok": True}


def _move_out(db: Session, u: User):
    """Leaving: your own records come with you; nobody keeps any grant to them, and you keep none to theirs."""
    mine = my_person(db, u)
    if mine:
        db.execute(delete(Grant).where(Grant.person_id == mine.id))
    db.execute(delete(Grant).where(Grant.user_id == u.id))
    if u.household_id:
        dep = [g for g in db.scalars(select(Guardian).where(Guardian.user_id == u.id))]
        for g in dep:
            db.delete(g)


@r.post("/household/leave")
def leave(u: User = Depends(need_user), db: Session = Depends(get_db)):
    if not u.household_id:
        return {"ok": True}
    orphan = _orphans_if_gone(db, u)
    if orphan:
        raise HTTPException(409, f"Give {', '.join(orphan)} another guardian or their own login first.")
    old, was_admin = u.household_id, u.role == "admin"
    _move_out(db, u)
    h = Household(key=secrets.token_hex(16), name=(u.name.split(" ")[0] + "'s family") if u.name else "Family")
    db.add(h)
    db.flush()
    u.household_id = h.id
    mine = my_person(db, u)
    if mine:
        mine.household_id = h.id
    u.role = "admin"
    db.flush()
    if was_admin:   # ownership passes to the longest-standing adult left
        nxt = db.scalar(select(User).where(User.household_id == old).order_by(User.created))
        if nxt:
            nxt.role = "admin"
    db.commit()
    return {"ok": True}


def _orphans_if_gone(db: Session, u: User) -> list[str]:
    out = []
    for g in db.scalars(select(Guardian).where(Guardian.user_id == u.id)):
        p = db.get(Person, g.person_id)
        if not p or p.removed or p.household_id != u.household_id:
            continue
        others = db.scalars(select(Guardian.user_id).where(Guardian.person_id == p.id, Guardian.user_id != u.id)).all()
        if not others:
            out.append(p.name)
    return out


class UserRef(BaseModel):
    user_id: str


@r.post("/household/remove")
def remove_member(body: UserRef, u: User = Depends(need_user), db: Session = Depends(get_db)):
    if u.role != "admin":
        raise HTTPException(403, "Only the family owner can remove someone")
    m = db.get(User, body.user_id)
    if not m or m.household_id != u.household_id or m.id == u.id:
        raise HTTPException(400, "Not in this household")
    orphan = _orphans_if_gone(db, m)
    if orphan:
        raise HTTPException(409, f"{', '.join(orphan)} would have no guardian. Change their guardian first.")
    _move_out(db, m)
    h = Household(key=secrets.token_hex(16), name=(m.name.split(" ")[0] + "'s family") if m.name else "Family")
    db.add(h)
    db.flush()
    old = u.household_id
    m.household_id, m.role = h.id, "admin"
    mine = my_person(db, m)
    if mine:
        mine.household_id = h.id
    _note(db, h.id, "family", "You were removed from a family", f"{u.name or 'The owner'} removed you. All your records are still yours.", to_user=m.id)
    _note(db, old, "family", f"{m.name or 'A member'} is no longer in the family")
    db.commit()
    return {"ok": True}


@r.post("/people/{pid}/guardians")
def add_guardian(pid: str, body: UserRef, u: User = Depends(need_user), db: Session = Depends(get_db)):
    p, a = person_or_404(db, u, pid)
    if p.owner_user is not None or a.level != "guardian":
        raise HTTPException(403, "Only a guardian can do this")
    m = db.get(User, body.user_id)
    if not m or m.household_id != p.household_id:
        raise HTTPException(400, "Not in this household")
    db.merge(Guardian(person_id=p.id, user_id=m.id))
    _note(db, p.household_id, "family", f"You now look after {p.name}", f"{u.name or 'A guardian'} added you. You will get {p.name}'s medicine reminders.", {"person": p.id}, to_user=m.id)
    db.commit()
    return {"ok": True}


@r.delete("/people/{pid}/guardians/{uid}")
def drop_guardian(pid: str, uid: str, u: User = Depends(need_user), db: Session = Depends(get_db)):
    p, a = person_or_404(db, u, pid)
    if a.level != "guardian":
        raise HTTPException(403, "Only a guardian can do this")
    if len(db.scalars(select(Guardian.user_id).where(Guardian.person_id == p.id)).all()) <= 1:
        raise HTTPException(409, "Every dependent needs at least one guardian")
    g = db.get(Guardian, (p.id, uid))
    if g:
        db.delete(g)
    db.commit()
    return {"ok": True}


@r.delete("/people/{pid}")
def remove_dependent(pid: str, u: User = Depends(need_user), db: Session = Depends(get_db)):
    p, a = person_or_404(db, u, pid)
    if p.owner_user is not None or a.level != "guardian":
        raise HTTPException(403, "Only a guardian can remove a dependent")
    p.removed = now()   # kept 30 days; the purge job deletes it with its files after that
    db.commit()
    return {"ok": True, "purgeAfter": now() + 30 * 86400}


# ---- orders (labs, medicines) belong to a person too -----------------------------------------------------------------
def order_allowed(db: Session, u: User | None, member_id: str | None, write: bool = False) -> bool:
    """A lab booking or medicine order made for a Phase 0 person is health information about that person: only those
    who may read their reports see it, and only their owner or guardian may place one. Orders for the old
    household-blob members keep the old household-wide behaviour."""
    if not member_id:
        return True
    p = db.get(Person, member_id)
    if not p:
        return True
    if not u:
        return False
    a = access(db, u, p)
    return a.writer if write else a.can("summary")


# ---- notifications: one bell per account -----------------------------------------------------------------------------
CATEGORIES = [("meds", "Medicine reminders", "At dose time, and when a dose is missed"),
              ("orders", "Lab tests and orders", "Booked, confirmed, technician on the way, delivered"),
              ("reports", "Reports and prescriptions", "When a report is ready or a doctor sends a prescription"),
              ("family", "Family", "Someone joins, leaves, or changes what they share with you"),
              ("insights", "Health insights", "At most one a day"),
              ("safety", "Emergencies", "SOS and urgent blood requests. Always on.")]


def _visible(db: Session, u: User, n: Notice, people: dict) -> bool:
    if n.to_user:
        return n.to_user == u.id
    if n.member_id and n.member_id in people:
        return people[n.member_id].can("summary")
    if n.member_id:
        mine = db.get(Person, n.member_id)
        if mine:
            return False                          # a person from another household
    return True


def _note(db: Session, household_id: str, kind: str, title: str, body: str = "", ref: dict | None = None, member_id: str = "", to_user: str = "", url: str = "/app"):
    try:
        from .inbox import notify
        notify(db, household_id, kind, title, body, ref or {}, member_id, url, to_user)
    except Exception as e:                       # a notice must never break the action that caused it
        print("[people] notice failed:", type(e).__name__, str(e)[:120], flush=True)


@r.get("/inbox")
def inbox(u: User = Depends(need_user), db: Session = Depends(get_db)):
    if not u.household_id:
        return {"items": [], "unread": 0}
    people = {p.id: access(db, u, p) for p in db.scalars(select(Person).where(Person.household_id == u.household_id))}
    marks = {m.notice_id: m for m in db.scalars(select(NoticeMark).where(NoticeMark.user_id == u.id))}
    names = {p.id: p.name for p in db.scalars(select(Person).where(Person.household_id == u.household_id))}
    out = []
    for n in db.scalars(select(Notice).where(Notice.household_id == u.household_id).order_by(Notice.t.desc(), Notice.id.desc()).limit(300)):
        mk = marks.get(n.id)
        if (mk and mk.cleared) or not _visible(db, u, n, people):
            continue
        from .inbox import CATEGORY
        out.append({"id": n.id, "kind": n.kind, "cat": CATEGORY.get(n.kind, "other"), "title": n.title, "body": n.body, "ref": n.ref or {},
                    "t": n.t, "read": bool(mk and mk.read), "person": n.member_id if n.member_id in names else "", "personName": names.get(n.member_id, "")})
        if len(out) >= 150:
            break
    return {"items": out, "unread": sum(1 for x in out if not x["read"])}


class MarkIn(BaseModel):
    ids: list[int] = []
    all: bool = False


def _mark(db: Session, u: User, body: MarkIn, field: str):
    ids = body.ids[:500]
    if body.all:
        ids = [x["id"] for x in inbox(u, db)["items"]]
    for i in ids:
        n = db.get(Notice, i)
        if not n or n.household_id != u.household_id:
            continue
        m = db.get(NoticeMark, (u.id, i)) or NoticeMark(user_id=u.id, notice_id=i)
        setattr(m, field, True)
        if field == "cleared":
            m.read = True
        db.merge(m)
    db.commit()
    return {"ok": True}


@r.post("/inbox/read")
def inbox_read(body: MarkIn, u: User = Depends(need_user), db: Session = Depends(get_db)):
    return _mark(db, u, body, "read")


@r.post("/inbox/clear")
def inbox_clear(body: MarkIn, u: User = Depends(need_user), db: Session = Depends(get_db)):
    return _mark(db, u, body, "cleared")


@r.get("/notify-prefs")
def get_prefs(u: User = Depends(need_user), db: Session = Depends(get_db)):
    pr = db.get(NoticePref, u.id)
    p = (pr.prefs if pr else {}) or {}
    return [{"key": k, "title": t, "sub": d, "on": True if k == "safety" else p.get(k, True) is not False, "locked": k == "safety"} for k, t, d in CATEGORIES]


class PrefIn(BaseModel):
    key: str
    on: bool


@r.put("/notify-prefs")
def set_prefs(body: PrefIn, u: User = Depends(need_user), db: Session = Depends(get_db)):
    if body.key not in {k for k, _, _ in CATEGORIES} or body.key == "safety":
        raise HTTPException(400, "This one cannot be changed")
    pr = db.get(NoticePref, u.id) or NoticePref(user_id=u.id, prefs={})
    pr.prefs = {**(pr.prefs or {}), body.key: bool(body.on)}
    db.merge(pr)
    db.commit()
    return {"ok": True}


# ---- deletion and retention --------------------------------------------------------------------------------------------
def purge_person(db: Session, p: Person) -> None:
    """Everything about one person: records, files in storage, sharing, guardians, access log, notices about them."""
    from . import storage
    try:
        storage.delete_household(db, p.id)          # per-person files live under the person's id
    except Exception as e:
        print("[people] file purge failed:", type(e).__name__, str(e)[:120], flush=True)
    for model, col in ((HealthRecord, HealthRecord.person_id), (Grant, Grant.person_id), (Guardian, Guardian.person_id), (AccessLog, AccessLog.person_id)):
        db.query(model).filter(col == p.id).delete(synchronize_session=False)
    db.query(Notice).filter(Notice.member_id == p.id).delete(synchronize_session=False)
    db.delete(p)


def delete_user_data(db: Session, u: User) -> None:
    """Called when an account is deleted. Their own profile goes with every record and file. People they look after go too
    when no one else can look after them; if another adult in the family is a guardian, those people stay with that adult.
    Raises 409 when a dependent would be left with no guardian although other adults could take over."""
    deps = []
    for g in db.scalars(select(Guardian).where(Guardian.user_id == u.id)).all():
        p = db.get(Person, g.person_id)
        if not p:
            continue
        others = db.scalars(select(Guardian.user_id).where(Guardian.person_id == p.id, Guardian.user_id != u.id)).all()
        if not others:
            deps.append(p)
    adults = db.scalar(select(User.id).where(User.household_id == u.household_id, User.id != u.id)) if u.household_id else None
    if deps and adults:
        raise HTTPException(409, f"Make another adult the guardian of {', '.join(p.name for p in deps)} first (Family → their name).")
    for p in deps:
        purge_person(db, p)
    mine = my_person(db, u)
    if mine:
        purge_person(db, mine)
    db.query(Grant).filter(Grant.user_id == u.id).delete(synchronize_session=False)
    db.query(Guardian).filter(Guardian.user_id == u.id).delete(synchronize_session=False)
    db.query(NoticeMark).filter(NoticeMark.user_id == u.id).delete(synchronize_session=False)
    db.query(NoticePref).filter(NoticePref.user_id == u.id).delete(synchronize_session=False)
    db.query(Notice).filter(Notice.to_user == u.id).delete(synchronize_session=False)
    db.query(AccessLog).filter(AccessLog.user_id == u.id).delete(synchronize_session=False)


def purge(db: Session) -> dict:
    """Daily: dependents removed more than 30 days ago, invites expired a month ago, access log older than two years."""
    t = now()
    gone = db.scalars(select(Person).where(Person.removed.is_not(None), Person.removed < t - 30 * 86400)).all()
    for p in gone:
        purge_person(db, p)
    inv = db.query(HouseholdInvite).filter(HouseholdInvite.expires < t - 30 * 86400).delete(synchronize_session=False)
    old = db.query(AccessLog).filter(AccessLog.t < t - 730 * 86400).delete(synchronize_session=False)
    from . import ops
    return {"people": len(gone), "invites": inv, "accessLog": old, **ops.purge(db)}


def start_purge() -> None:
    import threading
    import time as _t

    from .db import session
    from .tasks import in_process_loops
    if not in_process_loops():
        return

    def loop():
        while True:
            try:
                with session() as db:
                    out = purge(db)
                if any(out.values()):
                    print("[people] purge", out, flush=True)
            except Exception as e:
                print("[people] purge failed:", type(e).__name__, str(e)[:160], flush=True)
            _t.sleep(6 * 3600)

    threading.Thread(target=loop, name="people-purge", daemon=True).start()

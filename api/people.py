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
from .models import (AccessLog, Grant, Guardian, HealthRecord, Household, HouseholdInvite, Notice, NoticeMark, NoticePref, Person, User, new_id, now)

r = APIRouter(prefix="/api/v2", dependencies=[Depends(csrf)])

RANK = {"none": 0, "medid": 1, "summary": 2, "all": 3, "guardian": 4, "owner": 5}
# which level reads which kind of record; womens kinds also need the womens switch
KIND_LEVEL = {"contact": "medid", "report": "summary", "vital": "summary", "med": "all", "dose": "all",
              "preg": "summary", "kick": "summary", "cycle": "summary"}
WOMENS = {"preg", "kick", "cycle"}
PROFILE_KEYS = ("dob", "sex", "blood", "height", "weight", "donated", "allergies", "conditions", "organDonor", "phone")
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


def person_json(db: Session, u: User, p: Person, a: Access) -> dict:
    pr = profile(p)
    out = {"id": p.id, "name": p.name, "color": p.color, "self": p.owner_user == u.id,
           "dependent": p.owner_user is None, "access": a.level, "womens": a.womens,
           "sex": pr.get("sex", ""), "age": age(pr.get("dob", "")), "medicalId": medical_id(db, p, a)}
    if a.can("summary"):
        out["profile"] = {k: pr.get(k, "") for k in PROFILE_KEYS}
    if a.womens:
        out["pregnancy"] = active_pregnancy(db, p.id)
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
    return out


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
        for i in db.scalars(select(HouseholdInvite).where(HouseholdInvite.household_id == u.household_id, HouseholdInvite.used_by.is_(None), HouseholdInvite.expires > now())):
            invites.append({"token": i.token[:6], "contact": i.contact, "relation": i.relation})
    h = db.get(Household, u.household_id) if u.household_id else None
    return {"user": {"id": u.id, "name": u.name, "email": u.email, "phone": u.phone, "role": u.role},
            "household": u.household_id, "hkey": h.key if h else None, "me": mine.id if mine else None, "people": people, "members": members,
            "invites": invites, "onboarded": bool(mine and contacts(db, mine.id))}


# ---- people -----------------------------------------------------------------------------------------------------------
class PersonIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    profile: dict = Field(default_factory=dict)
    dependent: bool = False


@r.post("/people")
def create_person(body: PersonIn, request: Request, u: User = Depends(need_user), db: Session = Depends(get_db)):
    limit(request, "v2people", 30, 600)
    h = ensure_household(db, u)
    n = len(db.scalars(select(Person.id).where(Person.household_id == h.id)).all())
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


@r.put("/people/{pid}")
def edit_person(pid: str, body: PersonEdit, u: User = Depends(need_user), db: Session = Depends(get_db)):
    p, a = person_or_404(db, u, pid)
    if not a.writer:
        raise HTTPException(403, "Only they can change their profile")
    if body.name is not None and body.name.strip():
        p.name = body.name.strip()[:80]
    if body.profile is not None:
        cur = profile(p)
        cur.update(clean_profile({**cur, **body.profile}))
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
    x = HealthRecord(person_id=p.id, kind=body.kind, blob=encrypt(body.data), day=body.day, by_user=u.id)
    db.add(x)
    db.commit()
    return rec_json(x)


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
    db.delete(x)
    db.commit()
    return {"ok": True}


# ---- reports: file to S3, read by AI, values stored ------------------------------------------------------------------
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
    storage.put(db, p.id, fid, data, mime, (file.filename or "report")[:120], u.id)
    reading = {}
    if read == "1":
        try:
            from . import ai
            pr = profile(p)
            preg = active_pregnancy(db, p.id)
            reading = ai.analyze("prescription" if doc == "prescription" else "report", data, mime, "", {"age": age(pr.get("dob", "")), "sex": pr.get("sex", ""), "allergies": pr.get("allergies", ""), "pregnant": bool(preg and preg.get("stage") == "pregnant")})
        except Exception as e:                            # the file is safe in storage; the person can enter values by hand
            reading = {"engine": "none", "warnings": ["The report was saved but could not be read automatically. Add the values yourself."], "error": type(e).__name__}
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
    flagged = [f for f in rec["findings"] if (f.get("flag") or "normal") not in ("normal", "unknown")]
    _note(db, p.household_id, "report", f"{p.name}: {rec['title']} read" if p.owner_user != u.id else f"Your {rec['title']} is read",
          (f"{len(flagged)} result{'s' if len(flagged) != 1 else ''} worth discussing" if flagged else "Results are in range") if rec["findings"] else "Saved. Add the values if needed.",
          {"person": p.id}, member_id=p.id)
    x = HealthRecord(person_id=p.id, kind="report", blob=encrypt(rec), file_id=fid, day=(rec["date"] or "")[:10] if re.fullmatch(r"\d{4}-\d{2}-\d{2}.*", rec["date"] or "") else _dt.date.today().isoformat(), by_user=u.id)
    db.add(x)
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


@r.post("/household/invite")
def invite(body: InviteIn, request: Request, u: User = Depends(need_user), db: Session = Depends(get_db)):
    limit(request, "v2invite", 20, 3600)
    h = ensure_household(db, u)
    c = body.contact.strip()
    kind = "email" if "@" in c else "phone"
    if kind == "email" and not re.fullmatch(r"[^@\s]+@[^@\s]+\.[a-z]{2,}", c.lower()):
        raise HTTPException(400, "Enter a valid email address")
    if kind == "phone":
        digits = re.sub(r"\D", "", c)
        if len(digits) < 10:
            raise HTTPException(400, "Enter a valid mobile number")
        c = "+91" + digits[-10:] if len(digits) <= 12 else "+" + digits
    t = secrets.token_urlsafe(24)
    db.add(HouseholdInvite(token=t, household_id=h.id, contact=c, relation=body.relation.strip()[:40], by_user=u.id, expires=now() + INVITE_DAYS * 86400))
    db.commit()
    origin = str(request.base_url).rstrip("/")
    link = f"{origin}/app/join/{t}"
    text = f"{u.name or 'Your family'} invited you to their family on Urban Health. Join with your own account: {link}"
    sent = False
    try:
        if kind == "email" and (messaging.email_ready() or messaging.demo()):
            messaging.send_invite_email(c, u.name or "Your family", body.relation or "", link)
            sent = True
        elif kind == "phone" and (messaging.alert_sms_ready() or messaging.demo()):
            sent = bool(messaging.send_text_sms(c, text))
    except Exception:
        sent = False
    return {"ok": True, "sent": sent, "link": link}


class JoinIn(BaseModel):
    token: str


@r.post("/household/join")
def join(body: JoinIn, u: User = Depends(need_user), db: Session = Depends(get_db)):
    i = db.get(HouseholdInvite, body.token)
    if not i or i.used_by or i.expires < now():
        raise HTTPException(400, "This invite has expired. Ask for a new one.")
    if u.household_id == i.household_id:
        return {"ok": True}
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

"""Admin: privacy & DPDP desk, the reports inbox, services by city, and messaging / DLT status.

* Privacy: accounts waiting out their 48-hour deletion notice, and a personal-data breach register with the clock the
  DPDP Rules set (tell the Board and each affected person without delay; detailed report to the Board within 72 hours).
* Reports inbox: uploads from outside labs that did not match the person, or that the person asked us to check. The team
  sees who uploaded and why it was paused, never the results.
* Services: medicine orders, home tests, hospital visits and buying insurance are switched on per city once licensed
  partners there are verified. The app reads /api/v2/services and shows "Coming soon in your area" otherwise.
* Messaging: what is configured for SMS (and the DLT registration it needs), email and WhatsApp templates.
"""
from __future__ import annotations

import os
import re
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from .admin import log, me as admin_me
from .db import get_db
from .models import Admin, HealthRecord, Person, Setting, User, now

ar = APIRouter(prefix="/api/admin")
pub = APIRouter(prefix="/api/v2")

SERVICES = {"medicine": "Medicine orders", "lab": "Home tests", "visits": "Hospital visits", "insurance": "Buy insurance"}
BOARD_HOURS = 72


def _get(db: Session, key: str, default):
    s = db.get(Setting, key)
    return (s.value if s and s.value is not None else default)


def _put(db: Session, key: str, value) -> None:
    s = db.get(Setting, key)
    if s:
        s.value = value
    else:
        db.add(Setting(key=key, value=value))
    db.flush()


def _mask(n: str) -> str:
    parts = [p for p in (n or "").split() if p]
    return " ".join(p[0] + "•" * max(1, len(p) - 1) for p in parts) or "—"


# ---- privacy & DPDP ---------------------------------------------------------------------------------------------------
@ar.get("/privacy")
def privacy(a: Admin = Depends(admin_me), db: Session = Depends(get_db)):
    er = []
    for s in db.scalars(select(Setting).where(Setting.key.like("erase:%"))).all():
        u = db.get(User, s.key[6:])
        er.append({"who": _mask(u.name if u else ""), "at": (s.value or {}).get("at"), "asked": (s.value or {}).get("asked")})
    br = _get(db, "breaches", {"rows": []}).get("rows", [])
    for b in br:
        b["boardDue"] = b.get("found", 0) + BOARD_HOURS * 3600
    return {"erasures": sorted(er, key=lambda x: x["at"] or 0), "breaches": sorted(br, key=lambda x: -x.get("found", 0)),
            "contact": {"name": os.getenv("GRIEVANCE_NAME", "Grievance Officer, Urban Health"), "email": os.getenv("GRIEVANCE_EMAIL") or os.getenv("SUPPORT_EMAIL") or "privacy@urbanhealth.in"},
            "rules": {"boardHours": BOARD_HOURS, "eraseNotice": "48 hours", "logs": "1 year minimum", "grievance": "within 90 days (we aim for 7)"}}


class BreachIn(BaseModel):
    title: str
    nature: str = ""
    affected: int = 0
    found: int = 0
    boardNotified: int | None = None
    usersNotified: int | None = None
    report: str = ""
    closed: int | None = None


@ar.post("/breaches")
def add_breach(b: BreachIn, a: Admin = Depends(admin_me), db: Session = Depends(get_db)):
    if len(b.title.strip()) < 4:
        raise HTTPException(400, "Describe what happened in a few words.")
    d = _get(db, "breaches", {"rows": []})
    row = {"id": uuid.uuid4().hex[:10], "title": b.title.strip()[:160], "nature": b.nature.strip()[:400], "affected": max(0, b.affected),
           "found": b.found or now(), "by": a.email, "boardNotified": None, "usersNotified": None, "report": "", "closed": None}
    _put(db, "breaches", {"rows": [row, *d.get("rows", [])][:200]})
    log(db, a.email, "breach recorded", row["title"])
    return row


@ar.put("/breaches/{bid}")
def edit_breach(bid: str, b: BreachIn, a: Admin = Depends(admin_me), db: Session = Depends(get_db)):
    d = _get(db, "breaches", {"rows": []})
    rows = d.get("rows", [])
    x = next((r for r in rows if r["id"] == bid), None)
    if not x:
        raise HTTPException(404)
    for k in ("boardNotified", "usersNotified", "closed"):
        v = getattr(b, k)
        if v is not None:
            x[k] = v or None
    if b.report:
        x["report"] = b.report.strip()[:4000]
    if b.affected:
        x["affected"] = b.affected
    _put(db, "breaches", {"rows": rows})
    log(db, a.email, "breach updated", x["title"])
    return x


# ---- reports inbox ----------------------------------------------------------------------------------------------------
@ar.get("/uploads-inbox")
def uploads_inbox(a: Admin = Depends(admin_me), db: Session = Depends(get_db)):
    from .family import decrypt
    out = []
    for x in db.scalars(select(HealthRecord).where(HealthRecord.kind == "upload").order_by(HealthRecord.created.desc()).limit(300)).all():
        try:
            d = decrypt(x.blob) or {}
        except Exception:                      # written under an older key: nothing to show the team
            continue
        m, v = d.get("match") or {}, d.get("via") or {}
        if m.get("ok", True) and not d.get("asked"):
            continue
        p = db.get(Person, x.person_id)
        out.append({"id": x.id, "lab": v.get("lab", ""), "ref": v.get("ref", ""), "labPhone": v.get("phone", ""), "link": v.get("link", ""),
                    "t": v.get("t") or x.created, "who": _mask(p.name if p else ""), "flags": [k for k in ("name", "age", "sex") if m.get(k) == "differs"],
                    "asked": d.get("asked"), "team": d.get("team")})
    return {"rows": out}


class TeamNote(BaseModel):
    note: str


@ar.post("/uploads-inbox/{rid}")
def uploads_note(rid: str, b: TeamNote, a: Admin = Depends(admin_me), db: Session = Depends(get_db)):
    from .family import decrypt, encrypt
    from .people import _note
    x = db.get(HealthRecord, rid)
    if not x or x.kind != "upload":
        raise HTTPException(404)
    d = decrypt(x.blob) or {}
    d["team"] = {"note": b.note.strip()[:300], "t": now(), "by": a.email}
    x.blob = encrypt(d)
    p = db.get(Person, x.person_id)
    if p and b.note.strip():
        _note(db, p.household_id, "report", f"Update on the report from {(d.get('via') or {}).get('lab', 'the lab')}", b.note.strip()[:200], {"person": p.id, "upload": x.id}, member_id=p.id)
    log(db, a.email, "upload inbox note", rid)
    return {"ok": True}


# ---- services by city -------------------------------------------------------------------------------------------------
def _services(db: Session) -> dict:
    s = _get(db, "services", None)
    if s is None:                                   # never set: everything stays on, as before
        return {k: {"on": True, "cities": []} for k in SERVICES}
    return {k: {"on": bool((s.get(k) or {}).get("on")), "cities": [c for c in (s.get(k) or {}).get("cities", []) if c]} for k in SERVICES}


@ar.get("/services")
def services(a: Admin = Depends(admin_me), db: Session = Depends(get_db)):
    return {"services": _services(db), "names": SERVICES}


class ServiceIn(BaseModel):
    on: bool
    cities: list[str] = []


@ar.put("/services/{key}")
def set_service(key: str, b: ServiceIn, a: Admin = Depends(admin_me), db: Session = Depends(get_db)):
    if key not in SERVICES:
        raise HTTPException(404)
    s = _get(db, "services", None)
    s = {k: {"on": True, "cities": []} for k in SERVICES} if s is None else s
    s = {**s, key: {"on": b.on, "cities": sorted({re.sub(r"\s+", " ", c).strip().title()[:40] for c in b.cities if c.strip()})[:50]}}
    _put(db, "services", s)
    log(db, a.email, f"service {key} {'on' if b.on else 'off'}", ", ".join(s[key]["cities"]))
    return _services(db)


@pub.get("/services")
def services_public(city: str = "", db: Session = Depends(get_db)):
    """What a family can use where they are. A service with no cities listed is on everywhere once switched on.
    Until the admin has set anything at all, everything stays as it was (on), so existing families see no change."""
    raw = _get(db, "services", None)
    if raw is None:
        return {k: True for k in SERVICES}
    c = city.strip().lower()
    return {k: v["on"] and (not v["cities"] or not c or c in [x.lower() for x in v["cities"]]) for k, v in _services(db).items()}


# ---- messaging & DLT --------------------------------------------------------------------------------------------------
@ar.get("/messaging")
def messaging_status(a: Admin = Depends(admin_me), db: Session = Depends(get_db)):
    from . import messaging
    mode = messaging.sms_mode()
    wa = bool(os.getenv("WA_TOKEN") and os.getenv("WA_PHONE_ID"))
    return {"sms": {"mode": mode, "ready": messaging.sms_ready(), "alerts": messaging.alert_sms_ready()},
            "email": {"ready": messaging.email_ready()},
            "whatsapp": {"ready": wa, "templates": {"notice": bool(os.getenv("WA_TEMPLATE_NOTICE")), "sos": bool(os.getenv("WA_TEMPLATE_SOS"))}},
            "dlt": _get(db, "dlt", {"entity": "", "header": "", "templates": {}})}


class DltIn(BaseModel):
    entity: str = ""
    header: str = ""
    templates: dict[str, str] = {}


@ar.put("/messaging/dlt")
def set_dlt(b: DltIn, a: Admin = Depends(admin_me), db: Session = Depends(get_db)):
    if b.entity and not re.fullmatch(r"\d{10,25}", b.entity.strip()):
        raise HTTPException(400, "The Entity ID is the long number the DLT portal gave you (digits only).")
    if b.header and not re.fullmatch(r"[A-Za-z]{6}", b.header.strip()):
        raise HTTPException(400, "A sender ID (header) is 6 letters, e.g. URBHLT.")
    v = {"entity": b.entity.strip(), "header": b.header.strip().upper(), "templates": {k[:24]: re.sub(r"\D", "", t)[:25] for k, t in list(b.templates.items())[:20]}}
    _put(db, "dlt", v)
    log(db, a.email, "DLT details saved", v["header"])
    return v

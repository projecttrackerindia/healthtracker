"""Doctors a family adds by hand — the family physician, the cardiologist — next to the ones read from reports."""
from __future__ import annotations

import re

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from .db import get_db
from .models import MyDoctor

r = APIRouter(prefix="/api/v2/my-doctors")
SPECIALTIES = ["Family physician", "General physician", "Cardiologist", "Diabetologist", "Endocrinologist", "Gynaecologist", "Paediatrician",
               "Orthopaedic", "Dermatologist", "ENT", "Ophthalmologist", "Neurologist", "Nephrologist", "Gastroenterologist", "Pulmonologist",
               "Psychiatrist", "Dentist", "Physiotherapist", "Other"]


def _user(request: Request, db: Session):
    from .auth import current_user
    u = current_user(request, db)
    if not u or not u.household_id:
        raise HTTPException(401, "Sign in first")
    return u


class DocIn(BaseModel):
    name: str
    specialty: str = ""
    hospital: str = ""
    phone: str = ""
    regNo: str = ""
    note: str = ""
    memberId: str = ""


def _j(d: MyDoctor) -> dict:
    return {"id": d.id, "name": d.name, "specialty": d.specialty, "hospital": d.hospital, "phone": d.phone, "regNo": d.reg_no, "note": d.note, "memberId": d.member_id}


def _clean(b: DocIn) -> dict:
    name = re.sub(r"\s+", " ", b.name).strip()[:100]
    if len(name) < 3:
        raise HTTPException(400, "Enter the doctor's name.")
    if not re.match(r"(?i)^dr\.?\s", name):
        name = "Dr " + name
    ph = re.sub(r"[^\d+]", "", b.phone)
    if ph:
        if re.fullmatch(r"[6-9]\d{9}", ph):
            ph = "+91" + ph
        elif re.fullmatch(r"0\d{9,11}", ph):
            pass                                  # a landline with STD code
        elif not re.fullmatch(r"\+91[6-9]\d{9}", ph):
            raise HTTPException(400, "Enter a 10-digit mobile or a landline with its STD code.")
    sp = b.specialty.strip()[:80]
    return {"name": name, "specialty": sp, "hospital": b.hospital.strip()[:120], "phone": ph, "reg_no": b.regNo.strip()[:40], "note": b.note.strip()[:200], "member_id": b.memberId[:32]}


@r.get("")
def list_(request: Request, db: Session = Depends(get_db)):
    u = _user(request, db)
    return {"rows": [_j(d) for d in db.scalars(select(MyDoctor).where(MyDoctor.household_id == u.household_id).order_by(MyDoctor.name)).all()], "specialties": SPECIALTIES}


@r.post("")
def add(b: DocIn, request: Request, db: Session = Depends(get_db)):
    u = _user(request, db)
    if len(db.scalars(select(MyDoctor.id).where(MyDoctor.household_id == u.household_id)).all()) >= 40:
        raise HTTPException(400, "Up to 40 doctors.")
    d = MyDoctor(household_id=u.household_id, **_clean(b))
    db.add(d)
    db.flush()
    return _j(d)


@r.put("/{did}")
def edit(did: str, b: DocIn, request: Request, db: Session = Depends(get_db)):
    u = _user(request, db)
    d = db.get(MyDoctor, did)
    if not d or d.household_id != u.household_id:
        raise HTTPException(404)
    for k, v in _clean(b).items():
        setattr(d, k, v)
    return _j(d)


@r.delete("/{did}")
def remove(did: str, request: Request, db: Session = Depends(get_db)):
    u = _user(request, db)
    d = db.get(MyDoctor, did)
    if not d or d.household_id != u.household_id:
        raise HTTPException(404)
    db.delete(d)
    return {"ok": True}

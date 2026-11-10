"""Government health cover: which schemes a family member may qualify for, and how to apply.

There is no public API that lets a private app enrol anyone in PM-JAY or a state scheme: enrolment happens on the
government's own portal, the Ayushman app, a Common Service Centre or an empanelled hospital, with Aadhaar e-KYC.
So this module does the honest part: it asks a few questions, says which schemes look likely and why, lists the
documents, links to the official page and helpline, and lets the family keep the card number in the app.

Rules change. Every scheme carries the date its details were last checked, and the app says "the portal decides".
"""
from __future__ import annotations

import re

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from .db import get_db
from .models import SchemeCard

r = APIRouter(prefix="/api/v2/schemes")
CHECKED = "Nov 2026"

# kind: central | state | job.  rule: function name below.  States use the names the app already stores.
SCHEMES: dict[str, dict] = {
    "pmjay": {"name": "Ayushman Bharat PM-JAY", "kind": "central", "cover": "₹5 lakh a family a year",
              "who": "Families in the SECC 2011 list or the state's added list (many ration-card families are added).",
              "apply": "Check your name at beneficiary.nha.gov.in or the Ayushman app with Aadhaar, then do e-KYC. A Common Service Centre or an empanelled hospital's Arogya Mitra can do it for you.",
              "url": "https://beneficiary.nha.gov.in", "help": "14555",
              "docs": ["Aadhaar (with your mobile linked)", "Ration card", "Mobile phone for the OTP"]},
    "vayvandana": {"name": "Ayushman Vay Vandana (70+)", "kind": "central", "cover": "₹5 lakh a year for the senior, on top of family cover",
                   "who": "Everyone aged 70 or more, whatever the income.",
                   "apply": "Register on the Ayushman app or beneficiary.nha.gov.in with Aadhaar e-KYC. Takes about 10 minutes.",
                   "url": "https://beneficiary.nha.gov.in", "help": "14555",
                   "docs": ["Aadhaar showing age 70+", "Mobile phone for the OTP"]},
    "cghs": {"name": "CGHS", "kind": "job", "cover": "Treatment at CGHS centres and listed hospitals",
             "who": "Central government employees, pensioners and their dependants.",
             "apply": "Apply through your office (serving) or online on the CGHS portal (pensioners).",
             "url": "https://cghs.mohfw.gov.in", "help": "1800-208-8900", "docs": ["Service or PPO details", "Dependants' proof", "Photos"]},
    "echs": {"name": "ECHS", "kind": "job", "cover": "Treatment at ECHS polyclinics and listed hospitals",
             "who": "Ex-servicemen drawing a pension, and their dependants.",
             "apply": "Apply online on the ECHS portal or at your station headquarters.",
             "url": "https://echs.gov.in", "help": "1800-114-115", "docs": ["Discharge book / PPO", "Dependants' proof"]},
    "esic": {"name": "ESIC", "kind": "job", "cover": "Free treatment at ESI dispensaries and hospitals",
             "who": "Workers registered by their employer under ESI (usually earning up to ₹21,000 a month) and family.",
             "apply": "Your employer registers you. Download your e-Pehchan card from the ESIC portal.",
             "url": "https://www.esic.gov.in", "help": "1800-11-2526", "docs": ["Insurance number from your employer", "Aadhaar"]},
    # State schemes. Most now run together with PM-JAY: one card, higher cover.
    "aarogyasri": {"name": "Rajiv Aarogyasri", "kind": "state", "state": "Telangana", "cover": "Up to ₹10 lakh a family a year",
                   "who": "Families with a white ration card (food security card) in Telangana.", "card": True,
                   "apply": "Show the ration card and Aadhaar at an empanelled hospital's Aarogyamithra desk; no separate enrolment.",
                   "url": "https://aarogyasri.telangana.gov.in", "help": "104", "docs": ["White ration card", "Aadhaar"]},
    "ntrvs": {"name": "Dr NTR Vaidya Seva", "kind": "state", "state": "Andhra Pradesh", "cover": "Cashless treatment, family floater",
              "who": "Families with a rice card in Andhra Pradesh.", "card": True,
              "apply": "Show the rice card and Aadhaar at an empanelled hospital; Vaidya Mitra registers you.",
              "url": "https://drntrvaidyaseva.ap.gov.in", "help": "104", "docs": ["Rice card", "Aadhaar"]},
    "cmchis": {"name": "CM Comprehensive Health Insurance (CMCHIS)", "kind": "state", "state": "Tamil Nadu", "cover": "Up to ₹5 lakh a family a year",
               "who": "Tamil Nadu families with a yearly income up to ₹1.2 lakh.", "card": True,
               "apply": "Get an income certificate, then enrol at the district CMCHIS kiosk with the ration card.",
               "url": "https://www.cmchistn.com", "help": "1800-425-3993", "docs": ["Ration card", "Income certificate", "Aadhaar"]},
    "mjpjay": {"name": "Mahatma Jyotirao Phule Jan Arogya Yojana", "kind": "state", "state": "Maharashtra", "cover": "Up to ₹5 lakh a family a year",
               "who": "Maharashtra families with a yellow, orange, white or Antyodaya ration card.", "card": True,
               "apply": "Show the ration card and Aadhaar at an empanelled hospital's Arogyamitra desk.",
               "url": "https://www.jeevandayee.gov.in", "help": "155388", "docs": ["Ration card", "Aadhaar"]},
    "abark": {"name": "Ayushman Bharat – Arogya Karnataka", "kind": "state", "state": "Karnataka", "cover": "₹5 lakh for BPL families; co-pay for others",
              "who": "Karnataka residents; full cover with a BPL (priority household) card.", "card": True,
              "apply": "Get the AB-ArK card at a Karnataka One centre or an empanelled hospital with Aadhaar and ration card.",
              "url": "https://arogya.karnataka.gov.in", "help": "104", "docs": ["Ration card", "Aadhaar"]},
    "kasp": {"name": "Karunya Arogya Suraksha Padhathi (KASP)", "kind": "state", "state": "Kerala", "cover": "₹5 lakh a family a year",
             "who": "Kerala families in the PM-JAY list or earlier RSBY/state lists.", "card": True,
             "apply": "Check eligibility at an empanelled hospital's KASP desk with the ration card and Aadhaar.",
             "url": "https://sha.kerala.gov.in", "help": "14555", "docs": ["Ration card", "Aadhaar"]},
    "bsky": {"name": "Biju Swasthya Kalyan Yojana", "kind": "state", "state": "Odisha", "cover": "₹5 lakh a family (₹10 lakh for women)",
             "who": "Odisha families with a food security (NFSA/SFSS) card.", "card": True,
             "apply": "Use the BSKY card, or the ration card and Aadhaar, at an empanelled hospital.",
             "url": "https://bsky.odisha.gov.in", "help": "104", "docs": ["Ration card", "Aadhaar"]},
    "swasthyasathi": {"name": "Swasthya Sathi", "kind": "state", "state": "West Bengal", "cover": "₹5 lakh a family a year",
                      "who": "West Bengal residents not covered by another government scheme.",
                      "apply": "Apply at a Duare Sarkar camp or on the Swasthya Sathi portal.",
                      "url": "https://swasthyasathi.gov.in", "help": "1800-345-5384", "docs": ["Aadhaar", "Proof of residence in West Bengal"]},
}
STATES = sorted({s["state"] for s in SCHEMES.values() if s.get("state")} | {"Delhi", "Gujarat", "Rajasthan", "Uttar Pradesh", "Bihar", "Madhya Pradesh", "Punjab", "Haryana", "Assam", "Other"})


class CheckIn(BaseModel):
    state: str = ""
    age: int | None = None
    rationCard: str = ""        # "yes" | "no" | "dontknow"
    job: str = ""               # "central" | "exservice" | "esi" | "" (none)
    incomeLow: bool | None = None   # yearly family income under about ₹1.2–2.5 lakh


def _public(k: str) -> dict:
    s = SCHEMES[k]
    return {"id": k, **{x: s.get(x) for x in ("name", "kind", "state", "cover", "who", "apply", "url", "help", "docs")}}


def check(b: CheckIn) -> list[dict]:
    """Likely / maybe for each scheme, with the reason in a sentence. Never "no" — the portal decides."""
    out: list[dict] = []
    card = b.rationCard == "yes"

    def add(k, level, why):
        out.append({**_public(k), "level": level, "why": why})

    if b.age is not None and b.age >= 70:
        add("vayvandana", "likely", "Everyone 70 or older qualifies, whatever the income.")
    if b.job == "central":
        add("cghs", "likely", "Central government staff and pensioners are covered by CGHS.")
    if b.job == "exservice":
        add("echs", "likely", "Pensioned ex-servicemen are covered by ECHS.")
    if b.job == "esi":
        add("esic", "likely", "Workers registered under ESI are covered with their family.")
    if b.job in ("central", "exservice"):
        out.append({"id": "note", "level": "note", "name": "One scheme only",
                    "why": "With CGHS or ECHS you must choose: you can't use PM-JAY as well. The 70+ cover lets you pick either."})
    else:
        st = next((k for k, s in SCHEMES.items() if s.get("state") == b.state), None)
        if st:
            sc = SCHEMES[st]
            if b.state == "West Bengal":
                add(st, "likely", "Open to West Bengal residents without another government scheme.")
            elif sc.get("card") and card:
                add(st, "likely", f"You said you have a ration card; {sc['state']} covers card-holding families.")
            elif b.state == "Tamil Nadu" and b.incomeLow:
                add(st, "likely", "Family income under ₹1.2 lakh a year qualifies.")
            else:
                add(st, "maybe", "Depends on your ration card or income. The hospital desk or portal can confirm in minutes.")
        if card or b.incomeLow:
            add("pmjay", "likely" if card and b.incomeLow else "maybe", "Ration-card and low-income families are often on the list. Check with Aadhaar — it takes a minute.")
        else:
            add("pmjay", "maybe", "Only families on the government list qualify. Checking with Aadhaar takes a minute and costs nothing.")
    order = {"likely": 0, "maybe": 1, "note": 2}
    out.sort(key=lambda x: order.get(x["level"], 3))
    return out


@r.get("")
def catalogue():
    return {"checked": CHECKED, "states": STATES, "schemes": [_public(k) for k in SCHEMES],
            "note": "We can't enrol you ourselves — no government system allows apps to do that. We show where and how, and keep your card here."}


@r.post("/check")
def run_check(b: CheckIn):
    if b.age is not None and not 0 <= b.age <= 120:
        raise HTTPException(400, "Enter an age between 0 and 120.")
    return {"checked": CHECKED, "results": check(b),
            "beware": "Enrolment is always free. Nobody from the government will ask for money or an OTP on a call."}


# ---- cards the family keeps ---------------------------------------------------------------------------------------
def _user(request: Request, db: Session):
    from .auth import current_user
    u = current_user(request, db)
    if not u or not u.household_id:
        raise HTTPException(401, "Sign in first")
    return u


class CardIn(BaseModel):
    scheme: str
    number: str
    memberId: str = ""
    validUntil: str = ""


def _card(c: SchemeCard, full: bool = False) -> dict:
    from .family import decrypt
    d = {"id": c.id, "scheme": c.scheme, "name": SCHEMES.get(c.scheme, {}).get("name", c.scheme), "memberId": c.member_id,
         "last4": c.last4, "validUntil": c.valid_until, "help": SCHEMES.get(c.scheme, {}).get("help", "")}
    if full:
        try:
            d["number"] = (decrypt(c.blob) or {}).get("n", "")
        except Exception:
            d["number"] = ""
    return d


@r.get("/cards")
def cards(request: Request, db: Session = Depends(get_db)):
    u = _user(request, db)
    return {"rows": [_card(c) for c in db.scalars(select(SchemeCard).where(SchemeCard.household_id == u.household_id)).all()]}


@r.post("/cards")
def add_card(b: CardIn, request: Request, db: Session = Depends(get_db)):
    from .family import encrypt
    u = _user(request, db)
    if b.scheme not in SCHEMES:
        raise HTTPException(400, "Choose a scheme from the list.")
    n = re.sub(r"[^A-Za-z0-9]", "", b.number).upper()
    if not 6 <= len(n) <= 24:
        raise HTTPException(400, "Enter the card or beneficiary number as printed (6–24 letters and digits).")
    if re.fullmatch(r"\d{12}", n):
        raise HTTPException(400, "That looks like an Aadhaar number. Enter the scheme card number instead — we don't store Aadhaar.")
    if b.validUntil and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", b.validUntil):
        raise HTTPException(400, "Valid-until must be a date.")
    if len(db.scalars(select(SchemeCard.id).where(SchemeCard.household_id == u.household_id)).all()) >= 20:
        raise HTTPException(400, "Up to 20 cards.")
    c = SchemeCard(household_id=u.household_id, member_id=b.memberId[:32], scheme=b.scheme, blob=encrypt({"n": n}), last4=n[-4:], valid_until=b.validUntil)
    db.add(c)
    db.flush()
    return _card(c)


@r.get("/cards/{cid}")
def show_card(cid: str, request: Request, db: Session = Depends(get_db)):
    u = _user(request, db)
    c = db.get(SchemeCard, cid)
    if not c or c.household_id != u.household_id:
        raise HTTPException(404)
    return _card(c, full=True)


@r.delete("/cards/{cid}")
def del_card(cid: str, request: Request, db: Session = Depends(get_db)):
    u = _user(request, db)
    c = db.get(SchemeCard, cid)
    if not c or c.household_id != u.household_id:
        raise HTTPException(404)
    db.delete(c)
    return {"ok": True}

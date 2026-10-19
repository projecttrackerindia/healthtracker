"""The blood network (/api/v1/donor, /api/v1/blood, /api/partner/blood).

Donors: a family member switches on "blood donor" in Medical ID and consents to be called; we keep their group, first
name, phone, rough location and last donation. Requests: only verified hospitals and blood banks (partner portal) can
raise one — the Transplantation of Human Organs Act and the NBTC guidelines leave no room for a public marketplace,
and organs are never requested here at all (pledges go to NOTTO). When a request is raised, compatible donors within
the radius who are eligible (90/120 days since the last donation) get a push and an in-app notice. A donor offers,
the hospital accepts, the donor shares their live position on the way (every ~20 s, only while travelling), and both
sides see the map and the ETA. Nothing is exchanged until the hospital accepts: then the hospital sees the donor's
name and phone, and the donor sees the ward and contact.
"""
from __future__ import annotations

import math
import time

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from .auth import limit
from .db import get_db
from .inbox import notify
from .models import BloodRequest, Donor, DonorResponse, Household, PartnerUser, Store, User, now
from .partner import me as partner_me
from .partner import my_store
from .routes import household

r = APIRouter(prefix="/api/v1")
pr = APIRouter(prefix="/api/partner/blood")
GROUPS = ("A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-")
# who can give to whom (red cells); platelets/plasma follow their own rules, hospitals know — we notify broadly for those
CAN_GIVE_TO = {"O-": set(GROUPS), "O+": {"O+", "A+", "B+", "AB+"}, "A-": {"A-", "A+", "AB-", "AB+"}, "A+": {"A+", "AB+"}, "B-": {"B-", "B+", "AB-", "AB+"}, "B+": {"B+", "AB+"},
               "AB-": {"AB-", "AB+"}, "AB+": {"AB+"}}
ELIG_DAYS = {"male": 90, "female": 120}
EXPIRES = {"now": 12 * 3600, "24h": 36 * 3600, "72h": 4 * 86400}
REQUESTER_KINDS = ("hospital", "bloodbank")
AVG_KMH = 22.0  # city traffic


def km(lat1, lng1, lat2, lng2) -> float:
    p = math.pi / 180
    a = 0.5 - math.cos((lat2 - lat1) * p) / 2 + math.cos(lat1 * p) * math.cos(lat2 * p) * (1 - math.cos((lng2 - lng1) * p)) / 2
    return 12742 * math.asin(math.sqrt(a))


def compatible(donor_group: str, needed: str, component: str) -> bool:
    if component in ("platelets", "plasma"):
        return True  # plasma compatibility is inverted and platelets are flexible: let the hospital decide
    return needed in CAN_GIVE_TO.get(donor_group, set())


def eligible(d: Donor, today: str) -> bool:
    if not d.last_donation:
        return True
    try:
        last = time.mktime(time.strptime(d.last_donation, "%Y-%m-%d"))
    except ValueError:
        return True
    return (time.time() - last) / 86400 >= ELIG_DAYS.get(d.sex, 90)


# ---- donors (family) --------------------------------------------------------------------------------------------------------
class DonorIn(BaseModel):
    member: str
    name: str = ""
    group: str
    phone: str = ""
    lat: float | None = None
    lng: float | None = None
    city: str = ""
    lastDonation: str = ""
    sex: str = ""
    consent: bool = False


def donor_json(d: Donor) -> dict:
    return {"id": d.id, "member": d.member_id, "group": d.group, "city": d.city, "lastDonation": d.last_donation, "active": d.active, "donations": d.donations, "since": d.consent_t, "located": d.lat is not None}


@r.put("/donor")
def donor_put(body: DonorIn, request: Request, db: Session = Depends(get_db), x_dokko_key: str | None = Header(None)):
    h = household(db, x_dokko_key)
    if not h:
        raise HTTPException(400, "missing household key")
    if body.group not in GROUPS:
        raise HTTPException(400, "Add the blood group on the health card first.")
    if not body.consent:
        raise HTTPException(400, "Consent is needed to be called for blood.")
    limit(request, f"donor:{h.id}", 30, 3600)
    d = db.scalar(select(Donor).where(Donor.household_id == h.id, Donor.member_id == body.member[:32]))
    if not d:
        d = Donor(household_id=h.id, member_id=body.member[:32], group=body.group)
        db.add(d)
    d.group, d.name, d.phone, d.city, d.last_donation, d.sex, d.active, d.updated = body.group, body.name.split(" ")[0][:80], body.phone[:20], body.city[:80], body.lastDonation[:10], body.sex[:8], True, now()
    if body.lat is not None and body.lng is not None:
        d.lat, d.lng = round(body.lat, 4), round(body.lng, 4)  # ~10 m is plenty; we never need the exact door
    db.flush()
    return donor_json(d)


@r.get("/donor")
def donor_list(db: Session = Depends(get_db), x_dokko_key: str | None = Header(None)):
    h = household(db, x_dokko_key, create=False)
    if not h:
        return {"donors": []}
    return {"donors": [donor_json(d) for d in db.scalars(select(Donor).where(Donor.household_id == h.id)).all()]}


@r.delete("/donor/{member}")
def donor_off(member: str, db: Session = Depends(get_db), x_dokko_key: str | None = Header(None)):
    h = household(db, x_dokko_key, create=False)
    d = h and db.scalar(select(Donor).where(Donor.household_id == h.id, Donor.member_id == member[:32]))
    if not d:
        raise HTTPException(404)
    db.delete(d)
    return {"ok": True}


# ---- requests: the family side ---------------------------------------------------------------------------------------------
def req_json(db: Session, q: BloodRequest, me_lat=None, me_lng=None, mine: DonorResponse | None = None, full=False) -> dict:
    s = db.get(Store, q.store_id)
    j = {"id": q.id, "group": q.group, "component": q.component, "units": q.units, "urgency": q.urgency, "patient": q.patient, "hospital": q.hospital or (s.name if s else ""),
         "address": q.address, "lat": q.lat, "lng": q.lng, "status": q.status, "created": q.created, "expires": q.expires, "notes": q.notes, "storeKind": s.kind if s else "",
         "verified": bool(s and s.verified), "responders": db.scalar(select(DonorResponse).where(DonorResponse.request_id == q.id, DonorResponse.status.in_(("accepted", "on_way", "arrived")))) is not None}
    if me_lat is not None and me_lng is not None:
        j["km"] = round(km(me_lat, me_lng, q.lat, q.lng), 1)
    if mine:
        j["mine"] = {"id": mine.id, "status": mine.status, "eta": mine.eta_min, "t": mine.updated}
        if mine.status in ("accepted", "on_way", "arrived", "donated"):
            j["ward"], j["phone"] = q.ward, q.phone  # the contact is revealed once the hospital accepts
    if full:
        j["ward"], j["phone"] = q.ward, q.phone
    return j


@r.get("/blood/requests")
def requests_near(lat: float | None = None, lng: float | None = None, group: str = "", radius: int = 50, db: Session = Depends(get_db), x_dokko_key: str | None = Header(None)):
    """Open requests near the person; donors can respond. Visible to everyone, actionable by donors."""
    h = household(db, x_dokko_key, create=False)
    t = now()
    rows = db.scalars(select(BloodRequest).where(BloodRequest.status == "open", BloodRequest.expires > t).order_by(BloodRequest.created.desc()).limit(300)).all()
    mine = {x.request_id: x for x in db.scalars(select(DonorResponse).where(DonorResponse.household_id == h.id)).all()} if h else {}
    out = []
    for q in rows:
        if lat is not None and lng is not None and km(lat, lng, q.lat, q.lng) > radius:
            continue
        if group and group in GROUPS and not compatible(group, q.group, q.component):
            continue
        out.append(req_json(db, q, lat, lng, mine.get(q.id)))
    out.sort(key=lambda x: (x.get("km", 999), -x["created"]))
    return {"requests": out[:60], "t": t}


@r.get("/blood/{rid}")
def request_one(rid: str, lat: float | None = None, lng: float | None = None, db: Session = Depends(get_db), x_dokko_key: str | None = Header(None)):
    h = household(db, x_dokko_key, create=False)
    q = db.get(BloodRequest, rid)
    if not q:
        raise HTTPException(404)
    mine = h and db.scalar(select(DonorResponse).where(DonorResponse.request_id == rid, DonorResponse.household_id == h.id))
    return req_json(db, q, lat, lng, mine)


class RespondIn(BaseModel):
    member: str
    lat: float | None = None
    lng: float | None = None


@r.post("/blood/{rid}/respond")
def respond(rid: str, body: RespondIn, request: Request, db: Session = Depends(get_db), x_dokko_key: str | None = Header(None)):
    h = household(db, x_dokko_key)
    if not h:
        raise HTTPException(400, "missing household key")
    limit(request, f"bresp:{h.id}", 20, 3600)
    q = db.get(BloodRequest, rid)
    if not q or q.status != "open" or q.expires < now():
        raise HTTPException(404, "This request is closed.")
    d = db.scalar(select(Donor).where(Donor.household_id == h.id, Donor.member_id == body.member[:32], Donor.active == True))  # noqa: E712
    if not d:
        raise HTTPException(400, "Switch on blood donor in Medical ID first (with the blood group).")
    if not compatible(d.group, q.group, q.component):
        raise HTTPException(400, f"{d.group} cannot be given to {q.group} for this component.")
    if not eligible(d, time.strftime("%Y-%m-%d")):
        raise HTTPException(400, "Too soon since the last donation (3 months for men, 4 for women).")
    cur = db.scalar(select(DonorResponse).where(DonorResponse.request_id == rid, DonorResponse.donor_id == d.id))
    if cur and cur.status not in ("withdrawn", "declined"):
        return {"ok": True, "response": cur.status}
    if not cur:
        cur = DonorResponse(request_id=rid, donor_id=d.id, household_id=h.id)
        db.add(cur)
    cur.status, cur.updated = "offered", now()
    if body.lat is not None and body.lng is not None:
        cur.lat, cur.lng, cur.loc_t = body.lat, body.lng, now()
        cur.eta_min = int(km(body.lat, body.lng, q.lat, q.lng) / AVG_KMH * 60) + 5
    db.flush()
    try:
        from .partner import alert_store
        alert_store(db, q.store_id, f"Blood donor offered · {d.group} for request {q.id}", f"{d.name} ({d.group}) has offered to donate for {q.patient or 'the patient'}. Accept them in the partner portal → Blood requests; their phone is shown after you accept.")
    except Exception:
        pass
    return {"ok": True, "response": cur.status, "id": cur.id}


class LocIn(BaseModel):
    lat: float
    lng: float
    status: str = ""   # on_way | arrived


@r.post("/blood/{rid}/location")
def location(rid: str, body: LocIn, db: Session = Depends(get_db), x_dokko_key: str | None = Header(None)):
    h = household(db, x_dokko_key, create=False)
    q = db.get(BloodRequest, rid)
    cur = h and db.scalar(select(DonorResponse).where(DonorResponse.request_id == rid, DonorResponse.household_id == h.id))
    if not q or not cur or cur.status not in ("accepted", "on_way", "arrived"):
        raise HTTPException(400, "Location is shared only after the hospital accepts.")
    cur.lat, cur.lng, cur.loc_t, cur.updated = body.lat, body.lng, now(), now()
    dist = km(body.lat, body.lng, q.lat, q.lng)
    cur.eta_min = max(1, int(dist / AVG_KMH * 60) + 3)
    if body.status in ("on_way", "arrived"):
        cur.status = body.status
    elif dist < 0.15 and cur.status == "on_way":
        cur.status = "arrived"
    return {"ok": True, "status": cur.status, "km": round(dist, 1), "eta": cur.eta_min}


@r.post("/blood/{rid}/withdraw")
def withdraw(rid: str, db: Session = Depends(get_db), x_dokko_key: str | None = Header(None)):
    h = household(db, x_dokko_key, create=False)
    cur = h and db.scalar(select(DonorResponse).where(DonorResponse.request_id == rid, DonorResponse.household_id == h.id))
    if not cur:
        raise HTTPException(404)
    cur.status, cur.updated = "withdrawn", now()
    return {"ok": True}


# ---- requests: hospitals and blood banks -----------------------------------------------------------------------------------
def _requester(db: Session, u: PartnerUser) -> Store:
    s = my_store(db, u)
    if s.kind not in REQUESTER_KINDS and not (u.role == "doctor" and u.verified):
        raise HTTPException(403, "Blood requests can be raised by hospitals, blood banks and verified doctors.")
    if not s.verified:
        raise HTTPException(403, "Your store is awaiting verification; requests open once it is verified.")
    return s


class ReqIn(BaseModel):
    group: str
    component: str = "whole"
    units: int = 1
    urgency: str = "24h"
    patient: str = ""
    ward: str = ""
    phone: str = ""
    notes: str = ""
    radiusKm: int = 25
    lat: float | None = None
    lng: float | None = None


def notify_donors(db: Session, q: BloodRequest) -> int:
    today = time.strftime("%Y-%m-%d")
    n = 0
    seen_h = set()
    for d in db.scalars(select(Donor).where(Donor.active == True)).all():  # noqa: E712
        if d.lat is None or d.household_id in seen_h or not compatible(d.group, q.group, q.component) or not eligible(d, today):
            continue
        dist = km(d.lat, d.lng, q.lat, q.lng)
        if dist > q.radius_km:
            continue
        seen_h.add(d.household_id)
        urg = {"now": "needed now", "24h": "needed within 24 hours", "72h": "needed this week"}.get(q.urgency, "")
        notify(db, d.household_id, "blood", f"{q.group} blood {urg} · {q.hospital}", f"{q.units} unit{'s' if q.units > 1 else ''} of {q.component} blood, {dist:.1f} km away. You match. Open Safety → Medical ID → Donor to respond.",
               {"request": q.id, "group": q.group, "km": round(dist, 1), "hospital": q.hospital}, d.member_id, "/app#page=mid")
        n += 1
    return n


def preq_json(db: Session, q: BloodRequest) -> dict:
    j = req_json(db, q, full=True)
    resp = db.scalars(select(DonorResponse).where(DonorResponse.request_id == q.id).order_by(DonorResponse.created)).all()
    out = []
    for x in resp:
        d = db.get(Donor, x.donor_id)
        revealed = x.status in ("accepted", "on_way", "arrived", "donated")
        out.append({"id": x.id, "status": x.status, "group": d.group if d else "", "name": (d.name if d else "Donor") if revealed else (d.name[:1] + "…" if d and d.name else "Donor"),
                    "phone": d.phone if (d and revealed) else "", "donations": d.donations if d else 0, "lat": x.lat if revealed else None, "lng": x.lng if revealed else None,
                    "km": round(km(x.lat, x.lng, q.lat, q.lng), 1) if x.lat is not None else None, "eta": x.eta_min, "locT": x.loc_t, "offered": x.created, "updated": x.updated})
    j["responses"] = out
    j["notified"] = q.notified
    return j


@pr.post("")
def create(body: ReqIn, request: Request, db: Session = Depends(get_db), u: PartnerUser = Depends(partner_me)):
    s = _requester(db, u)
    limit(request, f"breq:{s.id}", 20, 3600)
    if body.group not in GROUPS:
        raise HTTPException(400, "blood group")
    if body.component not in ("whole", "platelets", "plasma", "rbc"):
        raise HTTPException(400, "component")
    urgency = body.urgency if body.urgency in EXPIRES else "24h"
    q = BloodRequest(store_id=s.id, created_by=u.id, patient=body.patient.strip()[:40], group=body.group, component=body.component, units=max(1, min(20, body.units)), urgency=urgency,
                     lat=body.lat if body.lat is not None else s.lat, lng=body.lng if body.lng is not None else s.lng, hospital=s.name, address=", ".join(x for x in (s.address, s.area, s.city) if x),
                     ward=body.ward.strip()[:80], phone=(body.phone or s.phone or "").strip()[:20], notes=body.notes.strip()[:300], radius_km=max(5, min(100, body.radiusKm)), expires=now() + EXPIRES[urgency])
    db.add(q)
    db.flush()
    q.notified = notify_donors(db, q)
    return preq_json(db, q)


@pr.get("")
def mine(status: str = "open", db: Session = Depends(get_db), u: PartnerUser = Depends(partner_me)):
    s = my_store(db, u)
    qq = select(BloodRequest).where(BloodRequest.store_id == s.id).order_by(BloodRequest.created.desc())
    if status != "all":
        qq = qq.where(BloodRequest.status == status)
    rows = db.scalars(qq.limit(100)).all()
    t = now()
    for q in rows:
        if q.status == "open" and q.expires < t:
            q.status = "expired"
    return {"requests": [preq_json(db, q) for q in rows], "can": s.kind in REQUESTER_KINDS or (u.role == "doctor" and u.verified), "store": {"lat": s.lat, "lng": s.lng, "name": s.name, "verified": s.verified}}


@pr.get("/{rid}")
def one(rid: str, db: Session = Depends(get_db), u: PartnerUser = Depends(partner_me)):
    q = db.get(BloodRequest, rid)
    if not q or q.store_id != u.store_id:
        raise HTTPException(404)
    return preq_json(db, q)


class StatusIn(BaseModel):
    status: str   # fulfilled | closed


@pr.post("/{rid}/status")
def set_status(rid: str, body: StatusIn, db: Session = Depends(get_db), u: PartnerUser = Depends(partner_me)):
    q = db.get(BloodRequest, rid)
    if not q or q.store_id != u.store_id:
        raise HTTPException(404)
    if body.status not in ("fulfilled", "closed"):
        raise HTTPException(400)
    q.status, q.updated = body.status, now()
    for x in db.scalars(select(DonorResponse).where(DonorResponse.request_id == rid, DonorResponse.status.in_(("offered", "accepted", "on_way")))).all():
        if body.status == "fulfilled" and x.status in ("accepted", "on_way"):
            continue
        notify(db, x.household_id, "blood", f"Blood request at {q.hospital} is {body.status}", "Thank you for offering. No need to travel now.", {"request": q.id, "status": body.status}, "", "/app#page=mid")
        x.status = "declined" if x.status == "offered" else x.status
    return preq_json(db, q)


class RespAct(BaseModel):
    action: str   # accept | decline | donated


@pr.post("/{rid}/responses/{xid}")
def act(rid: str, xid: str, body: RespAct, db: Session = Depends(get_db), u: PartnerUser = Depends(partner_me)):
    q = db.get(BloodRequest, rid)
    x = db.get(DonorResponse, xid)
    if not q or q.store_id != u.store_id or not x or x.request_id != rid:
        raise HTTPException(404)
    d = db.get(Donor, x.donor_id)
    if body.action == "accept":
        x.status = "accepted"
        notify(db, x.household_id, "blood", f"{q.hospital} accepted your offer — thank you", f"Go to {q.ward or 'the blood bank'}; call {q.phone or 'the hospital'} on arrival. Tap Start journey in Medical ID → Donor so they can see you coming.",
               {"request": q.id, "accepted": True}, d.member_id if d else "", "/app#page=mid")
    elif body.action == "decline":
        x.status = "declined"
        notify(db, x.household_id, "blood", f"{q.hospital}: not needed this time", "Thank you for offering; another donor was closer or the need was met.", {"request": q.id}, d.member_id if d else "", "/app#page=mid")
    elif body.action == "donated":
        x.status = "donated"
        if d:
            d.donations = (d.donations or 0) + 1
            d.last_donation = time.strftime("%Y-%m-%d")
        notify(db, x.household_id, "blood", "Thank you for donating 🩸", f"{q.hospital} recorded your donation today. Your next eligible date is updated on the Medical ID.", {"request": q.id, "donated": True}, d.member_id if d else "", "/app#page=mid")
    else:
        raise HTTPException(400)
    x.updated = now()
    return preq_json(db, q)

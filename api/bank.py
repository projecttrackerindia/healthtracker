"""Board 12 · a blood bank's Requests: hospitals ask for units, the bank answers with what it can give, packs and
sends; stock by group at a glance; donors near the bank on standby for the group that is short.

Units leave the shelf count when the bank confirms them, so the tiles stay true without a second step. Donors are
shown by first name and initial, distance and when they last gave; their numbers stay hidden until they say yes to
a call (that is the donor flow in api/blood.py, reused by "Ask N donors")."""
from __future__ import annotations

import time

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from .blood import GROUPS, compatible, eligible, km
from .db import get_db
from .models import BloodStock, Donor, PartnerUser, Store, UnitRequest, now
from .partner import me as partner_me
from .partner import my_store

pr = APIRouter(prefix="/api/partner/bank")
REPLY_MIN = {True: 60, False: 6 * 60}     # urgent: an hour to answer; otherwise six


def ur_json(db: Session, q: UnitRequest, side: str) -> dict:
    other = db.get(Store, q.from_store if side == "bank" else q.to_store)
    return {"id": q.id, "group": q.group, "component": q.component, "units": q.units, "given": q.given, "reason": q.reason,
            "needBy": q.need_by, "urgent": q.urgent, "patient": q.patient, "doctor": q.doctor, "status": q.status,
            "replyBy": q.reply_by, "created": q.created, "updated": q.updated,
            "from" if side == "bank" else "to": {"id": other.id, "name": other.name, "area": other.area or "", "phone": other.phone or ""} if other else None,
            "km": round(km(other.lat, other.lng, *_ll(db, q.to_store if side == "bank" else q.from_store)), 1) if other and other.lat else None}


def _ll(db: Session, sid: str) -> tuple[float, float]:
    s = db.get(Store, sid)
    return (s.lat or 0, s.lng or 0) if s else (0, 0)


def take_from_shelf(st: BloodStock, n: int) -> None:
    """Units leave the shelf oldest-date first, so the bags nearest their date are issued before they are wasted.
    With dated bags the count is their sum; without dates it is a plain number."""
    if st.batches:
        left, out = n, []
        for b in sorted(st.batches, key=lambda y: y.get("exp", "9999")):
            k = min(left, int(b.get("n") or 0))
            left -= k
            if int(b.get("n") or 0) - k > 0:
                out.append({**b, "n": int(b["n"]) - k})
        st.batches = out
        st.units = sum(int(b["n"]) for b in out)
    else:
        st.units -= n
    st.updated = now()


def _bank(db: Session, u: PartnerUser) -> Store:
    s = my_store(db, u)
    if s.kind != "bloodbank":
        raise HTTPException(403, "This is for blood banks.")
    return s


@pr.get("/banks")
def banks(group: str = "", db: Session = Depends(get_db, scope="function"), u: PartnerUser = Depends(partner_me)):
    """Verified blood banks for a hospital to ask, nearest first, with whether they have the group on the shelf."""
    me_ = my_store(db, u)
    out = []
    for b in db.scalars(select(Store).where(Store.kind == "bloodbank", Store.verified == True, Store.active == True)).all():  # noqa: E712
        st = db.scalar(select(BloodStock).where(BloodStock.store_id == b.id, BloodStock.group == group, BloodStock.component == "whole")) if group else None
        out.append({"id": b.id, "name": b.name, "area": b.area or "", "km": round(km(me_.lat or 0, me_.lng or 0, b.lat or 0, b.lng or 0), 1) if b.lat else None,
                    "has": (st.units > 0) if st else None})
    out.sort(key=lambda x: (x["km"] is None, x["km"] or 0))
    return {"banks": out[:20]}


class AskIn(BaseModel):
    bank: str
    group: str
    component: str = "whole"
    units: int = 1
    reason: str = ""
    needBy: str = ""
    urgent: bool = False
    patient: str = ""


@pr.post("/requests")
def ask(body: AskIn, db: Session = Depends(get_db, scope="function"), u: PartnerUser = Depends(partner_me)):
    s = my_store(db, u)
    if s.kind != "hospital":
        raise HTTPException(403, "Hospitals ask a blood bank for units.")
    if not s.verified:
        raise HTTPException(403, "Your hospital is awaiting verification.")
    b = db.get(Store, body.bank)
    if not b or b.kind != "bloodbank" or not b.verified:
        raise HTTPException(404, "blood bank not found")
    if body.group not in GROUPS or body.component not in ("whole", "platelets", "plasma", "rbc"):
        raise HTTPException(400, "Choose the group and component.")
    if not 1 <= body.units <= 20:
        raise HTTPException(400, "1 to 20 units.")
    q = UnitRequest(from_store=s.id, to_store=b.id, created_by=u.id, group=body.group, component=body.component, units=body.units,
                    reason=body.reason.strip()[:80], need_by=body.needBy.strip()[:40], urgent=bool(body.urgent),
                    patient=body.patient.strip()[:40], doctor=(u.name if u.role == "doctor" else "")[:60],
                    reply_by=now() + REPLY_MIN[bool(body.urgent)] * 60)
    db.add(q)
    db.flush()
    return ur_json(db, q, "hospital")


@pr.get("/requests")
def requests(db: Session = Depends(get_db, scope="function"), u: PartnerUser = Depends(partner_me)):
    s = my_store(db, u)
    side = "bank" if s.kind == "bloodbank" else "hospital"
    col = UnitRequest.to_store if side == "bank" else UnitRequest.from_store
    rows = db.scalars(select(UnitRequest).where(col == s.id, UnitRequest.created > now() - 7 * 86400).order_by(UnitRequest.created.desc()).limit(100)).all()
    # urgent and unanswered first, then the rest newest first
    rows.sort(key=lambda q: (q.status != "new", not q.urgent, -q.created))
    return {"side": side, "requests": [ur_json(db, q, side) for q in rows]}


class AnswerIn(BaseModel):
    units: int


@pr.post("/requests/{rid}/answer")
def answer(rid: str, body: AnswerIn, db: Session = Depends(get_db, scope="function"), u: PartnerUser = Depends(partner_me)):
    """The bank gives what it can: all of it, part of it, or none. The shelf count drops by what is given."""
    s = _bank(db, u)
    q = db.get(UnitRequest, rid)
    if not q or q.to_store != s.id:
        raise HTTPException(404)
    if q.status != "new":
        raise HTTPException(409, "Already answered.")
    n = max(0, min(int(body.units), q.units))
    if n:
        st = db.scalar(select(BloodStock).where(BloodStock.store_id == s.id, BloodStock.group == q.group, BloodStock.component == q.component))
        if not st or st.units < n:
            raise HTTPException(409, f"Only {st.units if st else 0} unit{'s' if not st or st.units != 1 else ''} of {q.group} on the shelf.")
        take_from_shelf(st, n)
    q.given, q.status, q.updated = n, ("confirmed" if n == q.units else "partial" if n else "declined"), now()
    return ur_json(db, q, "bank")


class MoveIn(BaseModel):
    to: str


@pr.post("/requests/{rid}/status")
def move(rid: str, body: MoveIn, db: Session = Depends(get_db, scope="function"), u: PartnerUser = Depends(partner_me)):
    s = my_store(db, u)
    q = db.get(UnitRequest, rid)
    if not q or s.id not in (q.to_store, q.from_store):
        raise HTTPException(404)
    nxt = {"confirmed": ("packed",), "partial": ("packed",), "packed": ("sent",)}
    if s.id == q.from_store:
        if body.to != "cancelled" or q.status not in ("new",):
            raise HTTPException(409, "A hospital can cancel only before the bank answers.")
    elif body.to not in nxt.get(q.status, ()):
        raise HTTPException(409, f"From {q.status} the next step is {', '.join(nxt.get(q.status, ())) or 'nothing'}.")
    q.status, q.updated = body.to, now()
    return ur_json(db, q, "bank" if s.id == q.to_store else "hospital")


@pr.get("/donors")
def donors(group: str, db: Session = Depends(get_db, scope="function"), u: PartnerUser = Depends(partner_me)):
    """Opted-in donors near the bank who can give for this group today. First name and initial only."""
    s = _bank(db, u)
    if group not in GROUPS:
        raise HTTPException(400, "group")
    today = time.strftime("%Y-%m-%d")
    out, seen = [], set()
    for d in db.scalars(select(Donor).where(Donor.active == True)).all():  # noqa: E712
        if d.lat is None or d.household_id in seen or not compatible(d.group, group, "whole") or not eligible(d, today):
            continue
        dist = km(d.lat, d.lng, s.lat or 0, s.lng or 0)
        if dist > 15:
            continue
        seen.add(d.household_id)
        parts = (d.name or "Donor").split()
        out.append({"id": d.id, "name": parts[0] + (" " + parts[1][0] if len(parts) > 1 else ""), "group": d.group, "km": round(dist, 1), "donations": d.donations or 0,
                    "lastGave": d.last_donation[:7] if d.last_donation else ""})
    out.sort(key=lambda x: x["km"])
    return {"group": group, "donors": out[:12], "total": len(out)}



# ---- donation camps (blood bank) and booking a slot (family) ---------------------------------------------------------------
from fastapi import APIRouter as _AR  # noqa: E402

from .auth import need_user  # noqa: E402
from .inbox import notify  # noqa: E402
from .models import BloodCamp, User  # noqa: E402

CAMP_KM = 15
fr = _AR(prefix="/api/v2/camps")


def camp_json(c: BloodCamp, store_name: str = "", mine: bool = False, dist: float | None = None) -> dict:
    return {"id": c.id, "day": c.day, "start": c.start, "end": c.end, "place": c.place, "address": c.address, "lat": c.lat, "lng": c.lng,
            "slots": c.slots, "booked": len(c.booked or []), "left": max(0, c.slots - len(c.booked or [])), "notified": c.notified,
            "cancelled": c.cancelled, "bank": store_name, "mine": mine, "km": round(dist, 1) if dist is not None else None}


class CampIn(BaseModel):
    day: str
    start: str = "09:00"
    end: str = "14:00"
    place: str
    address: str = ""
    slots: int = 40


@pr.get("/camps")
def bank_camps(db: Session = Depends(get_db, scope="function"), u: PartnerUser = Depends(partner_me)):
    s = _bank(db, u)
    today = time.strftime("%Y-%m-%d")
    rows = db.scalars(select(BloodCamp).where(BloodCamp.store_id == s.id, BloodCamp.day >= today).order_by(BloodCamp.day)).all()
    return {"camps": [camp_json(c, s.name) for c in rows]}


@pr.post("/camps")
def bank_camp_new(body: CampIn, db: Session = Depends(get_db, scope="function"), u: PartnerUser = Depends(partner_me)):
    import re as _re
    s = _bank(db, u)
    if not _re.fullmatch(r"\d{4}-\d{2}-\d{2}", body.day) or body.day < time.strftime("%Y-%m-%d"):
        raise HTTPException(400, "Choose a date from today on.")
    if not body.place.strip():
        raise HTTPException(400, "Where is the camp?")
    lat, lng = s.lat, s.lng
    c = BloodCamp(store_id=s.id, day=body.day, start=body.start[:5], end=body.end[:5], place=body.place.strip()[:120],
                  address=(body.address.strip() or ", ".join(x for x in (s.address, s.area, s.city) if x))[:240], lat=lat, lng=lng,
                  slots=max(5, min(500, int(body.slots))))
    db.add(c)
    db.flush()
    n, seen = 0, set()
    when = time.strftime("%a %d %b", time.strptime(c.day, "%Y-%m-%d"))
    for d in db.scalars(select(Donor).where(Donor.active == True)).all():  # noqa: E712
        if d.lat is None or d.household_id in seen or lat is None or km(d.lat, d.lng, lat, lng) > CAMP_KM:
            continue
        seen.add(d.household_id)
        notify(db, d.household_id, "blood", f"Blood donation camp · {when}",
               f"{s.name} at {c.place}, {c.start}–{c.end}. Book a slot if you'd like to give; no pressure if you can't.",
               {"camp": c.id}, d.member_id, "/app#page=mid")
        n += 1
    c.notified = n
    return camp_json(c, s.name)


@pr.post("/camps/{cid}/cancel")
def bank_camp_cancel(cid: str, db: Session = Depends(get_db, scope="function"), u: PartnerUser = Depends(partner_me)):
    s = _bank(db, u)
    c = db.get(BloodCamp, cid)
    if not c or c.store_id != s.id:
        raise HTTPException(404)
    c.cancelled = True
    for b in c.booked or []:
        d = db.get(Donor, b.get("donor"))
        if d:
            notify(db, d.household_id, "blood", "Blood donation camp cancelled", f"{s.name} cancelled the camp on {c.day}. Thank you for offering.", {"camp": c.id}, d.member_id, "/app")
    return camp_json(c, s.name)


def _my_donors(db: Session, u: User) -> list:
    return db.scalars(select(Donor).where(Donor.household_id == (u.household_id or "-"), Donor.active == True)).all()  # noqa: E712


@fr.get("")
def family_camps(db: Session = Depends(get_db, scope="function"), u: User = Depends(need_user)):
    ds = _my_donors(db, u)
    if not ds:
        return {"camps": [], "donor": False}
    today = time.strftime("%Y-%m-%d")
    out = []
    for c in db.scalars(select(BloodCamp).where(BloodCamp.day >= today, BloodCamp.cancelled == False).order_by(BloodCamp.day).limit(100)).all():  # noqa: E712
        near = [km(d.lat, d.lng, c.lat, c.lng) for d in ds if d.lat is not None and c.lat is not None]
        if not near or min(near) > CAMP_KM:
            continue
        st = db.get(Store, c.store_id)
        mine = any(b.get("donor") in {d.id for d in ds} for b in c.booked or [])
        out.append(camp_json(c, st.name if st else "", mine, min(near)))
    return {"camps": out[:6], "donor": True}


@fr.post("/{cid}/book")
def family_book(cid: str, db: Session = Depends(get_db, scope="function"), u: User = Depends(need_user)):
    c = db.get(BloodCamp, cid)
    ds = _my_donors(db, u)
    if not c or c.cancelled or not ds:
        raise HTTPException(404)
    ids = {d.id for d in ds}
    if any(b.get("donor") in ids for b in c.booked or []):
        return camp_json(c, mine=True)
    if len(c.booked or []) >= c.slots:
        raise HTTPException(409, "This camp is full. Thank you for wanting to give.")
    c.booked = (c.booked or []) + [{"donor": ds[0].id, "t": now()}]
    return camp_json(c, mine=True)


@fr.post("/{cid}/unbook")
def family_unbook(cid: str, db: Session = Depends(get_db, scope="function"), u: User = Depends(need_user)):
    c = db.get(BloodCamp, cid)
    if not c:
        raise HTTPException(404)
    ids = {d.id for d in _my_donors(db, u)}
    c.booked = [b for b in c.booked or [] if b.get("donor") not in ids]
    return camp_json(c)



# ---- the blood bank's own Today, processing charges and earnings ------------------------------------------------------------
COMPONENTS = {"whole": "Whole blood", "prbc": "Red cells", "platelets": "Platelets", "plasma": "Plasma"}
ISSUED = ("confirmed", "partial", "packed", "sent")


class FeesIn(BaseModel):
    fees: dict[str, int]


@pr.get("/fees")
def bank_fees(db: Session = Depends(get_db, scope="function"), u: PartnerUser = Depends(partner_me)):
    s = _bank(db, u)
    return {"fees": (s.profile or {}).get("bloodFees", {}), "components": COMPONENTS}


@pr.put("/fees")
def bank_fees_set(body: FeesIn, db: Session = Depends(get_db, scope="function"), u: PartnerUser = Depends(partner_me)):
    s = _bank(db, u)
    if u.role not in ("owner", "manager"):
        raise HTTPException(403, "Only the owner or a manager can change charges.")
    fees = {k: max(0, min(20000, int(v))) for k, v in body.fees.items() if k in COMPONENTS}
    s.profile = {**(s.profile or {}), "bloodFees": fees}
    return {"fees": fees, "components": COMPONENTS}


@pr.get("/earnings")
def bank_earnings(db: Session = Depends(get_db, scope="function"), u: PartnerUser = Depends(partner_me)):
    """Units issued, month by month, and the processing charges they carry at the bank's own rates.
    Hospitals pay the bank directly; this is the bank's record, not a payout from Urban Health."""
    s = _bank(db, u)
    if u.role not in ("owner", "manager"):
        raise HTTPException(403, "Earnings are for the owner or a manager.")
    fees = (s.profile or {}).get("bloodFees", {})
    rows = db.scalars(select(UnitRequest).where(UnitRequest.to_store == s.id, UnitRequest.status.in_(ISSUED), UnitRequest.given > 0)
                      .order_by(UnitRequest.updated.desc()).limit(3000)).all()
    months: dict[str, dict] = {}
    for q in rows:
        m = time.strftime("%Y-%m", time.localtime(q.updated or q.created))
        x = months.setdefault(m, {"month": m, "units": 0, "amount": 0, "requests": 0, "byHospital": {}, "byComponent": {}})
        amt = q.given * int(fees.get(q.component, 0) or 0)
        x["units"] += q.given
        x["amount"] += amt
        x["requests"] += 1
        h = db.get(Store, q.from_store)
        hn = h.name if h else "Hospital"
        bh = x["byHospital"].setdefault(hn, {"name": hn, "units": 0, "amount": 0})
        bh["units"] += q.given
        bh["amount"] += amt
        x["byComponent"][q.component] = x["byComponent"].get(q.component, 0) + q.given
    out = sorted(months.values(), key=lambda x: x["month"], reverse=True)[:12]
    for x in out:
        x["byHospital"] = sorted(x["byHospital"].values(), key=lambda y: -y["units"])
    return {"months": out, "fees": fees, "components": COMPONENTS, "feesSet": any(int(v or 0) > 0 for v in fees.values())}


@pr.get("/today")
def bank_today(db: Session = Depends(get_db, scope="function"), u: PartnerUser = Depends(partner_me)):
    s = _bank(db, u)
    t0 = int(time.mktime(time.strptime(time.strftime("%Y-%m-%d"), "%Y-%m-%d")))
    reqs = db.scalars(select(UnitRequest).where(UnitRequest.to_store == s.id, UnitRequest.created > now() - 7 * 86400)).all()
    waiting = [q for q in reqs if q.status == "new"]
    to_pack = [q for q in reqs if q.status in ("confirmed", "partial")]
    packed = [q for q in reqs if q.status == "packed"]
    issued_today = sum(q.given for q in reqs if q.status in ISSUED and (q.updated or 0) >= t0)
    stock = db.scalars(select(BloodStock).where(BloodStock.store_id == s.id)).all()
    low = sorted([{"group": x.group, "component": x.component, "units": x.units} for x in stock if x.component == "whole" and x.units <= 3], key=lambda y: y["units"])
    donors = db.scalars(select(Donor).where(Donor.active == True)).all()  # noqa: E712
    near = sum(1 for d in donors if d.lat is not None and s.lat is not None and km(d.lat, d.lng, s.lat, s.lng) <= 15)
    camp = db.scalar(select(BloodCamp).where(BloodCamp.store_id == s.id, BloodCamp.cancelled == False, BloodCamp.day >= time.strftime("%Y-%m-%d")).order_by(BloodCamp.day))  # noqa: E712
    return {"waiting": [ur_json(db, q, "bank") for q in sorted(waiting, key=lambda q: (not q.urgent, q.created))][:5],
            "counts": {"waiting": len(waiting), "toPack": len(to_pack), "packed": len(packed), "issuedToday": issued_today, "donorsNear": near},
            "low": low, "camp": camp_json(camp, s.name) if camp else None,
            "units": sum(x.units for x in stock if x.component == "whole")}

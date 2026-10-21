"""The technician's side of a lab booking: today's jobs, setting off, arriving, collecting.

A booking used to go straight from "confirmed" to "collected" with nobody attached to it, which is why the
family's old status line said "Phlebotomist assigned" when no phlebotomist had been. The lab now assigns a
named person, and that person's phone drives the rest of the job.

The screens this serves are built for someone between houses on a scooter: four of them, big targets, nothing
that needs two hands or a good connection. Everything here is therefore small, idempotent where it can be, and
safe to retry — a tap that times out and is tapped again must not break the job.
"""
from __future__ import annotations

import time

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.db import get_db
from api.inbox import notify
from api.models import Order, PartnerUser, Store, TrackPing, now
from api.partner import me, my_store

r = APIRouter(prefix="/api/partner/tech")

# While the agent is travelling. Outside this window nothing is written and nothing is served.
LIVE_STATES = ("en_route", "arrived")
TRAIL_KEEP = 24 * 3600          # the trail is swept this long after the job is done
PING_MAX_AGE = 300              # a position older than this is not "live", it is history


def _tech(u: PartnerUser = Depends(me)) -> PartnerUser:
    """Only a technician's own sign-in reaches these endpoints. A lab owner uses the console."""
    if u.role not in ("tech", "owner"):
        raise HTTPException(403, "This is the technician app.")
    if u.must_change:
        # The lab handed this password across a counter and it is written on a slip somewhere. Behind here are
        # families' addresses and phone numbers, so the slip stops being a way in before the addresses appear.
        raise HTTPException(403, "Choose your own password before you start.")
    return u


def _job(db: Session, u: PartnerUser, oid: str) -> Order:
    o = db.get(Order, oid)
    if not o or o.store_id != u.store_id:
        raise HTTPException(404, "job not found")
    if u.role == "tech" and o.agent_id != u.id:
        raise HTTPException(403, "This job is assigned to someone else.")
    return o


def job_json(db: Session, o: Order) -> dict:
    """What the technician's screen needs, and nothing else about the family."""
    a = o.addr or {}
    return {
        "id": o.id, "status": o.status, "slot": o.slot, "member": o.member,
        "tests": [i.get("name") or i.get("code") for i in (o.items or [])],
        "address": o.address or ", ".join(x for x in [a.get("line1"), a.get("area"), a.get("city")] if x),
        "landmark": a.get("landmark", ""), "pin": a.get("pin", ""),
        "lat": a.get("lat"), "lng": a.get("lng"),
        "phone": a.get("phone", ""),          # so they can call the family from the doorstep
        "startedAt": o.started_at, "arrivedAt": o.arrived_at, "doneAt": o.done_at,
    }


@r.get("/jobs")
def jobs(db: Session = Depends(get_db), u: PartnerUser = Depends(_tech)):
    """Today's work. Open jobs first, because that is what the person is looking for."""
    q = select(Order).where(Order.store_id == u.store_id, Order.kind == "lab",
                            Order.status.in_(("assigned", "en_route", "arrived")))
    if u.role == "tech":
        q = q.where(Order.agent_id == u.id)
    rows = db.scalars(q.order_by(Order.created).limit(50)).all()
    # The job in hand stays at the top. A list that reorders itself the moment somebody taps Start is the kind
    # of thing that makes a person on a scooter open the wrong job.
    rank = {"en_route": 0, "arrived": 0, "assigned": 1}
    rows.sort(key=lambda o: (rank.get(o.status, 2), o.slot or "", o.created or 0))
    return {"jobs": [job_json(db, o) for o in rows]}


class Move(BaseModel):
    note: str = ""


def _advance(db: Session, o: Order, to: str, u: PartnerUser, family: str) -> dict:
    """One place where a technician moves a job, so the timeline, the stamps and the family notice cannot
    drift apart. Idempotent: tapping twice is a tap, not an error."""
    from api.partner import LABEL, NEXT_LAB

    if o.status == to:
        return job_json(db, o)
    if to not in NEXT_LAB.get(o.status, []):
        raise HTTPException(400, f"Cannot go from '{LABEL.get(o.status, o.status)}' to '{LABEL.get(to, to)}'.")
    o.status = to
    t = now()
    if to == "en_route":
        o.started_at = t
    elif to == "arrived":
        o.arrived_at = t
    elif to == "collected":
        o.done_at = t
    o.timeline = (o.timeline or []) + [{"s": to, "t": t, "by": u.email or u.phone, "role": "tech"}]
    s = db.get(Store, o.store_id)
    notify(db, o.household_id, "order", f"{s.name if s else 'Lab'}: {LABEL.get(to, to)}", family,
           {"order": o.id, "status": to, "kind": "lab", "track": to in LIVE_STATES}, o.member_id or "", "/app")
    return job_json(db, o)


@r.post("/jobs/{oid}/start")
def start(oid: str, body: Move, db: Session = Depends(get_db), u: PartnerUser = Depends(_tech)):
    """Setting off. This is what turns the family's live map on, so it is also the moment the technician's
    position starts being shared — and they are told so on this screen, not in terms nobody reads."""
    o = _job(db, u, oid)
    return _advance(db, o, "en_route", u, "Your technician is on the way. Track them in the app.")


@r.post("/jobs/{oid}/arrived")
def arrived(oid: str, body: Move, db: Session = Depends(get_db), u: PartnerUser = Depends(_tech)):
    o = _job(db, u, oid)
    return _advance(db, o, "arrived", u, "Your technician has arrived.")


@r.post("/jobs/{oid}/collected")
def collected(oid: str, body: Move, db: Session = Depends(get_db), u: PartnerUser = Depends(_tech)):
    """Sample taken. The trail stops here and the report clock starts."""
    o = _job(db, u, oid)
    out = _advance(db, o, "collected", u, "Sample collected. Your report will arrive in the app.")
    return out


class Ping(BaseModel):
    lat: float
    lng: float
    accuracy: float = 0
    heading: float | None = None


@r.post("/jobs/{oid}/ping")
def ping(oid: str, body: Ping, db: Session = Depends(get_db), u: PartnerUser = Depends(_tech)):
    """Where the technician is. Accepted only while they are actually travelling — a job that has not started
    or is already collected writes nothing, so a phone left running cannot keep broadcasting someone."""
    o = _job(db, u, oid)
    if o.status not in LIVE_STATES:
        return {"ok": True, "tracking": False}
    if not (-90 <= body.lat <= 90 and -180 <= body.lng <= 180):
        raise HTTPException(400, "bad position")
    db.add(TrackPing(order_id=o.id, lat=body.lat, lng=body.lng, accuracy=body.accuracy, heading=body.heading, at=now()))
    db.query(TrackPing).filter(TrackPing.at < int(time.time()) - TRAIL_KEEP).delete()
    return {"ok": True, "tracking": True}


def track_for_family(db: Session, o: Order) -> dict:
    """What the family's map gets. Each shape below is true; none of them is a stationary pin pretending to be
    live, which reads as broken and is worse than an honest gap."""
    if o.status not in LIVE_STATES:
        return {"live": False, "state": o.status}
    rows = db.scalars(select(TrackPing).where(TrackPing.order_id == o.id)
                      .order_by(TrackPing.id.desc()).limit(2)).all()
    if not rows:
        return {"live": False, "state": o.status, "why": "not sharing yet"}
    last = rows[0]
    age = int(time.time()) - last.at
    pts = [{"lat": x.lat, "lng": x.lng, "at": x.at} for x in reversed(rows)]
    return {"live": age < PING_MAX_AGE, "state": o.status, "ageS": age, "points": pts,
            "lat": last.lat, "lng": last.lng, "heading": last.heading}

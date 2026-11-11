"""Medicine orders without stock of our own: offer the order to the nearest pharmacy, move on if it does not answer,
and hand it to the Urban Health desk when nobody does.

  placed ──(store accepts = "checking")──▶ packing ──▶ out ──▶ delivered
     │ 3 min, no answer: next nearest pharmacy (up to 3 stores)
     └ still nobody: "unclaimed" — the admin desk phones shops and assigns one, or the store accepts but has no rider
       and Urban Health picks the sealed, billed bag up ("courier = uh"). We never sell or stock medicine ourselves.
"""
from __future__ import annotations

import threading
from contextlib import contextmanager
import time

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from .admin import me as admin_me, log
from .db import get_db, session
from .booking import km
from .models import Admin, Order, PartnerUser, Store
from .models import now

OFFER_S = 180          # each pharmacy gets three minutes
MAX_STORES = 3         # then the desk takes over
r = APIRouter(prefix="/api/admin/dispatch")


def _here(o: Order):
    a = o.addr or {}
    return (a.get("lat"), a.get("lng")) if a.get("lat") else (None, None)


def candidates(db: Session, o: Order, skip: set[str]) -> list[tuple[float, Store]]:
    from .booking import live, serves
    lat, lng = _here(o)
    pin = (o.addr or {}).get("pin", "")
    out = []
    for s in live(db, "pharmacy"):
        if s.id in skip or not s.delivery:
            continue
        if lat and s.lat is not None:
            d = km((lat, lng), (s.lat, s.lng))
        else:
            d = 99.0
        if serves(s, pin, lat, lng) or d <= 6:
            out.append((round(d, 1), s))
    return sorted(out, key=lambda x: x[0])


def family_line(o: Order, s: Store) -> tuple[str, str] | None:
    """The words on the family's lock screen for each step — short, specific, never alarming."""
    if o.kind != "medicine":
        return None
    eta = f" · arriving in about {max(5, round((o.eta or 0) / 60))} min" if o.eta else ""
    return {
        "checking": (f"{s.name} accepted your order", "A registered pharmacist is checking your prescription."),
        "packing": ("Packing your medicines", f"{s.name} is packing your order."),
        "out": (f"Out for delivery{eta}", f"Keep your doorstep code {o.door_code} ready." if o.door_code else "Your medicines are on the way."),
        "delivered": ("Delivered", "Take care. Rate the pharmacy in Orders."),
    }.get(o.status)


def _notify_store(db: Session, o: Order, s: Store) -> None:
    from .booking import after_order
    code = o.door_code
    after_order(db, o, s)
    o.door_code = code or o.door_code


def tick(db: Session) -> int:
    from .inbox import notify
    moved = 0
    for o in db.scalars(select(Order).where(Order.kind == "medicine", Order.status == "placed", Order.accepted_at.is_(None))).all():
        tl = o.timeline or []
        if any(t.get("s") == "unclaimed" for t in tl):
            continue
        since = o.offered_at if o.offered_at is not None else (o.created or now())
        if now() - since < OFFER_S:
            continue
        tried = list(o.tried or []) + [o.store_id]
        nxt = candidates(db, o, set(tried)) if len(tried) < MAX_STORES else []
        if nxt:
            d, s = nxt[0]
            o.tried, o.store_id, o.offered_at = tried, s.id, now()
            o.timeline = tl + [{"s": "reoffered", "t": now(), "to": s.id}]
            _notify_store(db, o, s)
        else:
            o.tried = tried
            o.timeline = tl + [{"s": "unclaimed", "t": now()}]
            notify(db, o.household_id, "order", "Finding a pharmacy for you", "Nearby shops are busy. Our team is calling pharmacies now — usually a few minutes.",
                   {"order": o.id, "status": "placed", "kind": "medicine"}, o.member_id or "", "/app")
        moved += 1
    return moved


def start() -> None:
    from .tasks import in_process_loops
    if not in_process_loops():
        return

    def loop():
        while True:
            try:
                with session() as db:
                    tick(db)
            except Exception as e:
                print("[dispatch] tick failed:", type(e).__name__, str(e)[:200], flush=True)
            time.sleep(30)
    threading.Thread(target=loop, name="dispatch", daemon=True).start()


# ---- the desk -------------------------------------------------------------------------------------------------------
def _row(db: Session, o: Order) -> dict:
    a = o.addr or {}
    cands = candidates(db, o, set())
    owner = lambda s: db.scalar(select(PartnerUser).where(PartnerUser.store_id == s.id, PartnerUser.role == "owner", PartnerUser.active == True))  # noqa: E712
    return {"id": o.id, "items": [{"name": i.get("name"), "qty": i.get("qty", 1), "rx": bool(i.get("rx"))} for i in (o.items or [])],
            "total": o.total, "area": a.get("area", ""), "pin": a.get("pin", ""), "since": o.created, "rx": bool(o.rx_files),
            "tried": [db.get(Store, x).name for x in (o.tried or []) if db.get(Store, x)],
            "stores": [{"id": s.id, "name": s.name, "km": d, "phone": s.phone or (owner(s).phone if owner(s) else ""), "area": s.area} for d, s in cands[:8]]}


@r.get("")
def desk(a: Admin = Depends(admin_me), db: Session = Depends(get_db)):
    un = [o for o in db.scalars(select(Order).where(Order.kind == "medicine", Order.status == "placed").order_by(Order.created)).all()
          if any(t.get("s") == "unclaimed" for t in (o.timeline or []))]
    norider = db.scalars(select(Order).where(Order.kind == "medicine", Order.status == "packing", Order.courier == "uh")).all()
    return {"unclaimed": [_row(db, o) for o in un], "pickups": [{**_row(db, o), "store": o.store.name if o.store else "", "storeArea": o.store.area if o.store else "",
                                                               "lat": o.store.lat if o.store else None, "lng": o.store.lng if o.store else None} for o in norider]}


class AssignIn(BaseModel):
    store: str
    note: str = ""


@r.post("/{oid}/assign")
def assign(oid: str, b: AssignIn, a: Admin = Depends(admin_me), db: Session = Depends(get_db)):
    """The desk phoned a pharmacy and it said yes: give them the order, already accepted."""
    from .inbox import notify
    o = db.get(Order, oid)
    s = db.get(Store, b.store)
    if not o or o.kind != "medicine" or o.status != "placed":
        raise HTTPException(409, "This order is no longer waiting.")
    if not s or s.kind != "pharmacy" or not s.active or not s.verified:
        raise HTTPException(400, "Choose a live pharmacy.")
    o.store_id, o.offered_at, o.accepted_at, o.status = s.id, now(), now(), "checking"
    o.timeline = (o.timeline or []) + [{"s": "checking", "t": now(), "by": a.email, "note": ("Assigned by Urban Health. " + b.note)[:200]}]
    _notify_store(db, o, s)
    notify(db, o.household_id, "order", f"{s.name} accepted your order", "A registered pharmacist is checking your prescription.",
           {"order": o.id, "status": "checking", "kind": "medicine", "store": s.name}, o.member_id or "", "/app")
    log(db, a.email, "dispatch.assign", f"{o.id} → {s.name}")
    return {"ok": True}


@r.post("/{oid}/pickup-done")
def picked(oid: str, a: Admin = Depends(admin_me), db: Session = Depends(get_db)):
    """Urban Health collected the sealed, billed bag from the pharmacy and is on the way."""
    from .inbox import notify
    o = db.get(Order, oid)
    if not o or o.status != "packing" or o.courier != "uh":
        raise HTTPException(409, "Nothing to pick up here.")
    o.status, o.started_at = "out", now()
    o.timeline = (o.timeline or []) + [{"s": "out", "t": now(), "by": a.email, "note": "Picked up by Urban Health"}]
    l = family_line(o, o.store)
    notify(db, o.household_id, "order", l[0], l[1], {"order": o.id, "status": "out", "kind": "medicine"}, o.member_id or "", "/app")
    log(db, a.email, "dispatch.pickup", o.id)
    return {"ok": True}


def live(o: Order) -> dict | None:
    """The big card at the top of a medicine order: one headline, one line, a progress fraction and an ETA."""
    if o.kind != "medicine":
        return None
    s = o.store
    tl = o.timeline or []
    st = o.status
    trip = None
    a = o.addr or {}
    if s is not None and s.lat is not None and a.get("lat"):
        trip = km((s.lat, s.lng), (a["lat"], a["lng"]))
    ride = max(8, round((trip or 3) * 3.2 + 4))          # city traffic: ~19 km/h plus parking and stairs
    unclaimed = any(t.get("s") == "unclaimed" for t in tl)
    if st == "placed":
        if unclaimed:
            return {"phase": "finding", "title": "Finding a pharmacy", "sub": "Nearby shops are busy — our team is calling pharmacies for you.", "pct": .12}
        return {"phase": "finding", "title": "Waiting for the pharmacy", "sub": f"{s.name if s else 'A pharmacy'} usually accepts within 3 minutes.", "pct": .12,
                "left": max(0, OFFER_S - (now() - (o.offered_at or o.created or now())))}
    if st == "checking":
        return {"phase": "accepted", "title": "Order accepted", "sub": "A registered pharmacist is checking your prescription." if any(i.get("rx") for i in (o.items or [])) and not o.verified_at
                else f"{s.name if s else 'The pharmacy'} is picking your medicines.", "pct": .35, "etaMin": ride + 10}
    if st == "packing":
        return {"phase": "packed", "title": "Packed", "sub": "Waiting for the rider to pick it up." if o.courier != "uh" else "Our rider is on the way to the pharmacy.",
                "pct": .6, "etaMin": ride + 4, "bill": (o.pack or {}).get("bill")}
    if st == "out":
        left = max(1, ride - (now() - (o.started_at or now())) // 60)
        return {"phase": "out", "title": f"Arriving in {left} min" if left > 2 else "Arriving now", "sub": "Out for delivery · keep your doorstep code ready.",
                "pct": .7 + .28 * (1 - left / ride), "etaMin": left}
    if st == "delivered":
        return {"phase": "done", "title": "Delivered", "sub": "Take care. Rate the pharmacy below.", "pct": 1}
    if st == "cancelled":
        return {"phase": "cancelled", "title": "Cancelled", "sub": next((t.get("reason") or t.get("note") or "" for t in reversed(tl) if t.get("s") == "cancelled"), ""), "pct": 0}
    return None

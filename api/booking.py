"""Booking: where we come, whether we serve it, which slot has room, the doorstep code, changing or cancelling,
telling the partner, the invoice, and "tell me when you come here".

A home visit or a delivery is only accepted with a saved address that has a map pin, a flat number and a landmark,
and only from a partner that serves that PIN code. Before this, an order could be placed with no address at all."""
from __future__ import annotations

import html
import json
import math
import os
import re
import secrets
import time
import urllib.parse
import urllib.request

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .db import get_db
from .models import AreaWait, Household, Order, PartnerUser, SavedAddress, Store, now

r = APIRouter(prefix="/api/v2")
SLOT_CAP = 6               # home visits a lab can do in one hourly slot unless it sets its own
FREE_CANCEL_H = 2          # free to cancel or move until this many hours before the slot
LATE_CANCEL_FEE = 50
RADIUS_KM = 12             # a partner with no PIN list serves this far around its pin


def _ist(t: int):
    return time.gmtime(t + 19800)


def km(a, b) -> float:
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 6371 * 2 * math.asin(math.sqrt(h))


def _user(request: Request, db: Session):
    from .auth import current_user
    u = current_user(request, db)
    if not u or not u.household_id:
        raise HTTPException(401, "Sign in first")
    return u


# ---- addresses -------------------------------------------------------------------------------------------------------
class AddrIn(BaseModel):
    label: str = "Home"
    line1: str
    line2: str
    landmark: str
    area: str = ""
    city: str = ""
    state: str = ""
    pin: str
    lat: float
    lng: float
    acc: int = 0
    name: str = ""
    phone: str = ""
    note: str = ""


def _clean(v, n):
    return re.sub(r"[<>\x00-\x1f]", "", str(v or "")).strip()[:n]


def addr_json(a: SavedAddress) -> dict:
    return {"id": a.id, "label": a.label, "line1": a.line1, "line2": a.line2, "landmark": a.landmark, "area": a.area, "city": a.city, "state": a.state,
            "pin": a.pin, "lat": a.lat, "lng": a.lng, "acc": a.acc, "name": a.name, "phone": a.phone, "note": a.note}


def _validate(body: AddrIn) -> dict:
    from .auth import norm_id
    d = {k: _clean(getattr(body, k), n) for k, n in (("label", 20), ("line1", 120), ("line2", 160), ("landmark", 120), ("area", 80), ("city", 80),
                                                       ("state", 40), ("name", 80), ("note", 160))}
    if len(d["line1"]) < 1:
        raise HTTPException(400, "Enter the house or flat number, and the floor.")
    if len(d["line2"]) < 3:
        raise HTTPException(400, "Enter the building or street.")
    if not re.fullmatch(r"[1-9]\d{5}", (body.pin or "").strip()):
        raise HTTPException(400, "PIN code is 6 digits.")
    if not (6 <= body.lat <= 37.5 and 68 <= body.lng <= 97.5):
        raise HTTPException(400, "Put the pin on the map at your door.")
    d["pin"] = body.pin.strip()
    d["lat"], d["lng"], d["acc"] = round(body.lat, 6), round(body.lng, 6), max(0, min(5000, int(body.acc or 0)))
    d["phone"] = ""
    if body.phone.strip():
        kind, ph = norm_id(body.phone)
        if kind != "phone":
            raise HTTPException(400, "Enter a mobile number for the person at the door.")
        d["phone"] = ph
    if d["label"] not in ("Home", "Work", "Parents", "Other"):
        d["label"] = "Other"
    return d


@r.get("/addresses")
def addresses(request: Request, db: Session = Depends(get_db)):
    u = _user(request, db)
    rows = db.scalars(select(SavedAddress).where(SavedAddress.household_id == u.household_id).order_by(SavedAddress.updated.desc())).all()
    return {"rows": [{**addr_json(a), "serve": serviceable(db, a.pin, a.lat, a.lng)} for a in rows]}


@r.post("/addresses")
def add_address(body: AddrIn, request: Request, db: Session = Depends(get_db)):
    u = _user(request, db)
    if db.scalar(select(func.count(SavedAddress.id)).where(SavedAddress.household_id == u.household_id)) >= 12:
        raise HTTPException(400, "Up to 12 saved addresses. Remove one first.")
    a = SavedAddress(household_id=u.household_id, **_validate(body))
    if not a.name:
        a.name = (u.name if hasattr(u, "name") else "") or ""
    if not a.phone:
        a.phone = u.phone or ""
    db.add(a)
    db.flush()
    return {**addr_json(a), "serve": serviceable(db, a.pin, a.lat, a.lng)}


@r.put("/addresses/{aid}")
def edit_address(aid: str, body: AddrIn, request: Request, db: Session = Depends(get_db)):
    u = _user(request, db)
    a = db.get(SavedAddress, aid)
    if not a or a.household_id != u.household_id:
        raise HTTPException(404)
    for k, v in _validate(body).items():
        setattr(a, k, v)
    a.updated = now()
    return {**addr_json(a), "serve": serviceable(db, a.pin, a.lat, a.lng)}


@r.delete("/addresses/{aid}")
def del_address(aid: str, request: Request, db: Session = Depends(get_db)):
    u = _user(request, db)
    a = db.get(SavedAddress, aid)
    if not a or a.household_id != u.household_id:
        raise HTTPException(404)
    db.delete(a)
    return {"ok": True}


# ---- where we are on the map -----------------------------------------------------------------------------------------
_GEO: dict[str, tuple[int, dict]] = {}


def _nominatim(path: str, params: dict) -> list | dict:
    """OpenStreetMap's geocoder, cached for a day. One request a second is their rule; the cache keeps us well under."""
    key = path + json.dumps(params, sort_keys=True)
    hit = _GEO.get(key)
    if hit and hit[0] > now():
        return hit[1]
    url = f"https://nominatim.openstreetmap.org/{path}?" + urllib.parse.urlencode({**params, "format": "jsonv2", "addressdetails": 1, "countrycodes": "in"})
    req = urllib.request.Request(url, headers={"User-Agent": "UrbanHealth/1.0 (support@urbanhealth.in)", "Accept-Language": "en"})
    try:
        out = json.loads(urllib.request.urlopen(req, timeout=6).read())
    except Exception:
        out = [] if path == "search" else {}
    _GEO[key] = (now() + 86400, out)
    if len(_GEO) > 5000:
        _GEO.clear()
    return out


def _parts(a: dict) -> dict:
    ad = a.get("address") or {}
    return {"area": ad.get("suburb") or ad.get("neighbourhood") or ad.get("city_district") or ad.get("village") or "",
            "city": ad.get("city") or ad.get("town") or ad.get("county") or "", "state": ad.get("state") or "", "pin": (ad.get("postcode") or "").replace(" ", "")[:6],
            "street": ", ".join(x for x in (ad.get("building"), ad.get("road")) if x), "road": ad.get("road") or "",
            # The bold line on the card, like delivery apps: the building or place if known, else the street, else the area
            "title": a.get("name") or ad.get("building") or ad.get("amenity") or ad.get("road") or ad.get("neighbourhood") or ad.get("suburb") or ""}


@r.get("/geo/reverse")
def reverse(lat: float, lng: float, request: Request, db: Session = Depends(get_db)):
    from .auth import limit
    limit(request, "geo", 60, 600)
    if not (6 <= lat <= 37.5 and 68 <= lng <= 97.5):
        raise HTTPException(400, "Outside India")
    a = _nominatim("reverse", {"lat": round(lat, 5), "lon": round(lng, 5), "zoom": 18})
    p = _parts(a) if isinstance(a, dict) else {}
    return {**p, "serve": serviceable(db, p.get("pin", ""), lat, lng)}


@r.get("/geo/search")
def search(q: str, request: Request, lat: float | None = None, lng: float | None = None):
    from .auth import limit
    limit(request, "geo", 60, 600)
    q = (q or "").strip()[:120]
    if len(q) < 3:
        return {"rows": []}
    params = {"q": q, "limit": 6}
    if lat and lng:
        params["viewbox"] = f"{lng - .3},{lat + .3},{lng + .3},{lat - .3}"
    res = _nominatim("search", params)
    return {"rows": [{"title": (x.get("display_name") or "").split(",")[0], "sub": ", ".join((x.get("display_name") or "").split(",")[1:4]).strip(),
                      "lat": float(x["lat"]), "lng": float(x["lon"]), **_parts(x)} for x in (res or [])[:6]]}


# ---- do we come here? ------------------------------------------------------------------------------------------------
def _pins(s: Store) -> set[str]:
    p = (s.profile or {}).get("pins") or ""
    if isinstance(p, (list, tuple)):
        p = " ".join(map(str, p))
    return set(re.findall(r"\b\d{6}\b", f"{p} {s.pin or ''}"))


def serves(s: Store, pin: str, lat: float | None, lng: float | None) -> bool:
    pins = _pins(s)
    if pin and pin in pins:
        return True
    if (s.profile or {}).get("pins"):
        return False
    return bool(lat and lng and s.lat is not None and km((lat, lng), (s.lat, s.lng)) <= RADIUS_KM)


def live(db: Session, kind: str):
    return [s for s in db.scalars(select(Store).where(Store.kind == kind, Store.verified == True, Store.active == True)).all()  # noqa: E712
            if s.notes != "practice"]


def serviceable(db: Session, pin: str, lat: float | None, lng: float | None) -> dict:
    labs = [s for s in live(db, "lab") if s.home_collection and serves(s, pin, lat, lng)]
    ph = [s for s in live(db, "pharmacy") if s.delivery and serves(s, pin, lat, lng)]
    near = None
    if lat and lng:
        cands = sorted(((km((lat, lng), (s.lat, s.lng)), s) for s in live(db, "lab") if s.lat is not None), key=lambda x: x[0])
        if cands:
            d, s = cands[0]
            near = {"id": s.id, "name": s.name, "km": round(d, 1), "area": s.area}
    return {"labs": len(labs), "pharmacies": len(ph), "nearestLab": near,
            "homeHours": next(((s.profile or {}).get("homeHours") for s in labs if (s.profile or {}).get("homeHours")), "")}


@r.get("/serviceable")
def serviceable_api(pin: str = "", lat: float | None = None, lng: float | None = None, db: Session = Depends(get_db)):
    return serviceable(db, pin.strip()[:6], lat, lng)


class WaitIn(BaseModel):
    pin: str
    kind: str = "lab"


@r.post("/area-wait")
def area_wait(body: WaitIn, request: Request, db: Session = Depends(get_db)):
    u = _user(request, db)
    if not re.fullmatch(r"[1-9]\d{5}", body.pin or ""):
        raise HTTPException(400, "PIN code is 6 digits.")
    kind = body.kind if body.kind in ("lab", "pharmacy") else "lab"
    if not db.scalar(select(AreaWait).where(AreaWait.pin == body.pin, AreaWait.kind == kind, AreaWait.household_id == u.household_id, AreaWait.notified == 0)):
        db.add(AreaWait(pin=body.pin, kind=kind, household_id=u.household_id))
    return {"ok": True}


def notify_area(db: Session, s: Store) -> int:
    """A partner went live: tell every family that asked about its PIN codes."""
    from .inbox import notify
    pins = _pins(s)
    n = 0
    for w in db.scalars(select(AreaWait).where(AreaWait.pin.in_(pins), AreaWait.kind == s.kind, AreaWait.notified == 0)).all():
        notify(db, w.household_id, "area", f"{s.name} now comes to {w.pin}",
               "Home sample collection is now available in your area." if s.kind == "lab" else "Medicine delivery is now available in your area.", {"store": s.id})
        w.notified = now()
        n += 1
    return n


# ---- slots -----------------------------------------------------------------------------------------------------------
def slot_time(slot: str) -> int | None:
    """'Wed 11 Nov · 7:00 AM' → epoch (IST). Year is the next occurrence."""
    m = re.match(r"\w{3}\s+(\d{1,2})\s+(\w{3})\s*·\s*(\d{1,2}):(\d{2})\s*(AM|PM)", (slot or "").strip(), re.I)
    if not m:
        return None
    d, mon, h, mi = int(m.group(1)), m.group(2).title(), int(m.group(3)) % 12 + (12 if m.group(5).upper() == "PM" else 0), int(m.group(4))
    y = _ist(now()).tm_year
    for yy in (y, y + 1):
        try:
            t = int(_ist_to_epoch(yy, mon, d, h, mi))
        except ValueError:
            return None
        if t > now() - 30 * 86400:
            return t
    return None


def _ist_to_epoch(y, mon, d, h, mi) -> float:
    import calendar
    return calendar.timegm(time.strptime(f"{y} {mon} {d} {h}:{mi}", "%Y %b %d %H:%M")) - 19800


def cap(s: Store) -> int:
    try:
        return max(1, min(50, int((s.profile or {}).get("slotCap") or SLOT_CAP)))
    except (TypeError, ValueError):
        return SLOT_CAP


def booked(db: Session, s: Store, slot: str, exclude: str = "") -> int:
    return db.scalar(select(func.count(Order.id)).where(Order.store_id == s.id, Order.slot == slot, Order.status != "cancelled", Order.id != exclude)) or 0


@r.get("/stores/{sid}/slots")
def slots(sid: str, db: Session = Depends(get_db)):
    from .routes import _slots
    s = db.get(Store, sid)
    if not s or not s.active:
        raise HTTPException(404)
    c = cap(s)
    return {"rows": [{"slot": x, "left": max(0, c - booked(db, s, x))} for x in _slots()]}


# ---- order hooks (called from routes.create_order) -------------------------------------------------------------------
def check_order(db: Session, s: Store, body, household_id: str) -> dict | None:
    """Everything that must be true before a home visit or a delivery is accepted. Returns the clean address."""
    from .routes import clean_addr
    home = (body.kind == "lab" and bool(body.slot)) or (body.kind != "lab" and s.kind == "pharmacy" and s.delivery)
    if not home:
        return clean_addr(body.addr)
    a = None
    aid = (body.addr or {}).get("id") if isinstance(body.addr, dict) else None
    if aid:
        sa = db.get(SavedAddress, aid)
        if not sa or sa.household_id != household_id:
            raise HTTPException(400, "Choose one of your saved addresses.")
        a = {**addr_json(sa)}
    elif isinstance(body.addr, dict):
        a = body.addr
    ca = clean_addr(a) or {}
    for k in ("lat", "lng"):
        if a and a.get(k) is not None:
            ca[k] = float(a[k])
    if not ca.get("line1") or not ca.get("landmark") or not re.fullmatch(r"[1-9]\d{5}", ca.get("pin", "")) or ca.get("lat") is None:
        raise HTTPException(400, "Add the address with a map pin, flat number and landmark before booking.")
    if not serves(s, ca["pin"], ca.get("lat"), ca.get("lng")):
        raise HTTPException(409, f"{s.name} doesn't come to {ca['pin']}. Choose another lab or visit the lab instead.")
    if body.kind == "lab" and body.slot:
        st = slot_time(body.slot)
        if st and st < now() + 3600:
            raise HTTPException(400, "That slot is too soon. Choose a later one.")
        if booked(db, s, body.slot) >= cap(s):
            raise HTTPException(409, "That slot just filled up. Choose another time.")
    return ca


def after_order(db: Session, o: Order, s: Store) -> None:
    """Give the family a doorstep code and tell the partner straight away."""
    from . import messaging
    if (o.kind == "lab" and o.slot) or (o.kind == "medicine" and s.delivery):
        o.door_code = f"{secrets.randbelow(9000) + 1000}"
    owner = db.scalar(select(PartnerUser).where(PartnerUser.store_id == s.id, PartnerUser.role == "owner", PartnerUser.active == True))  # noqa: E712
    what = ", ".join(i.get("name", "") for i in (o.items or [])[:2])
    text = f"New Urban Health {'booking' if o.kind == 'lab' else 'order'} #{o.id}: {what}{' · ' + o.slot if o.slot else ''}. Accept within 10 min: urbanhealth.in/partner"
    try:
        if owner and owner.phone and (messaging.alert_sms_ready() or messaging.demo()):
            messaging.send_text_sms(owner.phone, text)
        if owner and owner.email and not owner.email.endswith(".invalid") and messaging.email_ready():
            messaging.send_mail(owner.email, f"New order #{o.id}", text)
    except Exception as e:
        print("[booking] partner alert failed:", str(e)[:120], flush=True)


# ---- change or cancel ------------------------------------------------------------------------------------------------
def _mine(request: Request, db: Session, oid: str) -> Order:
    u = _user(request, db)
    o = db.get(Order, oid)
    if not o or o.household_id != u.household_id:
        raise HTTPException(404)
    return o


def cancel_terms(o: Order) -> dict:
    st = slot_time(o.slot) if o.slot else None
    if o.status in ("collected", "processing", "ready", "out", "delivered", "cancelled", "refunded"):
        return {"can": False, "free": False, "fee": 0, "why": "This order can't be cancelled at this stage."}
    if st and st - now() < FREE_CANCEL_H * 3600:
        return {"can": True, "free": False, "fee": LATE_CANCEL_FEE, "why": f"Less than {FREE_CANCEL_H} hours to your slot: a ₹{LATE_CANCEL_FEE} fee applies."}
    return {"can": True, "free": True, "fee": 0, "why": f"Free until {FREE_CANCEL_H} hours before the slot."}


@r.get("/orders/{oid}/terms")
def terms(oid: str, request: Request, db: Session = Depends(get_db)):
    o = _mine(request, db, oid)
    t = cancel_terms(o)
    return {**t, "canMove": t["can"] and t["free"] and o.kind == "lab" and bool(o.slot)}


@r.post("/orders/{oid}/cancel")
def cancel(oid: str, request: Request, db: Session = Depends(get_db)):
    from .inbox import notify
    o = _mine(request, db, oid)
    t = cancel_terms(o)
    if not t["can"]:
        raise HTTPException(409, t["why"])
    o.status, o.cancel_fee = "cancelled", t["fee"]
    o.timeline = (o.timeline or []) + [{"s": "cancelled", "t": now(), "by": "family", "fee": t["fee"]}]
    notify(db, o.household_id, "order", "Booking cancelled", ("A ₹%d late-cancellation fee applies. " % t["fee"] if t["fee"] else "") +
           ("Your refund is on its way." if o.payment != "cod" else ""), {"order": o.id})
    return {"ok": True, "fee": t["fee"]}


class MoveIn(BaseModel):
    slot: str


@r.post("/orders/{oid}/reschedule")
def reschedule(oid: str, body: MoveIn, request: Request, db: Session = Depends(get_db)):
    o = _mine(request, db, oid)
    t = cancel_terms(o)
    if o.kind != "lab" or not o.slot or not (t["can"] and t["free"]):
        raise HTTPException(409, f"This booking can only be moved until {FREE_CANCEL_H} hours before the slot.")
    s = db.get(Store, o.store_id)
    st = slot_time(body.slot)
    if not st or st < now() + 3 * 3600:
        raise HTTPException(400, "Choose a slot at least 3 hours from now.")
    if booked(db, s, body.slot, exclude=o.id) >= cap(s):
        raise HTTPException(409, "That slot is full. Choose another time.")
    old, o.slot = o.slot, body.slot[:40]
    o.timeline = (o.timeline or []) + [{"s": "rescheduled", "t": now(), "by": "family", "from": old, "to": o.slot}]
    return {"ok": True, "slot": o.slot}


# ---- invoice ---------------------------------------------------------------------------------------------------------
@r.get("/orders/{oid}/invoice", response_class=HTMLResponse)
def invoice(oid: str, request: Request, db: Session = Depends(get_db)):
    o = _mine(request, db, oid)
    if o.status not in ("ready", "delivered", "completed", "collected", "processing"):
        raise HTTPException(409, "The invoice is ready once the visit or delivery is done.")
    s = db.get(Store, o.store_id)
    h = db.get(Household, o.household_id)
    E = html.escape
    rows = "".join(f"<tr><td>{E(str(i.get('name', '')))}</td><td>{i.get('qty', 1)}</td><td>₹{i.get('price', 0):,}</td><td>₹{i.get('price', 0) * (i.get('qty') or 1):,}</td></tr>" for i in (o.items or []))
    gst = s.gst_pct or 0
    tax = round((o.total or 0) * gst / (100 + gst)) if gst else 0
    when = time.strftime("%d %b %Y", _ist(o.created or now()))
    doc = f"""<!doctype html><meta charset="utf-8"><title>Invoice {E(o.id)}</title><style>body{{font:14px/1.5 -apple-system,Inter,sans-serif;max-width:720px;margin:30px auto;padding:0 20px;color:#1D1D1F}}
table{{width:100%;border-collapse:collapse;margin:16px 0}}td,th{{text-align:left;padding:8px;border-bottom:1px solid #eee}}th{{font-size:12px;color:#666}}.r{{text-align:right}}
.top{{display:flex;justify-content:space-between}}h1{{font-size:22px;margin:0}}@media print{{button{{display:none}}}}</style>
<div class="top"><div><h1>Tax invoice</h1><div>#{E(o.id)} · {when}</div></div><div style="text-align:right"><b>{E(s.name if s else '')}</b><br>{E(s.address if s else '')}, {E(s.city if s else '')}<br>{('GSTIN ' + E(s.gstin)) if s and s.gstin else 'GST not registered'}<br>{('Licence ' + E(s.licence)) if s and s.licence else ''}</div></div>
<p>Billed to: <b>{E(o.member or (h.name if h else ''))}</b><br>{E(o.address or '')}</p>
<table><tr><th>Item</th><th>Qty</th><th>Price</th><th>Amount</th></tr>{rows}
<tr><td colspan="3">Home visit / delivery</td><td>₹{o.fee or 0:,}</td></tr>{f'<tr><td colspan="3">Discount</td><td>− ₹{o.discount:,}</td></tr>' if o.discount and o.kind != 'medicine' else ''}
<tr><th colspan="3">Total (incl. GST{' ₹' + format(tax, ',') if tax else ''})</th><th>₹{o.total or 0:,}</th></tr></table>
<p style="color:#666;font-size:12.5px">Paid by {E((o.payment or '').upper())}. Booked through Urban Health. Questions: support in the app, or the grievance officer at urbanhealth.in/privacy.</p>
<button onclick="print()">Print or save as PDF</button>"""
    return HTMLResponse(doc, headers={"Cache-Control": "private, no-store"})


def check_door(o: Order, code: str, sample: str = "") -> None:
    """The family reads a 4-digit code to the technician or the rider. Without it nothing is marked
    collected or delivered, so a job cannot be closed from the road."""
    if o.door_code and o.status not in ("collected", "delivered"):
        if str(code or "").strip() != o.door_code:
            raise HTTPException(400, "Ask the family for the 4-digit doorstep code shown in their app.")
    sid = re.sub(r"[^A-Za-z0-9-]", "", sample or "")[:24]
    if sid:
        o.sample_id = sid
    elif o.kind == "lab" and not o.sample_id:
        o.sample_id = f"UH-{o.id[-6:]}"


def _visit_day(o: Order) -> bool:
    st = slot_time(o.slot or "")
    if not st:
        return True
    return _ist(st)[:3] <= _ist(now())[:3]


def _mask_phone(p: str) -> str:
    d = re.sub(r"\D", "", p or "")
    return ("•••••• " + d[-4:]) if len(d) >= 4 else ""


def partner_view(o: Order, j: dict) -> None:
    """What a partner sees of the family. The code is never theirs to see. The full address and phone
    appear on the visit day (or once the job is under way); before that, the area and PIN are enough to plan."""
    j.pop("doorCode", None)
    j["needsCode"] = bool(o.door_code)
    st = o.status or ""
    if _visit_day(o) or st in ("en_route", "arrived", "out", "collected", "delivered"):
        return
    a = dict(o.addr or {})
    j["addr"] = {k: a[k] for k in ("area", "city", "pin", "label", "note") if a.get(k)}
    j["address"] = ", ".join(x for x in (a.get("area"), a.get("city"), a.get("pin")) if x) or "Shown on the visit day"
    j["addrHidden"] = True
    if a.get("phone"):
        j["addr"]["phone"] = _mask_phone(a["phone"])


def evening_before(db: Session) -> int:
    """At 8 pm IST: tomorrow's home visits get a fasting note; nothing else is said."""
    from .inbox import notify
    tom = _ist(now() + 86400)[:3]
    n = 0
    for o in db.scalars(select(Order).where(Order.kind == "lab", Order.slot != "", Order.status.in_(("placed", "confirmed", "assigned")))).all():
        st = slot_time(o.slot)
        if not st or _ist(st)[:3] != tom or any(t.get("s") == "fast_note" for t in (o.timeline or [])):
            continue
        fast = any(("fast" in str(i.get("prep", "")).lower()) or i.get("code") in ("fbs", "lipid", "glucose_f", "fasting") for i in (o.items or []))
        body = ("Don't eat for 10–12 hours before the visit. Water is fine. Take regular medicines unless your doctor said otherwise."
                if fast else "Keep the doorstep code ready. Water and breakfast are fine for these tests.")
        notify(db, o.household_id, "visit", f"Tomorrow {o.slot.split('·')[-1].strip()}: home sample visit", body, {"order": o.id})
        o.timeline = (o.timeline or []) + [{"s": "fast_note", "t": now()}]
        n += 1
    return n

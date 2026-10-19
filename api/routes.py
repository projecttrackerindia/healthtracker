"""Public API (/api/v1). The app sends its anonymous household key in X-DoKKo-Key; no login yet."""
from __future__ import annotations

import math
import os
import time
from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, Request, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from . import ai as AI
CATALOG_RX = {x["id"]: bool(x.get("rx")) for x in AI.CATALOG}
from .db import get_db
from .models import AiCache, AiJob, Household, User, LabTest, Order, Plan, Seasonal, Store, StoreItem, Subscription, Video, now
from .security import valid_key
from .seed import CITIES, TESTS

r = APIRouter(prefix="/api/v1")
MAX_UPLOAD = 15 * 1024 * 1024
AI_CAP = {"free": 3, "family": 30, "plus": 100000}


# ---------------------------------------------------------------------------------------------------------------------
def km(lat1, lng1, lat2, lng2):
    p = math.pi / 180
    a = .5 - math.cos((lat2 - lat1) * p) / 2 + math.cos(lat1 * p) * math.cos(lat2 * p) * (1 - math.cos((lng2 - lng1) * p)) / 2
    return 12742 * math.asin(math.sqrt(a))


def nearest_city(lat, lng):
    best, bd = None, 1e9
    for city, c in CITIES.items():
        for _, la, lo in c["areas"]:
            d = km(lat, lng, la, lo)
            if d < bd:
                best, bd = city, d
    return best, bd


def household(db: Session, key: str | None, create=True) -> Household | None:
    k = valid_key(key)
    if not k:
        return None
    h = db.scalar(select(Household).where(Household.key == k))
    if h is None and create:
        # the app's first two requests can race to create the same household: let the loser pick up the winner's row
        from sqlalchemy.exc import IntegrityError
        try:
            with db.begin_nested():
                h = Household(key=k)
                db.add(h)
                db.flush()
        except IntegrityError:
            h = db.scalar(select(Household).where(Household.key == k))
    if h:
        h.last_seen = now()
        if h.blocked:
            raise HTTPException(403, "This install has been blocked. Contact support.")
    return h


def store_json(s: Store, d=None, extra=None):
    o = {"id": s.id, "kind": s.kind, "name": s.name, "brand": s.brand, "area": s.area, "city": s.city, "address": s.address, "phone": s.phone,
         "hours": s.hours, "open24": s.open_24h, "rating": s.rating, "ratingN": s.rating_n, "discount": s.discount_pct, "delivery": s.delivery,
         "fee": s.delivery_fee, "freeAbove": s.free_above, "etaMin": s.eta_min, "home": s.home_collection, "collectionFee": s.collection_fee,
         "verified": s.verified, "licence": s.licence, "lat": s.lat, "lng": s.lng}
    if d is not None:
        o["km"] = round(d, 1)
    if extra:
        o.update(extra)
    return o


class Loc(BaseModel):
    lat: float | None = None
    lng: float | None = None
    city: str | None = None


def resolve_loc(db: Session, loc: Loc, h: Household | None):
    lat, lng = loc.lat, loc.lng
    if (lat is None or lng is None) and h and h.lat is not None:
        lat, lng = h.lat, h.lng
    if lat is None or lng is None:
        city = loc.city or (h.city if h else "") or "Hyderabad"
        c = CITIES.get(city) or CITIES["Hyderabad"]
        lat, lng = c["areas"][0][1], c["areas"][0][2]
        return lat, lng, city, True
    if h and (h.lat is None or km(lat, lng, h.lat, h.lng) > 2):
        h.lat, h.lng = lat, lng
        h.city = nearest_city(lat, lng)[0] or h.city
    return lat, lng, nearest_city(lat, lng)[0], False


# ---------------------------------------------------------------------------------------------------------------------
@r.get("/config")
def config():
    return {"version": os.getenv("RAILWAY_GIT_COMMIT_SHA", "dev")[:8], "region": os.getenv("DOKKO_REGION", "IN"),
            "emergency": {"national": "112", "ambulance": "108"}, "languages": ["en", "hi", "te"],
            # public: only whether smart reading is available. The provider and model stay server-side (named in the privacy policy).
            "ai": {"engine": "ai" if os.getenv("ANTHROPIC_API_KEY") else "local"},
            "payments": "razorpay" if os.getenv("RAZORPAY_KEY_ID") else ("upi" if _upi_on() else "demo"), "cities": list(CITIES)}


class Hello(BaseModel):
    name: str = ""
    members: int = 1
    city: str = ""
    lat: float | None = None
    lng: float | None = None
    phone: str = ""
    email: str = ""


@r.post("/hello")
def hello(body: Hello, request: Request, db: Session = Depends(get_db), x_dokko_key: str | None = Header(None)):
    from .auth import current_user
    h = household(db, x_dokko_key)
    if not h:
        raise HTTPException(400, "missing household key")
    u = current_user(request, db)
    if u:  # signed in: this account's orders, plan and AI quota follow it to every device
        if u.household_id and u.household_id != h.id:
            own = db.get(Household, u.household_id)
            if own:
                return {"adoptKey": own.key}
        if not u.household_id:
            # the first sign-in that claims a family is its admin; people who join by invitation come in as members or caregivers
            others = db.scalar(select(User.id).where(User.household_id == h.id, User.id != u.id))
            u.role = u.role if others else "admin"
        u.household_id = h.id
    if body.name:
        h.name = body.name[:80]
    if body.members:
        h.members = max(1, min(30, body.members))
    if body.city:
        h.city = body.city[:80]
    if body.phone:
        h.phone = body.phone[:24]
    if body.email:
        h.email = body.email[:120]
    if body.lat is not None and body.lng is not None:
        h.lat, h.lng = body.lat, body.lng
        h.city = nearest_city(body.lat, body.lng)[0] or h.city
    used = db.scalar(select(func.count(AiJob.id)).where(AiJob.household_id == h.id, AiJob.t > now() - 30 * 86400)) or 0
    return {"id": h.id, "account": ({"name": u.name, "email": u.email, "phone": u.phone} if u else None), "plan": h.plan, "planUntil": h.plan_until, "city": h.city, "ai": {"used": used, "cap": AI_CAP.get(h.plan, 3)}, "orders": len(h.orders)}


# ---- partners -------------------------------------------------------------------------------------------------------
@r.get("/stores")
def stores(kind: str = "pharmacy", lat: float | None = None, lng: float | None = None, city: str | None = None, q: str = "", limit: int = 12,
           db: Session = Depends(get_db), x_dokko_key: str | None = Header(None)):
    h = household(db, x_dokko_key, create=False)
    la, lo, cty, approx = resolve_loc(db, Loc(lat=lat, lng=lng, city=city), h)
    rows = db.scalars(select(Store).where(Store.kind == kind, Store.active == True)).all()  # noqa: E712
    out = []
    for s in rows:
        d = km(la, lo, s.lat, s.lng)
        if q and q.lower() not in (s.name + s.area + s.city).lower():
            continue
        out.append((d, s))
    out.sort(key=lambda x: x[0])
    return {"city": cty, "approx": approx, "stores": [store_json(s, d) for d, s in out[:limit]]}


class QuoteItem(BaseModel):
    sku: str = ""
    name: str = ""
    qty: int = Field(1, ge=1, le=20)


class QuoteReq(Loc):
    items: list[QuoteItem]


@r.post("/quotes")
def quotes(body: QuoteReq, db: Session = Depends(get_db), x_dokko_key: str | None = Header(None)):
    """Compare nearby pharmacies for a basket: price per store, discount, delivery fee, ETA, rating, 'ordered before'."""
    h = household(db, x_dokko_key, create=False)
    la, lo, cty, approx = resolve_loc(db, body, h)
    rows = db.scalars(select(Store).where(Store.kind == "pharmacy", Store.active == True)).all()  # noqa: E712
    near = sorted(((km(la, lo, s.lat, s.lng), s) for s in rows), key=lambda x: x[0])[:10]
    if not near:
        return {"city": cty, "approx": approx, "stores": []}
    ids = [s.id for _, s in near]
    items = db.scalars(select(StoreItem).where(StoreItem.store_id.in_(ids))).all()
    by = {}
    for it in items:
        by.setdefault(it.store_id, {})[it.sku] = it
    prev = set()
    if h:
        prev = {o.store_id for o in db.scalars(select(Order).where(Order.household_id == h.id)).all()}
    want = [(i.sku or AI.match_sku(i.name or "") and AI.match_sku(i.name)["id"] or "", i.name, i.qty) for i in body.items]
    res = []
    for d, s in near:
        inv = by.get(s.id, {})
        lines, sub, mrp, missing = [], 0, 0, []
        for sku, name, qty in want:
            it = inv.get(sku)
            if it and it.stock > 0:
                lines.append({"sku": sku, "name": it.name, "qty": qty, "price": it.price, "mrp": it.mrp})
                sub += it.price * qty
                mrp += it.mrp * qty
            else:
                missing.append(name or sku)
        fee = 0 if (s.free_above and sub >= s.free_above) or not s.delivery else s.delivery_fee
        res.append({**store_json(s, d), "lines": lines, "missing": missing, "subtotal": sub, "mrpTotal": mrp, "saving": mrp - sub, "fee": fee,
                    "total": sub + fee, "complete": not missing, "orderedBefore": s.id in prev, "eta": _eta_text(s.eta_min)})
    comp = [x for x in res if x["complete"]] or res
    tags = {}
    for key, label, fn in (("total", "Cheapest", lambda x: x["total"]), ("km", "Nearest", lambda x: x["km"]), ("etaMin", "Fastest", lambda x: x["etaMin"]),
                           ("rating", "Best rated", lambda x: -x["rating"]), ("saving", "Biggest discount", lambda x: -x["saving"])):
        best = min(comp, key=fn)
        tags.setdefault(best["id"], []).append(label)
    for x in res:
        x["tags"] = tags.get(x["id"], []) + (["Ordered before"] if x["orderedBefore"] else [])
        x["score"] = round(100 - x["total"] / max(1, min(c["total"] for c in comp)) * 30 - x["km"] * 2 - x["etaMin"] / 10 + x["rating"] * 4 + (6 if x["orderedBefore"] else 0) - (40 if not x["complete"] else 0), 1)
    res.sort(key=lambda x: -x["score"])
    return {"city": cty, "approx": approx, "stores": res, "recommended": res[0]["id"] if res else None}


def _eta_text(m):
    if m < 60:
        return f"{m} min"
    if m < 24 * 60:
        return f"{round(m / 60, 1):g} h"
    return f"{round(m / 1440)} day{'s' if m >= 2880 else ''}"


# ---- orders ---------------------------------------------------------------------------------------------------------
STEPS_MED = [("placed", "Order placed"), ("checking", "Pharmacist checking"), ("packing", "Packing"), ("out", "Out for delivery"), ("delivered", "Delivered")]
STEPS_LAB = [("placed", "Booked"), ("confirmed", "Phlebotomist assigned"), ("collected", "Sample collected"), ("processing", "In the lab"), ("ready", "Report ready")]
DEMO_SECONDS = [0, 20, 60, 120, 240]  # demo clock: how the status advances when no partner app is connected


class OrderReq(BaseModel):
    store: str
    kind: str = "medicine"
    items: list[dict]
    address: str = ""
    member: str = ""
    rxShared: bool = False
    rxDocs: list[str] = []
    memberId: str = ""
    slot: str = ""
    payment: str = "cod"
    lat: float | None = None
    lng: float | None = None
    addr: dict | None = None   # a saved address from the profile (home / work / other)


ADDR_KEYS = ("label", "name", "phone", "line1", "line2", "landmark", "area", "city", "state", "pin")


def clean_addr(a: dict | None) -> dict | None:
    if not isinstance(a, dict):
        return None
    out = {k: str(a.get(k, "")).strip()[:120] for k in ADDR_KEYS if a.get(k)}
    for k in ("lat", "lng"):
        try:
            if a.get(k) is not None:
                out[k] = round(float(a[k]), 6)
        except (TypeError, ValueError):
            pass
    return out or None


def addr_line(a: dict | None) -> str:
    if not a:
        return ""
    parts = [a.get("line1"), a.get("line2"), a.get("landmark"), a.get("area"), a.get("city")]
    s = ", ".join(x for x in parts if x)
    if a.get("pin"):
        s += f" - {a['pin']}"
    who = " · ".join(x for x in (a.get("name"), a.get("phone")) if x)
    return (who + " · " if who else "") + s


def _status(o: Order):
    steps = STEPS_LAB if o.kind == "lab" else STEPS_MED
    if o.status == "cancelled":
        return steps, -1
    live = max(i for i, (k, _) in enumerate(steps) if any(t["s"] == k for t in (o.timeline or [])) or i == 0)
    i = live
    if os.getenv("APP_ENV", "production") != "production":
        # demo progression on staging only: in production, only the partner (or admin) advances an order
        el = now() - o.created
        i = max(live, max(i for i, s in enumerate(DEMO_SECONDS) if el >= s))
    if o.status in ("return_requested", "returned", "refunded"):
        return steps, i
    return steps, i


def order_json(o: Order):
    steps, i = _status(o)
    return {"id": o.id, "kind": o.kind, "store": store_json(o.store) if o.store else None, "items": o.items, "subtotal": o.subtotal, "fee": o.fee,
            "discount": o.discount, "total": o.total, "address": o.address, "member": o.member, "rxShared": o.rx_shared, "slot": o.slot,
            "status": "cancelled" if i < 0 else (o.status if o.status in ("return_requested", "returned", "refunded") else steps[i][0]), "step": i, "steps": [s[1] for s in steps], "created": o.created, "eta": o.eta,
            "payment": o.payment, "rating": o.rating, "ratingTags": o.rating_tags, "ratingNote": o.rating_note, "timeline": o.timeline, "addr": o.addr}


@r.post("/orders")
def create_order(body: OrderReq, db: Session = Depends(get_db), x_dokko_key: str | None = Header(None)):
    h = household(db, x_dokko_key)
    if not h:
        raise HTTPException(400, "missing household key")
    s = db.get(Store, body.store)
    if not s or not s.active:
        raise HTTPException(404, "store not found")
    if body.kind == "lab":
        codes = [i.get("code") for i in body.items]
        tests = {t.code: t for t in db.scalars(select(LabTest).where(LabTest.store_id == s.id, LabTest.code.in_(codes))).all()}
        lines = [{"code": c, "name": tests[c].name, "price": tests[c].price, "fasting": tests[c].fasting} for c in codes if c in tests]
        sub = sum(l["price"] for l in lines)
        fee = s.collection_fee if body.slot else 0
        disc = 0
    else:
        inv = {i.sku: i for i in db.scalars(select(StoreItem).where(StoreItem.store_id == s.id)).all()}
        lines, sub, disc = [], 0, 0
        for i in body.items:
            it = inv.get(i.get("sku"))
            if not it:
                continue
            q = max(1, min(20, int(i.get("qty", 1))))
            rx = bool(i.get("rx")) or bool(CATALOG_RX.get(it.sku))  # the catalogue decides, not the browser
            lines.append({"sku": it.sku, "name": it.name, "qty": q, "price": it.price, "mrp": it.mrp, "rx": rx, "member": str(i.get("member", ""))[:40]})
            sub += it.price * q
            disc += (it.mrp - it.price) * q
            it.stock = max(0, it.stock - q)
        fee = 0 if (s.free_above and sub >= s.free_above) or not s.delivery else s.delivery_fee
    if not lines:
        raise HTTPException(400, "nothing available at this store")
    if body.kind != "lab" and any(l.get("rx") for l in lines) and not body.rxShared:
        raise HTTPException(400, "This order has prescription-only medicines. Upload or choose the prescription first; the pharmacist must see it before dispensing.")
    rx_files = [str(x)[:48] for x in body.rxDocs[:6]] if body.rxShared else []
    o = Order(household_id=h.id, store_id=s.id, kind=body.kind, items=lines, subtotal=sub, fee=fee, discount=disc, total=sub + fee,
              address=(body.address or addr_line(clean_addr(body.addr)))[:240], addr=clean_addr(body.addr), member=body.member[:80], member_id=body.memberId[:32] or None, rx_files=rx_files, rx_shared=body.rxShared, slot=body.slot[:40], payment=body.payment[:24],
              timeline=[{"s": "placed", "t": now()}], eta=now() + s.eta_min * 60)
    db.add(o)
    db.flush()
    o.store = s
    return order_json(o)


@r.get("/orders")
def list_orders(db: Session = Depends(get_db), x_dokko_key: str | None = Header(None)):
    h = household(db, x_dokko_key, create=False)
    if not h:
        return {"orders": []}
    rows = db.scalars(select(Order).where(Order.household_id == h.id).order_by(Order.created.desc()).limit(50)).all()
    return {"orders": [order_json(o) for o in rows]}


class RateReq(BaseModel):
    rating: int = Field(ge=1, le=5)
    tags: list[str] = []
    note: str = ""


@r.post("/orders/{oid}/rate")
def rate(oid: str, body: RateReq, db: Session = Depends(get_db), x_dokko_key: str | None = Header(None)):
    h = household(db, x_dokko_key, create=False)
    o = db.get(Order, oid)
    if not h or not o or o.household_id != h.id:
        raise HTTPException(404)
    steps, i = _status(o)
    if i < len(steps) - 1:
        raise HTTPException(409, "you can rate once the order is delivered")
    first = o.rating is None
    o.rating, o.rating_tags, o.rating_note = body.rating, [t[:30] for t in body.tags][:8], body.note[:400]
    s = o.store
    if s and first:
        s.rating = round((s.rating * s.rating_n + body.rating) / (s.rating_n + 1), 2)
        s.rating_n += 1
    return order_json(o)


@r.post("/orders/{oid}/cancel")
def cancel(oid: str, db: Session = Depends(get_db), x_dokko_key: str | None = Header(None)):
    h = household(db, x_dokko_key, create=False)
    o = db.get(Order, oid)
    if not h or not o or o.household_id != h.id:
        raise HTTPException(404)
    steps, i = _status(o)
    if i >= 3:
        raise HTTPException(409, "already out for delivery")
    o.status = "cancelled"
    o.timeline = (o.timeline or []) + [{"s": "cancelled", "t": now()}]
    return order_json(o)


# ---- labs -----------------------------------------------------------------------------------------------------------
class LabReq(Loc):
    tests: list[str]
    home: bool = False


@r.post("/labs/quotes")
def lab_quotes(body: LabReq, db: Session = Depends(get_db), x_dokko_key: str | None = Header(None)):
    """Estimate for a set of tests at nearby labs: per-test prices, total, fasting needs, turnaround and home collection."""
    h = household(db, x_dokko_key, create=False)
    la, lo, cty, approx = resolve_loc(db, body, h)
    codes = [c for c in body.tests if c in TESTS]
    rows = db.scalars(select(Store).where(Store.kind == "lab", Store.active == True)).all()  # noqa: E712
    near = sorted(((km(la, lo, s.lat, s.lng), s) for s in rows), key=lambda x: x[0])[:8]
    ids = [s.id for _, s in near]
    tests = db.scalars(select(LabTest).where(LabTest.store_id.in_(ids), LabTest.code.in_(codes))).all() if ids and codes else []
    by = {}
    for t in tests:
        by.setdefault(t.store_id, {})[t.code] = t
    res = []
    for d, s in near:
        tv = by.get(s.id, {})
        lines = [{"code": c, "name": tv[c].name, "price": tv[c].price, "tat": tv[c].tat_hours, "fasting": tv[c].fasting} for c in codes if c in tv]
        missing = [TESTS[c][0] for c in codes if c not in tv]
        sub = sum(l["price"] for l in lines)
        fee = s.collection_fee if body.home and s.home_collection else 0
        res.append({**store_json(s, d), "lines": lines, "missing": missing, "subtotal": sub, "fee": fee, "total": sub + fee, "complete": not missing,
                    "fasting": any(l["fasting"] for l in lines), "tatHours": max([l["tat"] for l in lines] or [0]),
                    "slots": _slots(), "typical": sum(TESTS[c][1] for c in codes)})
    comp = [x for x in res if x["complete"] and (not body.home or x["home"])] or res
    tags = {}
    if comp:
        for label, fn in (("Cheapest", lambda x: x["total"]), ("Nearest", lambda x: x["km"]), ("Fastest report", lambda x: x["tatHours"]), ("Best rated", lambda x: -x["rating"])):
            tags.setdefault(min(comp, key=fn)["id"], []).append(label)
    for x in res:
        x["tags"] = tags.get(x["id"], []) + (["NABL"] if x["licence"].startswith("NABL") else [])
        x["score"] = round(100 - x["total"] / max(1, min(c["total"] for c in comp)) * 30 - x["km"] * 2 + x["rating"] * 4 - (40 if not x["complete"] else 0) - (15 if body.home and not x["home"] else 0), 1)
    res.sort(key=lambda x: -x["score"])
    return {"city": cty, "approx": approx, "tests": [{"code": c, "name": TESTS[c][0], "typical": TESTS[c][1], "fasting": TESTS[c][3]} for c in codes],
            "labs": res, "recommended": res[0]["id"] if res else None}


def _slots():
    t = datetime.now()
    base = t.replace(minute=0, second=0, microsecond=0)
    out = []
    for dayoff in (0, 1, 2):
        for hr in (6, 7, 8, 9, 10, 16, 17):
            when = base.replace(hour=hr) + __import__("datetime").timedelta(days=dayoff)
            if (when - t).total_seconds() > 3 * 3600:
                out.append(when.strftime("%a %d %b · %I:%M %p").replace(" 0", " "))
    return out[:10]


@r.get("/labs/tests")
def lab_tests():
    return {"tests": [{"code": c, "name": v[0], "typical": v[1], "tat": v[2], "fasting": v[3]} for c, v in TESTS.items()]}


# ---- AI -------------------------------------------------------------------------------------------------------------
@r.post("/ai/analyze")
async def analyze(request: Request, kind: str = Form("report"), text: str = Form(""), context: str = Form("{}"), consent: str = Form("0"),
                  file: UploadFile | None = File(None), db: Session = Depends(get_db), x_dokko_key: str | None = Header(None)):
    if consent not in ("1", "true", "yes"):
        raise HTTPException(400, "consent required: the document leaves the device for analysis")
    h = household(db, x_dokko_key)
    if not h:
        raise HTTPException(400, "missing household key")
    cap = AI_CAP.get(h.plan, 3)
    used = db.scalar(select(func.count(AiJob.id)).where(AiJob.household_id == h.id, AiJob.t > now() - 30 * 86400, AiJob.engine == "claude")) or 0
    data, mime = None, ""
    if file is not None:
        data = await file.read()
        mime = (file.content_type or "application/octet-stream").split(";")[0]
        if len(data) > MAX_UPLOAD:
            raise HTTPException(413, "file too large (15 MB max)")
        if not (mime == "application/pdf" or mime.startswith("image/") or mime.startswith("text/")):
            raise HTTPException(415, "PDF, photo or text only")
    if not data and not text.strip():
        raise HTTPException(400, "nothing to analyse")
    try:
        import json
        ctx = json.loads(context or "{}")
    except Exception:
        ctx = {}
    kind = kind if kind in ("report", "prescription", "card", "policy") else "report"
    capped = bool(os.getenv("ANTHROPIC_API_KEY")) and used >= cap
    try:
        if kind == "policy":
            if capped:
                out = {"engine": "local", "kind": "policy", "readable": False, "ms": 0, "warnings": [f"Monthly smart-reading limit for the {h.plan} plan reached ({cap}). Enter the key terms yourself, or upgrade in Family & Privacy → Plan."]}
            else:
                txt = text or ""
                if data and (mime.startswith("text/")):
                    txt = data.decode("utf-8", "ignore")
                out = AI.analyze_policy(None if mime.startswith("text/") else data, mime, txt)
        elif kind == "card":
            out = AI.analyze_card(data, mime)
            if capped:
                out = {"engine": "local", "kind": "card", "readable": False, "fields": {}, "ms": 0,
                       "warnings": [f"Monthly smart-reading limit for the {h.plan} plan reached ({cap}). Fill in the details yourself, or upgrade in Family & Privacy → Plan."]}
        else:
            out = AI.analyze(kind, data, mime, text, ctx, force_local=capped)
        if capped:
            out["warnings"] = list(out.get("warnings", [])) + [f"Monthly AI limit for the {h.plan} plan reached ({cap}); the basic reader was used. Upgrade in Family & Privacy → Plan."]
    except Exception as e:
        db.add(AiJob(household_id=h.id, kind=kind, engine="error", ok=False))
        print("[ai] analysis failed:", str(e)[:300], flush=True)  # details stay in the server log
        raise HTTPException(500, "We could not read this document right now. Please try again in a few minutes.")
    db.add(AiJob(household_id=h.id, kind=kind, engine=out["engine"], ms=out["ms"], findings=len(out.get("findings", [])) + len(out.get("medicines", [])) + len(out.get("fields", {}))))
    out["quota"] = {"used": used + (1 if out["engine"] == "claude" else 0), "cap": cap, "plan": h.plan}
    # what the browser sees: no provider or model names
    out["engine"] = "ai" if out["engine"] == "claude" else "local"
    out.pop("model", None)
    return out


class AskIn(BaseModel):
    question: str = ""
    context: dict = {}
    member: str = ""


def _ai_quota(db, h, kind: str, caps: dict) -> tuple[int, int]:
    cap = caps.get(h.plan, list(caps.values())[0])
    used = db.scalar(select(func.count(AiJob.id)).where(AiJob.household_id == h.id, AiJob.t > now() - 30 * 86400, AiJob.kind == kind, AiJob.engine == "claude")) or 0
    return used, cap


@r.post("/ai/ask")
def ai_ask(body: AskIn, request: Request, db: Session = Depends(get_db), x_dokko_key: str | None = Header(None)):
    """A question about the family's own records. The app sends structured context, never documents."""
    from . import agent
    h = household(db, x_dokko_key)
    if not h:
        raise HTTPException(400, "missing household key")
    if not agent.enabled():
        raise HTTPException(503, "The health assistant is not available right now.")
    q = body.question.strip()
    if len(q) < 3:
        raise HTTPException(400, "Ask a question first.")
    used, cap = _ai_quota(db, h, "ask", agent.ASK_CAP)
    if used >= cap:
        raise HTTPException(429, f"You have used this month's {cap} questions on the {h.plan} plan. Upgrade in Family & Privacy → Plan for more.")
    t0 = time.time()
    try:
        out = agent.ask(q, body.context)
    except Exception as e:
        AI._fail("health assistant", e)
        db.add(AiJob(household_id=h.id, kind="ask", engine="error", ok=False))
        raise HTTPException(502, "The health assistant could not answer right now. Please try again in a minute.")
    db.add(AiJob(household_id=h.id, kind="ask", engine="claude", ms=int((time.time() - t0) * 1000)))
    out["quota"] = {"used": used + 1, "cap": cap, "plan": h.plan}
    return out


@r.post("/ai/insight")
def ai_insight(body: AskIn, request: Request, db: Session = Depends(get_db), x_dokko_key: str | None = Header(None)):
    """Daily insight for one person; cached by day and by the records it was made from."""
    from . import agent
    h = household(db, x_dokko_key)
    if not h:
        raise HTTPException(400, "missing household key")
    if not agent.enabled():
        raise HTTPException(503, "Insights are not available right now.")
    key = f"{h.id}:{body.member[:32]}:{agent.ctx_key(body.context)}"
    hit = db.get(AiCache, key)
    if hit:
        return {**hit.value, "cached": True}
    used, cap = _ai_quota(db, h, "insight", agent.INSIGHT_CAP)
    if used >= cap:
        raise HTTPException(429, f"This month's insights on the {h.plan} plan are used up. Upgrade in Family & Privacy → Plan.")
    t0 = time.time()
    try:
        out = agent.insight(body.context)
    except Exception as e:
        AI._fail("daily insight", e)
        db.add(AiJob(household_id=h.id, kind="insight", engine="error", ok=False))
        raise HTTPException(502, "Insights could not be prepared right now.")
    db.add(AiJob(household_id=h.id, kind="insight", engine="claude", ms=int((time.time() - t0) * 1000)))
    db.merge(AiCache(key=key, household_id=h.id, value=out))
    db.query(AiCache).filter(AiCache.t < now() - 2 * 86400).delete()
    return {**out, "cached": False}


class MedCheckIn(BaseModel):
    context: dict = {}
    member: str = ""


@r.post("/ai/medcheck")
def ai_medcheck(body: MedCheckIn, request: Request, db: Session = Depends(get_db), x_dokko_key: str | None = Header(None)):
    """Medicine-safety check for one person: interactions, duplicates, allergy clashes, timing. Cached per medicine list per day."""
    from . import agent
    h = household(db, x_dokko_key)
    if not h:
        raise HTTPException(400, "missing household key")
    if not agent.enabled():
        raise HTTPException(503, "The medicine check is not available right now.")
    meds = body.context.get("medicines") or []
    if not meds:
        return {"alerts": [], "duplicates": [], "timing": [], "ok": True, "cached": False}
    # local checks first: an allergy named in a medicine's name is never allowed to wait for the model
    allergies = [str(a).lower() for a in (body.context.get("allergies") or [])]
    local = [{"level": "stop", "about": [m.get("name", "")], "title": "Listed allergy", "detail": f"{m.get('name', '')} matches an allergy on this profile ({a}). Do not take it; call the doctor or pharmacist."}
             for m in meds for a in allergies if a and len(a) > 3 and a in str(m.get("name", "") + " " + m.get("generic", "")).lower()]
    key = f"{h.id}:medcheck:{body.member[:32]}:{agent.ctx_key(body.context)}"
    hit = db.get(AiCache, key)
    if hit:
        out = dict(hit.value)
        out["alerts"] = local + [a for a in out.get("alerts", []) if a.get("title") != "Listed allergy"]
        return {**out, "cached": True}
    used, cap = _ai_quota(db, h, "insight", agent.INSIGHT_CAP)
    if used >= cap:
        raise HTTPException(429, f"This month's checks on the {h.plan} plan are used up. Upgrade in Family & Privacy → Plan.")
    t0 = time.time()
    try:
        out = AI.medcheck(body.context)
    except Exception as e:
        AI._fail("medicine check", e)
        db.add(AiJob(household_id=h.id, kind="insight", engine="error", ok=False))
        raise HTTPException(502, "The medicine check could not run right now.")
    db.add(AiJob(household_id=h.id, kind="insight", engine="claude", ms=int((time.time() - t0) * 1000)))
    out["alerts"] = local + out.get("alerts", [])
    out["ok"] = not any(a["level"] != "note" for a in out["alerts"])
    db.merge(AiCache(key=key, household_id=h.id, value=out))
    return {**out, "cached": False}


# ---- seasonal, videos, plans ----------------------------------------------------------------------------------------
@r.get("/seasonal")
def seasonal(month: int | None = None, region: str = "IN", db: Session = Depends(get_db)):
    m = month or datetime.now().month
    rows = db.scalars(select(Seasonal).where(Seasonal.active == True)).all()  # noqa: E712
    out = [x for x in rows if m in (x.months or []) and x.region in (region, "IN")]
    out.sort(key=lambda x: {"high": 0, "medium": 1, "low": 2}.get(x.risk, 3))
    return {"month": m, "region": region, "items": [{"id": x.id, "disease": x.disease, "emoji": x.emoji, "risk": x.risk, "summary": x.summary, "symptoms": x.symptoms,
                                                     "prevention": x.prevention, "seeDoctor": x.see_doctor, "source": x.source, "months": x.months} for x in out]}


@r.get("/videos")
def videos(db: Session = Depends(get_db)):
    rows = db.scalars(select(Video).where(Video.active == True).order_by(Video.sort)).all()  # noqa: E712
    return {"videos": [{"id": v.id, "topic": v.topic, "title": v.title, "channel": v.channel, "yt": v.yt, "lang": v.lang, "minutes": v.minutes, "source": v.source} for v in rows]}


def _upi_on() -> bool:
    from .upipay import enabled
    return enabled()


@r.get("/plans")
def plans(db: Session = Depends(get_db), x_dokko_key: str | None = Header(None)):
    h = household(db, x_dokko_key, create=False)
    rows = db.scalars(select(Plan).where(Plan.active == True).order_by(Plan.sort)).all()  # noqa: E712
    subs = db.scalars(select(Subscription).where(Subscription.household_id == h.id).order_by(Subscription.started.desc()).limit(12)).all() if h else []
    return {"plans": [{"code": p.code, "name": p.name, "month": p.price_month, "year": p.price_year, "members": p.members, "features": p.features} for p in rows],
            "current": h.plan if h else "free", "until": h.plan_until if h else None, "provider": "razorpay" if os.getenv("RAZORPAY_KEY_ID") else (_upi_on() and "upi") or ("soon" if os.getenv("APP_ENV", "production") == "production" else "demo"),
            "keyId": os.getenv("RAZORPAY_KEY_ID", ""),
            "history": [{"id": s.id, "plan": s.plan, "period": s.period, "amount": s.amount, "status": s.status, "started": s.started, "renews": s.renews, "invoice": s.invoice_no, "provider": s.provider} for s in subs]}


class SubReq(BaseModel):
    plan: str
    period: str = "month"
    paymentId: str = ""
    orderId: str = ""
    signature: str = ""


@r.post("/subscribe")
def subscribe(body: SubReq, db: Session = Depends(get_db), x_dokko_key: str | None = Header(None)):
    """Demo mode: activates at once and issues an invoice number. With Razorpay keys: creates/validates a payment first."""
    h = household(db, x_dokko_key)
    if not h:
        raise HTTPException(400, "missing household key")
    p = db.get(Plan, body.plan)
    if not p or not p.active:
        raise HTTPException(404, "plan not found")
    amount = p.price_year if body.period == "year" else p.price_month
    provider = "demo"
    ref = ""
    if amount > 0 and not os.getenv("RAZORPAY_KEY_ID") and os.getenv("APP_ENV", "production") == "production":
        # a paid plan can only be activated by a verified payment; without a payment provider nothing is switched
        raise HTTPException(503, "Pay by UPI from the plan page; the plan switches as soon as the payment is confirmed." if _upi_on() else "Paid plans open soon. You stay on the Free plan until online payment is live.")
    if os.getenv("RAZORPAY_KEY_ID") and amount > 0:
        from .payments import create_order, verify_payment
        if not body.paymentId:
            return {"action": "pay", **create_order(amount, f"{h.id}:{p.code}:{body.period}")}
        if not verify_payment(body.orderId, body.paymentId, body.signature):
            raise HTTPException(400, "payment signature invalid")
        provider, ref = "razorpay", body.paymentId
    days = 365 if body.period == "year" else 30
    start = max(now(), h.plan_until or 0) if h.plan == p.code else now()
    h.plan, h.plan_until = p.code, (start + days * 86400 if amount > 0 else None)
    n = (db.scalar(select(func.count(Subscription.id))) or 0) + 1
    sub = Subscription(household_id=h.id, plan=p.code, period=body.period, amount=amount, status="active", provider=provider, provider_ref=ref,
                       renews=h.plan_until, invoice_no=f"THT-{time.strftime('%Y%m')}-{n:05d}")
    db.add(sub)
    return {"ok": True, "plan": h.plan, "until": h.plan_until, "invoice": sub.invoice_no, "amount": amount, "provider": provider}


@r.get("/hospitals")
def hospitals(lat: float | None = None, lng: float | None = None, city: str | None = None, db: Session = Depends(get_db), x_dokko_key: str | None = Header(None)):
    h = household(db, x_dokko_key, create=False)
    la, lo, cty, approx = resolve_loc(db, Loc(lat=lat, lng=lng, city=city), h)
    rows = db.scalars(select(Store).where(Store.kind == "hospital", Store.active == True)).all()  # noqa: E712
    near = sorted(((km(la, lo, s.lat, s.lng), s) for s in rows), key=lambda x: x[0])[:5]
    return {"city": cty, "approx": approx, "hospitals": [store_json(s, d) for d, s in near]}

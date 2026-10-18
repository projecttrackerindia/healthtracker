"""Admin API (/api/admin): login, dashboard, partners (pharmacies, labs, hospitals), price lists, orders, households,
plans & subscriptions, seasonal advisories, first-aid videos, admins and the audit log. Session = signed HttpOnly cookie."""
from __future__ import annotations

import csv
import io
import time
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, Response, UploadFile, File
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .ai import LAST_ERROR as AI_LAST_ERROR
from .db import get_db
from .models import Admin, AiJob, Audit, Household, HouseholdState, HouseholdStateHistory, LabTest, Order, Plan, Seasonal, Store, StoreItem, Subscription, Video, now
from .security import check_pw, hash_pw, sign, verify
from .seed import CATALOG, TESTS

r = APIRouter(prefix="/api/admin")
COOKIE = "dk_admin"
FAILS: dict[str, list[float]] = {}


def me(request: Request, db: Session = Depends(get_db)) -> Admin:
    p = verify(request.cookies.get(COOKIE))
    if not p:
        raise HTTPException(401, "login required")
    a = db.get(Admin, p.get("id"))
    if not a:
        raise HTTPException(401, "login required")
    return a


def owner(a: Admin = Depends(me)) -> Admin:
    if a.role != "owner":
        raise HTTPException(403, "owner only")
    return a


def log(db: Session, who: str, what: str, detail: str = ""):
    db.add(Audit(who=who, what=what[:200], detail=detail[:4000]))


class Login(BaseModel):
    email: str
    password: str


@r.post("/login")
def login(body: Login, request: Request, response: Response, db: Session = Depends(get_db)):
    ip = request.client.host if request.client else "?"
    recent = [t for t in FAILS.get(ip, []) if t > time.time() - 900]
    if len(recent) >= 8:
        raise HTTPException(429, "too many attempts; try again in 15 minutes")
    a = db.scalar(select(Admin).where(Admin.email == body.email.strip().lower()))
    if not a or not check_pw(body.password, a.pw_hash):
        FAILS[ip] = recent + [time.time()]
        raise HTTPException(401, "wrong email or password")
    FAILS.pop(ip, None)
    a.last_login = now()
    log(db, a.email, "login")
    response.set_cookie(COOKIE, sign({"id": a.id, "e": a.email}), httponly=True, samesite="strict", secure=request.url.scheme == "https", max_age=12 * 3600, path="/")
    return {"ok": True, "email": a.email, "role": a.role}


@r.post("/logout")
def logout(response: Response):
    response.delete_cookie(COOKIE, path="/")
    return {"ok": True}


@r.get("/me")
def whoami(a: Admin = Depends(me)):
    return {"email": a.email, "role": a.role}


# ---- settings and client errors -------------------------------------------------------------------------------------
class ReviewerIn(BaseModel):
    name: str = ""
    qualification: str = ""
    registration: str = ""
    date: str = ""
    scope: str = ""


@r.get("/settings")
def settings_get(a: Admin = Depends(me), db: Session = Depends(get_db)):
    from .models import Setting
    rv = db.get(Setting, "reviewer")
    return {"reviewer": rv.value if rv else {}}


@r.post("/settings/reviewer")
def settings_reviewer(body: ReviewerIn, a: Admin = Depends(me), db: Session = Depends(get_db)):
    from .models import Setting
    val = {k: v.strip()[:120] for k, v in body.model_dump().items()}
    if not val["name"]:
        val = {}
    rv = db.get(Setting, "reviewer")
    if rv:
        rv.value = val
    else:
        db.add(Setting(key="reviewer", value=val))
    log(db, a.email, "reviewer", str(val)[:200])
    return {"reviewer": val}


@r.get("/client-errors")
def client_errors(a: Admin = Depends(me), db: Session = Depends(get_db)):
    from .models import ClientError
    rows = db.scalars(select(ClientError).order_by(ClientError.t.desc()).limit(100)).all()
    return [{"id": e.id, "t": e.t, "message": e.message, "stack": e.stack[:600], "page": e.page, "ua": e.ua, "version": e.version, "count": e.count} for e in rows]


@r.delete("/client-errors")
def client_errors_clear(a: Admin = Depends(me), db: Session = Depends(get_db)):
    from .models import ClientError
    n = db.query(ClientError).delete()
    return {"cleared": n}


# ---- dashboard ------------------------------------------------------------------------------------------------------
@r.post("/ai/test")
def ai_test(a: Admin = Depends(me)):
    """Why is smart reading off? Calls the model once and returns the exact error (admins only)."""
    from . import ai as AI
    return AI.test_connection()


@r.get("/stats")
def stats(a: Admin = Depends(me), db: Session = Depends(get_db)):
    t = now()
    day, week, month = t - 86400, t - 7 * 86400, t - 30 * 86400
    cnt = lambda q: db.scalar(select(func.count()).select_from(q.subquery())) or 0  # noqa: E731
    orders = db.scalars(select(Order).where(Order.created > month)).all()
    rev = sum(o.total for o in orders if o.status != "cancelled")
    rated = [o.rating for o in orders if o.rating]
    subs = db.scalars(select(Subscription).where(Subscription.started > month)).all()
    byday = {}
    for o in orders:
        d = datetime.fromtimestamp(o.created).strftime("%d %b")
        byday[d] = byday.get(d, 0) + 1
    ai = db.scalars(select(AiJob).where(AiJob.t > month)).all()
    return {
        "households": {"total": cnt(select(Household.id)), "new7": cnt(select(Household.id).where(Household.created > week)), "active1": cnt(select(Household.id).where(Household.last_seen > day)),
                       "paid": cnt(select(Household.id).where(Household.plan != "free"))},
        "partners": {k: cnt(select(Store.id).where(Store.kind == k, Store.active == True)) for k in ("pharmacy", "lab", "hospital")},  # noqa: E712
        "pending": cnt(select(Store.id).where(Store.verified == False)),  # noqa: E712
        "orders": {"month": len(orders), "revenue": rev, "avgRating": round(sum(rated) / len(rated), 2) if rated else None, "open": cnt(select(Order.id).where(Order.status.in_(("placed", "checking", "packing", "out", "confirmed", "collected", "processing")))),
                   "byDay": sorted(byday.items(), key=lambda kv: datetime.strptime(kv[0] + " " + str(datetime.now().year), "%d %b %Y"))},
        "subscriptions": {"month": len(subs), "mrr": sum(s.amount if s.period == "month" else round(s.amount / 12) for s in subs if s.status == "active")},
        "ai": {"month": len(ai), "claude": sum(1 for j in ai if j.engine == "claude"), "local": sum(1 for j in ai if j.engine == "local"), "errors": sum(1 for j in ai if not j.ok),
               "avgMs": round(sum(j.ms for j in ai) / len(ai)) if ai else 0},
        "engine": "claude" if __import__("os").getenv("ANTHROPIC_API_KEY") else "local",
        "aiLastError": AI_LAST_ERROR,
    }


# ---- partners -------------------------------------------------------------------------------------------------------
class StoreIn(BaseModel):
    kind: str = "pharmacy"
    name: str
    brand: str = ""
    address: str = ""
    area: str = ""
    city: str = ""
    pin: str = ""
    lat: float
    lng: float
    phone: str = ""
    hours: str = "8 am – 10 pm"
    open_24h: bool = False
    licence: str = ""
    discount_pct: float = 0
    delivery: bool = True
    delivery_fee: int = 30
    free_above: int = 499
    eta_min: int = 60
    home_collection: bool = False
    collection_fee: int = 0
    verified: bool = False
    active: bool = True
    owner_email: str = ""
    notes: str = ""


def sj(s: Store):
    return {c.name: getattr(s, c.name) for c in Store.__table__.columns}


@r.get("/stores")
def admin_stores(kind: str = "", q: str = "", pending: int = 0, a: Admin = Depends(me), db: Session = Depends(get_db)):
    st = select(Store).order_by(Store.created.desc())
    if kind:
        st = st.where(Store.kind == kind)
    if pending:
        st = st.where(Store.verified == False)  # noqa: E712
    rows = db.scalars(st).all()
    if q:
        ql = q.lower()
        rows = [s for s in rows if ql in (s.name + s.city + s.area + s.brand + s.owner_email).lower()]
    counts = dict(db.execute(select(Order.store_id, func.count(Order.id)).group_by(Order.store_id)).all())
    return {"stores": [{**sj(s), "orders": counts.get(s.id, 0), "items": len(s.items) if s.kind == "pharmacy" else len(s.tests)} for s in rows[:500]]}


@r.post("/stores")
def add_store(body: StoreIn, a: Admin = Depends(me), db: Session = Depends(get_db)):
    s = Store(**body.model_dump())
    db.add(s)
    db.flush()
    if s.kind == "pharmacy":  # start with the full catalogue at the store's discount; edit later
        for m in CATALOG:
            db.add(StoreItem(store_id=s.id, sku=m["id"], name=m["name"], mrp=m["mrp"], price=max(1, round(m["mrp"] * (1 - s.discount_pct / 100))), stock=20))
    elif s.kind == "lab":
        for code, (name, price, tat, fast) in TESTS.items():
            db.add(LabTest(store_id=s.id, code=code, name=name, price=max(50, round(price * (1 - s.discount_pct / 100) / 10) * 10), tat_hours=tat, fasting=fast))
    log(db, a.email, f"store.add {s.kind} {s.name}")
    return sj(s)


@r.put("/stores/{sid}")
def edit_store(sid: str, body: dict, a: Admin = Depends(me), db: Session = Depends(get_db)):
    s = db.get(Store, sid)
    if not s:
        raise HTTPException(404)
    allowed = {c.name for c in Store.__table__.columns} - {"id", "created"}
    for k, v in body.items():
        if k in allowed:
            setattr(s, k, v)
    log(db, a.email, f"store.edit {s.name}", str({k: v for k, v in body.items() if k in allowed})[:1000])
    return sj(s)


@r.delete("/stores/{sid}")
def del_store(sid: str, a: Admin = Depends(owner), db: Session = Depends(get_db)):
    s = db.get(Store, sid)
    if not s:
        raise HTTPException(404)
    s.active = False
    log(db, a.email, f"store.deactivate {s.name}")
    return {"ok": True}


@r.get("/stores/{sid}/prices")
def prices(sid: str, a: Admin = Depends(me), db: Session = Depends(get_db)):
    s = db.get(Store, sid)
    if not s:
        raise HTTPException(404)
    if s.kind == "lab":
        return {"kind": "lab", "rows": [{"id": t.id, "code": t.code, "name": t.name, "price": t.price, "tat_hours": t.tat_hours, "fasting": t.fasting} for t in sorted(s.tests, key=lambda t: t.name)]}
    return {"kind": "pharmacy", "rows": [{"id": i.id, "sku": i.sku, "name": i.name, "mrp": i.mrp, "price": i.price, "stock": i.stock} for i in sorted(s.items, key=lambda i: i.name)]}


@r.put("/stores/{sid}/prices")
def set_prices(sid: str, body: dict, a: Admin = Depends(me), db: Session = Depends(get_db)):
    """body.rows: [{id, price, stock|tat_hours}] ; body.add: [{sku|code, name, price, ...}] ; body.remove: [ids]"""
    s = db.get(Store, sid)
    if not s:
        raise HTTPException(404)
    M = LabTest if s.kind == "lab" else StoreItem
    for row in body.get("rows", []):
        o = db.get(M, row.get("id"))
        if not o or o.store_id != s.id:
            continue
        for k in ("price", "stock", "tat_hours", "fasting", "name", "mrp"):
            if k in row and hasattr(o, k):
                setattr(o, k, row[k])
    for row in body.get("add", []):
        if s.kind == "lab":
            db.add(LabTest(store_id=s.id, code=row.get("code", "custom")[:40], name=row.get("name", "")[:120], price=int(row.get("price", 0)), tat_hours=int(row.get("tat_hours", 24)), fasting=bool(row.get("fasting"))))
        else:
            db.add(StoreItem(store_id=s.id, sku=row.get("sku", "custom")[:40], name=row.get("name", "")[:120], mrp=int(row.get("mrp", row.get("price", 0))), price=int(row.get("price", 0)), stock=int(row.get("stock", 20))))
    for rid in body.get("remove", []):
        o = db.get(M, rid)
        if o and o.store_id == s.id:
            db.delete(o)
    log(db, a.email, f"prices.edit {s.name}", f"{len(body.get('rows', []))} rows, +{len(body.get('add', []))}, -{len(body.get('remove', []))}")
    return {"ok": True}


@r.post("/stores/import")
async def import_stores(file: UploadFile = File(...), a: Admin = Depends(owner), db: Session = Depends(get_db)):
    """CSV columns: kind,name,brand,address,area,city,pin,lat,lng,phone,hours,licence,discount_pct,delivery_fee,free_above,eta_min,home_collection,collection_fee,owner_email"""
    txt = (await file.read()).decode("utf-8", "ignore")
    n = 0
    for row in csv.DictReader(io.StringIO(txt)):
        try:
            body = StoreIn(**{k: (v if v != "" else StoreIn.model_fields[k].default) for k, v in row.items() if k in StoreIn.model_fields})
        except Exception:
            continue
        add_store(body, a, db)
        n += 1
    log(db, a.email, f"stores.import {n}")
    return {"imported": n}


# ---- orders ---------------------------------------------------------------------------------------------------------
@r.get("/orders")
def admin_orders(status: str = "", store: str = "", limit: int = 200, a: Admin = Depends(me), db: Session = Depends(get_db)):
    from .routes import order_json
    st = select(Order).order_by(Order.created.desc()).limit(limit)
    if status:
        st = st.where(Order.status == status)
    if store:
        st = st.where(Order.store_id == store)
    rows = db.scalars(st).all()
    return {"orders": [{**order_json(o), "household": o.household.name or o.household.key[:8] + "…", "householdId": o.household_id} for o in rows]}


class Advance(BaseModel):
    status: str


@r.post("/orders/{oid}/status")
def set_status(oid: str, body: Advance, a: Admin = Depends(me), db: Session = Depends(get_db)):
    from .routes import STEPS_LAB, STEPS_MED, order_json
    o = db.get(Order, oid)
    if not o:
        raise HTTPException(404)
    steps = STEPS_LAB if o.kind == "lab" else STEPS_MED
    if body.status != "cancelled" and body.status not in [k for k, _ in steps]:
        raise HTTPException(400, "unknown status")
    o.status = body.status
    o.timeline = (o.timeline or []) + [{"s": body.status, "t": now(), "by": a.email}]
    log(db, a.email, f"order.status {oid} → {body.status}")
    return order_json(o)


# ---- households -----------------------------------------------------------------------------------------------------
@r.get("/households")
def households(q: str = "", a: Admin = Depends(me), db: Session = Depends(get_db)):
    rows = db.scalars(select(Household).order_by(Household.last_seen.desc()).limit(1000)).all()
    if q:
        ql = q.lower()
        rows = [h for h in rows if ql in (h.name + h.city + h.email + h.phone + h.key).lower()]
    oc = dict(db.execute(select(Order.household_id, func.count(Order.id)).group_by(Order.household_id)).all())
    ac = dict(db.execute(select(AiJob.household_id, func.count(AiJob.id)).group_by(AiJob.household_id)).all())
    return {"households": [{"id": h.id, "key": h.key[:6] + "…", "name": h.name, "city": h.city, "plan": h.plan, "planUntil": h.plan_until, "members": h.members, "blocked": h.blocked,
                            "created": h.created, "lastSeen": h.last_seen, "orders": oc.get(h.id, 0), "ai": ac.get(h.id, 0), "phone": h.phone, "email": h.email, "notes": h.notes} for h in rows]}


@r.get("/households/{hid}/history")
def household_history(hid: str, a: Admin = Depends(me), db: Session = Depends(get_db)):
    """Previous versions of the family's record (contents stay encrypted; only sizes, times and who saved are shown)."""
    cur = db.get(HouseholdState, hid)
    rows = db.scalars(select(HouseholdStateHistory).where(HouseholdStateHistory.household_id == hid).order_by(HouseholdStateHistory.version.desc()).limit(60)).all()
    return {"current": {"version": cur.version, "size": cur.size, "updatedBy": cur.updated_by} if cur else None,
            "history": [{"id": x.id, "version": x.version, "size": x.size, "t": x.t, "updatedBy": x.updated_by, "sections": len(x.sect or {})} for x in rows]}


@r.post("/households/{hid}/restore/{hist_id}")
def household_restore(hid: str, hist_id: int, a: Admin = Depends(me), db: Session = Depends(get_db)):
    """Put an earlier version back as the live record. The replaced one is itself kept in history, so a restore can be undone."""
    x = db.get(HouseholdStateHistory, hist_id)
    cur = db.get(HouseholdState, hid)
    if not x or x.household_id != hid or not cur:
        raise HTTPException(404)
    db.add(HouseholdStateHistory(household_id=hid, version=cur.version, blob=cur.blob, sect=cur.sect or {}, size=cur.size, updated_by=cur.updated_by or ""))
    cur.version, cur.blob, cur.sect, cur.size, cur.updated_by = cur.version + 1, x.blob, x.sect or {}, x.size, "restore:" + a.email
    log(db, a.email, f"household.restore {hid}", f"from version {x.version}")
    return {"ok": True, "version": cur.version}


@r.put("/households/{hid}")
def edit_household(hid: str, body: dict, a: Admin = Depends(me), db: Session = Depends(get_db)):
    h = db.get(Household, hid)
    if not h:
        raise HTTPException(404)
    for k in ("plan", "plan_until", "blocked", "notes", "name"):
        if k in body:
            setattr(h, k, body[k])
    if "plan" in body:
        db.add(Subscription(household_id=h.id, plan=h.plan, period="admin", amount=0, status="active", provider="admin", renews=h.plan_until, invoice_no=""))
    log(db, a.email, f"household.edit {hid}", str(body)[:500])
    return {"ok": True}


# ---- plans & billing ------------------------------------------------------------------------------------------------
@r.get("/plans")
def admin_plans(a: Admin = Depends(me), db: Session = Depends(get_db)):
    rows = db.scalars(select(Plan).order_by(Plan.sort)).all()
    subs = db.scalars(select(Subscription).order_by(Subscription.started.desc()).limit(300)).all()
    names = {h.id: (h.name or h.key[:8] + "…") for h in db.scalars(select(Household).where(Household.id.in_({s.household_id for s in subs}))).all()} if subs else {}
    return {"plans": [{c.name: getattr(p, c.name) for c in Plan.__table__.columns} for p in rows],
            "subscriptions": [{"id": s.id, "household": names.get(s.household_id, "?"), "plan": s.plan, "period": s.period, "amount": s.amount, "status": s.status, "provider": s.provider,
                               "ref": s.provider_ref, "started": s.started, "renews": s.renews, "invoice": s.invoice_no} for s in subs],
            "provider": "razorpay" if __import__("os").getenv("RAZORPAY_KEY_ID") else "demo"}


@r.put("/plans/{code}")
def edit_plan(code: str, body: dict, a: Admin = Depends(owner), db: Session = Depends(get_db)):
    p = db.get(Plan, code)
    if not p:
        p = Plan(code=code[:24], name=body.get("name", code))
        db.add(p)
    for k in ("name", "price_month", "price_year", "members", "features", "active", "sort"):
        if k in body:
            setattr(p, k, body[k])
    log(db, a.email, f"plan.edit {code}", str(body)[:500])
    return {"ok": True}


# ---- content: seasonal + videos -------------------------------------------------------------------------------------
@r.get("/seasonal")
def admin_seasonal(a: Admin = Depends(me), db: Session = Depends(get_db)):
    return {"items": [{c.name: getattr(x, c.name) for c in Seasonal.__table__.columns} for x in db.scalars(select(Seasonal).order_by(Seasonal.disease)).all()]}


@r.post("/seasonal")
def save_seasonal(body: dict, a: Admin = Depends(me), db: Session = Depends(get_db)):
    x = db.get(Seasonal, body.get("id")) if body.get("id") else None
    if x is None:
        x = Seasonal(disease=body.get("disease", "New advisory"))
        db.add(x)
    for k in ("region", "months", "disease", "emoji", "risk", "summary", "symptoms", "prevention", "see_doctor", "source", "active"):
        if k in body:
            setattr(x, k, body[k])
    x.updated = now()
    db.flush()
    log(db, a.email, f"seasonal.save {x.disease}")
    return {"id": x.id}


@r.delete("/seasonal/{sid}")
def del_seasonal(sid: str, a: Admin = Depends(me), db: Session = Depends(get_db)):
    x = db.get(Seasonal, sid)
    if x:
        db.delete(x)
        log(db, a.email, f"seasonal.delete {x.disease}")
    return {"ok": True}


@r.get("/videos")
def admin_videos(a: Admin = Depends(me), db: Session = Depends(get_db)):
    return {"videos": [{c.name: getattr(v, c.name) for c in Video.__table__.columns} for v in db.scalars(select(Video).order_by(Video.sort)).all()]}


@r.post("/videos")
def save_video(body: dict, a: Admin = Depends(me), db: Session = Depends(get_db)):
    v = db.get(Video, body.get("id")) if body.get("id") else None
    yt = str(body.get("yt", "")).strip()
    if "youtube.com" in yt or "youtu.be" in yt:
        import re
        m = re.search(r"(?:v=|youtu\.be/|embed/)([A-Za-z0-9_-]{11})", yt)
        yt = m.group(1) if m else yt
    if v is None:
        v = Video(topic=body.get("topic", "other"), title=body.get("title", ""), channel=body.get("channel", ""), yt=yt)
        db.add(v)
    for k in ("topic", "title", "channel", "lang", "minutes", "source", "verified", "active", "sort"):
        if k in body:
            setattr(v, k, body[k])
    if yt:
        v.yt = yt[:16]
    db.flush()
    log(db, a.email, f"video.save {v.title}")
    return {"id": v.id}


@r.delete("/videos/{vid}")
def del_video(vid: str, a: Admin = Depends(me), db: Session = Depends(get_db)):
    v = db.get(Video, vid)
    if v:
        db.delete(v)
    return {"ok": True}


# ---- admins + audit -------------------------------------------------------------------------------------------------
class AdminIn(BaseModel):
    email: str
    password: str = ""
    role: str = "ops"


@r.get("/admins")
def admins(a: Admin = Depends(owner), db: Session = Depends(get_db)):
    return {"admins": [{"id": x.id, "email": x.email, "role": x.role, "created": x.created, "lastLogin": x.last_login} for x in db.scalars(select(Admin)).all()]}


@r.post("/admins")
def add_admin(body: AdminIn, a: Admin = Depends(owner), db: Session = Depends(get_db)):
    e = body.email.strip().lower()
    x = db.scalar(select(Admin).where(Admin.email == e))
    if x is None:
        if len(body.password) < 8:
            raise HTTPException(400, "password: 8 characters minimum")
        x = Admin(email=e, pw_hash=hash_pw(body.password), role=body.role if body.role in ("owner", "ops", "content") else "ops")
        db.add(x)
    else:
        if body.password:
            if len(body.password) < 8:
                raise HTTPException(400, "password: 8 characters minimum")
            x.pw_hash = hash_pw(body.password)
        x.role = body.role if body.role in ("owner", "ops", "content") else x.role
    log(db, a.email, f"admin.save {e} {x.role}")
    return {"ok": True}


@r.delete("/admins/{aid}")
def del_admin(aid: int, a: Admin = Depends(owner), db: Session = Depends(get_db)):
    if aid == a.id:
        raise HTTPException(400, "cannot delete yourself")
    x = db.get(Admin, aid)
    if x:
        db.delete(x)
        log(db, a.email, f"admin.delete {x.email}")
    return {"ok": True}


@r.get("/audit")
def audit(limit: int = 200, a: Admin = Depends(me), db: Session = Depends(get_db)):
    return {"rows": [{"t": x.t, "who": x.who, "what": x.what, "detail": x.detail} for x in db.scalars(select(Audit).order_by(Audit.t.desc()).limit(limit)).all()]}


# ---- accounts (sign-in identities) -----------------------------------------------------------------------------------
@r.get("/users")
def users(q: str = "", a: Admin = Depends(me), db: Session = Depends(get_db)):
    from .models import AuthSession, Passkey, User
    rows = db.scalars(select(User).order_by(User.created.desc()).limit(2000)).all()
    if q:
        ql = q.lower()
        rows = [u for u in rows if ql in ((u.name or "") + (u.email or "") + (u.phone or "")).lower()]
    pk = dict(db.execute(select(Passkey.user_id, func.count(Passkey.id)).group_by(Passkey.user_id)).all())
    ss = dict(db.execute(select(AuthSession.user_id, func.count(AuthSession.id)).where(AuthSession.expires > now()).group_by(AuthSession.user_id)).all())
    plans = {h.id: h.plan for h in db.scalars(select(Household).where(Household.id.in_({u.household_id for u in rows if u.household_id}))).all()} if rows else {}
    return {"users": [{"id": u.id, "name": u.name, "email": u.email, "phone": u.phone, "emailVerified": u.email_verified, "phoneVerified": u.phone_verified,
                       "passkeys": pk.get(u.id, 0), "sessions": ss.get(u.id, 0), "twoStep": u.two_step, "hasPassword": bool(u.pw_hash),
                       "locked": bool(u.locked_until and u.locked_until > now()), "disabled": u.disabled, "plan": plans.get(u.household_id, "free"),
                       "created": u.created, "lastLogin": u.last_login} for u in rows]}


@r.post("/users/{uid}")
def user_action(uid: str, body: dict, a: Admin = Depends(me), db: Session = Depends(get_db)):
    from .models import AuthSession, User
    u = db.get(User, uid)
    if not u:
        raise HTTPException(404)
    act = body.get("action")
    if act == "unlock":
        u.locked_until, u.failed = None, 0
    elif act == "disable":
        u.disabled = True
        db.query(AuthSession).filter(AuthSession.user_id == u.id).delete()
    elif act == "enable":
        u.disabled = False
    elif act == "signout":
        db.query(AuthSession).filter(AuthSession.user_id == u.id).delete()
    else:
        raise HTTPException(400, "unknown action")
    log(db, a.email, f"user.{act} {u.email or u.phone}")
    return {"ok": True}

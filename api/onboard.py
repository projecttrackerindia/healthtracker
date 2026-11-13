"""Partner onboarding: what a lab, pharmacy or hospital must show us before families can walk in.

Admin side (/api/admin/onboard): the list with what's missing, one partner in full, edits, steps, go-live and pause.
Partner side (/api/partner/onboarding): the shop owner, standing in the shop, drops the live pin and takes the photos.
A pin dropped from somewhere else is caught by its accuracy and by how far it lands from the address we already have.

Photos are re-encoded on the way in, which throws away everything the camera wrote into the file (EXIF, GPS, maker
notes). The time and the place we keep are the ones the phone told us when it was taken, stored next to it."""
from __future__ import annotations

import io
import math
import re

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import Response as RawResponse
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from . import storage
from .admin import log, me as admin_me
from .db import get_db
from .models import Admin, PartnerUser, Store, StoreItem, new_id, now
from .partner import me as partner_me, my_store

ar = APIRouter(prefix="/api/admin/onboard")
pr = APIRouter(prefix="/api/partner/onboarding")
pub = APIRouter(prefix="/api/v2/stores")

PHOTO_SLOTS = [("front", "Shop front with signboard"), ("reception", "Reception"), ("sample", "Sample / counter area"),
               ("inside", "Lab bench / store inside"), ("licence", "Licence on the wall"), ("waiting", "Waiting area")]
NEEDED = {"front", "reception", "inside", "licence"}
STEPS = ["Details", "Photos & location", "Licence", "Prices", "Team", "Bank & go live"]
MAX_PHOTO = 8 * 1024 * 1024
PROFILE_KEYS = {"hoursWeek", "hoursSun", "homeHours", "pins", "reportTime", "access", "languages", "payment", "femaleCollector",
                "frontDesk", "ownerName", "ownerPhone", "pathologist", "pathologistReg", "nablExpiry", "establishmentReg",
                "bmwAgreement", "sampleReport", "bankName", "bankLast4", "payoutCycle", "emergency", "parking",
                "licenceExpiry", "bankIfsc", "bankHolder"}
AGREEMENT_VERSION = "2026-11"   # bump when the partner agreement text changes; partners accept the new one


def exp_of(p: dict) -> str:
    """Licence valid-until date: drug licence (pharmacy), NABL (lab) or clinical establishment (hospital)."""
    return (p or {}).get("licenceExpiry") or (p or {}).get("nablExpiry") or ""


def expire_partners(db: Session) -> dict:
    """Daily: a partner whose licence has lapsed stops receiving orders the same day, and a doctor or pharmacist whose
    council registration has lapsed loses approval. Both are logged and can be restored once renewed."""
    from .models import Audit
    today, paused, lapsed = _today(), 0, 0
    for st in db.scalars(select(Store).where(Store.active == True, Store.verified == True)).all():  # noqa: E712
        e = exp_of(st.profile or {})
        if e and e < today:
            st.active = False
            db.add(Audit(who="system", what=f"onboard.auto_pause {st.id}", detail=f"licence expired {e}"))
            paused += 1
    for u in db.scalars(select(PartnerUser).where(PartnerUser.verified == True)).all():  # noqa: E712
        if u.reg_expiry and u.reg_expiry < today:
            u.verified, u.verify_by = False, ""
            db.add(Audit(who="system", what=f"partner.registration_lapsed {u.id}", detail=u.reg_expiry))
            lapsed += 1
    db.commit()
    return {"paused": paused, "lapsed": lapsed}


def _file_ns(s: Store) -> str:
    return f"store-{s.id}"[:32]


def km(a: tuple[float, float], b: tuple[float, float]) -> float:
    la1, lo1, la2, lo2 = map(math.radians, (*a, *b))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 6371 * 2 * math.asin(math.sqrt(h))


def checks(db: Session, s: Store) -> list[dict]:
    """One row per onboarding step: done or not, and in plain words what is still missing."""
    p = s.profile or {}
    shots = {x.get("slot") for x in (s.photos or [])}
    users = db.scalar(select(func.count(PartnerUser.id)).where(PartnerUser.store_id == s.id, PartnerUser.active == True)) or 0  # noqa: E712
    items = db.scalar(select(func.count(StoreItem.id)).where(StoreItem.store_id == s.id)) or 0
    exp = exp_of(p)
    expired = bool(exp) and exp < _today()
    miss = [
        [x for x, ok in (("name", s.name), ("address", s.address), ("PIN code", s.pin), ("shop phone", s.phone), ("owner email", s.owner_email)) if not ok],
        ([f"{len(NEEDED - shots)} photo(s): " + ", ".join(dict(PHOTO_SLOTS)[k] for k in sorted(NEEDED - shots))] if NEEDED - shots else [])
        + (["live pin from the shop"] if not s.pin_at else (["a more accurate pin (now ±%d m)" % s.pin_acc] if s.pin_acc > 50 else []))
        + ([] if s.landmark else ["landmark"]),
        ([] if s.licence else ["licence / NABL number"]) + (["licence has expired"] if expired else [])
        + ([] if exp else ["licence valid-until date"]) + ([] if s.gstin else ["GSTIN"]),
        [] if items else ["price list"],
        ([] if users else ["owner sign-in"]) + ([] if s.kind != "lab" or p.get("pathologist") else ["signing pathologist"]),
        ([] if p.get("bankLast4") and p.get("bankIfsc") and p.get("bankHolder") else ["payout bank account (holder, IFSC, last 4)"])
        + ([] if (p.get("agreement") or {}).get("v") == AGREEMENT_VERSION else ["partner agreement accepted by the owner"]),
    ]
    return [{"step": i + 1, "name": STEPS[i], "done": not m, "missing": m} for i, m in enumerate(miss)]


def _today() -> str:
    import time
    return time.strftime("%Y-%m-%d", time.localtime())


def status_of(s: Store, ck: list[dict]) -> tuple[str, str]:
    """(tab, tag) — tab is review | live | paused; tag is the one-line state shown in the list."""
    if not s.active:
        return "paused", "Paused"
    exp = exp_of(s.profile or {})
    if exp and exp < _today():
        return ("paused" if s.verified else "review"), "Licence expired"
    if s.verified:
        soon = exp and exp < _plus_days(30)
        return "live", ("Licence expires soon" if soon else "Live")
    first = next((c for c in ck if not c["done"]), None)
    if not first:
        return "review", "Ready to go live"
    if s.created > now() - 86400 and first["step"] == 1:
        return "review", "New"
    return "review", {2: "Photos or pin missing", 3: "Licence check", 4: "Prices missing", 5: "Team missing", 6: "Bank missing"}.get(first["step"], "Details missing")


def _plus_days(n: int) -> str:
    import time
    return time.strftime("%Y-%m-%d", time.localtime(time.time() + n * 86400))


def card(db: Session, s: Store, full: bool = False) -> dict:
    ck = checks(db, s)
    tab, tag = status_of(s, ck)
    out = {"id": s.id, "kind": s.kind, "name": s.name, "area": s.area, "city": s.city, "created": s.created, "tab": tab, "tag": tag,
           "step": next((c["step"] for c in ck if not c["done"]), 7), "verified": s.verified, "active": s.active,
           "cover": next((x["id"] for x in (s.photos or []) if x.get("slot") == "front"), None)}
    if full:
        p = s.profile or {}
        users = db.scalars(select(PartnerUser).where(PartnerUser.store_id == s.id)).all()
        out.update({
            "address": s.address, "pin": s.pin, "phone": s.phone, "ownerEmail": s.owner_email, "landmark": s.landmark, "lat": s.lat, "lng": s.lng,
            "pinAt": s.pin_at, "pinBy": s.pin_by, "pinAcc": s.pin_acc, "hours": s.hours, "open24h": s.open_24h, "licence": s.licence, "gstin": s.gstin,
            "homeCollection": s.home_collection, "collectionFee": s.collection_fee, "freeAbove": s.free_above, "etaMin": s.eta_min,
            "commission": s.commission_pct, "profile": {k: p.get(k) for k in PROFILE_KEYS if k in p},
            "photos": [{k: x.get(k) for k in ("id", "slot", "label", "t", "acc", "by", "far")} for x in (s.photos or [])],
            "slots": [{"slot": k, "label": v, "needed": k in NEEDED} for k, v in PHOTO_SLOTS],
            "checks": ck, "steps": STEPS, "publicPath": __import__("api.public_pages", fromlist=["path_of"]).path_of(s) if s.verified and s.active else "",
            "items": db.scalar(select(func.count(StoreItem.id)).where(StoreItem.store_id == s.id)) or 0,
            "team": [{"name": u.name, "email": u.email, "role": u.role, "verified": u.verified, "active": u.active, "lastLogin": u.last_login} for u in users],
        })
    return out


def _store(db: Session, sid: str) -> Store:
    s = db.get(Store, sid)
    if not s:
        raise HTTPException(404, "No such partner")
    return s


# ---- admin -----------------------------------------------------------------------------------------------------------
@ar.get("")
def board(kind: str = "lab", tab: str = "review", q: str = "", a: Admin = Depends(admin_me), db: Session = Depends(get_db)):
    rows = db.scalars(select(Store).where(Store.kind == kind).order_by(Store.created.desc())).all()
    cards = [card(db, s) for s in rows]
    counts = {t: sum(1 for c in cards if c["tab"] == t) for t in ("review", "live", "paused")}
    ql = q.strip().lower()
    shown = [c for c in cards if c["tab"] == tab and (not ql or ql in f"{c['name']} {c['area']} {c['city']}".lower()
                                                         or ql in ((db.get(Store, c["id"]).licence or "").lower()))]
    pins = set()
    for s in rows:
        if s.verified and s.active:
            pins.update(str(x).strip() for x in ((s.profile or {}).get("pins") or "").replace(",", " ").split() if x.strip())
    soon = sum(1 for s in rows if s.verified and (s.profile or {}).get("nablExpiry") and (s.profile or {})["nablExpiry"] < _plus_days(30))
    items = db.scalar(select(func.count(StoreItem.id)).join(Store, Store.id == StoreItem.store_id).where(Store.kind == kind, Store.verified == True)) or 0  # noqa: E712
    return {"counts": counts, "rows": shown, "kpi": {"live": counts["live"], "waiting": sum(1 for c in cards if c["tab"] == "review" and c["tag"] == "Ready to go live") or counts["review"],
                                                     "items": items, "pins": len(pins), "expiring": soon}}


@ar.get("/{sid}")
def one(sid: str, a: Admin = Depends(admin_me), db: Session = Depends(get_db)):
    return card(db, _store(db, sid), True)


class EditIn(BaseModel):
    name: str | None = None
    address: str | None = None
    area: str | None = None
    city: str | None = None
    pin: str | None = None
    phone: str | None = None
    ownerEmail: str | None = None
    landmark: str | None = None
    hours: str | None = None
    licence: str | None = None
    gstin: str | None = None
    homeCollection: bool | None = None
    freeAbove: int | None = None
    commission: float | None = None
    profile: dict | None = None


def _clean(v, n=160):
    return re.sub(r"[<>\x00-\x1f]", "", str(v or "")).strip()[:n]


@ar.put("/{sid}")
def edit(sid: str, body: EditIn, a: Admin = Depends(admin_me), db: Session = Depends(get_db)):
    s = _store(db, sid)
    m = {"name": ("name", 120), "address": ("address", 240), "area": ("area", 80), "city": ("city", 80), "pin": ("pin", 12),
         "phone": ("phone", 24), "ownerEmail": ("owner_email", 120), "landmark": ("landmark", 160), "hours": ("hours", 80),
         "licence": ("licence", 64), "gstin": ("gstin", 20)}
    for k, (col, n) in m.items():
        v = getattr(body, k)
        if v is not None:
            setattr(s, col, _clean(v, n))
    if body.pin is not None and s.pin and not re.fullmatch(r"\d{6}", s.pin):
        raise HTTPException(400, "PIN code is 6 digits")
    if body.gstin is not None and s.gstin and not re.fullmatch(r"\d{2}[A-Z]{5}\d{4}[A-Z][0-9A-Z]Z[0-9A-Z]", s.gstin.upper()):
        raise HTTPException(400, "That GSTIN doesn't look right (15 characters, e.g. 36AABCU9603R1ZM)")
    s.gstin = s.gstin.upper()
    if body.homeCollection is not None:
        s.home_collection = body.homeCollection
    if body.freeAbove is not None:
        s.free_above = max(0, int(body.freeAbove))
    if body.commission is not None:
        s.commission_pct = max(0.0, min(50.0, float(body.commission)))
    if body.profile is not None:
        p = dict(s.profile or {})
        for k, v in body.profile.items():
            if k in PROFILE_KEYS:
                p[k] = v if isinstance(v, bool) else _clean(v, 300)
        if p.get("bankLast4") and not re.fullmatch(r"\d{4}", p["bankLast4"]):
            raise HTTPException(400, "Only the last 4 digits of the account, please")
        for k in ("nablExpiry", "licenceExpiry"):
            if p.get(k) and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", p[k]):
                raise HTTPException(400, "Expiry date as YYYY-MM-DD")
        if p.get("bankIfsc"):
            p["bankIfsc"] = p["bankIfsc"].upper().replace(" ", "")
            if not re.fullmatch(r"[A-Z]{4}0[A-Z0-9]{6}", p["bankIfsc"]):
                raise HTTPException(400, "That IFSC doesn't look right (11 characters, e.g. HDFC0001234)")
        s.profile = p
    log(db, a.email, f"onboard.edit {s.id}", ",".join(k for k, v in body.model_dump().items() if v is not None))
    return card(db, s, True)


class StateIn(BaseModel):
    action: str  # live | pause | resume | decline
    note: str = ""


@ar.post("/{sid}/state")
def state(sid: str, body: StateIn, a: Admin = Depends(admin_me), db: Session = Depends(get_db)):
    s = _store(db, sid)
    if body.action == "live":
        left = [c for c in checks(db, s) if not c["done"]]
        if left:
            raise HTTPException(409, "Not ready yet: " + "; ".join(f"{c['name']} — {', '.join(c['missing'])}" for c in left))
        s.verified, s.active, s.step = True, True, 7
        from .booking import notify_area
        notify_area(db, s)
    elif body.action == "pause":
        s.active = False
    elif body.action == "resume":
        s.active = True
    elif body.action == "decline":
        s.active, s.verified = False, False
    else:
        raise HTTPException(400, "unknown action")
    log(db, a.email, f"onboard.{body.action} {s.id}", body.note[:400])
    return card(db, s, True)


def _save_photo(db: Session, s: Store, slot: str, data: bytes, lat: float | None, lng: float | None, acc: int | None, by: str) -> dict:
    if slot not in dict(PHOTO_SLOTS):
        raise HTTPException(400, "Unknown photo slot")
    if len(data) > MAX_PHOTO:
        raise HTTPException(413, "Photo is over 8 MB")
    from PIL import Image, ImageOps
    try:
        im = Image.open(io.BytesIO(data))
        im.verify()
        im = ImageOps.exif_transpose(Image.open(io.BytesIO(data))).convert("RGB")
    except Exception:
        raise HTTPException(400, "That file is not a photo")
    im.thumbnail((1600, 1600))
    out = io.BytesIO()
    im.save(out, "JPEG", quality=84, optimize=True)  # a fresh file: no EXIF, GPS or maker notes survive
    pid = new_id("ph")
    storage.put(db, _file_ns(s), pid, out.getvalue(), "image/jpeg", f"{slot}.jpg", by)
    far = None
    if lat is not None and lng is not None and s.lat is not None:
        far = round(km((lat, lng), (s.lat, s.lng)) * 1000)
    photos = [x for x in (s.photos or []) if x.get("slot") != slot]
    rec = {"id": pid, "slot": slot, "label": dict(PHOTO_SLOTS)[slot], "t": now(), "lat": lat, "lng": lng, "acc": acc, "by": by, "far": far}
    old = [x["id"] for x in (s.photos or []) if x.get("slot") == slot]
    for o in old:
        from .models import StoredFile
        f = db.get(StoredFile, (_file_ns(s), o))
        if f:
            db.delete(f)
    s.photos = photos + [rec]
    return rec


@ar.post("/{sid}/photos")
async def admin_photo(sid: str, slot: str = Form(...), file: UploadFile = File(...), a: Admin = Depends(admin_me), db: Session = Depends(get_db)):
    s = _store(db, sid)
    rec = _save_photo(db, s, slot, await file.read(), None, None, None, "admin:" + a.email)
    log(db, a.email, f"onboard.photo {s.id} {slot}")
    return rec


@ar.delete("/{sid}/photos/{pid}")
def admin_photo_del(sid: str, pid: str, a: Admin = Depends(admin_me), db: Session = Depends(get_db)):
    s = _store(db, sid)
    s.photos = [x for x in (s.photos or []) if x.get("id") != pid]
    from .models import StoredFile
    f = db.get(StoredFile, (_file_ns(s), pid))
    if f:
        db.delete(f)
    log(db, a.email, f"onboard.photo.delete {s.id}")
    return {"ok": True}


def _photo_bytes(db: Session, s: Store, pid: str) -> RawResponse:
    if not any(x.get("id") == pid for x in (s.photos or [])):
        raise HTTPException(404, "No such photo")
    got = storage.get(db, _file_ns(s), pid)
    if not got:
        raise HTTPException(404, "No such photo")
    return RawResponse(got[1], media_type="image/jpeg", headers={"Cache-Control": "private, max-age=86400", "X-Content-Type-Options": "nosniff"})


@ar.get("/{sid}/photos/{pid}")
def admin_photo_get(sid: str, pid: str, a: Admin = Depends(admin_me), db: Session = Depends(get_db)):
    return _photo_bytes(db, _store(db, sid), pid)


# ---- partner (at the shop) -------------------------------------------------------------------------------------------
@pr.get("")
def mine(u: PartnerUser = Depends(partner_me), db: Session = Depends(get_db)):
    s = my_store(db, u)
    c = card(db, s, True)
    c.pop("commission", None)
    return c


class PinIn(BaseModel):
    lat: float
    lng: float
    acc: int
    landmark: str = ""


@pr.post("/location")
def drop_pin(body: PinIn, u: PartnerUser = Depends(partner_me), db: Session = Depends(get_db)):
    if u.role != "owner":
        raise HTTPException(403, "Only the owner can set the shop's location")
    if not (6 <= body.lat <= 37.5 and 68 <= body.lng <= 97.5):
        raise HTTPException(400, "That location is outside India")
    if body.acc > 200:
        raise HTTPException(400, f"Your phone's location is only accurate to {body.acc} m. Step outside the shop door, wait a few seconds and try again.")
    s = my_store(db, u)
    moved = round(km((body.lat, body.lng), (s.lat, s.lng)) * 1000) if s.lat is not None else 0
    s.lat, s.lng, s.pin_acc, s.pin_at, s.pin_by = body.lat, body.lng, int(body.acc), now(), (u.name or u.email)[:80]
    if body.landmark.strip():
        s.landmark = _clean(body.landmark, 160)
    if s.verified and moved > 300:
        s.verified = False  # a live shop that moves needs a fresh look before families are sent there
    from .admin import log as alog
    alog(db, "partner:" + u.email, f"onboard.pin {s.id}", f"moved {moved} m, ±{body.acc} m")
    return {"ok": True, "moved": moved, "relisted": not s.verified}


@pr.post("/photos")
async def partner_photo(slot: str = Form(...), lat: float | None = Form(None), lng: float | None = Form(None), acc: int | None = Form(None),
                        file: UploadFile = File(...), u: PartnerUser = Depends(partner_me), db: Session = Depends(get_db)):
    s = my_store(db, u)
    return _save_photo(db, s, slot, await file.read(), lat, lng, acc, (u.name or u.email)[:80])


@pr.get("/photos/{pid}")
def partner_photo_get(pid: str, u: PartnerUser = Depends(partner_me), db: Session = Depends(get_db)):
    return _photo_bytes(db, my_store(db, u), pid)


# ---- families see the photos of live partners ------------------------------------------------------------------------
@pub.get("/{sid}/photos/{pid}")
def public_photo(sid: str, pid: str, db: Session = Depends(get_db)):
    s = db.get(Store, sid)
    if not s or not s.verified or not s.active:
        raise HTTPException(404, "No such photo")
    return _photo_bytes(db, s, pid)

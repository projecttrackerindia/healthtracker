"""The shared catalogue: medicines, lab tests and packages, with photos and the prescription rules built in.

Prescription medicines are never advertised: they don't appear on public pages, in offers or banners, and a
pharmacy cannot pack them before a prescription is checked. Photos are of real packs, re-encoded on upload."""
from __future__ import annotations

import io
import re

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import Response as RawResponse
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from . import storage
from .admin import log, me as admin_me
from .db import get_db
from .models import Admin, CatalogMed, CatalogTest, LabTest, Package, Store, StoreItem, new_id, now
from .seed import CATALOG, TESTS

ar = APIRouter(prefix="/api/admin/catalog")
pub = APIRouter(prefix="/api/v2/catalog")
NS = "catalog"
SIDES = ("front", "strip", "back")
# not every test is a blood sample: imaging and tracings are done at the centre, a Pap smear is a swab
SAMPLE = {"xray": "Imaging", "usg": "Imaging", "echo": "Imaging", "ecg": "ECG tracing", "pap": "Cervical swab"}
VALUES = {"cbc": 24, "lipid": 8, "lft": 11, "kft": 9, "thy": 3, "urine": 18}


def ensure(db: Session) -> None:
    """First run: copy the built-in lists into the database so they can be edited."""
    if not db.scalar(select(func.count(CatalogMed.sku))):
        for m in CATALOG:
            strength = re.match(r"([\d.,/ ]+\s*(?:mg|mcg|g|iu|ml|%)[^·]*)", m.get("form", ""), re.I)
            db.add(CatalogMed(sku=m["id"], name=m["name"], form=m.get("form", ""), cat=m.get("cat", ""), mrp=m.get("mrp", 0), rx=bool(m.get("rx")),
                              schedule="H" if m.get("rx") else "", salt=m["name"], storage="Below 25 °C, dry place",
                              cold=bool(re.search(r"insulin|vaccin", m["name"], re.I))))
    if not db.scalar(select(func.count(CatalogTest.code))):
        for code, (name, price, tat, fast) in TESTS.items():
            db.add(CatalogTest(code=code, name=name, tat_hours=tat, fasting=fast, values=VALUES.get(code, 1),
                               sample=SAMPLE.get(code, "Urine" if "urine" in code else "Blood")))
    for code, smp in SAMPLE.items():
        t = db.get(CatalogTest, code)
        if t and t.sample == "Blood":
            t.sample = smp
    if not db.scalar(select(func.count(Package.code))):
        have = set(TESTS)
        for code, name, who, tests, color, icon in [
            ("heartdia", "Heart & diabetes check", "Adults over 30, or anyone with diabetes, high BP or a family history of heart disease.",
             ["cbc", "hba1c", "lipid", "thy", "vitd", "kft"], "blue", "heart"),
            ("fullbody", "Full body checkup", "A yearly check of blood, sugar, cholesterol, liver, kidney and thyroid.",
             ["cbc", "hba1c", "lipid", "lft", "kft", "thy", "vitd", "b12", "urine"], "green", "check"),
            ("women", "Women's health", "Blood count, iron, thyroid, vitamin D and B12, often low in women.",
             ["cbc", "iron", "thy", "vitd", "b12", "hb"], "pink", "women")]:
            db.add(Package(code=code, name=name, who=who, tests=[t for t in tests if t in have], color=color, icon=icon, active=False))   # drafts until priced
    db.flush()


def _short(t: str, n: int) -> str:
    """Cut at a word, not mid-word, and say that it was cut."""
    t = t.strip()
    return t if len(t) <= n else t[:n].rsplit(" ", 1)[0].rstrip(",.;:") + "…"


def _range(xs: list[int]) -> list[int] | None:
    xs = sorted(x for x in xs if x)
    return [xs[0], xs[-1]] if xs else None


def med_json(m: CatalogMed, prices: dict) -> dict:
    p = prices.get(m.sku, [])
    return {"sku": m.sku, "name": m.name, "salt": m.salt, "form": m.form, "cat": m.cat, "maker": m.maker, "mrp": m.mrp, "rx": m.rx,
            "schedule": m.schedule, "storage": m.storage, "photos": m.photos or [], "hidden": m.hidden,
            "range": _range(p), "stores": len(p), "rule": ("Prescription · Schedule " + m.schedule) if m.rx else "Over the counter",
            "about": m.about or "", "organ": m.organ or "", "test": m.test or "", "refillDays": m.refill_days or 0, "cold": bool(m.cold)}


@ar.get("/meds")
def meds(tab: str = "all", q: str = "", a: Admin = Depends(admin_me), db: Session = Depends(get_db)):
    ensure(db)
    prices: dict[str, list[int]] = {}
    for sku, price in db.execute(select(StoreItem.sku, StoreItem.price).join(Store, Store.id == StoreItem.store_id).where(Store.verified == True)).all():  # noqa: E712
        prices.setdefault(sku, []).append(price)
    rows = db.scalars(select(CatalogMed).order_by(CatalogMed.cat, CatalogMed.name)).all()
    counts = {"all": len(rows), "photos": sum(1 for m in rows if not m.photos), "rx": sum(1 for m in rows if m.rx), "otc": sum(1 for m in rows if not m.rx), "hidden": sum(1 for m in rows if m.hidden),
              "sch": sum(1 for m in rows if m.schedule), "cold": sum(1 for m in rows if m.cold)}
    ql = q.strip().lower()
    f = {"all": lambda m: True, "photos": lambda m: not m.photos, "rx": lambda m: m.rx, "otc": lambda m: not m.rx, "hidden": lambda m: m.hidden,
         "sch": lambda m: bool(m.schedule), "cold": lambda m: bool(m.cold)}.get(tab, lambda m: True)
    out = [med_json(m, prices) for m in rows if f(m) and (not ql or ql in f"{m.name} {m.salt} {m.maker} {m.cat}".lower())]
    cheaper = {}
    for m in rows:
        cheaper.setdefault((m.salt or m.name).lower(), []).append(m)
    for j in out:
        same = [x for x in cheaper.get((j["salt"] or j["name"]).lower(), []) if x.sku != j["sku"] and x.mrp and x.mrp < (j["mrp"] or 10 ** 9)]
        j["cheaper"] = {"n": len(same), "from": min(x.mrp for x in same)} if same else None
        j["subs"] = [{"name": x.name, "maker": x.maker or "", "mrp": x.mrp} for x in sorted(same, key=lambda x: x.mrp)[:3]]
        pr = sorted(prices.get(j["sku"], []))
        j["prices"] = {"low": pr[0], "usual": pr[len(pr) // 2], "n": len(pr)} if pr else None
    return {"rows": out, "counts": counts, "cats": sorted({m.cat for m in rows if m.cat})}


class MedIn(BaseModel):
    name: str
    salt: str = ""
    form: str = ""
    cat: str = ""
    maker: str = ""
    mrp: int = 0
    rx: bool = False
    schedule: str = ""
    storage: str = ""
    hidden: bool = False
    about: str = ""
    organ: str = ""
    test: str = ""
    refillDays: int = 0
    cold: bool = False


def _clean(v, n):
    return re.sub(r"[<>\x00-\x1f]", "", str(v or "")).strip()[:n]


@ar.put("/meds/{sku}")
def save_med(sku: str, body: MedIn, a: Admin = Depends(admin_me), db: Session = Depends(get_db)):
    ensure(db)
    m = db.get(CatalogMed, sku)
    if not m:
        if not re.fullmatch(r"[a-z0-9_-]{2,40}", sku):
            raise HTTPException(400, "Code: 2–40 lowercase letters, digits or dashes")
        m = CatalogMed(sku=sku, name="")
        db.add(m)
    if len(body.name.strip()) < 2:
        raise HTTPException(400, "Enter the medicine name")
    if body.schedule not in ("", "H", "H1", "X"):
        raise HTTPException(400, "Schedule is H, H1, X or none")
    if body.schedule and not body.rx:
        raise HTTPException(400, "A scheduled medicine always needs a prescription")
    if body.mrp < 0 or body.mrp > 200000:
        raise HTTPException(400, "Check the MRP")
    if not 0 <= body.refillDays <= 365:
        raise HTTPException(400, "Refill days: 0 to 365")
    for k, n in (("name", 120), ("salt", 160), ("form", 120), ("cat", 40), ("maker", 120), ("storage", 120), ("about", 300), ("organ", 40), ("test", 40)):
        setattr(m, k, _clean(getattr(body, k), n))
    m.organ, m.test = m.organ.lower(), m.test.lower()
    m.mrp, m.rx, m.schedule, m.hidden, m.updated = body.mrp, body.rx, body.schedule, body.hidden, now()
    m.refill_days, m.cold = body.refillDays, body.cold
    log(db, a.email, f"catalog.med {sku}", m.name)
    return med_json(m, {})


MED_COLS = ("sku", "name", "salt", "form", "cat", "maker", "mrp", "rx", "schedule", "storage", "about", "organ", "test", "refill_days", "cold")


@ar.post("/meds/import")
async def import_meds(file: UploadFile = File(...), a: Admin = Depends(admin_me), db: Session = Depends(get_db)):
    """Add or update medicines from a CSV with a header row. Known columns: sku, name, salt, form, cat, maker, mrp, rx (yes/no),
    schedule (blank, H, H1 or X), storage, about, organ, test, refill_days, cold (yes/no). Rows with a problem are
    skipped and listed back by line, so one bad line never blocks the rest."""
    import csv
    ensure(db)
    raw = await file.read()
    if len(raw) > 2 * 1024 * 1024:
        raise HTTPException(413, "CSV is over 2 MB")
    try:
        text_ = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise HTTPException(400, "Save the file as UTF-8 CSV")
    rd = csv.DictReader(io.StringIO(text_))
    head = {(h or "").strip().lower() for h in (rd.fieldnames or [])}
    if not {"sku", "name"} <= head:
        raise HTTPException(400, "The first row must name the columns, at least: sku, name")
    added = updated = 0
    bad: list[dict] = []
    for n, row in enumerate(rd, start=2):
        if n > 5001:
            bad.append({"line": n, "why": "Only the first 5,000 rows are read"})
            break
        r = {(k or "").strip().lower(): (v or "").strip() for k, v in row.items()}
        sku, name = r.get("sku", "").lower(), r.get("name", "")
        sch = r.get("schedule", "").upper().replace("SCHEDULE", "").strip()
        why = ("Code: 2–40 lowercase letters, digits or dashes" if not re.fullmatch(r"[a-z0-9_-]{2,40}", sku) else
               "Name missing" if len(name) < 2 else
               "Schedule is H, H1, X or blank" if sch not in ("", "H", "H1", "X") else
               "MRP is not a number" if r.get("mrp") and not re.fullmatch(r"\d{1,6}", r["mrp"]) else
               "Refill days is not a number" if r.get("refill_days") and not re.fullmatch(r"\d{1,3}", r["refill_days"]) else "")
        if why:
            bad.append({"line": n, "why": why})
            continue
        m = db.get(CatalogMed, sku)
        if m:
            updated += 1
        else:
            m = CatalogMed(sku=sku, name="", storage="Below 25 °C, dry place")
            db.add(m)
            added += 1
        for k, ln in (("name", 120), ("salt", 160), ("form", 120), ("cat", 40), ("maker", 120), ("storage", 120), ("about", 300), ("organ", 40), ("test", 40)):
            if k in r and (r[k] or k == "name"):
                setattr(m, k, _clean(r[k], ln))
        if "mrp" in r and r["mrp"]:
            m.mrp = int(r["mrp"])
        if "schedule" in r:
            m.schedule = sch
        if r.get("rx"):
            m.rx = r["rx"].lower() in ("1", "yes", "y", "true", "rx")
        if m.schedule:
            m.rx = True   # a scheduled medicine always needs a prescription
        if r.get("refill_days"):
            m.refill_days = int(r["refill_days"])
        if "cold" in r and r["cold"]:
            m.cold = r["cold"].lower() in ("1", "yes", "y", "true")
        m.updated = now()
    db.flush()
    log(db, a.email, "catalog.med.import", f"added={added} updated={updated} skipped={len(bad)}")
    return {"added": added, "updated": updated, "skipped": bad[:50], "skippedN": len(bad)}


def _photo(data: bytes) -> bytes:
    from PIL import Image, ImageOps
    if len(data) > 8 * 1024 * 1024:
        raise HTTPException(413, "Photo is over 8 MB")
    try:
        im = Image.open(io.BytesIO(data))
        im.verify()
        im = ImageOps.exif_transpose(Image.open(io.BytesIO(data))).convert("RGB")
    except Exception:
        raise HTTPException(400, "That file is not a photo")
    im.thumbnail((1400, 1400))
    out = io.BytesIO()
    im.save(out, "JPEG", quality=86, optimize=True)
    return out.getvalue()


@ar.post("/meds/{sku}/photo")
async def med_photo(sku: str, side: str = Form("front"), file: UploadFile = File(...), a: Admin = Depends(admin_me), db: Session = Depends(get_db)):
    m = db.get(CatalogMed, sku)
    if not m:
        raise HTTPException(404)
    if side not in SIDES:
        raise HTTPException(400, "Side is front, strip or back")
    data = _photo(await file.read())
    pid = new_id("cp")
    storage.put(db, NS, pid, data, "image/jpeg", f"{sku}-{side}.jpg", "admin:" + a.email)
    m.photos = [p for p in (m.photos or []) if p.get("side") != side] + [{"id": pid, "side": side}]
    m.updated = now()
    log(db, a.email, f"catalog.photo {sku} {side}")
    return {"photos": m.photos}


@pub.get("/meds/{sku}/photo/{pid}")
def med_photo_get(sku: str, pid: str, db: Session = Depends(get_db)):
    m = db.get(CatalogMed, sku)
    if not m or m.hidden or not any(p.get("id") == pid for p in (m.photos or [])):
        raise HTTPException(404)
    got = storage.get(db, NS, pid)
    if not got:
        raise HTTPException(404)
    return RawResponse(got[1], media_type="image/jpeg", headers={"Cache-Control": "public, max-age=604800"})


# ---- lab tests and packages ------------------------------------------------------------------------------------------
def _lab_prices(db: Session) -> dict[str, dict[str, int]]:
    out: dict[str, dict[str, int]] = {}
    for sid, code, price in db.execute(select(LabTest.store_id, LabTest.code, LabTest.price).join(Store, Store.id == LabTest.store_id).where(Store.verified == True, Store.active == True)).all():  # noqa: E712
        out.setdefault(code, {})[sid] = price
    return out


@ar.get("/tests")
def tests(a: Admin = Depends(admin_me), db: Session = Depends(get_db)):
    ensure(db)
    lp = _lab_prices(db)
    rows = db.scalars(select(CatalogTest).order_by(CatalogTest.name)).all()
    return {"rows": [{"code": t.code, "name": t.name, "values": t.values, "sample": t.sample, "fasting": t.fasting, "tat": t.tat_hours, "about": t.about,
                      "hidden": t.hidden, "range": _range(list(lp.get(t.code, {}).values())), "labs": len(lp.get(t.code, {}))} for t in rows]}


def pkg_json(db: Session, p: Package, lp: dict) -> dict:
    names = {t.code: t for t in db.scalars(select(CatalogTest).where(CatalogTest.code.in_(p.tests or []))).all()}
    labs = None
    for c in p.tests or []:
        have = set(lp.get(c, {}))
        labs = have if labs is None else labs & have
    labs = labs or set()
    sums = [sum(lp[c][sid] for c in p.tests) for sid in labs]
    single = sum(min(lp[c].values()) for c in p.tests if lp.get(c)) if p.tests else 0
    mrp = sum(TESTS.get(c, ("", 0, 0, 0))[1] for c in p.tests)
    return {"code": p.code, "name": p.name, "who": p.who, "color": p.color, "icon": p.icon, "price": p.price, "active": p.active,
            "tests": [{"code": c, "name": names[c].name if c in names else c, "values": names[c].values if c in names else 1,
                       "fasting": names[c].fasting if c in names else False} for c in p.tests or []],
            "values": sum(names[c].values for c in p.tests if c in names), "fasting": any(names[c].fasting for c in p.tests if c in names),
            "mrp": mrp, "cheapestSingly": single, "suggested": int(round(mrp * 0.42 / 50) * 50) if mrp else 0,
            "labs": len(labs), "labRange": _range(sums)}


@ar.get("/packages")
def packages(a: Admin = Depends(admin_me), db: Session = Depends(get_db)):
    ensure(db)
    lp = _lab_prices(db)
    return {"rows": [pkg_json(db, p, lp) for p in db.scalars(select(Package).order_by(Package.name)).all()],
            "allTests": [{"code": t.code, "name": t.name} for t in db.scalars(select(CatalogTest).where(CatalogTest.hidden == False).order_by(CatalogTest.name)).all()]}  # noqa: E712


class PkgIn(BaseModel):
    name: str
    who: str = ""
    tests: list[str] = []
    color: str = "blue"
    icon: str = "heart"
    price: int = 0
    active: bool = False


@ar.put("/packages/{code}")
def save_pkg(code: str, body: PkgIn, a: Admin = Depends(admin_me), db: Session = Depends(get_db)):
    ensure(db)
    if not re.fullmatch(r"[a-z0-9_-]{2,40}", code):
        raise HTTPException(400, "Code: 2–40 lowercase letters, digits or dashes")
    known = {t.code for t in db.scalars(select(CatalogTest)).all()}
    bad = [t for t in body.tests if t not in known]
    if bad:
        raise HTTPException(400, "Unknown tests: " + ", ".join(bad))
    if len(set(body.tests)) < 2:
        raise HTTPException(400, "A package needs at least 2 different tests")
    if body.color not in ("blue", "green", "pink", "orange", "purple", "teal") or body.icon not in ("heart", "check", "women", "men", "drop", "sun", "shield"):
        raise HTTPException(400, "Choose a colour and an icon from the list")
    p = db.get(Package, code) or Package(code=code, name="")
    if p not in db:
        db.add(p)
    p.name, p.who = _clean(body.name, 120), _clean(body.who, 240)
    if len(p.name) < 3:
        raise HTTPException(400, "Name the package")
    p.tests, p.color, p.icon, p.price, p.active, p.updated = list(dict.fromkeys(body.tests)), body.color, body.icon, max(0, body.price), body.active, now()
    db.flush()
    j = pkg_json(db, p, _lab_prices(db))
    if p.active and not p.price:
        raise HTTPException(400, "Set a price before making the package live.")
    if p.active and j["mrp"] and p.price >= j["mrp"]:
        raise HTTPException(400, f"The package price should be below buying the tests separately (₹{j['mrp']:,}).")
    log(db, a.email, f"catalog.package {code}", p.name)
    return j


@pub.get("/packages")
def public_packages(db: Session = Depends(get_db)):
    ensure(db)
    lp = _lab_prices(db)
    return {"rows": [pkg_json(db, p, lp) for p in db.scalars(select(Package).where(Package.active == True, Package.price > 0)).all()]}  # noqa: E712


@pub.get("/suggest")
def suggest(q: str, request: Request, db: Session = Depends(get_db)):
    """Typing help for "Add medicine": what this family ordered or already takes first, then the shared list."""
    import re as _re
    from .medlist import NAMES
    q = _re.sub(r"\s+", " ", (q or "").strip().lower())[:60]
    if len(q) < 2:
        return {"rows": []}
    out: list[dict] = []
    seen: set[str] = set()

    def add(name: str, sub: str, src: str):
        k = name.lower()
        if k not in seen and len(out) < 12:
            seen.add(k)
            out.append({"name": name, "sub": sub, "src": src})
    try:
        from .auth import current_user
        from .models import Order
        u = current_user(request, db)
        if u and u.household_id:
            for o in db.scalars(select(Order).where(Order.household_id == u.household_id, Order.kind == "medicine").order_by(Order.created.desc()).limit(30)).all():
                for i in o.items or []:
                    n = i.get("name") or ""
                    if q in n.lower():
                        add(n, "You ordered this", "ordered")
    except Exception:
        pass
    words = q.split()
    match = lambda n: all(w in n.lower() for w in words)
    starts = lambda n: n.lower().startswith(q)
    cat = db.scalars(select(CatalogMed)).all()
    for m in sorted([m for m in cat if match(m.name) or match(m.salt or "")], key=lambda m: (not starts(m.name), m.name))[:8]:
        add(f"{m.name}{(' ' + m.form.split('·')[0].strip()) if m.form else ''}".strip(), _short(m.about or "", 110) or m.salt or m.cat or "", "catalog")
    for n in sorted([n for n in NAMES if match(n)], key=lambda n: (not starts(n), n)):
        add(n, "", "common")
    return {"rows": out}

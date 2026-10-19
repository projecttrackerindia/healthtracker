"""TheHealthTracker's own shop (/api/v1/shop, /api/admin/products): packages and merchandise delivered to the family's
address — the hospital-bag package first. Products are rows in shop_products; price, MRP and stock sit on the system
store's StoreItems (same sku) so a purchase is an ordinary order (kind "shop"): receipt PDF, returns, UPI or cash on
delivery, tracking in Orders, settlements. The team fulfils shop orders from Admin → Orders (or a partner sign-in on
the shop store).
"""
from __future__ import annotations

import os
import time

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import storage
from .admin import Admin, log
from .admin import me as admin_me
from .db import get_db
from .models import ShopProduct, Store, StoreItem, now

r = APIRouter(prefix="/api/v1/shop")
ar = APIRouter(prefix="/api/admin")
SHOP_ID = "s_tht_shop"
BAG_SKU = "bag-complete"
BAG_INCLUDES = [
    {"group": "Mother", "name": "Front-open cotton nighties (TheHealthTracker Mother line)", "qty": 3},
    {"group": "Mother", "name": "Maternity pads, extra-long", "qty": 2, "unit": "packs"},
    {"group": "Mother", "name": "Disposable underwear", "qty": 1, "unit": "pack of 10"},
    {"group": "Mother", "name": "Nursing bra + breast pads", "qty": 2},
    {"group": "Mother", "name": "Slippers & warm socks", "qty": 1},
    {"group": "Mother", "name": "Toiletry kit (towel, lip balm, essentials)", "qty": 1},
    {"group": "Mother", "name": "Water bottle with straw", "qty": 1},
    {"group": "Mother", "name": "Healthy snacks box", "qty": 1},
    {"group": "Mother", "name": "Phone charger long cable (USB-C)", "qty": 1},
    {"group": "Mother", "name": "Hair ties", "qty": 1, "unit": "pack"},
    {"group": "Baby", "name": "Cotton jhablas", "qty": 6},
    {"group": "Baby", "name": "Caps, mittens, socks set", "qty": 2},
    {"group": "Baby", "name": "Muslin swaddle wraps", "qty": 3},
    {"group": "Baby", "name": "Soft towels", "qty": 2},
    {"group": "Baby", "name": "Newborn diapers", "qty": 1, "unit": "pack of 36"},
    {"group": "Baby", "name": "Cotton wool & soft cloths", "qty": 1},
    {"group": "Baby", "name": "Warm blanket", "qty": 1},
    {"group": "Partner", "name": "Snacks & water", "qty": 1},
    {"group": "Partner", "name": "Charger & power bank", "qty": 1},
    {"group": "TheHealthTracker", "name": "Hospital bag (tote) with document folder for the MCP card, reports and cards", "qty": 1},
    {"group": "TheHealthTracker", "name": "Mother's recovery journal & baby's first record book", "qty": 1},
    {"group": "TheHealthTracker", "name": "Laminated emergency card (blood group, contacts, Medical ID QR)", "qty": 1},
]


def ensure_shop(db: Session) -> Store:
    s = db.get(Store, SHOP_ID)
    if not s:
        s = Store(id=SHOP_ID, kind="shop", name="TheHealthTracker Store", brand="TheHealthTracker", address="Hyderabad", area="", city="Hyderabad", lat=17.385, lng=78.4867,
                  phone=os.getenv("SUPPORT_PHONE", ""), hours="Ships Mon–Sat", verified=True, active=True, delivery=True, delivery_fee=0, free_above=0, eta_min=4 * 1440,
                  rating=0, rating_n=0, owner_email=os.getenv("LEGAL_EMAIL") or "support@thehealthtracker.com", notes="System store for packages and merchandise.")
        db.add(s)
        db.flush()
    if not db.get(ShopProduct, BAG_SKU):
        db.add(ShopProduct(sku=BAG_SKU, name="Hospital Bag · Complete", tagline="Everything on the hospital-bag list, packed and delivered before the due date.",
                           description="One package that covers the mother, the baby and the partner from the checklist in your birth plan, in a TheHealthTracker tote with a document folder for the MCP card, reports and cards. "
                                       "Mother's wear comes in your size; baby items are newborn size (0–3 months). Packed in Hyderabad and shipped across India.",
                           includes=BAG_INCLUDES, sizes=["S", "M", "L", "XL", "XXL"], size_note="Mother's nighties and nursing bras — pick your usual size; maternity fit.",
                           badge="Birth plan", ships_in="3–5 days", sort=1, active=True))
        db.add(StoreItem(store_id=SHOP_ID, sku=BAG_SKU, name="Hospital Bag · Complete", mrp=3999, price=2999, stock=50))
        db.flush()
    return s


def product_json(db: Session, p: ShopProduct) -> dict:
    it = db.scalar(select(StoreItem).where(StoreItem.store_id == SHOP_ID, StoreItem.sku == p.sku))
    return {"sku": p.sku, "name": p.name, "tagline": p.tagline, "description": p.description, "includes": p.includes or [], "sizes": p.sizes or [], "sizeNote": p.size_note,
            "badge": p.badge, "shipsIn": p.ships_in, "active": p.active, "price": it.price if it else 0, "mrp": it.mrp if it else 0, "stock": it.stock if it else 0,
            "image": f"/api/v1/shop/image/{p.sku}" if p.image_key else "", "store": SHOP_ID, "updated": p.updated}


@r.get("/products")
def products(db: Session = Depends(get_db)):
    ensure_shop(db)
    rows = db.scalars(select(ShopProduct).where(ShopProduct.active == True).order_by(ShopProduct.sort)).all()  # noqa: E712
    return {"store": SHOP_ID, "products": [product_json(db, p) for p in rows], "cod": True, "upi": True}


@r.get("/products/{sku}")
def product(sku: str, db: Session = Depends(get_db)):
    p = db.get(ShopProduct, sku)
    if not p or not p.active:
        raise HTTPException(404)
    return product_json(db, p)


@r.get("/image/{sku}")
def image(sku: str, db: Session = Depends(get_db)):
    p = db.get(ShopProduct, sku)
    s3 = storage._s3()
    if not p or not p.image_key or not s3:
        raise HTTPException(404)
    try:
        obj = s3.get_object(Bucket=os.getenv("S3_BUCKET"), Key=p.image_key)
    except Exception:
        raise HTTPException(404)
    return Response(obj["Body"].read(), media_type=obj.get("ContentType") or "image/jpeg", headers={"Cache-Control": "public, max-age=86400"})


# ---- admin ----------------------------------------------------------------------------------------------------------------------
class ProductIn(BaseModel):
    sku: str
    name: str
    tagline: str = ""
    description: str = ""
    includes: list[dict] = []
    sizes: list[str] = []
    sizeNote: str = ""
    badge: str = ""
    shipsIn: str = "3–5 days"
    price: int
    mrp: int = 0
    stock: int = 0
    sort: int = 0
    active: bool = True


@ar.get("/products")
def admin_products(a: Admin = Depends(admin_me), db: Session = Depends(get_db)):
    ensure_shop(db)
    rows = db.scalars(select(ShopProduct).order_by(ShopProduct.sort)).all()
    return {"store": SHOP_ID, "products": [product_json(db, p) for p in rows]}


@ar.put("/products/{sku}")
def admin_put(sku: str, body: ProductIn, a: Admin = Depends(admin_me), db: Session = Depends(get_db)):
    ensure_shop(db)
    sku = sku.strip().lower()[:40]
    if not sku.replace("-", "").isalnum() or len(body.name.strip()) < 3 or body.price < 0:
        raise HTTPException(400, "sku (letters, digits, dashes), a name and a price are needed.")
    p = db.get(ShopProduct, sku) or ShopProduct(sku=sku)
    p.name, p.tagline, p.description = body.name.strip()[:120], body.tagline.strip()[:160], body.description.strip()[:4000]
    p.includes = [{"group": str(i.get("group", ""))[:30], "name": str(i.get("name", ""))[:120], "qty": int(i.get("qty", 1) or 1), **({"unit": str(i["unit"])[:20]} if i.get("unit") else {})} for i in body.includes if i.get("name")][:60]
    p.sizes, p.size_note, p.badge, p.ships_in, p.sort, p.active, p.updated = [str(x)[:8] for x in body.sizes][:10], body.sizeNote[:160], body.badge[:40], body.shipsIn[:40], body.sort, body.active, now()
    db.add(p)
    it = db.scalar(select(StoreItem).where(StoreItem.store_id == SHOP_ID, StoreItem.sku == sku))
    if not it:
        it = StoreItem(store_id=SHOP_ID, sku=sku, name=p.name, mrp=body.mrp or body.price, price=body.price, stock=body.stock)
        db.add(it)
    else:
        it.name, it.price, it.mrp, it.stock = p.name, body.price, body.mrp or body.price, body.stock
    db.flush()
    log(db, a.email, f"shop.product.save {sku} ₹{body.price}")
    return product_json(db, p)


@ar.put("/products/{sku}/image")
async def admin_image(sku: str, file: UploadFile = File(...), a: Admin = Depends(admin_me), db: Session = Depends(get_db)):
    p = db.get(ShopProduct, sku)
    s3 = storage._s3()
    if not p:
        raise HTTPException(404)
    if not s3:
        raise HTTPException(503, "No bucket configured (S3_BUCKET).")
    data = await file.read()
    mime = (file.content_type or "image/jpeg").split(";")[0]
    if not mime.startswith("image/") or len(data) > 4 * 1024 * 1024:
        raise HTTPException(415, "An image up to 4 MB.")
    key = f"shop/{sku}.{ 'png' if 'png' in mime else 'webp' if 'webp' in mime else 'jpg'}"
    s3.put_object(Bucket=os.getenv("S3_BUCKET"), Key=key, Body=data, ContentType=mime)
    p.image_key, p.updated = key, now()
    return product_json(db, p)

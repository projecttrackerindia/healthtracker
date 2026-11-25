"""The hospital bag page (/hospital-bag): the family builds their own bag, signs in with their Urban Health account
(the same passkey, mobile code or email code as the app, through /api/v1/auth) and orders it from Urban Health's own
shop (store s_tht_shop). The result is an ordinary shop order: it shows in Orders in the app, has a receipt, and the
team packs it from Admin → Orders.

Every item comes from one of three brands: Mee Mee (baby care, nursing and the backpack), SuperBottoms (baby clothes)
and Pee Safe (postpartum care), plus the Urban Health emergency card, which is free. Ids start with the brand
(mm-, sb-, ps-, uh-). What each item is (name, group, complete-bag quantity, sizes) is defined in BAG below and matches
the page; tests/test_bag_checkout.py keeps the two in step. Price, stock per size and availability live in the
bag_items table, and the team edits them in Admin → Shop. Prices always come from the server, never from the browser.

Pricing: BAG holds each item's list price, the brand's own price on its website. Every item sells at least OFF_PCT
(30%) below it: the selling price is at most offer_price(list) = list × 70 ÷ 100, rounded down to the rupee, so the
discount shown is never more than the real one. Prices are whole rupees and the bag's total is the plain sum of price ×
quantity, so the page, the checkout, the receipt and a refund always agree to the rupee. BAG_RATE (an extra saving
inside a complete bag) stays 1.
Things the three brands don't make (nighties, slippers, toiletries, chargers and so on) are on the "from home" list.
Payment: online through Razorpay when it is switched on (rzp.py), or on delivery. There is no other way to pay.
"""
from __future__ import annotations

import math
import re
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from .admin import Admin, log
from .admin import me as admin_me
from .auth import csrf, current_user, limit, norm_id
from .db import get_db
from .models import BagChecklist, BagItem, Household, Order, ReminderSent, SavedAddress, now
from .routes import order_json
from .shop import SHOP_ID, ensure_shop

r = APIRouter(prefix="/api/v1/shop/bag")
ar = APIRouter(prefix="/api/admin/products/bag")
IST = timezone(timedelta(hours=5, minutes=30))
GROUP = {"m": "Mother", "b": "Baby", "d": "The bag"}
MAX_QTY = 20
MIN_DAYS = 3   # earliest delivery: packed and shipped in three days
BAG_RATE = 1.0   # no extra saving inside a complete bag; the offer is per item (OFF_PCT)
OFF_PCT = 30     # every item sells at least this far below the brand's own price

# id, group, name, list price (₹, the brand's own price), quantity in the complete bag, part of the complete bag, choices, returnable once opened
BAG = [
    # id, group, name, list price (the brand's own price; we sell at least 30% below it), complete-bag qty, in the complete bag, sizes, returnable
    ("mm-bra", "m", "Nursing bra", 749, 2, True, ["S", "M", "L", "XL"], False),
    ("mm-bpads", "m", "Breast pads", 229, 1, True, None, False),
    ("ps-pads", "m", "Maternity pads", 419, 1, True, None, False),
    ("ps-undies", "m", "Disposable underwear", 180, 1, True, ["L–XL", "XL–XXL"], False),
    ("ps-wash", "m", "Intimate wash", 126, 1, True, None, False),
    ("mm-belt", "m", "Belly support belt", 799, 0, False, None, True),
    ("sb-jhabla", "b", "Mulmul jhablas", 411, 6, True, ["0–3 m", "3–6 m"], True),
    ("sb-caps", "b", "Cap, mittens, booties and bib", 399, 2, True, None, True),
    ("mm-swad", "b", "Muslin swaddles", 999, 1, True, None, True),
    ("mm-towel", "b", "Bamboo cotton towels", 799, 2, True, None, True),
    ("mm-diaper", "b", "Newborn diapers", 215, 2, True, None, True),
    ("mm-wipes", "b", "Baby wipes", 149, 1, True, None, False),
    ("mm-nest", "b", "Padded carry nest", 999, 1, True, None, True),
    ("sb-home", "b", "Going-home set", 1049, 0, False, None, True),
    ("mm-bag", "d", "Diaper backpack", 1999, 1, True, None, True),
    ("uh-card", "d", "Emergency card", 0, 1, True, None, True),
]
BRANDS = {"mm": "Mee Mee", "sb": "SuperBottoms", "ps": "Pee Safe", "uh": "Urban Health"}


def brand(iid: str) -> str:
    return BRANDS.get(iid.split("-")[0], "")


BY_ID = {b[0]: b for b in BAG}


def offer_price(list_price: int) -> int:
    """The highest price an item may sell at: OFF_PCT below its list price, rounded down to the rupee."""
    return int(list_price) * (100 - OFF_PCT) // 100


def pct_off(list_price: int, price: int) -> int:
    """The discount in whole percent, rounded down, so a badge never claims more than the real saving."""
    return (int(list_price) - int(price)) * 100 // int(list_price) if list_price else 0

# The shop's return and refund policy, short form: shown at checkout, in the page's questions and in the API. The full
# policy is the page at /hospital-bag/policies (site/home/policies.html); bagreturns.py applies the same rules.
POLICY = [
    "Cancel free of charge until your bag is packed.",
    "Return or exchange unused items in their original packing within 7 days of delivery. A size that doesn’t fit is exchanged once, free.",
    "For hygiene reasons, maternity pads, disposable underwear, nursing bras, breast pads, intimate wash and wipes can’t be returned once opened, unless they arrive damaged or wrong.",
    "Damaged or wrong item? Tell us within 48 hours of delivery with a photo, and we’ll replace it or refund it.",
    "Refunds go back the way you paid, or to your UPI ID if you paid on delivery, usually within 5–7 working days of the item reaching us.",
]
POLICY_URL = "/hospital-bag/policies"
# what the family packs themselves: documents first, then the things the three brands don't make
HOME_ITEMS = {"mcp": "MCP card", "scan": "Scan and lab reports", "idp": "ID proof", "ins": "Insurance card",
              "h-nighty": "Two or three front-open nighties", "h-clothes": "Loose clothes to go home in", "h-slip": "Slippers and socks",
              "h-toil": "Toothbrush, paste, soap and comb", "h-bottle": "Water bottle", "h-snack": "Snacks for you and your partner",
              "h-hair": "Hair ties", "ph": "Phone, charger and power bank"}


def online_ready() -> bool:
    from .rzp import enabled
    return enabled()


# ---- the live list: price, stock and availability ----------------------------------------------------------------------
def _keys(b) -> list[str]:
    return list(b[6]) if b[6] else [""]


def ensure_bag(db: Session) -> dict[str, BagItem]:
    """Every item on the page has a row; new rows start at the offer price with stock not counted yet. A price above
    the offer ceiling (set before the offer began) comes down to it, so no item is ever sold at less than OFF_PCT off."""
    rows = {x.id: x for x in db.scalars(select(BagItem)).all()}
    for b in BAG:
        cap = offer_price(b[3])
        if b[0] not in rows:
            rows[b[0]] = BagItem(id=b[0], price=cap, stock={k: None for k in _keys(b)}, active=True)
            db.add(rows[b[0]])
        elif rows[b[0]].price > cap:
            rows[b[0]].price, rows[b[0]].updated, rows[b[0]].updated_by = cap, now(), f"offer: {OFF_PCT}% off"
    db.flush()
    return rows


def _left(row: BagItem | None, key: str):
    """How many are left of this size, or None when the team does not count it."""
    if not row:
        return None
    v = (row.stock or {}).get(key)
    return None if v is None else max(0, int(v))


def live_json(rows: dict[str, BagItem]) -> list[dict]:
    out = []
    for b in BAG:
        x = rows.get(b[0])
        p = x.price if x else offer_price(b[3])
        out.append({"id": b[0], "group": GROUP[b[1]], "brand": brand(b[0]), "name": b[2], "price": p, "list": b[3], "off": pct_off(b[3], p), "free": b[3] == 0,
                    "def": b[4], "inBag": b[5], "opts": b[6],
                    "returnable": b[7], "active": bool(x.active) if x else True, "stock": {k: _left(x, k) for k in _keys(b)}})
    return out


def price_bag(items: dict, twins: bool = False, opts: dict | None = None, prices: dict | None = None) -> dict:
    """The bag's lines and total, the same arithmetic as the page (totals() in bag.html), in the same order."""
    opts, prices = opts or {}, prices or {}
    lines, units, full, exact = [], 0, 0, 0.0
    for iid, grp, name, launch, d, inb, choices, returnable in BAG:
        try:
            q = max(0, min(MAX_QTY, int(items.get(iid, 0) or 0)))
        except (TypeError, ValueError):
            q = 0
        if not q:
            continue
        if launch == 0:
            q = 1   # a free item comes once with the bag
        p = min(int(prices.get(iid, offer_price(launch))), offer_price(launch))   # never above the offer ceiling
        cap = d * (2 if twins and grp == "b" else 1) if inb else 0
        b = min(q, cap)
        exact += b * p * BAG_RATE + (q - b) * p
        full += q * launch   # at the brands' own prices
        units += q
        opt = str(opts.get(iid) or "")
        if choices:
            opt = opt if opt in choices else choices[0]
        line = {"sku": "hb-" + iid, "name": f"{name} ({brand(iid)})" + (f" · {opt}" if opt else ""), "qty": q, "price": p, "list": launch, "off": pct_off(launch, p), "group": GROUP[grp],
                "brand": brand(iid)}
        if b:
            line["bag"] = b   # how many of these are at the bag price
        if opt:
            line["opt"] = opt
        if not returnable:
            line["returnable"] = False
        lines.append(line)
    total = int(math.floor(exact + .5))   # JavaScript's Math.round
    return {"lines": lines, "units": units, "full": full, "total": total, "save": full - total, "off": pct_off(full, total)}


def restock(db: Session, o: Order) -> None:
    """A cancelled hospital-bag order puts its counted stock back, once."""
    if not o or o.store_id != SHOP_ID or any(t.get("s") == "restocked" for t in (o.timeline or [])):
        return
    lines = [ln for ln in (o.items or []) if str(ln.get("sku", "")).startswith("hb-")]
    if not lines:
        return
    rows = {x.id: x for x in db.scalars(select(BagItem)).all()}
    for ln in lines:
        x = rows.get(ln["sku"][3:])
        key = ln.get("opt", "")
        if x and _left(x, key) is not None:
            x.stock = {**(x.stock or {}), key: _left(x, key) + int(ln.get("qty") or 0)}
    o.timeline = (o.timeline or []) + [{"s": "restocked", "t": now()}]


# ---- what the page reads -----------------------------------------------------------------------------------------------
@r.get("")
def bag_info(db: Session = Depends(get_db, scope="function")):
    rows = ensure_bag(db)
    c = price_bag({b[0]: b[4] for b in BAG if b[5]}, prices={k: v.price for k, v in rows.items()})
    return {"store": SHOP_ID, "online": online_ready(), "cod": True, "minDays": MIN_DAYS, "items": live_json(rows), "policy": POLICY, "policyUrl": POLICY_URL,
            "rate": BAG_RATE, "home": [[k, v] for k, v in HOME_ITEMS.items()],
            "offPct": OFF_PCT, "complete": {"total": c["total"], "full": c["full"], "units": c["units"], "save": c["save"], "off": c["off"]}}


class QuoteIn(BaseModel):
    items: dict = {}
    opts: dict = {}
    twins: bool = False


@r.post("/quote")
def quote(body: QuoteIn, db: Session = Depends(get_db, scope="function")):
    return price_bag(body.items, body.twins, body.opts, {k: v.price for k, v in ensure_bag(db).items()})


# ---- placing the order -------------------------------------------------------------------------------------------------
class AddrIn(BaseModel):
    id: str = ""        # one of the account's saved addresses
    name: str = ""
    phone: str = ""
    line1: str = ""     # flat or house number, floor
    line2: str = ""     # building, street and area
    landmark: str = ""
    city: str = ""
    state: str = ""
    pin: str = ""


class BillIn(BaseModel):
    same: bool = True
    name: str = ""
    line: str = ""


class OrderIn(QuoteIn):
    token: str = ""     # the page's own id for this attempt, so a double tap never makes two orders
    deliverOn: str = ""
    addr: AddrIn
    bill: BillIn = BillIn()
    payment: str = "cod"


def _clean(v, n: int) -> str:
    return re.sub(r"[<>\x00-\x1f]", "", str(v or "")).strip()[:n]


def _address(db: Session, h: Household, a: AddrIn) -> dict:
    if a.id:
        sa = db.get(SavedAddress, a.id)
        if not sa or sa.household_id != h.id:
            raise HTTPException(400, "Choose one of your saved addresses.")
        out = {k: _clean(getattr(sa, k), 160) for k in ("label", "name", "phone", "line1", "line2", "landmark", "area", "city", "state", "pin") if getattr(sa, k)}
        if not out.get("name") or not out.get("phone"):
            raise HTTPException(400, "This saved address has no name or mobile number for the delivery. Add a new address instead.")
        return out
    out = {"name": _clean(a.name, 80), "line1": _clean(a.line1, 120), "line2": _clean(a.line2, 160), "landmark": _clean(a.landmark, 120),
           "city": _clean(a.city, 80), "state": _clean(a.state, 40), "pin": _clean(a.pin, 6)}
    if len(out["name"]) < 2:
        raise HTTPException(400, "Enter the name of the person receiving the bag.")
    try:
        kind, ph = norm_id(a.phone)
    except HTTPException:
        kind, ph = "", ""
    if kind != "phone" or not re.fullmatch(r"\+91[6-9]\d{9}", ph):
        raise HTTPException(400, "Enter a 10-digit mobile number for the delivery.")
    out["phone"] = ph
    if not re.fullmatch(r"[1-9]\d{5}", out["pin"]):
        raise HTTPException(400, "PIN code is 6 digits.")
    if not out["line1"]:
        raise HTTPException(400, "Enter the flat or house number.")
    if len(out["line2"]) < 3:
        raise HTTPException(400, "Enter the building, street and area.")
    if len(out["city"]) < 2:
        raise HTTPException(400, "Enter the city.")
    return {k: v for k, v in out.items() if v}


def _line(a: dict) -> str:
    s = ", ".join(x for x in (a.get("line1"), a.get("line2"), a.get("landmark"), a.get("area"), a.get("city"), a.get("state")) if x)
    s += f" - {a['pin']}" if a.get("pin") else ""
    who = " · ".join(x for x in (a.get("name"), a.get("phone")) if x)
    return (who + " · " if who else "") + s


def _today() -> date:
    return datetime.now(IST).date()


def _deliver_on(s: str) -> date:
    today = _today()
    first = today + timedelta(days=MIN_DAYS)
    try:
        d = date.fromisoformat((s or "")[:10])
    except ValueError:
        return first + timedelta(days=1)
    if d < first or d > today + timedelta(days=300):
        raise HTTPException(400, f"Choose a delivery day from {first.strftime('%a %d %b')} onwards.")
    return d


def _household(db: Session, u) -> Household:
    """The account's own family. The page links it first with /api/v1/hello, exactly as the app does."""
    h = db.get(Household, u.household_id) if u.household_id else None
    if not h:
        raise HTTPException(409, "Your account is still being set up. Refresh the page and try again.")
    if h.blocked:
        raise HTTPException(403, "This account can't place orders. Contact support.")
    return h


def _take_stock(db: Session, lines: list[dict]) -> None:
    """Check every counted size is in stock, then take it. Rows are locked on Postgres so two families can't both buy
    the last one."""
    ids = [ln["sku"][3:] for ln in lines]
    rows = {x.id: x for x in db.scalars(select(BagItem).where(BagItem.id.in_(ids)).with_for_update()).all()}
    for ln in lines:
        x, key = rows.get(ln["sku"][3:]), ln.get("opt", "")
        name = BY_ID[ln["sku"][3:]][2] + (f" in {key}" if key else "")
        if x and not x.active:
            raise HTTPException(409, f"{BY_ID[x.id][2]} isn't available right now. Remove it from your bag and try again.")
        n = _left(x, key)
        if n is not None and ln["qty"] > n:
            raise HTTPException(409, f"{name} has just sold out. Remove it or choose another size." if n == 0 else
                                f"Only {n} left of {name}. Lower the number and try again.")
    for ln in lines:
        x, key = rows.get(ln["sku"][3:]), ln.get("opt", "")
        n = _left(x, key)
        if x and n is not None:
            x.stock = {**(x.stock or {}), key: n - ln["qty"]}


@r.post("/order", dependencies=[Depends(csrf)])
def place(body: OrderIn, request: Request, db: Session = Depends(get_db, scope="function"), x_dokko_key: str | None = Header(None)):
    u = current_user(request, db)
    if not u:
        raise HTTPException(401, "Sign in to place your order.")
    limit(request, f"bagorder:{u.id}", 12, 3600)
    h = _household(db, u)
    s = ensure_shop(db)
    if not s.active:
        raise HTTPException(503, "The shop is closed for a short while. Please try again later.")
    token = _clean(body.token, 40)
    if token:
        # the same attempt twice (a double tap, a retry after a dropped connection): the first order is the answer
        for o in db.scalars(select(Order).where(Order.household_id == h.id, Order.store_id == SHOP_ID, Order.created > now() - 1800)).all():
            if (o.timeline or [{}])[0].get("k") == token:
                o.store = s
                return {"order": order_json(o), "key": h.key, "again": True}
    rows = ensure_bag(db)
    q = price_bag(body.items, body.twins, body.opts, {k: v.price for k, v in rows.items()})
    if not q["lines"] or q["total"] <= 0:
        raise HTTPException(400, "Your bag is empty. Add something first.")
    pay = body.payment if body.payment in ("cod", "online") else ""
    if not pay:
        raise HTTPException(400, "Choose online payment or pay on delivery.")
    if pay == "online" and not online_ready():
        raise HTTPException(400, "Online payment is not switched on yet. Choose pay on delivery.")
    addr = _address(db, h, body.addr)
    if not body.bill.same:
        bn, bl = _clean(body.bill.name, 80), _clean(body.bill.line, 200)
        if len(bn) < 2 or len(bl) < 8:
            raise HTTPException(400, "Enter the billing name and address, or bill to the delivery address.")
        addr["bill"] = {"name": bn, "line": bl}
    day = _deliver_on(body.deliverOn)
    _take_stock(db, q["lines"])
    eta = int(datetime(day.year, day.month, day.day, 18, 0, tzinfo=IST).timestamp())
    o = Order(household_id=h.id, store_id=SHOP_ID, kind="shop", items=q["lines"], subtotal=q["full"], fee=0, discount=q["save"], total=q["total"],
              address=_line(addr)[:240], addr=addr, member=(u.name or addr.get("name") or "")[:80], slot=("Deliver on " + day.strftime("%a %d %b %Y"))[:40],
              payment=pay, timeline=[{"s": "placed", "t": now(), "k": token, "via": "hospital-bag"}], eta=eta)
    db.add(o)
    db.flush()
    o.store = s
    what = f"{q['units']} items · ₹{q['total']:,}"
    try:
        from .inbox import notify
        notify(db, h.id, "order", f"Hospital bag ordered · {o.id}",
               f"{what}. {'Pay when it arrives' if pay == 'cod' else 'Finish the payment to confirm'}. Arrives by {day.strftime('%a %d %b')}.",
               {"order": o.id}, "", "/app#page=orders")
    except Exception as e:
        print("[bag] family notice failed:", str(e)[:120], flush=True)
    try:
        from .partner import alert_store
        items = "\n".join(f"  {ln['qty']} × {ln['name']}" for ln in q["lines"])
        alert_store(db, SHOP_ID, f"New hospital bag order {o.id} · ₹{q['total']:,}",
                    f"{o.member} ordered a hospital bag ({what}).\n{items}\n{o.slot}\nAddress: {o.address}\nPayment: {'on delivery' if pay == 'cod' else 'online (Razorpay)'}.")
    except Exception as e:
        print("[bag] team alert failed:", str(e)[:120], flush=True)
    return {"order": order_json(o), "key": h.key}


@r.post("/orders/{oid}/cod", dependencies=[Depends(csrf)])
def pay_on_delivery(oid: str, request: Request, db: Session = Depends(get_db, scope="function")):
    """The family closed the Razorpay window and would rather pay when the bag arrives."""
    u = current_user(request, db)
    if not u:
        raise HTTPException(401, "Sign in first.")
    h = _household(db, u)
    o = db.get(Order, oid)
    if not o or o.household_id != h.id or o.store_id != SHOP_ID:
        raise HTTPException(404, "order not found")
    if o.payment.endswith("paid"):
        raise HTTPException(400, "This order is already paid.")
    if o.status in ("cancelled", "refunded"):
        raise HTTPException(400, "This order is closed.")
    if o.payment != "cod":
        o.payment = "cod"
        o.timeline = (o.timeline or []) + [{"s": "pay_cod", "t": now()}]
    o.store = ensure_shop(db)
    return {"order": order_json(o)}


# ---- the packing checklist, kept with the account ---------------------------------------------------------------------
class ChecklistIn(BaseModel):
    packed: dict = {}
    remind: bool | None = None   # None: leave the reminders as they are
    due: str = ""                # only used to work out the reminder dates; not stored


def _checklist_json(db: Session, h: Household, c: BagChecklist | None) -> dict:
    last = db.scalars(select(Order).where(Order.household_id == h.id, Order.store_id == SHOP_ID, Order.status != "cancelled").order_by(Order.created.desc()).limit(10)).all()
    o = next((x for x in last if any(str(ln.get("sku", "")).startswith("hb-") for ln in (x.items or []))), None)
    items = [{"id": ln["sku"][3:], "name": BY_ID[ln["sku"][3:]][2], "qty": int(ln.get("qty") or 1)}
             for ln in (o.items if o else []) if str(ln.get("sku", "")).startswith("hb-") and ln["sku"][3:] in BY_ID]
    return {"packed": (c.packed if c else {}) or {}, "remind": (c.remind if c else []) or [], "items": items, "order": o.id if o else None}


@r.get("/checklist")
def checklist(request: Request, db: Session = Depends(get_db, scope="function")):
    u = current_user(request, db)
    if not u:
        raise HTTPException(401, "Sign in first.")
    h = _household(db, u)
    return _checklist_json(db, h, db.get(BagChecklist, h.id))


@r.put("/checklist", dependencies=[Depends(csrf)])
def save_checklist(body: ChecklistIn, request: Request, db: Session = Depends(get_db, scope="function")):
    u = current_user(request, db)
    if not u:
        raise HTTPException(401, "Sign in first.")
    h = _household(db, u)
    limit(request, f"bagcheck:{h.id}", 240, 600)
    c = db.get(BagChecklist, h.id) or BagChecklist(household_id=h.id, packed={}, remind=[])
    ok = set(BY_ID) | set(HOME_ITEMS)
    c.packed = {k: True for k, v in (body.packed or {}).items() if v and k in ok}
    if body.remind is False:
        c.remind = []
    elif body.remind:
        try:
            due = date.fromisoformat(body.due[:10])
        except ValueError:
            raise HTTPException(400, "Set your due date first.")
        today = _today()
        if not today - timedelta(days=21) <= due <= today + timedelta(days=300):
            raise HTTPException(400, "Check the due date.")
        c.remind = [{"week": w, "on": (due - timedelta(days=(40 - w) * 7)).isoformat()} for w in (34, 36)
                    if due - timedelta(days=(40 - w) * 7) >= today]
    c.updated = now()
    db.add(c)
    db.flush()
    return _checklist_json(db, h, c)


def send_reminders(db: Session, today: date) -> int:
    """Called from the morning pass (proactive.run_morning): the week-34 and week-36 notices a family asked for.
    One send per family and week, and a notice is not sent more than three days late."""
    from .inbox import notify
    n = 0
    for c in db.scalars(select(BagChecklist)).all():
        for rm in c.remind or []:
            try:
                on = date.fromisoformat(rm.get("on", ""))
            except ValueError:
                continue
            if not (on <= today <= on + timedelta(days=3)):
                continue
            k = f"bag:{c.household_id}:{rm.get('week')}"
            if db.get(ReminderSent, k):
                continue
            db.add(ReminderSent(key=k))
            db.flush()   # written now, so a second pass in the same session sees it
            packed = sum(1 for v in (c.packed or {}).values() if v)
            if rm.get("week") == 34:
                title, text = "Week 34: time to pack the hospital bag", "Open your packing list and tick things off as they go in. Keep the MCP card, reports and ID together."
            else:
                title, text = "Week 36: keep the hospital bag by the door", (f"{packed} things are packed so far. " if packed else "") + "Check the list once more so nothing is left at home."
            notify(db, c.household_id, "bag_reminder", title, text, {"week": rm.get("week")}, "", "/hospital-bag#pack")
            n += 1
    return n


# ---- the team: prices, stock and availability (Admin → Shop) -----------------------------------------------------------
@ar.get("/items")
def admin_items(a: Admin = Depends(admin_me), db: Session = Depends(get_db, scope="function")):
    rows = ensure_bag(db)
    out = live_json(rows)
    for x in out:
        row = rows[x["id"]]
        x["updated"], x["updatedBy"] = row.updated, row.updated_by
    complete = price_bag({b[0]: b[4] for b in BAG if b[5]}, prices={k: v.price for k, v in rows.items()})
    return {"items": out, "complete": {"total": complete["total"], "full": complete["full"], "off": complete["off"]}, "rate": BAG_RATE, "offPct": OFF_PCT}


class ItemIn(BaseModel):
    id: str
    price: int
    active: bool = True
    stock: dict = {}     # {"S": 10, "M": null}: null is "not counted"


class ItemsIn(BaseModel):
    items: list[ItemIn]


@ar.put("/items")
def admin_save_items(body: ItemsIn, a: Admin = Depends(admin_me), db: Session = Depends(get_db, scope="function")):
    rows = ensure_bag(db)
    changed = []
    for it in body.items[:60]:
        b, x = BY_ID.get(it.id), rows.get(it.id)
        if not b or not x:
            raise HTTPException(400, f"Unknown item {it.id}.")
        if b[3] == 0 and it.price != 0:
            raise HTTPException(400, f"{b[2]} comes free with every bag.")
        if b[3] and not 1 <= it.price <= offer_price(b[3]):
            raise HTTPException(400, f"{b[2]}: keep it at least {OFF_PCT}% below the brand's ₹{b[3]:,}, so ₹{offer_price(b[3]):,} or less.")
        stock = {}
        for k in _keys(b):
            v = it.stock.get(k)
            if v is None or v == "":
                stock[k] = None
            else:
                try:
                    stock[k] = max(0, min(100000, int(v)))
                except (TypeError, ValueError):
                    raise HTTPException(400, f"Stock for {b[2]}{' ' + k if k else ''} must be a number.")
        if (x.price, bool(x.active), x.stock or {}) != (it.price, it.active, stock):
            changed.append(f"{it.id} ₹{x.price}→₹{it.price}" if x.price != it.price else it.id)
            x.price, x.active, x.stock, x.updated, x.updated_by = it.price, it.active, stock, now(), a.email[:160]
    if changed:
        log(db, a.email, "shop.bag.items", ", ".join(changed)[:400])
    return admin_items(a, db)


# ---- the packing slip (Admin → Orders) ----------------------------------------------------------------------------------
sr = APIRouter(prefix="/api/admin/orders")


def _pdf_text(v) -> str:
    """The built-in PDF fonts cover Latin text only: swap the few characters the shop uses that they lack."""
    return (str(v or "").replace("₹", "Rs. ").replace("–", "-").replace("—", "-").replace("’", "'").replace("‘", "'")
            .replace("“", '"').replace("”", '"').replace("→", "->"))


def _wrap(s: str, n: int) -> list[str]:
    out, cur = [], ""
    for w in str(s).split():
        if cur and len(cur) + 1 + len(w) > n:
            out.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
    return out + ([cur] if cur else [])


def slip_pdf(o: Order) -> bytes:
    """One A4 page per bag (more if it is long): what to pack, with sizes and colours, where it goes, on which day, and
    what the courier collects. No prices, so it can travel inside the bag."""
    try:
        import pymupdf  # type: ignore
    except ImportError:  # pragma: no cover
        import fitz as pymupdf  # type: ignore
    from .billing import INK, LINE, LOGO, MUTE, money
    doc = pymupdf.open()
    W, M = 595, 44
    a = o.addr if isinstance(o.addr, dict) else {}
    t = lambda page, xy, s, size=10, bold=False, color=INK: page.insert_text(xy, _pdf_text(s), fontsize=size, fontname="hebo" if bold else "helv", color=color)  # noqa: E731

    def new_page(first: bool):
        page = doc.new_page(width=595, height=842)
        y = 46
        if LOGO.exists():
            page.insert_image(pymupdf.Rect(M, y - 6, M + 150, y + 34), filename=str(LOGO), keep_proportion=True)
        t(page, (W - M - 190, y + 6), "PACKING SLIP" if first else "PACKING SLIP (continued)", 9, color=MUTE)
        t(page, (W - M - 190, y + 24), f"UH-{o.id}", 16, True)
        y += 56
        page.draw_line((M, y), (W - M, y), color=LINE, width=1)
        return page, y + 22

    page, y = new_page(True)
    col2 = W / 2 + 10
    t(page, (M, y), "SHIP TO", 8, color=MUTE)
    t(page, (col2, y), "DELIVER ON", 8, color=MUTE)
    y += 15
    t(page, (M, y), a.get("name") or o.member or "-", 12, True)
    t(page, (col2, y), (o.slot or "").replace("Deliver on ", "") or "-", 12, True)
    y += 15
    ph = re.sub(r"^\+91(\d{5})(\d{5})$", r"+91 \1 \2", a.get("phone", ""))
    left = [ph, ", ".join(x for x in (a.get("line1"), a.get("line2")) if x), a.get("landmark", ""),
            ", ".join(x for x in (a.get("area"), a.get("city"), a.get("state")) if x) + (f" - {a['pin']}" if a.get("pin") else "")]
    if not any(left[1:]):
        left = [o.address]
    pay = o.payment or ""
    right = [("PAYMENT", True), (f"Collect {money(o.total)} (cash or UPI)" if pay == "cod" else "Paid online. Collect nothing." if pay.endswith("paid")
                                  else "Online payment not received yet. Check before dispatch.", False)]
    yl, yr = y, y
    for s in [x for x in left if x]:
        for part in _wrap(s, 44):   # stays inside the left column
            t(page, (M, yl), part, 10, color=MUTE)
            yl += 13
    yr += 8
    for s, head in right:
        t(page, (col2, yr), s, 8 if head else 11, bold=not head, color=MUTE if head else INK)
        yr += 15
    y = max(yl, yr) + 18
    lines = [ln for ln in (o.items or [])]
    units = sum(int(ln.get("qty") or 1) for ln in lines)
    t(page, (M, y), f"{units} items in {len(lines)} lines. Tick each one as it goes in.", 10, color=MUTE)
    y += 10
    for grp in ("Mother", "Baby", "Partner", "Urban Health", None):
        rows = [ln for ln in lines if (ln.get("group") == grp) or (grp is None and ln.get("group") not in GROUP.values())]
        if not rows:
            continue
        if y > 760:
            page, y = new_page(False)
        y += 18
        t(page, (M, y), (grp or "Other").upper(), 8.5, True, MUTE)
        y += 4
        for ln in rows:
            if y > 790:
                page, y = new_page(False)
            y += 18
            page.draw_circle((M + 6, y - 4), 6.5, color=INK, width=0.8)
            t(page, (M + 22, y), f"{int(ln.get('qty') or 1)} ×".replace("×", "x"), 11, True)
            t(page, (M + 52, y), str(ln.get("name", ""))[:70], 11)
            page.draw_line((M + 22, y + 6), (W - M, y + 6), color=LINE, width=0.5)
    y += 40
    if y > 800:   # no room left for the signatures on this page
        page, y = new_page(False)
        y += 40
    y = max(y, 700)
    for i, label in enumerate(("Packed by", "Checked by", "Date")):
        x = M + i * 170
        page.draw_line((x, y), (x + 150, y), color=INK, width=0.6)
        t(page, (x, y + 12), label, 8.5, color=MUTE)
    t(page, (M, 842 - 22), f"Urban Health · urbanhealth.in · order placed {datetime.fromtimestamp(o.created, IST).strftime('%d %b %Y, %I:%M %p')} IST", 7.5, color=MUTE)
    out = doc.tobytes(garbage=3, deflate=True)
    doc.close()
    return out


@sr.get("/{oid}/slip.pdf")
def packing_slip(oid: str, a: Admin = Depends(admin_me), db: Session = Depends(get_db, scope="function")):
    from fastapi.responses import Response
    o = db.get(Order, oid)
    if not o:
        raise HTTPException(404, "order not found")
    if o.kind != "shop":
        raise HTTPException(400, "Packing slips are for shop orders.")
    log(db, a.email, "order.slip", oid)
    return Response(slip_pdf(o), media_type="application/pdf", headers={"Content-Disposition": f'inline; filename="UH-{o.id}-packing.pdf"', "Cache-Control": "private, no-store"})

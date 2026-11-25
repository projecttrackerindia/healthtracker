"""Returns, exchanges and refunds for hospital bag orders: the customer policy (POLICY in bagshop.py and the page at
/hospital-bag/policies) made real, in the same words.

The family asks from the order in the app (Orders → the bag → Return or exchange):
- Unused items in their original packing come back within 7 days of delivery. A size that doesn't fit is exchanged
  once, free, while the new size is in stock.
- Hygiene items (returnable False in BAG) come back only while still sealed, unless they arrive damaged or wrong.
- Damaged, faulty or wrong items: within 48 hours of delivery, with a photo; replaced or refunded in full.
- A bag that arrived after the promised day may be returned for a full refund of what comes back.
- The refund is what was paid for each unit that comes back (units at the bag price first). Online payments go back
  the way they came; pay-on-delivery refunds go to a UPI ID the family gives. Nobody is ever asked for a PIN or OTP.

A request is a timeline entry on the order {"s": "return_requested", "rid", "reason", "kind", "lines", "refund", "to",
"upi", "photos", "note"} and the order's status follows it: return_requested → returned (it reached us) → refunded,
or back to delivered when an exchange goes out or the request is declined. The team works them in Admin → Orders.
"""
from __future__ import annotations

import base64
import re
import secrets
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from .admin import Admin, log
from .admin import me as admin_me
from .auth import csrf, current_user, limit
from . import bagshop as _bs
from .bagshop import BY_ID, IST, SHOP_ID, _household, _left, brand
from .db import get_db
from .models import BagItem, Order, now

r = APIRouter(prefix="/api/v1/shop/bag")
xr = APIRouter(prefix="/api/admin/orders")

SUPPORT = "support@urbanhealth.in"
WINDOW = 7 * 86400      # unused items, sizes, late delivery
QUICK = 48 * 3600       # damaged, faulty or wrong
LATE_GRACE = 6 * 3600   # the promised time is 6 pm on the chosen day; after midnight it is a day late
REASONS = {   # key: (what the family taps, what it leads to)
    "size": ("Size doesn't fit", "exchange"),
    "damaged": ("Damaged or faulty", "refund"),
    "wrong": ("Not what I ordered", "refund"),
    "late": ("Arrived later than promised", "refund"),
    "not_needed": ("No longer needed", "refund"),
}
UPI_RE = re.compile(r"[A-Za-z0-9.\-_]{2,128}@[A-Za-z][A-Za-z0-9]{1,63}")
OPEN = ("return_requested", "returned")


def is_bag(o: Order) -> bool:
    return bool(o) and o.store_id == SHOP_ID and any(str(ln.get("sku", "")).startswith("hb-") for ln in (o.items or []))


def online_paid(o: Order) -> bool:
    p = o.payment or ""
    return p.endswith("paid") and not p.startswith("cod")


def delivered_at(o: Order) -> int:
    """The first delivery: every window counts from the day the bag arrived."""
    ts = [t.get("t") or 0 for t in (o.timeline or []) if t.get("s") == "delivered"]
    return min(ts) if ts else 0


def was_late(o: Order) -> bool:
    d = delivered_at(o)
    return bool(d and o.eta and d > o.eta + LATE_GRACE)


def _requests(o: Order) -> list[dict]:
    return [t for t in (o.timeline or []) if t.get("s") == "return_requested"]


def _outcome(o: Order, req: dict) -> tuple[str, dict]:
    """Where one request stands, from what the team recorded after it (up to the next request)."""
    tl = list(o.timeline or [])
    at = next((i for i, t in enumerate(tl) if t.get("s") == "return_requested" and t.get("rid") == req.get("rid")), len(tl))
    state, last = "requested", {}
    for t in tl[at + 1:]:
        if t.get("s") == "return_requested":
            break
        k = {"returned": "received", "refunded": "refunded", "exchanged": "exchanged", "return_declined": "declined"}.get(t.get("s"))
        if k:
            state, last = k, t
    return state, last


def refunded_so_far(o: Order) -> int:
    return sum(int(t.get("amount") or 0) for t in (o.timeline or []) if t.get("s") == "refunded")


def _used(o: Order) -> tuple[dict, set]:
    """Units already asked back (requests the team did not decline) and the lines already exchanged once."""
    used, exchanged = {}, set()
    for req in _requests(o):
        state, _ = _outcome(o, req)
        if state == "declined":
            continue
        for ln in req.get("lines") or []:
            used[ln["sku"]] = used.get(ln["sku"], 0) + int(ln.get("qty") or 0)
            if req.get("kind") == "exchange":
                exchanged.add(ln["sku"])
    return used, exchanged


def unit_refund(ln: dict, n: int) -> int:
    """What the family paid for n units of a line: the units at the bag price first, then the rest at full price."""
    p, b = int(ln.get("price") or 0), int(ln.get("bag") or 0)
    k = min(n, b)
    return int(round(k * p * _bs.BAG_RATE + (n - k) * p))


def _day(ts: int) -> str:
    return datetime.fromtimestamp(ts, IST).strftime("%a %d %b")


def summary(o: Order) -> dict | None:
    """What the order page shows: can the family ask, until when, and where the latest request stands. No database."""
    if not is_bag(o):
        return None
    d, t = delivered_at(o), now()
    used, _ = _used(o)
    left = sum(max(0, int(ln.get("qty") or 0) - used.get(ln["sku"], 0)) for ln in (o.items or [])
               if str(ln.get("sku", "")).startswith("hb-") and int(ln.get("price") or 0) > 0)
    reqs = _requests(o)
    out = {"can": bool(d) and o.status not in OPEN + ("cancelled",) and left > 0 and t <= d + WINDOW,
           "until": d + WINDOW if d else 0, "quickUntil": d + QUICK if d else 0, "delivered": d, "open": None,
           "refunded": refunded_so_far(o), "policy": "/hospital-bag/policies"}
    if reqs:
        req = reqs[-1]
        state, last = _outcome(o, req)
        out["open"] = {"state": state, "reason": REASONS.get(req.get("reason"), ("Return",))[0], "kind": req.get("kind"), "refund": req.get("refund", 0),
                       "to": req.get("to"), "upi": req.get("upi", ""), "t": req.get("t"), "why": last.get("why", ""), "amount": last.get("amount"),
                       "lines": [{"name": x.get("name"), "qty": x.get("qty"), "opt": x.get("opt", ""), "to": x.get("to", "")} for x in req.get("lines") or []]}
    return out


def options(db: Session, o: Order) -> dict:
    """Everything the return sheet needs: the lines that can still come back, the reasons open today and the sizes in stock."""
    s = summary(o) or {}
    d, t = delivered_at(o), now()
    used, exchanged = _used(o)
    rows = {x.id: x for x in db.scalars(select(BagItem)).all()}
    lines = []
    for ln in o.items or []:
        sku = str(ln.get("sku", ""))
        if not sku.startswith("hb-") or int(ln.get("price") or 0) <= 0:
            continue
        iid = sku[3:]
        b = BY_ID.get(iid)
        n = max(0, int(ln.get("qty") or 0) - used.get(sku, 0))
        lines.append({"sku": sku, "name": b[2] if b else ln.get("name", ""), "brand": brand(iid), "opt": ln.get("opt", ""), "qty": n, "bought": int(ln.get("qty") or 0),
                      "unit": unit_refund(ln, 1), "hygiene": ln.get("returnable") is False, "exchanged": sku in exchanged,
                      "sizes": [{"k": c, "left": _left(rows.get(iid), c)} for c in (b[6] or [])] if b and b[6] else []})
    reasons = []
    if d and t <= d + QUICK:
        reasons += ["damaged", "wrong"]
    if d and t <= d + WINDOW:
        if any(x["sizes"] and not x["exchanged"] and x["qty"] for x in lines):
            reasons.insert(0, "size")
        if was_late(o):
            reasons.append("late")
        reasons.append("not_needed")
    why = ""
    if not d:
        why = "You can ask for a return once your bag has been delivered."
    elif o.status in OPEN:
        why = "We're looking after your return request. You'll see each step here."
    elif t > d + WINDOW:
        why = f"The 7-day return window ended on {_day(d + WINDOW)}. If something isn't right, write to {SUPPORT} and we'll do our best to help."
    elif not any(x["qty"] for x in lines):
        why = "Everything in this order has already been returned."
    prev = next((q.get("upi") for q in reversed(_requests(o)) if q.get("upi")), "")
    return {**s, "can": bool(s.get("can")) and bool(reasons), "why": why, "reasons": [{"k": k, "label": REASONS[k][0], "kind": REASONS[k][1]} for k in reasons],
            "lines": lines, "pay": "online" if online_paid(o) else "cod", "upi": prev, "support": SUPPORT}


# ---- the family ---------------------------------------------------------------------------------------------------------
def _mine(request: Request, db: Session, oid: str):
    u = current_user(request, db)
    if not u:
        raise HTTPException(401, "Sign in first.")
    h = _household(db, u)
    o = db.get(Order, oid)
    if not o or o.household_id != h.id or not is_bag(o):
        raise HTTPException(404, "order not found")
    return u, h, o


@r.get("/orders/{oid}/return")
def return_options(oid: str, request: Request, db: Session = Depends(get_db, scope="function")):
    _, _, o = _mine(request, db, oid)
    return options(db, o)


class LineIn(BaseModel):
    sku: str
    qty: int = 1
    to: str = ""      # the new size, for an exchange


class ReturnIn(BaseModel):
    reason: str
    want: str = "refund"      # damaged or wrong: "refund" or "replace"
    lines: list[LineIn] = []
    unused: bool = False      # unused, in the original packing; hygiene items still sealed
    note: str = ""
    upi: str = ""
    photos: list[str] = []    # data: URLs, resized on the phone


def _photo(data_url: str) -> tuple[bytes, str]:
    from .storage import sniff
    m = re.fullmatch(r"data:image/[a-z+.-]+;base64,([A-Za-z0-9+/=\s]+)", data_url or "")
    if not m:
        raise HTTPException(400, "That photo couldn't be read. Try another one.")
    try:
        raw = base64.b64decode(m.group(1), validate=False)
    except Exception:
        raise HTTPException(400, "That photo couldn't be read. Try another one.")
    if len(raw) > 6 * 1024 * 1024:
        raise HTTPException(400, "That photo is too large. Try a smaller one.")
    mime = sniff(raw)
    if mime not in ("image/jpeg", "image/png", "image/webp", "image/heic"):
        raise HTTPException(400, "Add a photo (JPEG or PNG).")
    return raw, mime


@r.post("/orders/{oid}/return", dependencies=[Depends(csrf)])
def ask_return(oid: str, body: ReturnIn, request: Request, db: Session = Depends(get_db, scope="function")):
    from .routes import order_json
    u, h, o = _mine(request, db, oid)
    limit(request, f"bagreturn:{u.id}", 10, 3600)
    opt = options(db, o)
    if not opt["can"]:
        raise HTTPException(409, opt["why"] or "This order can't be returned now.")
    reasons = {x["k"] for x in opt["reasons"]}
    if body.reason not in REASONS:
        raise HTTPException(400, "Choose a reason.")
    if body.reason not in reasons:
        if body.reason in ("damaged", "wrong"):
            raise HTTPException(409, f"It's been more than 48 hours since your bag arrived. Please write to {SUPPORT} with a photo, and we'll do our best to help.")
        raise HTTPException(409, "That reason isn't open for this order.")
    by = {x["sku"]: x for x in opt["lines"]}
    picked, seen = [], set()
    for ln in body.lines[:20]:
        x = by.get(ln.sku)
        if not x or ln.sku in seen:
            raise HTTPException(400, "Choose the items to send back.")
        seen.add(ln.sku)
        if not 1 <= ln.qty <= x["qty"]:
            raise HTTPException(400, f"You can send back up to {x['qty']} of {x['name']}.")
        picked.append((ln, x))
    if not picked:
        raise HTTPException(400, "Choose the items to send back.")
    quick = body.reason in ("damaged", "wrong")
    if not quick and not body.unused:
        hyg = any(x["hygiene"] for _, x in picked)
        raise HTTPException(400, "Please confirm the items are unused and in their original packing" + (", and the hygiene items are still sealed." if hyg else "."))
    kind = REASONS[body.reason][1]
    if quick and body.want == "replace":
        kind = "replace"
    out = []
    for ln, x in picked:
        line = {"sku": ln.sku, "name": f"{x['name']} ({x['brand']})", "qty": ln.qty, "opt": x["opt"]}
        if kind == "exchange":
            sizes = {s["k"]: s["left"] for s in x["sizes"]}
            if not sizes:
                raise HTTPException(400, f"{x['name']} comes in one size, so it can be returned but not exchanged.")
            if x["exchanged"]:
                raise HTTPException(409, f"{x['name']} has already been exchanged once. You can still return it for a refund within 7 days.")
            if ln.to not in sizes or ln.to == x["opt"]:
                raise HTTPException(400, f"Choose the new size for {x['name']}.")
            if sizes[ln.to] is not None and sizes[ln.to] < ln.qty:
                raise HTTPException(409, f"{x['name']} in {ln.to} is out of stock right now. You can return it for a refund instead.")
            line["to"] = ln.to
        elif kind == "replace":
            line["to"] = x["opt"]
        out.append(line)
    refund = 0
    if kind == "refund":
        items = {ln["sku"]: ln for ln in o.items or []}
        refund = sum(unit_refund(items[ln["sku"]], ln["qty"]) for ln in out)
        refund = max(0, min(refund, int(o.total or 0) - refunded_so_far(o)))
    to, upi = "", ""
    if kind == "refund":
        if online_paid(o):
            to = "original"
        else:
            upi = re.sub(r"\s+", "", body.upi or "")
            if not UPI_RE.fullmatch(upi):
                raise HTTPException(400, "Enter the UPI ID to refund to, like name@okbank.")
            to = "upi"
    photos = [p for p in body.photos if p][:3]
    if quick and not photos:
        raise HTTPException(400, "Add a photo of the item, so we can sort it out quickly.")
    rid = secrets.token_hex(3)
    ids = []
    if photos:
        from .storage import put
        for i, p in enumerate(photos):
            raw, mime = _photo(p)
            fid = f"ret-{o.id}-{rid}-{i}"
            put(db, o.household_id, fid, raw, mime, f"Return photo {i + 1} for order {o.id}", u.id)
            ids.append(fid)
    note = re.sub(r"[<>\x00-\x1f]", " ", body.note or "").strip()[:300]
    req = {"s": "return_requested", "t": now(), "rid": rid, "reason": body.reason, "kind": kind, "lines": out, "refund": refund,
           "to": to, "upi": upi, "photos": ids, "note": note, "by": "family"}
    o.timeline = list(o.timeline or []) + [req]
    o.status = "return_requested"
    what = ", ".join(f"{ln['qty']} × {ln['name']}" + (f" → {ln['to']}" if kind == "exchange" else "") for ln in out)
    head = {"exchange": "Exchange requested", "replace": "Replacement requested"}.get(kind, "Return requested")
    then = {"exchange": "Your new size goes out as soon as we've arranged the pickup.",
            "replace": "We'll send a replacement and collect the one that's wrong."}.get(kind, f"Once it reaches us, we'll refund ₹{refund:,} " + ("the way you paid." if to == "original" else f"to {upi}."))
    try:
        from .inbox import notify
        notify(db, o.household_id, "order", f"{head} · {o.id}", f"We'll arrange the pickup from your door and keep you posted here. {then}", {"order": o.id}, "", "/app#page=orders")
    except Exception as e:
        print("[bag] return notice failed:", str(e)[:120], flush=True)
    try:
        from .partner import alert_store
        alert_store(db, SHOP_ID, f"{head} for {o.id} · {REASONS[body.reason][0]}",
                    f"{o.member} asked for a {kind} on hospital bag order {o.id}.\nReason: {REASONS[body.reason][0]}\nItems: {what}\n"
                    + (f"Refund: ₹{refund:,} " + ("to the original payment" if to == "original" else f"to UPI {upi}") + "\n" if kind == "refund" else "")
                    + (f"Note: {note}\n" if note else "") + (f"{len(ids)} photo(s) attached in Admin.\n" if ids else "")
                    + f"Pickup address: {o.address}\nOpen Admin → Orders → Returns and refunds.")
    except Exception as e:
        print("[bag] return team alert failed:", str(e)[:120], flush=True)
    return {"ok": True, "order": order_json(o)}


# ---- the team (Admin → Orders) -----------------------------------------------------------------------------------------
def _card(o: Order) -> dict:
    reqs = _requests(o)
    req = reqs[-1] if reqs and o.status in OPEN else None
    a = o.addr if isinstance(o.addr, dict) else {}
    out = {"id": o.id, "status": o.status, "member": o.member, "phone": a.get("phone", ""), "address": o.address, "payment": o.payment, "total": o.total,
           "created": o.created, "delivered": delivered_at(o), "refunded": refunded_so_far(o), "late": was_late(o)}
    if req:
        out["req"] = {"rid": req.get("rid"), "t": req.get("t"), "reason": REASONS.get(req.get("reason"), ("Return",))[0], "kind": req.get("kind"),
                      "lines": req.get("lines") or [], "refund": req.get("refund", 0), "to": req.get("to"), "upi": req.get("upi", ""),
                      "photos": len(req.get("photos") or []), "note": req.get("note", ""), "received": o.status == "returned"}
    else:
        out["due"] = max(0, int(o.total or 0) - refunded_so_far(o))   # cancelled after paying online: the whole order comes back
    return out


@xr.get("/returns")
def admin_returns(a: Admin = Depends(admin_me), db: Session = Depends(get_db, scope="function")):
    """Open return requests, and bags cancelled after an online payment that still need their refund."""
    rows = db.scalars(select(Order).where(Order.store_id == SHOP_ID, Order.status.in_(OPEN)).order_by(Order.created.desc()).limit(200)).all()
    cx = db.scalars(select(Order).where(Order.store_id == SHOP_ID, Order.status == "cancelled").order_by(Order.created.desc()).limit(300)).all()
    due = [o for o in cx if online_paid(o) and refunded_so_far(o) < int(o.total or 0)]
    return {"returns": [_card(o) for o in rows if is_bag(o)], "refunds": [_card(o) for o in due if is_bag(o)], "support": SUPPORT}


def _open(db: Session, oid: str) -> tuple[Order, dict]:
    o = db.get(Order, oid)
    if not o or not is_bag(o):
        raise HTTPException(404, "order not found")
    reqs = _requests(o)
    if o.status not in OPEN or not reqs:
        raise HTTPException(409, "This order has no open return.")
    return o, reqs[-1]


@xr.get("/{oid}/return/photo/{i}")
def admin_photo(oid: str, i: int, a: Admin = Depends(admin_me), db: Session = Depends(get_db, scope="function")):
    from fastapi.responses import Response

    from .storage import get
    o = db.get(Order, oid)
    reqs = _requests(o) if o else []
    ids = (reqs[-1].get("photos") or []) if reqs else []
    if not 0 <= i < len(ids):
        raise HTTPException(404, "no such photo")
    got = get(db, o.household_id, ids[i])
    if not got:
        raise HTTPException(404, "no such photo")
    row, data = got
    log(db, a.email, "order.return.photo", oid)
    return Response(data, media_type=row.mime, headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"})


def _tell(db: Session, o: Order, title: str, text: str) -> None:
    try:
        from .inbox import notify
        notify(db, o.household_id, "order", f"{title} · {o.id}", text, {"order": o.id}, "", "/app#page=orders")
    except Exception as e:
        print("[bag] return notice failed:", str(e)[:120], flush=True)


@xr.post("/{oid}/return/received")
def admin_received(oid: str, a: Admin = Depends(admin_me), db: Session = Depends(get_db, scope="function")):
    from .routes import order_json
    o, req = _open(db, oid)
    if o.status != "return_requested":
        raise HTTPException(409, "Already marked as received.")
    o.status = "returned"
    o.timeline = list(o.timeline or []) + [{"s": "returned", "t": now(), "by": a.email, "rid": req.get("rid")}]
    log(db, a.email, f"order.return.received {oid}")
    nxt = {"exchange": "Your new size goes out shortly.", "replace": "Your replacement goes out shortly."}.get(
        req.get("kind"), f"We're starting your refund of ₹{int(req.get('refund') or 0):,} today. It usually shows within 5 to 7 working days.")
    _tell(db, o, "We've received your return", nxt)
    return order_json(o)


class ExchangeIn(BaseModel):
    note: str = ""


@xr.post("/{oid}/return/exchange")
def admin_exchange(oid: str, body: ExchangeIn, a: Admin = Depends(admin_me), db: Session = Depends(get_db, scope="function")):
    """The new size (or the replacement) is on its way: count it out of stock and close the request."""
    from .routes import order_json
    o, req = _open(db, oid)
    if req.get("kind") not in ("exchange", "replace"):
        raise HTTPException(409, "This request is for a refund.")
    rows = {x.id: x for x in db.scalars(select(BagItem).with_for_update()).all()}
    for ln in req.get("lines") or []:
        x, key = rows.get(ln["sku"][3:]), ln.get("to", "")
        n = _left(x, key)
        if x and n is not None:
            x.stock = {**(x.stock or {}), key: max(0, n - int(ln.get("qty") or 0))}
    o.timeline = list(o.timeline or []) + [{"s": "exchanged", "t": now(), "by": a.email, "rid": req.get("rid"), "lines": req.get("lines"), "note": body.note.strip()[:200]}]
    o.status = "delivered"
    log(db, a.email, f"order.return.exchange {oid}")
    what = ", ".join(f"{ln['name']}" + (f" in {ln['to']}" if ln.get("to") else "") for ln in req.get("lines") or [])
    _tell(db, o, "Your exchange is on its way" if req.get("kind") == "exchange" else "Your replacement is on its way", f"{what}. Thank you for your patience.")
    return order_json(o)


class DeclineIn(BaseModel):
    why: str


@xr.post("/{oid}/return/decline")
def admin_decline(oid: str, body: DeclineIn, a: Admin = Depends(admin_me), db: Session = Depends(get_db, scope="function")):
    from .routes import order_json
    o, req = _open(db, oid)
    why = re.sub(r"[<>\x00-\x1f]", " ", body.why or "").strip()[:300]
    if len(why) < 8:
        raise HTTPException(400, "Tell the family why, in a sentence. They will see it.")
    o.timeline = list(o.timeline or []) + [{"s": "return_declined", "t": now(), "by": a.email, "rid": req.get("rid"), "why": why}]
    o.status = "delivered"
    log(db, a.email, f"order.return.decline {oid}", why)
    _tell(db, o, "About your return request", f"{why} If you think we've got this wrong, write to {SUPPORT} and we'll gladly look again.")
    return order_json(o)

"""Bills: a Urban Health-branded PDF receipt for every order, and return / claim requests.

The seller (pharmacy or lab) issues the tax invoice under its own licence and GSTIN; this receipt documents the order as
placed through the platform. The PDF is drawn with PyMuPDF (already a dependency) — no HTML-to-PDF service, no third party.
"""
from __future__ import annotations

import io
import os
import time
from pathlib import Path

from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .db import get_db
from .models import Order, now
from .routes import household, order_json

r = APIRouter(prefix="/api/v1")
ROOT = Path(__file__).resolve().parents[1]
LOGO = ROOT / "web" / "brand" / "png" / "user-logo.png"
INK, MUTE, BLUE, LINE = (0.07, 0.09, 0.15), (0.42, 0.45, 0.52), (0.18, 0.36, 1.0), (0.88, 0.9, 0.93)
RETURN_REASONS = {"damaged": "Damaged or tampered on arrival", "wrong": "Wrong item or strength delivered", "expiry": "Short expiry (less than 3 months)",
                  "not_needed": "No longer needed (sealed, within 7 days)", "quality": "Quality concern", "other": "Other"}
NON_RETURNABLE = ("insulin", "vaccine", "inhaler", "drops", "syrup", "injection", "refrigerat", "cold chain")


def _order(db: Session, oid: str, key: str | None) -> Order:
    h = household(db, key, create=False)
    o = db.get(Order, oid)
    if not h or not o or o.household_id != h.id:
        raise HTTPException(404, "order not found")
    return o


def money(n) -> str:
    n = int(round(n or 0))
    s = f"{n:,}"
    if n >= 1000:  # Indian grouping 12,34,567
        head, tail = str(n)[:-3], str(n)[-3:]
        parts = []
        while len(head) > 2:
            parts.insert(0, head[-2:]); head = head[:-2]
        if head:
            parts.insert(0, head)
        s = ",".join(parts) + "," + tail
    return "Rs. " + s


def receipt_pdf(o: Order) -> bytes:
    try:
        import pymupdf  # type: ignore
    except ImportError:  # pragma: no cover
        import fitz as pymupdf  # type: ignore
    doc = pymupdf.open()
    page = doc.new_page(width=595, height=842)  # A4
    W, M = 595, 44
    y = 46
    if LOGO.exists():
        page.insert_image(pymupdf.Rect(M, y - 6, M + 150, y + 34), filename=str(LOGO), keep_proportion=True)
    page.insert_text((W - M - 190, y + 6), "ORDER RECEIPT", fontsize=9, fontname="helv", color=MUTE)
    page.insert_text((W - M - 190, y + 24), f"THT-{o.id}", fontsize=16, fontname="hebo", color=INK)
    y += 56
    page.draw_line((M, y), (W - M, y), color=LINE, width=1)
    y += 20
    store = o.store
    col2 = W / 2 + 10
    page.insert_text((M, y), "ORDERED BY", fontsize=8, fontname="helv", color=MUTE)
    page.insert_text((col2, y), "SELLER", fontsize=8, fontname="helv", color=MUTE)
    y += 14
    page.insert_text((M, y), (o.member or "Family member")[:48], fontsize=11, fontname="hebo", color=INK)
    page.insert_text((col2, y), (store.name if store else "Partner")[:48], fontsize=11, fontname="hebo", color=INK)
    y += 14
    for line in [o.address[:70] or "—", time.strftime("%d/%m/%Y %H:%M", time.localtime(o.created)) + " IST",
                 f"Payment: {o.payment or 'as agreed with seller'}"]:
        page.insert_text((M, y), line, fontsize=9, fontname="helv", color=MUTE); y += 12
    y2 = y - 36
    if store:
        for line in [", ".join(x for x in (store.address, store.area, store.city) if x)[:70] or "—", f"Licence: {store.licence or 'on the seller invoice'}",
                     f"Phone: {store.phone or '—'}"]:
            page.insert_text((col2, y2), line, fontsize=9, fontname="helv", color=MUTE); y2 += 12
    y = max(y, y2) + 18
    # table
    page.draw_rect(pymupdf.Rect(M, y, W - M, y + 22), color=None, fill=(0.95, 0.96, 0.98))
    kind_lab = o.kind == "lab"
    page.insert_text((M + 8, y + 15), "TEST" if kind_lab else "ITEM", fontsize=8, fontname="hebo", color=MUTE)
    if not kind_lab:
        page.insert_text((W - M - 180, y + 15), "QTY", fontsize=8, fontname="hebo", color=MUTE)
        page.insert_text((W - M - 130, y + 15), "PRICE", fontsize=8, fontname="hebo", color=MUTE)
    page.insert_text((W - M - 60, y + 15), "AMOUNT", fontsize=8, fontname="hebo", color=MUTE)
    y += 22
    for it in o.items or []:
        y += 18
        name = str(it.get("name", ""))[:56] + (" (Rx)" if it.get("rx") else "")
        page.insert_text((M + 8, y), name, fontsize=10, fontname="helv", color=INK)
        price = int(it.get("price", 0) or 0)
        qty = int(it.get("qty", 1) or 1)
        if not kind_lab:
            page.insert_text((W - M - 180, y), str(qty), fontsize=10, fontname="helv", color=INK)
            page.insert_text((W - M - 130, y), money(price)[4:], fontsize=10, fontname="helv", color=INK)
        page.insert_text((W - M - 60, y), money(price * qty)[4:], fontsize=10, fontname="helv", color=INK)
        page.draw_line((M, y + 6), (W - M, y + 6), color=LINE, width=0.5)
    y += 22
    rows = [("Subtotal", o.subtotal), ("Home collection" if kind_lab else "Delivery", o.fee)]
    if o.discount:
        rows.append(("Savings off MRP", -o.discount))
    for label, val in rows:
        page.insert_text((W - M - 200, y), label, fontsize=9.5, fontname="helv", color=MUTE)
        page.insert_text((W - M - 60, y), (("- " if val < 0 else "") + money(abs(val))[4:]), fontsize=9.5, fontname="helv", color=INK)
        y += 15
    page.draw_line((W - M - 200, y - 4), (W - M, y - 4), color=INK, width=1)
    y += 8
    page.insert_text((W - M - 200, y), "Total paid / payable", fontsize=11, fontname="hebo", color=INK)
    page.insert_text((W - M - 80, y), money(o.total), fontsize=12, fontname="hebo", color=BLUE)
    y += 30
    st = order_json(o)
    page.insert_text((M, y), f"Status: {st['status'].replace('_', ' ')}", fontsize=9.5, fontname="helv", color=INK)
    y += 26
    foot = ["This receipt records an order placed through Urban Health (urbanhealth.in). The tax invoice under the seller's",
            "drug licence / NABL registration and GSTIN is issued by the seller and is available from them on request.",
            "Returns: sealed, unexpired medicines within 7 days of delivery; prescription, refrigerated and opened items cannot be returned.",
            "Raise a return or a claim from Bills in the app. Support: " + (os.getenv("LEGAL_EMAIL") or "support@urbanhealth.in") + "."]
    for line in foot:
        page.insert_text((M, y), line, fontsize=8, fontname="helv", color=MUTE); y += 11
    page.insert_text((M, 842 - 30), f"Generated {time.strftime('%d/%m/%Y %H:%M')} IST · Urban Health", fontsize=7.5, fontname="helv", color=MUTE)
    buf = io.BytesIO()
    doc.save(buf, garbage=3, deflate=True)
    doc.close()
    return buf.getvalue()


@r.get("/orders/{oid}/receipt.pdf")
def receipt(oid: str, db: Session = Depends(get_db), x_dokko_key: str | None = Header(None)):
    o = _order(db, oid, x_dokko_key)
    pdf = receipt_pdf(o)
    return Response(pdf, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="THT-{o.id}.pdf"', "Cache-Control": "private, no-store"})


class ReturnIn(BaseModel):
    reason: str
    note: str = ""
    items: list[str] = []


@r.post("/orders/{oid}/return")
def request_return(oid: str, body: ReturnIn, db: Session = Depends(get_db), x_dokko_key: str | None = Header(None)):
    """A return (medicines) or a re-test / refund request (labs). The seller answers from the partner side; the timeline shows it."""
    o = _order(db, oid, x_dokko_key)
    if body.reason not in RETURN_REASONS:
        raise HTTPException(400, "choose a reason")
    if o.status in ("cancelled", "return_requested", "returned", "refunded"):
        raise HTTPException(400, "This order already has a return or cancellation.")
    if o.kind != "lab":
        blocked = [i.get("name") for i in o.items if i.get("rx") or any(k in str(i.get("name", "")).lower() for k in NON_RETURNABLE)]
        wanted = [i for i in o.items if not body.items or i.get("sku") in body.items or i.get("name") in body.items]
        if wanted and all((w.get("name") in blocked) for w in wanted) and body.reason not in ("damaged", "wrong"):
            raise HTTPException(400, "Prescription, refrigerated and opened items can only be returned if damaged or wrong.")
        if o.created < now() - 7 * 86400 and body.reason not in ("damaged", "wrong", "quality"):
            raise HTTPException(400, "Returns are accepted within 7 days of delivery.")
    o.status = "return_requested"
    o.timeline = list(o.timeline or []) + [{"s": "return_requested", "t": now(), "reason": body.reason, "note": body.note[:300], "items": body.items[:20]}]
    return {"ok": True, "status": o.status, "reason": RETURN_REASONS[body.reason], "next": "The seller reviews the request within 2 working days. You will see the answer on this order and in notifications."}


@r.get("/returns/policy")
def policy():
    return {"reasons": RETURN_REASONS, "medicines": ["Sealed and unexpired, within 7 days of delivery", "Prescription-only, refrigerated (insulin, vaccines) and opened items are not returnable unless damaged or wrong",
            "Refund goes back the way you paid within 5-7 working days after the seller receives the item"],
            "labs": ["Cancel free up to 2 hours before the sample is collected", "A re-test is free if the lab reports a sample problem", "Refunds for cancelled bookings within 5-7 working days"],
            "insurance": ["Keep the original bill, the prescription and the discharge summary", "Cashless: show the card at the TPA desk before admission; planned treatment needs pre-authorisation 1-3 days ahead",
                          "Reimbursement: file within the insurer's window (usually 30 days of discharge) with the claim form, bills, reports and ID"]}

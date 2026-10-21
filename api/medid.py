"""Lock-screen Medical ID (/api/v1/medical-id, /m/<token>): what a first responder needs, nothing else.

The family switches it on per person from Safety. The app sends the few fields the person chose to show (blood group,
allergies, conditions, current medicines, emergency contacts, donor wish, doctor), the server seals them with the data
key, and publishes a page at urbanhealth.in/m/<token> plus a QR code to print or set as the phone's lock screen.
No sign-in is needed to read it (that is the point), so the page shows only what was chosen, counts views, and the
family can rotate the link or switch it off any time.
"""
from __future__ import annotations

import html
import io
import json
import secrets
import time
import zlib

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from .auth import limit
from .db import get_db
from .family import _key, open_with_keys
from .models import MedicalId, now
from .routes import household

r = APIRouter()
AAD = b"tht-medid-v1"
FIELDS = ("name", "age", "sex", "blood", "allergies", "conditions", "medicines", "contacts", "donor", "doctor", "doctorPhone", "notes", "pregnant", "lang")


def _seal(obj: dict) -> bytes:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    raw = zlib.compress(json.dumps(obj, separators=(",", ":"), ensure_ascii=False).encode(), 6)
    nonce = secrets.token_bytes(12)
    return b"v1" + nonce + AESGCM(_key()).encrypt(nonce, raw, AAD)


def _open(blob: bytes) -> dict:
    return json.loads(zlib.decompress(open_with_keys(blob[14:], blob[2:14], AAD)).decode())


def _clean(p: dict) -> dict:
    out = {}
    for k in FIELDS:
        v = p.get(k)
        if v in (None, "", [], {}):
            continue
        if k in ("allergies", "conditions", "medicines"):
            out[k] = [str(x).strip()[:80] for x in (v if isinstance(v, list) else [v]) if str(x).strip()][:12]
        elif k == "contacts":
            out[k] = [{"name": str(c.get("name", ""))[:60], "rel": str(c.get("rel", ""))[:30], "phone": str(c.get("phone", ""))[:20]}
                      for c in (v if isinstance(v, list) else []) if isinstance(c, dict) and str(c.get("phone", "")).strip()][:4]
        elif k == "pregnant":
            out[k] = bool(v)
        elif k == "age":
            try:
                out[k] = int(v)
            except Exception:
                pass
        else:
            out[k] = str(v).strip()[:200 if k == "notes" else 80]
    return out


def mid_json(m: MedicalId, base: str) -> dict:
    return {"member": m.member_id, "token": m.token, "enabled": m.enabled, "url": f"{base}/m/{m.token}", "views": m.views, "lastView": m.last_view, "updated": m.updated}


def _base(request: Request) -> str:
    host = request.headers.get("x-forwarded-host") or request.headers.get("host") or "urbanhealth.in"
    proto = request.headers.get("x-forwarded-proto") or request.url.scheme
    return f"{proto}://{host.split(',')[0].strip()}"


class MedIdIn(BaseModel):
    payload: dict
    rotate: bool = False


@r.get("/api/v1/medical-id")
def list_ids(request: Request, db: Session = Depends(get_db), x_dokko_key: str | None = Header(None)):
    h = household(db, x_dokko_key, create=False)
    if not h:
        return {"ids": []}
    rows = db.scalars(select(MedicalId).where(MedicalId.household_id == h.id)).all()
    return {"ids": [mid_json(m, _base(request)) for m in rows]}


@r.put("/api/v1/medical-id/{member}")
def put_id(member: str, body: MedIdIn, request: Request, db: Session = Depends(get_db), x_dokko_key: str | None = Header(None)):
    """Create, update or rotate one person's Medical ID. The payload is exactly what will be shown."""
    h = household(db, x_dokko_key)
    if not h:
        raise HTTPException(400, "missing household key")
    limit(request, f"medid:{h.id}", 30, 3600)
    payload = _clean(body.payload or {})
    if not payload.get("name"):
        raise HTTPException(400, "The name is needed.")
    cur = db.scalar(select(MedicalId).where(MedicalId.household_id == h.id, MedicalId.member_id == member[:32]))
    if cur and body.rotate:
        db.delete(cur)
        db.flush()
        cur = None
    if cur:
        cur.blob, cur.enabled, cur.updated = _seal(payload), True, now()
    else:
        cur = MedicalId(token=secrets.token_urlsafe(16), household_id=h.id, member_id=member[:32], blob=_seal(payload), enabled=True)
        db.add(cur)
    db.flush()
    return mid_json(cur, _base(request))


@r.post("/api/v1/medical-id/{member}/off")
def off_id(member: str, request: Request, db: Session = Depends(get_db), x_dokko_key: str | None = Header(None)):
    h = household(db, x_dokko_key, create=False)
    cur = h and db.scalar(select(MedicalId).where(MedicalId.household_id == h.id, MedicalId.member_id == member[:32]))
    if not cur:
        raise HTTPException(404)
    cur.enabled, cur.updated = False, now()
    return mid_json(cur, _base(request))


@r.get("/api/v1/medical-id/{member}/qr.svg")
def qr(member: str, request: Request, db: Session = Depends(get_db), x_dokko_key: str | None = Header(None)):
    import qrcode
    import qrcode.image.svg

    h = household(db, x_dokko_key, create=False)
    cur = h and db.scalar(select(MedicalId).where(MedicalId.household_id == h.id, MedicalId.member_id == member[:32]))
    if not cur or not cur.enabled:
        raise HTTPException(404)
    img = qrcode.make(f"{_base(request)}/m/{cur.token}", image_factory=qrcode.image.svg.SvgPathImage, box_size=12, border=2)
    buf = io.BytesIO()
    img.save(buf)
    return Response(buf.getvalue(), media_type="image/svg+xml", headers={"Cache-Control": "private, no-store"})


# ---- the public page ---------------------------------------------------------------------------------------------------------
def _load(db: Session, token: str) -> tuple[MedicalId, dict] | None:
    m = db.get(MedicalId, token[:40])
    if not m or not m.enabled:
        return None
    try:
        return m, _open(m.blob)
    except Exception:
        return None


@r.get("/api/v1/m/{token}")
def public_json(token: str, request: Request, db: Session = Depends(get_db)):
    limit(request, "medid-view", 120, 3600)
    got = _load(db, token)
    if not got:
        raise HTTPException(404, "This Medical ID is switched off or the link has changed.")
    m, p = got
    m.views, m.last_view = (m.views or 0) + 1, now()
    return {"medicalId": p, "updated": m.updated}


def page_html(p: dict, updated: int) -> str:
    e = html.escape
    rows = []
    if p.get("blood"):
        rows.append(("Blood group", f"<b class='big'>{e(p['blood'])}</b>"))
    if p.get("allergies"):
        rows.append(("Allergies", "<b class='red'>" + e(", ".join(p["allergies"])) + "</b>"))
    if p.get("conditions"):
        rows.append(("Conditions", e(", ".join(p["conditions"]))))
    if p.get("medicines"):
        rows.append(("Medicines", e(", ".join(p["medicines"]))))
    if p.get("pregnant"):
        rows.append(("Pregnant", "<b class='red'>Yes</b>"))
    if p.get("donor"):
        rows.append(("Donor", e(p["donor"])))
    if p.get("doctor"):
        rows.append(("Doctor", e(p["doctor"]) + (f" · <a href='tel:{e(p['doctorPhone'])}'>{e(p['doctorPhone'])}</a>" if p.get("doctorPhone") else "")))
    if p.get("notes"):
        rows.append(("Notes", e(p["notes"])))
    contacts = "".join(f"<a class='call' href='tel:{e(c['phone'])}'><span>{e(c['name'] or 'Emergency contact')}{(' · ' + e(c['rel'])) if c.get('rel') else ''}</span><b>{e(c['phone'])}</b></a>" for c in p.get("contacts") or [])
    who = e(p.get("name", "")) + (f", {p['age']}" if p.get("age") is not None else "") + (f" · {e(p['sex'])}" if p.get("sex") else "")
    body = "".join(f"<div class='row'><small>{k}</small><div>{v}</div></div>" for k, v in rows)
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex,nofollow">
<title>Medical ID · {e(p.get('name', ''))}</title>
<style>:root{{color-scheme:light}}*{{box-sizing:border-box}}body{{margin:0;font:16px/1.45 -apple-system,Segoe UI,Roboto,Inter,sans-serif;background:#f3f5f9;color:#111827}}
main{{max-width:520px;margin:0 auto;padding:18px 16px 40px}}.hd{{display:flex;align-items:center;gap:12px;margin:6px 0 14px}}.hd .pill{{background:#dc2626;color:#fff;font-weight:800;letter-spacing:.04em;font-size:12px;padding:5px 10px;border-radius:999px}}
h1{{font-size:24px;margin:0 0 4px}}.card{{background:#fff;border:1px solid #e5e7eb;border-radius:16px;padding:14px 16px;box-shadow:0 1px 2px rgba(0,0,0,.04);margin-bottom:12px}}
.row{{display:flex;gap:12px;padding:9px 0;border-bottom:1px solid #f1f5f9}}.row:last-child{{border:0}}.row small{{flex:0 0 110px;color:#6b7280;font-size:12px;text-transform:uppercase;letter-spacing:.04em;padding-top:3px}}
.big{{font-size:26px;color:#dc2626}}.red{{color:#b91c1c}}.call{{display:flex;justify-content:space-between;align-items:center;gap:10px;background:#111827;color:#fff;text-decoration:none;border-radius:12px;padding:12px 14px;margin:8px 0}}.call b{{font-size:17px}}
.sos{{display:block;text-align:center;background:#dc2626;color:#fff;font-weight:800;font-size:18px;text-decoration:none;border-radius:14px;padding:14px}}footer{{color:#6b7280;font-size:12px;margin-top:14px;text-align:center}}</style></head>
<body><main><div class="hd"><span class="pill">MEDICAL ID</span><small style="color:#6b7280">Shown by the person's choice · Urban Health</small></div>
<h1>{who}</h1><div class="card">{body or "<p>No details shared.</p>"}</div>
{f"<div class='card'><small style='color:#6b7280;font-size:12px;text-transform:uppercase;letter-spacing:.04em'>Emergency contacts</small>{contacts}</div>" if contacts else ""}
<a class="sos" href="tel:112">Call 112 · Emergency</a>
<footer>Updated {time.strftime('%d/%m/%Y', time.localtime(updated))}. Information entered by the family for emergencies; verify with the person or their doctor.</footer></main></body></html>"""


@r.get("/m/{token}", response_class=HTMLResponse, include_in_schema=False)
def public_page(token: str, request: Request, db: Session = Depends(get_db)):
    limit(request, "medid-view", 120, 3600)
    got = _load(db, token)
    if not got:
        return HTMLResponse("<!doctype html><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'><title>Medical ID</title><body style='font-family:system-ui;padding:32px;text-align:center'><h2>This Medical ID is switched off</h2><p>The link has changed or the family turned it off. In an emergency, call 112.</p>", status_code=404)
    m, p = got
    m.views, m.last_view = (m.views or 0) + 1, now()
    return HTMLResponse(page_html(p, m.updated), headers={"Cache-Control": "no-store", "X-Robots-Tag": "noindex"})

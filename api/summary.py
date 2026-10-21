"""Share the doctor summary by link (/api/v1/summary/share, /ds/<token>).

The app already prints a one-page summary per person. This turns the same page into a link that works for a doctor
with no app: it opens on any phone, shows who shared it and when it expires, prints cleanly, and goes dark on expiry or
when the family revokes it. The HTML is sealed with the data key at rest (same as documents), views are counted, and the
page carries noindex + a strict CSP so it is never cached or indexed.
"""
from __future__ import annotations

import html as _html
import re
import secrets
import time

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from .auth import csrf, need_user
from .db import get_db
from .family import my_household
from .fitbit import _open, _origin, _seal
from .models import SharedSummary, User, now
from .more import hlimit

r = APIRouter()
MAX_HTML = 400_000


class ShareIn(BaseModel):
    member: str = ""
    name: str = ""
    label: str = ""
    html: str
    hours: int = 48


def _clean(src: str) -> str:
    """The summary is the app's own markup, but it is user data too: no scripts, no handlers, no external loads."""
    s = re.sub(r"(?is)<script.*?</script>", "", src)
    s = re.sub(r"(?is)</?(iframe|object|embed|link|meta|form|input|textarea|select)[^>]*>", "", s)
    s = re.sub(r"(?i)\son\w+\s*=\s*(\"[^\"]*\"|'[^']*'|[^\s>]+)", "", s)
    s = re.sub(r"(?i)\s(href|src)\s*=\s*(\"javascript:[^\"]*\"|'javascript:[^']*'|javascript:[^\s>]+)", "", s)
    s = re.sub(r"(?is)<button[^>]*>.*?</button>", "", s)      # the print button; the page has its own
    m = re.search(r"(?is)<body[^>]*>(.*)</body>", s)
    return (m.group(1) if m else s).strip()


@r.post("/api/v1/summary/share", dependencies=[Depends(csrf)])
def share(body: ShareIn, request: Request, db: Session = Depends(get_db), u: User = Depends(need_user)):
    h = my_household(db, u)
    hlimit(request, "sumshare", h.id, 30, 3600)
    if not body.html or len(body.html) > MAX_HTML:
        raise HTTPException(400, "Nothing to share.")
    hours = max(1, min(24 * 14, body.hours))
    s = SharedSummary(token=secrets.token_urlsafe(27)[:36], household_id=h.id, member_id=body.member[:32], name=body.name[:80], label=body.label[:160],
                      blob=_seal({"html": _clean(body.html)}), by_user=u.id, expires=now() + hours * 3600)
    db.add(s)
    return {"token": s.token, "url": f"{_origin(request)}/ds/{s.token}", "expires": s.expires}


@r.get("/api/v1/summary/share")
def mine(db: Session = Depends(get_db), u: User = Depends(need_user)):
    h = my_household(db, u)
    rows = db.scalars(select(SharedSummary).where(SharedSummary.household_id == h.id, SharedSummary.revoked == False, SharedSummary.expires > now())).all()  # noqa: E712
    return [{"token": s.token, "member": s.member_id, "name": s.name, "label": s.label, "expires": s.expires, "views": s.views, "created": s.created} for s in rows]


@r.delete("/api/v1/summary/share/{token}", dependencies=[Depends(csrf)])
def revoke(token: str, db: Session = Depends(get_db), u: User = Depends(need_user)):
    h = my_household(db, u)
    s = db.get(SharedSummary, token[:36])
    if s and s.household_id == h.id:
        s.revoked = True
    return {"revoked": bool(s and s.household_id == h.id)}


GONE = "<!doctype html><meta charset=utf-8><meta name=robots content=noindex><title>Link expired</title><body style='font-family:system-ui;padding:40px;max-width:520px;margin:auto;text-align:center'><h2>This summary link has expired</h2><p>Ask the family to share a new one from Urban Health.</p>"


@r.get("/ds/{token}", include_in_schema=False)
def view(token: str, db: Session = Depends(get_db)):
    s = db.get(SharedSummary, token[:36])
    if not s or s.revoked or s.expires < now():
        return HTMLResponse(GONE, status_code=404, headers={"Cache-Control": "no-store"})
    s.views += 1
    inner = _open(s.blob).get("html", "")
    exp = time.strftime("%d %b %Y, %H:%M", time.localtime(s.expires))
    page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex,nofollow"><title>Health summary · {_html.escape(s.name or 'Urban Health')}</title>
<style>body{{margin:0;font:15px/1.5 Inter,-apple-system,"Segoe UI",Roboto,sans-serif;color:#14151b;background:#f4f5f9}}.bar{{background:#14151b;color:#fff;padding:12px 16px;display:flex;align-items:center;justify-content:space-between;gap:10px;flex-wrap:wrap;font-size:13px}}.bar b{{font-size:14px}}.bar button{{border:0;border-radius:999px;background:#fff;color:#14151b;font-weight:600;padding:8px 14px}}
.wrap{{max-width:820px;margin:0 auto;padding:16px}}.sheet{{background:#fff;border-radius:16px;padding:20px;box-shadow:0 1px 2px rgba(0,0,0,.05)}}@media print{{.bar{{display:none}}.sheet{{box-shadow:none;border-radius:0}}body{{background:#fff}}}}
.sheet h1,.sheet h2,.sheet h3{{margin:.6em 0 .3em}}.sheet table{{width:100%;border-collapse:collapse}}.sheet td,.sheet th{{padding:6px 8px;border-bottom:1px solid #e7e9f0;text-align:left;font-size:14px}}.sheet .foot{{color:#6b7080;font-size:12px}}</style></head>
<body><div class="bar"><div><b>Health summary · {_html.escape(s.name or '')}</b><br>Shared by the family through Urban Health · link valid till {exp}</div><button onclick="print()">Print / save PDF</button></div>
<div class="wrap"><div class="sheet">{inner}</div><p style="color:#6b7080;font-size:12px;text-align:center">Values are as entered by the family or read from reports; verify against originals. Not a hospital record.</p></div></body></html>"""
    return HTMLResponse(page, headers={"Cache-Control": "no-store", "X-Robots-Tag": "noindex", "X-Frame-Options": "DENY",
                                       "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; img-src data:; base-uri 'none'; form-action 'none'"})

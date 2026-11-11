"""Share with a doctor (a link that ends by itself) and the printable visit summary. One page, two doors."""
from __future__ import annotations

import datetime as _dt
import html
import os
import re
import secrets

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from .auth import limit, need_user
from .db import get_db
from .family import decrypt
from .models import DoctorShare, HealthRecord, Person, User, now

r = APIRouter(prefix="/api/v2")
E = html.escape


def _origin(request: Request) -> str:
    o = (os.getenv("APP_ORIGIN") or "").split(",")[0].strip().rstrip("/")
    return o or f"{request.headers.get('x-forwarded-proto', request.url.scheme)}://{request.headers.get('x-forwarded-host') or request.headers.get('host')}"


def _fmt(d: str) -> str:
    try:
        return _dt.date.fromisoformat(d[:10]).strftime("%-d %b %Y")
    except Exception:
        return d or ""


def _ec(cs: list) -> str:
    c = (cs or [None])[0]
    if not c:
        return ""
    return " · ".join(x for x in (c.get("name"), c.get("relation"), c.get("phone")) if x)


def render(db: Session, p: Person, scope: dict, note: str) -> str:
    from .people import profile, age
    pr = profile(p)
    recs = [x for x in db.scalars(select(HealthRecord).where(HealthRecord.person_id == p.id)) if x.kind in ("report", "med", "contact")]
    since = scope.get("since") or ""
    reports = sorted([x for x in recs if x.kind == "report" and (not scope.get("reports") or x.id in scope["reports"]) and (x.day or "") >= since], key=lambda x: x.day or "", reverse=True)
    meds = [decrypt(x.blob) for x in recs if x.kind == "med"] if scope.get("meds", True) else []
    meds = [m for m in meds if m.get("active") is not False]
    # every numeric test across the chosen reports, oldest to newest, for the trend table
    trend: dict[str, list] = {}
    allrep = [x for x in recs if x.kind == "report"]
    want = {f.get("test") for x in reports for f in ((decrypt(x.blob) or {}).get("findings") or [])}
    for x in sorted(allrep, key=lambda x: x.day or ""):
        for f in (decrypt(x.blob) or {}).get("findings") or []:
            k = f.get("test") or ""
            if k and k in want:
                trend.setdefault(k, []).append((x.day, f.get("value"), f.get("unit") or "", f.get("flag") or ""))
    flag = lambda f: {"high": "<b style='color:#C4291C'>High</b>", "low": "<b style='color:#B35C00'>Low</b>"}.get(f, "")
    rows = "".join(f"<tr><td>{E(k)}</td><td>{' → '.join(E(str(v)) for _, v, _, _ in vs[-4:])} {E(vs[-1][2])}</td><td>{flag(vs[-1][3])}</td><td class=m>{E(_fmt(vs[-1][0]))}</td></tr>" for k, vs in trend.items())
    reps = "".join(f"<li><b>{E((decrypt(x.blob) or {}).get('title') or 'Report')}</b> · {E(_fmt(x.day))}{(' · ' + E((decrypt(x.blob) or {}).get('lab') or '')) if (decrypt(x.blob) or {}).get('lab') else ''}<div class=m>{E(((decrypt(x.blob) or {}).get('summary') or '')[:300])}</div></li>" for x in reports[:20])
    medl = "".join(f"<li><b>{E(m.get('name',''))}</b> {E(m.get('dose',''))} <span class=m>{E(', '.join(m.get('times') or []))}</span></li>" for m in meds)
    a = age(pr.get("dob", ""))
    from .people import contacts
    try:
        ec = _ec(contacts(db, p.id))
    except Exception:
        ec = ""
    return f"""<!doctype html><html lang=en><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'><meta name=robots content=noindex>
<title>{E(p.name)} · health summary</title><style>body{{font-family:Inter,system-ui,sans-serif;color:#1D1D1F;background:#F2F2F7;margin:0;padding:20px}}main{{max-width:820px;margin:auto;background:#fff;border-radius:18px;padding:28px}}
h1{{font-size:26px;margin:0}}h2{{font-size:15px;letter-spacing:.04em;color:#6E6E73;margin:26px 0 8px;text-transform:uppercase}}.m{{color:#6E6E73;font-size:13px}}.id{{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-top:14px}}@media(max-width:560px){{.id{{grid-template-columns:1fr 1fr}}main{{padding:20px}}}}
.id div{{background:#F5F5F7;border-radius:12px;padding:10px}}.id small{{display:block;color:#6E6E73;font-size:11px}}table{{width:100%;border-collapse:collapse;font-size:14px}}td{{padding:8px 6px;border-bottom:1px solid #eee;vertical-align:top}}
ul{{padding-left:18px}}li{{margin:6px 0}}.note{{font-size:12px;color:#6E6E73;margin-top:22px}}@media print{{body{{background:#fff;padding:0}}main{{padding:0}}.np{{display:none}}}}</style>
<main><header style="display:flex;align-items:center;gap:10px;padding-bottom:16px;margin-bottom:18px;border-bottom:1px solid #EEE"><img src="/brand/png/user-icon-192.png" alt="" width=34 height=34 style="border-radius:9px"><div style="flex:1"><b style="font-size:17px;letter-spacing:-.2px">Urban Health</b><div class=m>Patient health summary · for the treating doctor</div></div><div class=m style="text-align:right">{E(note)}</div></header>
<div style="display:flex;justify-content:space-between;align-items:flex-end;gap:12px;flex-wrap:wrap"><div><h1>{E(p.name)}</h1><div class=m>{'Age ' + str(a) + ' · ' if a is not None else ''}{E((pr.get('sex') or '').title())}{(' · DOB ' + E(_fmt(pr.get('dob')))) if pr.get('dob') else ''}</div></div>
<div class=m style="text-align:right">Summary ID <b style="font-family:ui-monospace,Menlo,monospace;color:#1D1D1F">UH-{E(p.id[-8:].upper())}</b><br>{len(reports)} report{'s' if len(reports) != 1 else ''} · {len(meds)} medicine{'s' if len(meds) != 1 else ''}</div></div>
<div class=id><div><small>Blood group</small><b>{E(pr.get('blood') or '—')}</b></div><div><small>Allergies</small><b>{E(pr.get('allergies') or 'None')}</b></div><div><small>Conditions</small><b>{E(pr.get('conditions') or '—')}</b></div><div><small>Height · weight</small><b>{E(pr.get('height') or '—')} cm · {E(pr.get('weight') or '—')} kg</b></div></div>
{f"<h2>Results and trend</h2><table>{rows}</table>" if rows else ''}{f"<h2>Current medicines</h2><ul>{medl}</ul>" if medl else ''}{f"<h2>Reports</h2><ul>{reps}</ul>" if reps else ''}
{f"<h2>Emergency contact</h2><p>{E(ec)}</p>" if ec else ''}
<p class=note>Values as read from the reports the family uploaded; please confirm against the originals. This page is not a diagnosis.<br>Generated by Urban Health (urbanhealth.in) on {_dt.date.today().strftime('%-d %b %Y')} · shared by the patient's family through a private link that expires on its own.</p>
<p class=np><button onclick=print() style='font:600 15px Inter,system-ui;padding:12px 18px;border-radius:12px;border:0;background:#0071E3;color:#fff'>Print or save as PDF</button></p></main></html>"""


class ShareIn(BaseModel):
    hours: int = 24
    reports: list[str] = []
    meds: bool = True
    months: int = 6


@r.post("/people/{pid}/doctor-share")
def make(pid: str, body: ShareIn, request: Request, u: User = Depends(need_user), db: Session = Depends(get_db)):
    from .people import person_or_404
    limit(request, "dshare", 20, 3600)
    p, a = person_or_404(db, u, pid)
    if not a.writer:
        raise HTTPException(403, "Only they can share their records")
    since = (_dt.date.today() - _dt.timedelta(days=31 * max(1, min(60, body.months)))).isoformat()
    s = DoctorShare(token=secrets.token_urlsafe(24), person_id=p.id, by_user=u.id, scope={"reports": body.reports[:50], "meds": body.meds, "since": since}, expires=now() + max(1, min(168, body.hours)) * 3600)
    db.add(s)
    db.commit()
    return {"url": f"{_origin(request)}/dr/{s.token}", "expires": s.expires, "token": s.token[:8]}


@r.get("/people/{pid}/doctor-shares")
def mine(pid: str, u: User = Depends(need_user), db: Session = Depends(get_db)):
    from .people import person_or_404
    p, a = person_or_404(db, u, pid)
    if not a.writer:
        raise HTTPException(403, "Only they can see this")
    return [{"ref": s.token[:8], "expires": s.expires, "views": s.views, "created": s.created} for s in db.scalars(select(DoctorShare).where(DoctorShare.person_id == p.id, DoctorShare.revoked == False, DoctorShare.expires > now()))]  # noqa: E712


@r.delete("/doctor-shares/{ref}")
def revoke(ref: str, u: User = Depends(need_user), db: Session = Depends(get_db)):
    from .people import person_or_404
    s = db.scalar(select(DoctorShare).where(DoctorShare.token.like(re.sub(r"[^\w-]", "", ref)[:8] + "%"))) if len(ref) >= 6 else None
    if not s:
        raise HTTPException(404, "Not found")
    p, a = person_or_404(db, u, s.person_id)
    if not a.writer:
        raise HTTPException(403, "Not yours")
    s.revoked = True
    db.commit()
    return {"ok": True}


@r.get("/people/{pid}/summary", response_class=HTMLResponse)
def summary(pid: str, months: int = 6, u: User = Depends(need_user), db: Session = Depends(get_db)):
    from .people import person_or_404
    p, a = person_or_404(db, u, pid)
    if not a.can("summary"):
        raise HTTPException(403, "Not shared with you")
    since = (_dt.date.today() - _dt.timedelta(days=31 * max(1, min(60, months)))).isoformat()
    return HTMLResponse(render(db, p, {"since": since, "meds": a.can("all")}, f"Visit summary · last {months} months"), headers={"Cache-Control": "no-store"})


def public(token: str, db: Session) -> Response:
    s = db.get(DoctorShare, token)
    if not s or s.revoked or s.expires < now():
        return HTMLResponse("<!doctype html><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'><title>Link ended</title><body style='font-family:system-ui;padding:40px;max-width:520px;margin:auto'><h2>This link has ended</h2><p>The person who shared it can send a new one from Urban Health.</p>", status_code=404)
    p = db.get(Person, s.person_id)
    if not p or p.removed:
        return HTMLResponse("Not found", status_code=404)
    s.views += 1
    db.commit()
    until = _dt.datetime.fromtimestamp(s.expires, _dt.timezone(_dt.timedelta(hours=5, minutes=30))).strftime("%-d %b, %-I:%M %p")
    return HTMLResponse(render(db, p, s.scope or {}, f"Shared with you for medical care · link ends {until} · please do not forward"), headers={"Cache-Control": "no-store", "X-Robots-Tag": "noindex", "Referrer-Policy": "no-referrer"})


@r.get("/doctor-shares/{ref}/qr.svg")
def share_qr(ref: str, request: Request, u: User = Depends(need_user), db: Session = Depends(get_db)):
    """The QR for a share link, drawn here so the link never goes to an outside service."""
    import io

    import qrcode
    import qrcode.image.svg
    from .people import person_or_404
    s = db.scalar(select(DoctorShare).where(DoctorShare.token.like(re.sub(r"[^\w-]", "", ref)[:8] + "%"))) if len(ref) >= 6 else None
    if not s or s.revoked or s.expires < now():
        raise HTTPException(404, "Not found")
    p, a = person_or_404(db, u, s.person_id)
    if not a.writer:
        raise HTTPException(403, "Not yours")
    b = io.BytesIO()
    qrcode.make(f"{_origin(request)}/dr/{s.token}", image_factory=qrcode.image.svg.SvgPathImage, box_size=12, border=2).save(b)
    return Response(b.getvalue(), media_type="image/svg+xml", headers={"Cache-Control": "private, no-store"})

"""Upload links: a report from a lab or hospital that is not on Urban Health.

The person makes a link (48 hours by default, up to 3 files, an optional counter code). The lab opens it, sees only
what it needs to match the report (name, age, sex, last 4 digits of the phone), and uploads. Nothing is added to the
person's records until they accept it: an upload is stored as kind 'upload', which no access level can read, and it is
compared with the profile (name, age, sex) so a report printed for someone else is paused, not filed.

Security: unguessable token (only its hash is used for lookup), expiry, a file cap, an optional 6-digit code that locks
the link after 5 wrong tries, rate limits per address, PDF/photo only, 15 MB, the same sniffing, cleaning and virus scan
as an upload from the app, and every upload written to the person's access log.
"""
from __future__ import annotations

import difflib
import hashlib
import html
import re
import secrets
import time

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from .auth import csrf, limit, need_user
from .db import get_db
from .family import decrypt, encrypt
from .models import AccessLog, HealthRecord, Person, UploadLink, User, new_id, now

r = APIRouter(prefix="/api/v2", dependencies=[Depends(csrf)])
pub = APIRouter()

MAX_HOURS, MAX_FILES = 24 * 7, 5


def _h(token: str) -> str:
    return hashlib.sha256(("ul:" + token).encode()).hexdigest()


def _url(request: Request, token: str) -> str:
    return str(request.base_url).rstrip("/").replace("http://", "https://") + "/u/" + token if request.base_url.hostname not in ("localhost", "127.0.0.1", "testserver") else str(request.base_url).rstrip("/") + "/u/" + token


def _token(x: UploadLink) -> str:
    try:
        return (decrypt(x.token_enc) or {}).get("t", "")
    except Exception:
        return ""


def _link_json(x: UploadLink, request: Request) -> dict:
    t = _token(x)
    return {"id": x.id, "url": _url(request, t) if t else "", "code": x.code, "maxFiles": x.max_files, "used": x.used,
            "expires": x.expires, "created": x.created, "locked": x.tries >= 5,
            "live": not x.revoked and x.expires > now() and x.used < x.max_files and x.tries < 5}


def _phone_last4(p: Person) -> str:
    from .people import profile
    d = re.sub(r"\D", "", str(profile(p).get("phone") or ""))
    if len(d) < 4 and p.owner_user:
        from .db import SessionLocal
        with SessionLocal() as db:
            u = db.get(User, p.owner_user)
            d = re.sub(r"\D", "", str(getattr(u, "phone", "") or ""))
    return d[-4:] if len(d) >= 4 else ""


def match(p: Person, pt: dict) -> dict:
    """Compare what is printed on the report with the profile. Each of name / age / sex is ok, differs or missing."""
    from .people import _name_key, age, profile
    pr, out = profile(p), {}
    n = _name_key(pt.get("name", ""))
    if len(n) >= 3:
        mine = max(difflib.SequenceMatcher(None, n, _name_key(x)).ratio() for x in (p.name, pr.get("legalName") or p.name))
        out["name"] = "ok" if mine > 0.6 or any(len(w) > 3 and _name_key(w) in n for w in (p.name or "").split()) else "differs"
    else:
        out["name"] = "missing"
    a_ours = age(pr.get("dob", ""))
    try:
        a_rep = int(float(pt.get("age_years"))) if pt.get("age_years") not in (None, "") else None
    except (TypeError, ValueError):
        a_rep = None
    if a_rep is None and re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(pt.get("dob") or "")):
        a_rep = age(pt["dob"])
    out["age"] = "missing" if a_rep is None or a_ours is None else ("ok" if abs(a_rep - a_ours) <= 1 else "differs")
    out["ageOnReport"], out["ageOurs"] = a_rep, a_ours
    s_rep, s_ours = str(pt.get("sex") or "").lower()[:1], str(pr.get("sex") or "").lower()[:1]
    out["sex"] = "missing" if not s_rep or not s_ours else ("ok" if s_rep == s_ours else "differs")
    out["nameOnReport"] = pt.get("name", "")
    out["ok"] = "differs" not in (out["name"], out["age"], out["sex"])
    return out


# ---- the owner's side ---------------------------------------------------------------------------------------------------
class LinkIn(BaseModel):
    hours: int = Field(48, ge=1, le=MAX_HOURS)
    maxFiles: int = Field(3, ge=1, le=MAX_FILES)
    code: bool = True


@r.post("/people/{pid}/upload-links")
def make_link(pid: str, body: LinkIn, request: Request, u: User = Depends(need_user), db: Session = Depends(get_db)):
    from .people import person_or_404
    limit(request, "uplink-make", 20, 3600)
    p, a = person_or_404(db, u, pid)
    if not a.writer:
        raise HTTPException(403, "Only they can ask for reports")
    live = db.scalars(select(UploadLink).where(UploadLink.person_id == p.id, UploadLink.revoked == 0, UploadLink.expires > now())).all()
    if len(live) >= 5:
        raise HTTPException(429, "You already have 5 open links. Cancel one first.")
    t = secrets.token_urlsafe(18)
    x = UploadLink(token_hash=_h(t), token_enc=encrypt({"t": t}), person_id=p.id, household_id=p.household_id, by_user=u.id,
                   code=f"{secrets.randbelow(10**6):06d}" if body.code else "", max_files=body.maxFiles, expires=now() + body.hours * 3600)
    db.add(x)
    db.commit()
    return _link_json(x, request)


@r.get("/people/{pid}/upload-links")
def list_links(pid: str, request: Request, u: User = Depends(need_user), db: Session = Depends(get_db)):
    from .people import person_or_404
    p, a = person_or_404(db, u, pid)
    if not a.writer:
        raise HTTPException(403, "Only they can see this")
    rows = db.scalars(select(UploadLink).where(UploadLink.person_id == p.id, UploadLink.revoked == 0, UploadLink.expires > now() - 86400 * 7).order_by(UploadLink.created.desc()).limit(20)).all()
    return [_link_json(x, request) for x in rows]


def _own_link(db: Session, u: User, lid: str) -> UploadLink:
    from .people import person_or_404
    x = db.get(UploadLink, lid)
    if not x:
        raise HTTPException(404, "Not found")
    p, a = person_or_404(db, u, x.person_id)
    if not a.writer:
        raise HTTPException(403, "Only they can change this")
    return x


@r.delete("/upload-links/{lid}")
def cancel_link(lid: str, u: User = Depends(need_user), db: Session = Depends(get_db)):
    x = _own_link(db, u, lid)
    x.revoked = now()
    db.commit()
    return {"ok": True}


@r.get("/upload-links/{lid}/qr.svg")
def link_qr(lid: str, request: Request, u: User = Depends(need_user), db: Session = Depends(get_db)):
    import io

    import qrcode
    import qrcode.image.svg
    x = _own_link(db, u, lid)
    buf = io.BytesIO()
    qrcode.make(_url(request, _token(x)), image_factory=qrcode.image.svg.SvgPathImage, box_size=10, border=2).save(buf)
    return Response(buf.getvalue(), media_type="image/svg+xml", headers={"Cache-Control": "no-store"})


def _upload_row(db: Session, u: User, rid: str):
    from .people import person_or_404
    x = db.get(HealthRecord, rid)
    if not x or x.kind != "upload":
        raise HTTPException(404, "Not found")
    p, a = person_or_404(db, u, x.person_id)
    if not a.writer:
        raise HTTPException(403, "Only they can decide this")
    return x, p


@r.get("/people/{pid}/uploads")
def pending(pid: str, u: User = Depends(need_user), db: Session = Depends(get_db)):
    from .people import person_or_404, rec_json
    p, a = person_or_404(db, u, pid)
    if not a.writer:
        return []
    rows = db.scalars(select(HealthRecord).where(HealthRecord.person_id == p.id, HealthRecord.kind == "upload").order_by(HealthRecord.created.desc()).limit(30)).all()
    return [rec_json(x) for x in rows]


@r.post("/uploads/{rid}/accept")
def accept(rid: str, u: User = Depends(need_user), db: Session = Depends(get_db)):
    """'It's mine, add it': the upload becomes an ordinary report, compared with earlier results and searchable."""
    import datetime as _dt

    from .people import compare_findings, index_record, rec_json
    x, p = _upload_row(db, u, rid)
    rec = decrypt(x.blob) or {}
    rec["accepted"] = {"by": u.id, "t": now(), "despite": not (rec.get("match") or {}).get("ok", True)}
    rec["compare"] = compare_findings(db, p.id, rec.get("findings") or [], rec.get("date") or _dt.date.today().isoformat())
    x.kind, x.blob = "report", encrypt(rec)
    db.flush()
    index_record(db, x, rec)
    db.add(AccessLog(person_id=p.id, user_id=u.id, what="accepted an uploaded report"))
    db.commit()
    return rec_json(x)


@r.post("/uploads/{rid}/ask")
def ask_lab(rid: str, u: User = Depends(need_user), db: Session = Depends(get_db)):
    """'Ask the lab to check': kept apart, flagged for the Urban Health team, who contact the lab from the admin console."""
    x, p = _upload_row(db, u, rid)
    rec = decrypt(x.blob) or {}
    rec["asked"] = now()
    x.blob = encrypt(rec)
    db.commit()
    return {"ok": True}


@r.delete("/uploads/{rid}")
def reject(rid: str, u: User = Depends(need_user), db: Session = Depends(get_db)):
    """'Not mine, remove it': the record and its file are erased now."""
    from . import storage
    x, p = _upload_row(db, u, rid)
    if x.file_id:
        try:
            storage.delete(db, p.id, x.file_id)
        except Exception:
            pass
    db.delete(x)
    db.add(AccessLog(person_id=p.id, user_id=u.id, what="removed an uploaded report"))
    db.commit()
    return {"ok": True}


# ---- the lab's side (no sign-in) ---------------------------------------------------------------------------------------
def _live(db: Session, token: str) -> tuple[UploadLink, Person]:
    if not re.fullmatch(r"[\w-]{16,40}", token or ""):
        raise HTTPException(404, "This link is not valid.")
    x = db.scalar(select(UploadLink).where(UploadLink.token_hash == _h(token)))
    if not x or x.revoked:
        raise HTTPException(404, "This link has been cancelled. Please ask the patient for a new one.")
    if x.expires < now():
        raise HTTPException(410, "This link has expired. Please ask the patient for a new one.")
    if x.tries >= 5:
        raise HTTPException(423, "This link is locked after too many wrong codes. Please ask the patient for a new one.")
    if x.used >= x.max_files:
        raise HTTPException(410, "All the files for this link have been uploaded. Thank you.")
    p = db.get(Person, x.person_id)
    if not p or p.removed:
        raise HTTPException(404, "This link is not valid.")
    return x, p


@pub.post("/u/{token}/upload", dependencies=[Depends(csrf)], include_in_schema=False)
async def lab_upload(token: str, request: Request, file: UploadFile = File(...), lab: str = Form(...), ref: str = Form(""),
                     phone: str = Form(""), code: str = Form(""), confirm: str = Form(""), db: Session = Depends(get_db)):
    limit(request, "uplink-up", 20, 3600)
    x, p = _live(db, token)
    if x.code:
        if not secrets.compare_digest(re.sub(r"\D", "", code), x.code):
            x.tries += 1
            db.commit()
            left = max(0, 5 - x.tries)
            raise HTTPException(403, f"That code is not right. {left} tries left." if left else "This link is now locked. Please ask the patient for a new one.")
    if confirm != "1":
        raise HTTPException(400, "Please confirm the report belongs to this patient.")
    lab = re.sub(r"\s+", " ", lab or "").strip()[:80]
    if len(lab) < 3:
        raise HTTPException(400, "Please enter your lab or hospital name.")
    phone = re.sub(r"[^\d+]", "", phone or "")[:15]
    data = await file.read()
    if not data or len(data) > 15 * 1024 * 1024:
        raise HTTPException(413, "Files up to 15 MB")
    mime = file.content_type or "application/octet-stream"
    if not (mime.startswith("image/") or mime == "application/pdf"):
        raise HTTPException(415, "PDF or photo only")
    import hashlib as _h
    from .people import find_dup
    sha = _h.sha256(data).hexdigest()
    same, _ = find_dup(db, p.id, sha=sha)
    if same:                                      # the family already has it: say thanks, store nothing twice
        return {"ok": True, "dup": True, "left": max(0, x.max_files - x.used)}
    from . import storage
    mime, fname = storage.checked(data, file.filename or "report")
    data = storage.safe_document(data, mime)
    if mime not in ("application/pdf", "image/heic"):
        mime = "image/jpeg"
    storage.virus_scan(data)
    fid = new_id("f")
    storage.put(db, p.id, fid, data, mime, fname, "ext")
    reading, txt = {}, ""
    if mime == "application/pdf":
        try:
            from . import ai
            txt = ai.text_from(data, mime)
        except Exception:
            txt = ""
    try:
        from . import ai
        from .people import age, profile
        pr = profile(p)
        reading = ai.analyze("report", data, mime, "", {"age": age(pr.get("dob", "")), "sex": pr.get("sex", ""), "allergies": pr.get("allergies", ""), "pregnant": False})
    except Exception as e:
        reading = {"engine": "none", "warnings": ["Saved, but it could not be read automatically."], "error": type(e).__name__}
    pt = reading.get("patient") or {}
    m = match(p, pt)
    import datetime as _dt
    title = str(reading.get("title") or "Lab report").strip()[:80]
    from .people import doc_date
    rec = {"title": title, "doc": "report", "doctor": reading.get("doctor", ""), "date": doc_date(reading, txt),
           "findings": reading.get("findings", []), "medicines": [], "summary": reading.get("summary", ""),
           "focus": reading.get("focus", []), "followups": reading.get("followups", []), "questions": reading.get("questions_for_doctor", []),
           "warnings": reading.get("warnings", []), "engine": reading.get("engine", ""), "mime": mime, "name": (file.filename or "")[:120],
           "checked": False, "patient": pt, "lab": lab, "match": m,
           "via": {"link": x.id, "lab": lab, "ref": re.sub(r"\s+", " ", ref or "").strip()[:40], "phone": phone, "t": now(),
                   "ip": hashlib.sha256((request.client.host if request.client else "").encode()).hexdigest()[:16]}}
    for f in rec["findings"]:
        f["sure"] = f.get("sure") is not False
    from .people import _sig
    rec["sha"], rec["sig"] = sha, _sig(rec["findings"])
    if rec["date"] and rec["sig"]:
        same, _ = find_dup(db, p.id, date=rec["date"], sig=rec["sig"])
        if same:
            rec["dup"] = same.id
    day = rec["date"] or _dt.date.today().isoformat()
    hr = HealthRecord(person_id=p.id, kind="upload", blob=encrypt(rec), file_id=fid, day=day, by_user="ext")
    db.add(hr)
    x.used += 1
    db.add(AccessLog(person_id=p.id, user_id=("ext:" + lab)[:32], what="uploaded a report via your link"))
    from .people import _note
    _note(db, p.household_id, "report", f"{lab} uploaded a report for {p.name.split(' ')[0]}" if m["ok"] else f"Please check a report from {lab}",
          "Waiting for your OK before it's added" if m["ok"] else "The details on it don't match the profile, so it's kept apart",
          {"person": p.id, "upload": hr.id}, member_id=p.id)
    db.commit()
    return {"ok": True, "left": max(0, x.max_files - x.used)}


@pub.get("/u/{token}", response_class=HTMLResponse, include_in_schema=False)
def lab_page(token: str, request: Request, db: Session = Depends(get_db)):
    limit(request, "uplink-view", 120, 3600)
    e = html.escape
    try:
        x, p = _live(db, token)
    except HTTPException as ex:
        return HTMLResponse(_shell("Link not available", f"<h1>Link not available</h1><p class='lead'>{e(ex.detail)}</p>"), status_code=ex.status_code,
                            headers={"X-Robots-Tag": "noindex, nofollow", "Cache-Control": "no-store"})
    from .people import age, profile
    pr = profile(p)
    a = age(pr.get("dob", ""))
    sex = {"m": "Male", "f": "Female"}.get(str(pr.get("sex") or "").lower()[:1], "")
    last4 = _phone_last4(p)
    hours = max(1, (x.expires - now()) // 3600)
    ref = "UH-" + x.id[-6:].upper()
    body = f"""<div class="brand"><i></i>Urban Health · Secure upload</div>
<h1>Upload a report for this patient</h1><p class="lead">Please check these details match the report before uploading.</p>
<div class="card"><div class="row"><small>Patient</small><b>{e(p.name)}</b></div>
<div class="row two"><div><small>Age · sex</small><b>{e(str(a) if a is not None else '—')}{(' · ' + sex) if sex else ''}</b></div><div><small>Phone</small><b>{('•••• ' + last4) if last4 else '—'}</b></div></div>
<div class="row"><small>Request</small><b>{ref} · expires in {hours} h · {x.max_files - x.used} file{'s' if x.max_files - x.used != 1 else ''} left</b></div></div>
<form id="f" class="card form" novalidate>
<label><span>Your lab or hospital name</span><input name="lab" required maxlength="80" placeholder="e.g. Apollo Diagnostics, Adyar" autocomplete="organization"></label>
<label><span>Patient ID on your report <em>optional</em></span><input name="ref" maxlength="40" placeholder="UHID or lab number"></label>
<label><span>Your phone <em>optional</em></span><input name="phone" inputmode="tel" maxlength="15" placeholder="So we can reach you if something doesn't match"></label>
{'<label><span>Code from the patient</span><input name="code" required inputmode="numeric" maxlength="6" placeholder="6 digits" autocomplete="one-time-code"></label>' if x.code else ''}
<label class="drop" id="dz"><input type="file" name="file" accept="application/pdf,image/*" required hidden><b>Choose PDF or photo</b><span id="fn">PDF, JPG or PNG · up to 15 MB</span></label>
<label class="ck"><input type="checkbox" name="confirm" value="1"><i></i><span>I confirm this report belongs to the patient named above.</span></label>
<button id="go">Upload securely</button><p class="msg" id="msg" role="status"></p></form>
<p class="foot">Encrypted in transit and at rest, stored in India. The patient reviews the report before it is added to their records. Every upload is logged.</p>
<script>
const f=document.getElementById('f'),fn=document.getElementById('fn'),msg=document.getElementById('msg'),go=document.getElementById('go');
f.file.onchange=()=>{{const x=f.file.files[0];fn.textContent=x?(x.name.length>34?x.name.slice(0,22)+'…'+x.name.slice(-9):x.name)+' · '+Math.round(x.size/1024)+' KB':'PDF, JPG or PNG · up to 15 MB';document.getElementById('dz').classList.toggle('set',!!x)}};
f.onsubmit=async e=>{{e.preventDefault();msg.className='msg';
 if(f.lab.value.trim().length<3){{msg.textContent='Please enter your lab or hospital name.';return}}
 if(f.code&&!/^\\d{{6}}$/.test(f.code.value.trim())){{msg.textContent='Please enter the 6-digit code the patient gave you.';return}}
 if(!f.file.files[0]){{msg.textContent='Please choose the report file.';return}}
 if(!f.confirm.checked){{msg.textContent='Please confirm the report belongs to this patient.';return}}
 go.disabled=true;go.textContent='Uploading…';
 try{{const r=await fetch(location.pathname+'/upload',{{method:'POST',body:new FormData(f),headers:{{'x-tht':'1'}}}});const j=await r.json().catch(()=>({{}}));
  if(!r.ok)throw new Error(j.detail||'Upload failed. Please try again.');
  if(j.dup){{f.outerHTML='<div class="card done"><div class="tick">✓</div><h2>Already received</h2><p>This exact file is already with the patient, so nothing new was added. Thank you.</p><a href="" class="again">Upload a different file</a></div>';return}}
  f.outerHTML='<div class="card done"><div class="tick">✓</div><h2>Uploaded. Thank you.</h2><p>The patient has been told and will review it.'+(j.left?' You can upload '+j.left+' more file'+(j.left>1?'s':'')+' with this link.':'')+'</p>'+(j.left?'<a href="" class="again">Upload another</a>':'')+'</div>'}}
 catch(err){{msg.className='msg bad';msg.textContent=err.message;go.disabled=false;go.textContent='Upload securely'}}}};
</script>"""
    return HTMLResponse(_shell("Secure upload · Urban Health", body), headers={"X-Robots-Tag": "noindex, nofollow", "Cache-Control": "no-store", "Referrer-Policy": "no-referrer"})


def _shell(title: str, body: str) -> str:
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex,nofollow">
<title>{html.escape(title)}</title><style>
*{{box-sizing:border-box}}body{{margin:0;font:16px/1.45 -apple-system,BlinkMacSystemFont,"SF Pro Text",Inter,Roboto,sans-serif;background:#F2F2F7;color:#1D1D1F;-webkit-font-smoothing:antialiased}}
main{{max-width:520px;margin:0 auto;padding:22px 16px 40px}}.brand{{display:flex;align-items:center;gap:9px;font-weight:700;margin-bottom:18px}}.brand i{{width:28px;height:28px;border-radius:9px;background:linear-gradient(135deg,#2F6BFF,#5B46E0)}}
h1{{font-size:28px;letter-spacing:-.02em;line-height:1.15;margin:0 0 6px}}.lead{{color:#55555B;margin:0 0 16px}}
.card{{background:#fff;border-radius:22px;padding:6px 18px;margin-bottom:12px;box-shadow:0 1px 2px rgba(0,0,0,.04)}}.row{{padding:12px 0;border-bottom:.5px solid rgba(60,60,67,.14)}}.row:last-child{{border:0}}.row small,label span{{display:block;color:#8E8E93;font-size:13px}}.row b{{font-size:17px}}.two{{display:grid;grid-template-columns:1fr 1fr;gap:12px}}
.form{{padding:14px 18px 18px}}label{{display:block;margin-bottom:12px}}label em{{font-style:normal;color:#AEAEB2}}input{{width:100%;height:50px;border-radius:14px;border:0;background:#F2F2F7;padding:0 14px;font:inherit;font-size:16px;margin-top:5px;outline:0}}input:focus{{box-shadow:0 0 0 3px rgba(0,113,227,.25)}}
.drop{{border:2px dashed #C7C7CC;border-radius:20px;padding:20px;text-align:center;cursor:pointer;margin-top:4px}}.drop b{{display:block;font-size:16px;color:#0071E3}}.drop span{{display:block;color:#8E8E93;margin-top:2px;overflow-wrap:anywhere;word-break:break-word;max-width:100%}}.drop{{min-width:0;overflow:hidden}}.drop.set{{border-color:#30D158;background:#F0FBF3}}
.ck{{display:flex;gap:10px;align-items:flex-start;cursor:pointer;margin:14px 0}}.ck input{{display:none}}.ck i{{width:24px;height:24px;border-radius:12px;border:2px solid #C7C7CC;flex:none;margin-top:1px;display:grid;place-items:center}}.ck input:checked+i{{background:#0071E3;border-color:#0071E3}}.ck input:checked+i:after{{content:"✓";color:#fff;font-size:13px;font-weight:700}}.ck span{{color:#3A3A3C;font-size:15px}}
button{{width:100%;height:54px;border-radius:27px;border:0;background:#0071E3;color:#fff;font:inherit;font-size:17px;font-weight:600;cursor:pointer}}button:disabled{{opacity:.6}}
.msg{{min-height:20px;margin:10px 2px 0;font-size:14px;color:#55555B}}.msg.bad{{color:#C4291C}}.foot{{text-align:center;color:#8E8E93;font-size:13px;margin-top:14px}}
.done{{text-align:center;padding:26px 18px}}.tick{{width:64px;height:64px;border-radius:32px;background:#30D158;color:#fff;font-size:32px;display:grid;place-items:center;margin:0 auto 10px}}.done h2{{margin:0 0 6px}}.done p{{color:#55555B;margin:0}}.again{{display:inline-block;margin-top:14px;color:#0071E3;font-weight:600;text-decoration:none}}
</style></head><body><main>{body}</main></body></html>"""


@r.get("/privacy/contact")
def privacy_contact():
    """The Grievance Officer the Privacy centre shows (DPDP: contact details must be easy to find)."""
    import os
    return {"name": os.getenv("GRIEVANCE_NAME", "Grievance Officer, Urban Health"),
            "email": os.getenv("GRIEVANCE_EMAIL") or os.getenv("SUPPORT_EMAIL") or os.getenv("ADMIN_EMAIL", "") or "privacy@urbanhealth.in",
            "replyDays": 7}

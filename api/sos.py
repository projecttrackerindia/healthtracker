"""SOS that acts (/api/v1/sos, /sos/<token>).

One press in the app does three things at once: the phone dials (112/108 or the chosen contact), the server tells
everyone — email to contacts with an address, push + WhatsApp to the family's own phones (api/inbox.notify), free-text
SMS when a Twilio channel exists — and a public *live page* opens for the people alerted: a map that follows the person
while the alert is open, the Medical ID summary, and one-tap call / directions. The page needs no sign-in; its token is
48 random characters and the page goes quiet 24 h after the alert ends.

Nothing here is reachable with a demo key (server.py refuses demo writes), and the app never stores phone numbers of
contacts on the server beyond the alert's own row (the family keeps contacts on the device).
"""
from __future__ import annotations

import html
import json
import os
import secrets
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import messaging, whatsapp
from .auth import limit
from .db import get_db
from .fitbit import _origin
from .inbox import notify
from .models import SosAlert, now
from .routes import household

r = APIRouter()
APP = "TheHealthTracker"


class Contact(BaseModel):
    n: str = ""
    ph: str = ""
    em: str = ""


class Loc(BaseModel):
    lat: float
    lng: float
    acc: int | None = None


class StartIn(BaseModel):
    member: str = ""
    name: str = ""
    phone: str = ""                      # the person's own number, so helpers can call back
    summary: str = ""                    # blood group, allergies, conditions, medicines (text the app already builds)
    blood: str = ""
    loc: Loc | None = None
    contacts: list[Contact] = Field(default_factory=list)
    lang: str = "en"


def maps_link(lat: float, lng: float) -> str:
    return f"https://maps.google.com/?q={lat:.6f},{lng:.6f}"


def directions_link(lat: float, lng: float) -> str:
    return f"https://www.google.com/maps/dir/?api=1&destination={lat:.6f},{lng:.6f}&travelmode=driving"


def message(a: SosAlert, origin: str) -> str:
    lines = [f"EMERGENCY: {a.name} needs help."]
    if a.lat is not None:
        lines.append(f"Location: {maps_link(a.lat, a.lng)}" + (f" (about {a.acc} m)" if a.acc else ""))
    else:
        lines.append("Location: not available yet — the live page updates when it is.")
    lines.append(f"Live page: {origin}/sos/{a.token}")
    lines.append("Time: " + datetime.fromtimestamp(a.created, timezone.utc).astimezone().strftime("%d %b, %H:%M"))
    if a.data.get("summary"):
        lines.append(a.data["summary"])
    if a.data.get("phone"):
        lines.append(f"Call them: {a.data['phone']}")
    lines.append(f"Call 112 if you are nearby. Sent by {APP} SOS.")
    return "\n".join(lines)


def _email_html(a: SosAlert, origin: str) -> str:
    where = f'<p><a href="{maps_link(a.lat, a.lng)}" style="color:#2F5BFF">Open the location in Google Maps</a> · <a href="{directions_link(a.lat, a.lng)}" style="color:#2F5BFF">Directions</a></p>' if a.lat is not None else "<p>Location not available yet; the live page updates when it is.</p>"
    return f"""<div style="font-family:Inter,Segoe UI,Arial,sans-serif;max-width:520px;margin:auto;padding:24px;color:#14151b">
<div style="background:#E11D48;color:#fff;border-radius:14px;padding:18px 20px"><p style="margin:0;font-size:13px;letter-spacing:.08em;text-transform:uppercase;opacity:.85">Emergency</p><p style="margin:6px 0 0;font-size:22px;font-weight:700">{html.escape(a.name)} needs help</p></div>
<p style="font-size:16px;margin:18px 0 6px"><a href="{origin}/sos/{a.token}" style="display:inline-block;background:#14151b;color:#fff;text-decoration:none;padding:12px 18px;border-radius:999px;font-weight:600">Open the live page</a></p>
{where}
<p style="white-space:pre-line;background:#f4f5f9;border-radius:12px;padding:14px;font-size:14px">{html.escape(a.data.get('summary') or '')}</p>
{f'<p>Call them: <a href="tel:{html.escape(a.data["phone"])}">{html.escape(a.data["phone"])}</a></p>' if a.data.get("phone") else ''}
<p style="color:#6b7080;font-size:12px">Sent by {APP} SOS at {datetime.fromtimestamp(a.created, timezone.utc).astimezone().strftime('%d %b %Y, %H:%M')}. Call 112 if you are near them.</p></div>"""


def fan_out(db: Session, a: SosAlert, origin: str) -> list[dict]:
    """Every channel the server can drive on its own. Returns what went where; the app shows it and offers WhatsApp/SMS for the rest."""
    sent: list[dict] = []
    text = message(a, origin)
    for c in a.data.get("contacts") or []:
        if c.get("em") and messaging.email_ready():
            try:
                messaging.send_mail(c["em"], f"EMERGENCY: {a.name} needs help", text, _email_html(a, origin))
                sent.append({"n": c.get("n", ""), "channel": "email", "ok": True})
            except Exception as e:
                print("[sos] email failed:", str(e)[:160], flush=True)
                sent.append({"n": c.get("n", ""), "channel": "email", "ok": False})
        if c.get("ph"):
            try:
                if messaging.send_text_sms(c["ph"], text, flow_vars={"name": a.name, "link": f"{origin}/sos/{a.token}"}):
                    sent.append({"n": c.get("n", ""), "channel": "sms", "ok": True})
            except Exception as e:
                print("[sos] sms failed:", str(e)[:160], flush=True)
                sent.append({"n": c.get("n", ""), "channel": "sms", "ok": False})
            # WhatsApp straight from the server (Meta Cloud API) when it is set up: WA_TEMPLATE_SOS (name, link) or the notice template
            try:
                if whatsapp.ready():
                    ok = whatsapp.send_sos(c["ph"], a.name, f"{origin}/sos/{a.token}", text)
                    sent.append({"n": c.get("n", ""), "channel": "whatsapp", "ok": bool(ok)})
            except Exception as e:
                print("[sos] whatsapp failed:", str(e)[:160], flush=True)
    # the family's own phones: push (+ WhatsApp when that channel is live), through the inbox so it also shows in-app
    try:
        notify(db, a.household_id, "message", f"EMERGENCY: {a.name} needs help", "Open the live map and call them.", {"sos": a.token}, a.member_id, f"/sos/{a.token}")
        sent.append({"n": "family phones", "channel": "push", "ok": True})
    except Exception as e:
        print("[sos] notify failed:", str(e)[:160], flush=True)
    return sent


def alert_json(a: SosAlert, origin: str) -> dict:
    return {"id": a.id, "token": a.token, "url": f"{origin}/sos/{a.token}", "name": a.name, "active": a.active, "created": a.created, "updated": a.updated, "ended": a.ended,
            "loc": {"lat": a.lat, "lng": a.lng, "acc": a.acc} if a.lat is not None else None, "trail": (a.trail or [])[-50:], "sent": a.sent or [],
            "summary": a.data.get("summary", ""), "blood": a.data.get("blood", ""), "phone": a.data.get("phone", ""), "message": message(a, origin),
            "maps": maps_link(a.lat, a.lng) if a.lat is not None else "", "directions": directions_link(a.lat, a.lng) if a.lat is not None else ""}


def channels() -> dict:
    """Which alert channels this server drives by itself the moment SOS is pressed (the app shows the rest as one-tap)."""
    from .push import ready as push_ready
    return {"email": messaging.email_ready(), "sms": messaging.alert_sms_ready(), "whatsapp": whatsapp.ready(), "push": bool(push_ready())}


@r.get("/api/v1/sos/channels")
def sos_channels():
    return channels()


@r.post("/api/v1/sos/start")
def start(body: StartIn, request: Request, db: Session = Depends(get_db), x_dokko_key: str | None = Header(None)):
    h = household(db, x_dokko_key)
    if not h:
        raise HTTPException(400, "missing household key")
    limit(request, f"sos:{h.id}", 12, 3600)
    origin = _origin(request)
    for old in db.scalars(select(SosAlert).where(SosAlert.household_id == h.id, SosAlert.member_id == body.member[:32], SosAlert.active == True)).all():  # noqa: E712
        old.active, old.ended = False, now()      # one open alert per person
    a = SosAlert(household_id=h.id, token=secrets.token_urlsafe(36)[:48], member_id=body.member[:32], name=(body.name or "Someone")[:80],
                 data={"summary": body.summary[:1200], "blood": body.blood[:8], "phone": body.phone[:20], "lang": body.lang[:5],
                       "contacts": [{"n": c.n[:40], "ph": c.ph[:20], "em": c.em[:160]} for c in body.contacts[:12]]})
    if body.loc:
        a.lat, a.lng, a.acc = body.loc.lat, body.loc.lng, body.loc.acc
        a.trail = [[now(), round(body.loc.lat, 5), round(body.loc.lng, 5)]]
    db.add(a)
    db.flush()
    a.sent = fan_out(db, a, origin)
    return alert_json(a, origin)


class LocIn(BaseModel):
    loc: Loc


def _mine(db: Session, h, sid: str) -> SosAlert:
    a = h and db.get(SosAlert, sid)
    if not a or a.household_id != h.id:
        raise HTTPException(404)
    return a


@r.post("/api/v1/sos/{sid}/loc")
def update_loc(sid: str, body: LocIn, request: Request, db: Session = Depends(get_db), x_dokko_key: str | None = Header(None)):
    h = household(db, x_dokko_key, create=False)
    a = _mine(db, h, sid)
    if not a.active:
        raise HTTPException(409, "This alert has ended.")
    first = a.lat is None
    a.lat, a.lng, a.acc, a.updated = body.loc.lat, body.loc.lng, body.loc.acc, now()
    a.trail = ((a.trail or []) + [[now(), round(body.loc.lat, 5), round(body.loc.lng, 5)]])[-50:]
    origin = _origin(request)
    if first:
        a.sent = (a.sent or []) + fan_out(db, a, origin)   # the first fix goes out to everyone who was told "location not available yet"
    return alert_json(a, origin)


@r.post("/api/v1/sos/{sid}/end")
def end(sid: str, request: Request, db: Session = Depends(get_db), x_dokko_key: str | None = Header(None)):
    h = household(db, x_dokko_key, create=False)
    a = _mine(db, h, sid)
    if a.active:
        a.active, a.ended = False, now()
        try:
            notify(db, a.household_id, "message", f"{a.name} is safe", "The SOS alert has ended.", {"sos": a.token}, a.member_id, "/app")
        except Exception:
            pass
    return alert_json(a, _origin(request))


@r.get("/api/v1/sos/t/{token}")
def public_json(token: str, request: Request, db: Session = Depends(get_db)):
    a = db.scalar(select(SosAlert).where(SosAlert.token == token[:48]))
    if not a or (not a.active and a.ended and now() - a.ended > 86400):
        raise HTTPException(404, "This alert is no longer available.")
    j = alert_json(a, _origin(request))
    j.pop("id", None)
    return j


PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"><meta name="robots" content="noindex">
<title>Emergency · __NAME__</title>
<style>
:root{--red:#E11D48;--ink:#0b0c10;--mute:#6b7080;--card:#fff;--bg:#f4f5f9}
*{box-sizing:border-box}body{margin:0;font:15px/1.5 Inter,-apple-system,"Segoe UI",Roboto,sans-serif;background:var(--bg);color:var(--ink)}
.top{background:var(--red);color:#fff;padding:max(16px,env(safe-area-inset-top)) 18px 18px}.top small{display:block;font-size:12px;letter-spacing:.1em;text-transform:uppercase;opacity:.85}.top h1{margin:4px 0 0;font-size:24px;line-height:1.2}.top p{margin:6px 0 0;font-size:13px;opacity:.9}
.wrap{max-width:560px;margin:0 auto;padding:14px 14px 40px}.card{background:var(--card);border-radius:18px;padding:16px;margin:0 0 12px;box-shadow:0 1px 2px rgba(0,0,0,.05)}
.btns{display:grid;grid-template-columns:1fr 1fr;gap:10px}.btn{display:flex;align-items:center;justify-content:center;gap:8px;min-height:52px;border-radius:999px;background:var(--ink);color:#fff;text-decoration:none;font-weight:600;padding:0 16px}.btn.red{background:var(--red)}.btn.s{background:#e8eaf2;color:var(--ink)}
iframe{width:100%;height:300px;border:0;border-radius:14px;background:#dfe3ee}.sum{white-space:pre-line;font-size:14px}.mute{color:var(--mute);font-size:13px}
.live{display:inline-flex;align-items:center;gap:6px;font-size:12px;font-weight:600;color:var(--red)}.live i{width:8px;height:8px;border-radius:50%;background:var(--red);animation:p 1.2s infinite}@keyframes p{50%{opacity:.2}}
.ended{background:#14151b;color:#fff}
</style></head><body>
<div class="top"><small>Emergency · __APP__ SOS</small><h1 id="h">__NAME__ needs help</h1><p id="when"></p></div>
<div class="wrap">
<div class="card btns" id="btns"></div>
<div class="card"><div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px"><b>Where they are</b><span class="live" id="live"><i></i>live</span></div><div id="map"><p class="mute" style="margin:0">Waiting for a location…</p></div><p class="mute" id="acc" style="margin:8px 0 0"></p></div>
<div class="card"><b>Medical ID</b><p class="sum" id="sum" style="margin:6px 0 0"></p></div>
<p class="mute">This page was created when __NAME__ pressed SOS in __APP__. It updates by itself while the alert is open. If you are nearby, call 112 (police, fire, ambulance) or 108 (ambulance).</p>
</div>
<script>
const T=location.pathname.split('/').pop();let lastKey='';
const esc=s=>String(s||'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
async function tick(){let j;try{const r=await fetch('/api/v1/sos/t/'+encodeURIComponent(T),{cache:'no-store'});if(!r.ok)throw 0;j=await r.json()}catch(e){return}
 document.getElementById('h').textContent=j.active?j.name+' needs help':j.name+' is safe now';
 document.getElementById('when').textContent=(j.active?'Alert started ':'Alert ended ')+new Date((j.active?j.created:j.ended||j.updated)*1000).toLocaleString('en-IN',{day:'numeric',month:'short',hour:'numeric',minute:'2-digit'})+(j.active&&j.updated?' · location updated '+new Date(j.updated*1000).toLocaleTimeString('en-IN',{hour:'numeric',minute:'2-digit'}):'');
 document.querySelector('.top').classList.toggle('ended',!j.active);document.getElementById('live').style.display=j.active?'':'none';
 const b=[];if(j.phone)b.push(`<a class="btn red" href="tel:${esc(j.phone)}">📞 Call ${esc(j.name.split(' ')[0])}</a>`);b.push(`<a class="btn red" href="tel:112">📞 Call 112</a>`);
 if(j.directions)b.push(`<a class="btn" href="${esc(j.directions)}" target="_blank" rel="noopener">🧭 Directions</a>`);if(j.maps)b.push(`<a class="btn s" href="${esc(j.maps)}" target="_blank" rel="noopener">Open in Google Maps</a>`);
 document.getElementById('btns').innerHTML=b.join('');
 document.getElementById('sum').textContent=j.summary||'No Medical ID details were shared.';
 if(j.loc){const key=j.loc.lat.toFixed(5)+','+j.loc.lng.toFixed(5);if(key!==lastKey){lastKey=key;document.getElementById('map').innerHTML=`<iframe loading="lazy" referrerpolicy="no-referrer-when-downgrade" src="https://www.google.com/maps?q=${j.loc.lat},${j.loc.lng}&z=16&output=embed" title="Map"></iframe>`}
  document.getElementById('acc').textContent=(j.loc.acc?`Accurate to about ${j.loc.acc} m. `:'')+(j.trail&&j.trail.length>1?`${j.trail.length} positions recorded.`:'')}
}
tick();setInterval(tick,20000);
</script></body></html>"""


@r.get("/sos/{token}", include_in_schema=False)
def public_page(token: str, db: Session = Depends(get_db)):
    a = db.scalar(select(SosAlert).where(SosAlert.token == token[:48]))
    if not a or (not a.active and a.ended and now() - a.ended > 86400):
        return HTMLResponse("<!doctype html><meta charset=utf-8><title>Alert ended</title><body style='font-family:system-ui;padding:40px;text-align:center'><h1>This SOS alert is no longer available.</h1><p>If someone needs help now, call 112.</p>", status_code=404)
    page = PAGE.replace("__NAME__", html.escape(a.name)).replace("__APP__", APP)
    return HTMLResponse(page, headers={"Cache-Control": "no-store", "X-Frame-Options": "DENY",
                                       "Content-Security-Policy": "default-src 'self'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; frame-src https://www.google.com; connect-src 'self'; img-src data: https:; base-uri 'none'"})

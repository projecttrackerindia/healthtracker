"""Public pages Google can read: one per live partner, plus city and area lists.

Only business information: name, photos taken at the shop, address, landmark, hours, home-visit area, test prices,
rating from completed visits. Nothing about any family. Prescription medicines are never listed or priced here
(Drugs and Magic Remedies Act / Drugs and Cosmetics Rules). A paused or unverified partner returns 404 and drops out
of the sitemap at once."""
from __future__ import annotations

import html
import json
import math
import re

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from .db import get_db
from .models import LabTest, Store

r = APIRouter()
KINDS = {"labs": ("lab", "Diagnostic labs", "Lab", "DiagnosticLab"), "pharmacies": ("pharmacy", "Pharmacies", "Pharmacy", "Pharmacy"),
         "hospitals": ("hospital", "Hospitals & clinics", "Hospital", "MedicalClinic")}
SEG = {v[0]: k for k, v in KINDS.items()}


def slug(s: str) -> str:
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", (s or "").lower())).strip("-")[:60] or "x"


def listed(db: Session, kind: str | None = None):
    q = select(Store).where(Store.verified == True, Store.active == True, Store.kind.in_(tuple(SEG)))  # noqa: E712
    if kind:
        q = q.where(Store.kind == kind)
    return [s for s in db.scalars(q).all() if not (s.profile or {}).get("publicOff")]


def path_of(s: Store) -> str:
    return f"/{SEG.get(s.kind, 'labs')}/{slug(s.city)}/{slug(s.area or s.city)}/{slug(s.name)}-{s.id[-6:]}"


def sitemap_paths(db: Session) -> list[str]:
    out, areas = [], set()
    for s in listed(db):
        out.append(path_of(s))
        seg = SEG.get(s.kind, "labs")
        areas.add(f"/{seg}/{slug(s.city)}")
        areas.add(f"/{seg}/{slug(s.city)}/{slug(s.area or s.city)}")
    return sorted(areas) + out


E = html.escape
CSS = """*{box-sizing:border-box}body{margin:0;font:16px/1.5 -apple-system,Inter,system-ui,sans-serif;color:#1D1D1F;background:#fff}
a{color:#0066CC;text-decoration:none}.w{max-width:1120px;margin:0 auto;padding:0 20px}
nav{display:flex;align-items:center;gap:20px;padding:14px 0;border-bottom:1px solid #F2F2F7}nav b{font-size:17px}nav .g{margin-left:auto}
.btn{display:inline-block;background:#0071E3;color:#fff;border-radius:980px;padding:11px 20px;font-weight:600}
.crumb{font-size:13px;color:#6E6E73;margin:16px 0}h1{font-size:34px;letter-spacing:-.02em;margin:6px 0}
.pill{display:inline-block;font-size:12px;font-weight:600;padding:3px 9px;border-radius:99px;background:#F2F2F7;margin:2px 4px 2px 0}.ok{background:#E8F8EC;color:#1B6E30}.bl{background:#EAF3FF;color:#0059B3}
.grid{display:grid;grid-template-columns:1.25fr 1fr;gap:28px;margin:10px 0 40px}.ph{display:grid;grid-template-columns:2fr 1fr;grid-template-rows:1fr 1fr;gap:8px;height:300px}.ph img{width:100%;height:100%;object-fit:cover;border-radius:14px;background:#EEF1F5}.ph img:first-child{grid-row:span 2}
.card{background:#F9F9FB;border-radius:16px;padding:16px 18px;margin-top:14px}.kv{display:flex;justify-content:space-between;gap:12px;padding:7px 0;border-bottom:1px solid #EDEDF0;font-size:14.5px}.kv:last-child{border:0}.kv span{color:#6E6E73}.kv b{text-align:right}
.book{border:1px solid #EDEDF0;box-shadow:0 10px 30px rgba(0,0,0,.06);border-radius:18px;padding:18px;background:#fff}
.row{display:flex;gap:12px;align-items:center;background:#F9F9FB;border-radius:14px;padding:12px 14px;margin:8px 0;color:inherit}.row img{width:72px;height:56px;border-radius:10px;object-fit:cover;background:#EEF1F5}
.map{position:relative;height:170px;border-radius:14px;overflow:hidden;background:#E8EEF3}.map img{position:absolute;width:256px;height:256px}.pin{position:absolute;left:50%;top:50%;width:20px;height:20px;margin:-10px;border-radius:50%;background:#0071E3;border:4px solid #fff;box-sizing:border-box;box-shadow:0 2px 8px rgba(0,0,0,.3)}
footer{color:#6E6E73;font-size:13px;padding:30px 0;border-top:1px solid #F2F2F7}
@media(max-width:820px){.grid{grid-template-columns:1fr}.ph{height:220px}h1{font-size:27px}}"""


def page(request: Request, title: str, desc: str, body: str, ld: dict | list, canon: str) -> HTMLResponse:
    from server import _origin  # the canonical address, once configured
    origin = _origin(request)
    doc = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{E(title)}</title><meta name="description" content="{E(desc)}"><link rel="canonical" href="{E(origin + canon)}">
<meta property="og:title" content="{E(title)}"><meta property="og:description" content="{E(desc)}"><meta property="og:type" content="website">
<link rel="icon" href="/icon.svg"><style>{CSS}</style>
<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False).replace('</', '<\\/')}</script></head>
<body><div class="w"><nav><a href="/" style="color:inherit"><b>✚ Urban Health</b></a><a href="/labs/hyderabad">Lab tests</a><a href="/pharmacies/hyderabad">Pharmacies</a><a href="/hospitals/hyderabad">Doctors</a><a class="btn g" href="/app">Open the app</a></nav>
{body}<footer>Information is provided by each partner and checked by Urban Health before it goes live. Prices can change; the app shows the current price before you book. Not medical advice.</footer></div></body></html>"""
    return HTMLResponse(doc, headers={"Cache-Control": "public, max-age=900"})


def tiles(lat: float, lng: float) -> str:
    z, n = 16, 2 ** 16
    fx = (lng + 180) / 360 * n
    rr = math.radians(lat)
    fy = (1 - math.log(math.tan(rr) + 1 / math.cos(rr)) / math.pi) / 2 * n
    tx, ty, ox, oy = int(fx), int(fy), (fx - int(fx)) * 256, (fy - int(fy)) * 256
    imgs = "".join(f'<img alt="" loading="lazy" src="https://tile.openstreetmap.org/{z}/{tx + dx}/{ty + dy}.png" style="left:{dx * 256 - ox:.0f}px;top:{dy * 256 - oy:.0f}px">'
                   for dx in (-2, -1, 0, 1, 2) for dy in (-1, 0, 1))
    return f'<div class="map"><div style="position:absolute;left:50%;top:50%">{imgs}</div><span class="pin"></span><span style="position:absolute;right:6px;bottom:4px;font-size:10px;background:rgba(255,255,255,.85);padding:0 4px;border-radius:4px">© OpenStreetMap</span></div>'


def photo_urls(s: Store) -> list[str]:
    order = {"front": 0, "reception": 1, "inside": 2, "sample": 3, "waiting": 4}
    return [f"/api/v2/stores/{s.id}/photos/{p['id']}" for p in sorted(s.photos or [], key=lambda p: order.get(p.get("slot"), 9)) if p.get("slot") != "licence"]


def partner_page(seg: str, city: str, area: str, name: str, request: Request, db: Session = Depends(get_db)):
    if seg not in KINDS:
        raise HTTPException(404)
    kind, plural, single, schema = KINDS[seg]
    sid_tail = name.rsplit("-", 1)[-1]
    s = next((x for x in listed(db, kind) if x.id.endswith(sid_tail) and len(sid_tail) == 6), None)
    if not s:
        raise HTTPException(404)
    canon = path_of(s)
    p = s.profile or {}
    tests = sorted(db.scalars(select(LabTest).where(LabTest.store_id == s.id)).all(), key=lambda t: t.price)[:8] if kind == "lab" else []
    photos = photo_urls(s)
    hours = p.get("hoursWeek") or s.hours or ""
    rating = f"{s.rating:.1f}" if s.rating_n else ""
    nabl = s.licence if kind == "lab" else ""
    pills = "".join(f'<span class="pill {c}">{E(t)}</span>' for t, c in [(("NABL " + nabl) if nabl else "", "ok"), ("Home collection" if s.home_collection else "", "bl"),
                                                                           ("Home delivery" if kind == "pharmacy" and s.delivery else "", "bl"), ("Open 24 hours" if s.open_24h else "", "ok")] if t)
    ph = "".join(f'<img src="{E(u)}" alt="">' for u in photos[:3]) or '<img alt="">'
    tests_html = "".join(f'<div class="kv"><span>{E(t.name)}</span><b>₹{t.price:,}</b></div>' for t in tests)
    kv = lambda a, b: f'<div class="kv"><span>{E(a)}</span><b>{E(b)}</b></div>' if b else ""  # noqa: E731
    body = f"""<div class="crumb"><a href="/{seg}/{slug(s.city)}">{E(plural)} in {E(s.city)}</a> › <a href="/{seg}/{slug(s.city)}/{slug(s.area or s.city)}">{E(s.area or s.city)}</a> › {E(s.name)}</div>
<div class="grid"><div><div class="ph">{ph}</div><h1>{E(s.name)}{', ' + E(s.area) if s.area and s.area.lower() not in s.name.lower() else ''}</h1>
<div>{'<b>' + rating + ' ★</b> <span style="color:#6E6E73">' + str(s.rating_n) + ' ratings from completed visits</span> ' if rating else ''}{pills}</div>
{f'<div class="card"><b style="font-size:15px">Popular tests</b>{tests_html}</div>' if tests_html else ''}
{f'<div class="card"><b style="font-size:15px">About</b><p style="margin:6px 0 0;color:#3A3A3C;font-size:15px">{E(p.get("about", ""))}</p></div>' if p.get("about") else ''}</div>
<div><div class="book"><div style="font-size:18px;font-weight:700">{'Book a test at home' if kind == 'lab' else 'Order medicines' if kind == 'pharmacy' else 'Book a consultation'}</div>
<div style="color:#6E6E73;font-size:14px;margin:2px 0 12px">{E(' · '.join(x for x in [('Sample collected ' + p['homeHours']) if p.get('homeHours') else '', p.get('reportTime', '')] if x)) or 'Book in the Urban Health app'}</div>
<a class="btn" style="display:block;text-align:center" href="/app?partner={E(s.id)}">Book in the app</a></div>
<div class="card" style="padding:0;overflow:hidden">{tiles(s.lat, s.lng) if s.lat is not None else ''}<div style="padding:10px 16px">
{kv('Address', ', '.join(x for x in [s.address, s.area, s.city, s.pin] if x))}{kv('Landmark', s.landmark)}{kv('Hours', hours + (' · Sunday ' + p['hoursSun'] if p.get('hoursSun') else ''))}
{kv('Home visits in', p.get('pins', ''))}{kv('Access', p.get('access', ''))}{kv('Languages', p.get('languages', ''))}{kv('Phone', s.phone)}
<div class="kv"><span>Directions</span><b><a href="https://www.google.com/maps/search/?api=1&query={s.lat},{s.lng}" rel="nofollow">Open in Maps</a></b></div></div></div></div></div>"""
    from server import _origin
    origin = _origin(request)
    ld = {"@context": "https://schema.org", "@type": schema, "name": s.name, "url": origin + canon, "telephone": s.phone or None,
          "image": [origin + u for u in photos[:3]] or None,
          "address": {"@type": "PostalAddress", "streetAddress": s.address, "addressLocality": s.area or s.city, "addressRegion": "Telangana" if s.city.lower() in ("hyderabad", "secunderabad", "warangal") else "", "postalCode": s.pin, "addressCountry": "IN"},
          "geo": {"@type": "GeoCoordinates", "latitude": s.lat, "longitude": s.lng} if s.lat is not None else None, "openingHours": hours or None}
    if s.rating_n >= 5:
        ld["aggregateRating"] = {"@type": "AggregateRating", "ratingValue": round(s.rating, 1), "ratingCount": s.rating_n}
    if tests:
        ld["priceRange"] = f"₹{tests[0].price}–₹{tests[-1].price}"
    ld = {k: v for k, v in ld.items() if v not in (None, "", [])}
    desc = f"{s.name}, {s.area or s.city}. " + (f"NABL lab, home sample collection. " if kind == 'lab' and nabl else "") + \
           (", ".join(f"{t.name} ₹{t.price}" for t in tests[:3]) + ". " if tests else "") + (f"Open {hours}." if hours else "")
    return page(request, f"{s.name}, {s.area or s.city}" + (" · Home Collection" if kind == "lab" and s.home_collection else "") + " · Urban Health", desc[:300], body, ld, canon)


def _list_page(request: Request, db: Session, seg: str, city: str, area: str | None):
    if seg not in KINDS:
        raise HTTPException(404)
    kind, plural, single, schema = KINDS[seg]
    rows = [s for s in listed(db, kind) if slug(s.city) == city and (area is None or slug(s.area or s.city) == area)]
    if not rows:
        raise HTTPException(404)
    cname = rows[0].city
    aname = (rows[0].area or cname) if area else None
    where = aname or cname
    cheapest = {}
    if kind == "lab":
        for sid, price in db.execute(select(LabTest.store_id, LabTest.price).where(LabTest.code == "cbc", LabTest.store_id.in_([s.id for s in rows]))).all():
            cheapest[sid] = price
    rows.sort(key=lambda s: -(s.rating or 0) * (s.rating_n or 0) ** .5)
    items = "".join(f"""<a class="row" href="{E(path_of(s))}"><img src="{E((photo_urls(s) or [''])[0])}" alt=""><div style="flex:1"><b>{E(s.name)}</b><div style="color:#6E6E73;font-size:13.5px">{E(s.landmark or s.area or s.city)}{' · ' + E((s.profile or {}).get('hoursWeek') or s.hours) if ((s.profile or {}).get('hoursWeek') or s.hours) else ''}</div>
<div style="font-size:13.5px">{f'<b>{s.rating:.1f} ★</b>' if s.rating_n else ''}{f' · CBC from ₹{cheapest[s.id]}' if s.id in cheapest else ''}</div></div><span style="color:#0066CC;font-weight:600">View</span></a>""" for s in rows)
    areas = sorted({(slug(s.area or s.city), s.area or s.city) for s in listed(db, kind) if slug(s.city) == city})
    area_links = "" if area else "<div style='margin:6px 0 14px'>" + "".join(f'<a class="pill" href="/{seg}/{city}/{a}">{E(n)}</a>' for a, n in areas) + "</div>"
    body = f"""<div class="crumb"><a href="/">Home</a> › <a href="/{seg}/{city}">{E(plural)} in {E(cname)}</a>{' › ' + E(aname) if aname else ''}</div>
<h1>{E(plural)} in {E(where)}</h1><p style="color:#6E6E73;margin:0">{len(rows)} verified {single.lower()}{'s' if len(rows) != 1 else ''}{' with home collection' if kind == 'lab' else ''} · checked by Urban Health</p>{area_links}
<div style="max-width:760px">{items}</div>"""
    canon = f"/{seg}/{city}" + (f"/{area}" if area else "")
    from server import _origin
    origin = _origin(request)
    ld = {"@context": "https://schema.org", "@type": "ItemList", "name": f"{plural} in {where}",
          "itemListElement": [{"@type": "ListItem", "position": i + 1, "url": origin + path_of(s), "name": s.name} for i, s in enumerate(rows[:30])]}
    return page(request, f"{len(rows)} {plural} in {where}" + (" with Home Collection" if kind == "lab" else "") + " · Urban Health",
                f"Compare {plural.lower()} in {where} by rating, price and timings. Verified by Urban Health. Book in the app.", body, ld, canon)


def area_page(seg: str, city: str, area: str, request: Request, db: Session = Depends(get_db)):
    return _list_page(request, db, seg, city, area)


def city_page(seg: str, city: str, request: Request, db: Session = Depends(get_db)):
    return _list_page(request, db, seg, city, None)


def _bind(seg: str):
    def p4(city: str, area: str, name: str, request: Request, db: Session = Depends(get_db)):
        return partner_page(seg, city, area, name, request, db)

    def p3(city: str, area: str, request: Request, db: Session = Depends(get_db)):
        return area_page(seg, city, area, request, db)

    def p2(city: str, request: Request, db: Session = Depends(get_db)):
        return city_page(seg, city, request, db)
    r.add_api_route(f"/{seg}/{{city}}/{{area}}/{{name}}", p4, methods=["GET", "HEAD"], response_class=HTMLResponse, include_in_schema=False)
    r.add_api_route(f"/{seg}/{{city}}/{{area}}", p3, methods=["GET", "HEAD"], response_class=HTMLResponse, include_in_schema=False)
    r.add_api_route(f"/{seg}/{{city}}", p2, methods=["GET", "HEAD"], response_class=HTMLResponse, include_in_schema=False)


for _seg in KINDS:
    _bind(_seg)

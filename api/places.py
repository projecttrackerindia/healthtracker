"""Where the family is, and what is around them — from OpenStreetMap, with partner stores on top.

* GET /api/v1/geo/where?lat&lng          → place, district, state (Nominatim reverse geocoding, cached ~1 km cells)
* GET /api/v1/places?kind&lat&lng&radius → hospitals / clinics / labs / pharmacies / blood banks nearby (Overpass), merged with
                                           the partner stores from the admin panel (marked partner=true, with prices and booking)

Both are read-only public data. Results are cached in memory per rounded cell so a family browsing the map does not hammer
the OSM servers (their usage policy asks for ~1 request/second and a real User-Agent).
"""
from __future__ import annotations

import json
import math
import os
import threading
import time
import urllib.parse
import urllib.request

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .db import get_db
from .models import Store

r = APIRouter(prefix="/api/v1")
UA = "TheHealthTracker/1.0 (+https://thehealthtracker.com; support@thehealthtracker.com)"
NOMINATIM = os.getenv("NOMINATIM_URL", "https://nominatim.openstreetmap.org/reverse")
OVERPASS = os.getenv("OVERPASS_URL", "https://overpass-api.de/api/interpreter")
KINDS = {
    "hospital": '["amenity"="hospital"]',
    "clinic": '["amenity"~"^(clinic|doctors)$"]',
    "lab": '["healthcare"="laboratory"]',
    "pharmacy": '["amenity"="pharmacy"]',
    "blood": '["healthcare"="blood_donation"]',
}
STATE_CODES = {"Andhra Pradesh": "AP", "Telangana": "TS", "Karnataka": "KA", "Tamil Nadu": "TN", "Kerala": "KL", "Maharashtra": "MH", "Gujarat": "GJ",
               "Delhi": "DL", "Uttar Pradesh": "UP", "West Bengal": "WB", "Rajasthan": "RJ", "Madhya Pradesh": "MP", "Punjab": "PB", "Haryana": "HR",
               "Bihar": "BR", "Odisha": "OD", "Assam": "AS", "Jharkhand": "JH", "Chhattisgarh": "CG", "Uttarakhand": "UK", "Himachal Pradesh": "HP",
               "Goa": "GA", "Jammu and Kashmir": "JK", "Puducherry": "PY", "Chandigarh": "CH", "Tripura": "TR", "Manipur": "MN", "Meghalaya": "ML",
               "Nagaland": "NL", "Mizoram": "MZ", "Sikkim": "SK", "Arunachal Pradesh": "AR", "Ladakh": "LA"}
_CACHE: dict[str, tuple[float, dict]] = {}
_LOCK = threading.Lock()
_LAST_CALL = {"t": 0.0}


def _cached(key: str, ttl: int, make):
    now = time.time()
    with _LOCK:
        hit = _CACHE.get(key)
        if hit and now - hit[0] < ttl:
            return hit[1]
    val = make()
    with _LOCK:
        _CACHE[key] = (now, val)
        if len(_CACHE) > 5000:
            for k in sorted(_CACHE, key=lambda k: _CACHE[k][0])[:1000]:
                _CACHE.pop(k, None)
    return val


def _get(url: str, data: bytes | None = None, timeout: int = 12) -> dict:
    # be polite to OSM: at most ~1 request per second from this process
    with _LOCK:
        wait = 1.0 - (time.time() - _LAST_CALL["t"])
        if wait > 0:
            time.sleep(min(wait, 1.0))
        _LAST_CALL["t"] = time.time()
    req = urllib.request.Request(url, data=data, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8", "ignore"))


def km(a, b, c, d):
    p = math.pi / 180
    x = 0.5 - math.cos((c - a) * p) / 2 + math.cos(a * p) * math.cos(c * p) * (1 - math.cos((d - b) * p)) / 2
    return 12742 * math.asin(math.sqrt(x))


def _check(lat: float | None, lng: float | None):
    if lat is None or lng is None or not (-90 <= lat <= 90 and -180 <= lng <= 180):
        raise HTTPException(400, "lat and lng are required")


@r.get("/geo/where")
def where(lat: float | None = None, lng: float | None = None):
    _check(lat, lng)
    key = f"where:{round(lat, 2)}:{round(lng, 2)}"

    def make():
        try:
            j = _get(f"{NOMINATIM}?format=jsonv2&zoom=14&addressdetails=1&lat={lat}&lon={lng}")
        except Exception as e:
            print("[geo] reverse failed:", type(e).__name__, str(e)[:120], flush=True)
            return {"ok": False}
        a = j.get("address") or {}
        place = a.get("suburb") or a.get("neighbourhood") or a.get("village") or a.get("town") or a.get("city") or a.get("county") or ""
        city = a.get("city") or a.get("town") or a.get("village") or a.get("county") or a.get("state_district") or ""
        state = a.get("state") or ""
        return {"ok": True, "place": place, "city": city, "district": a.get("state_district") or a.get("county") or "", "state": state,
                "stateCode": STATE_CODES.get(state, ""), "pin": a.get("postcode") or "", "country": a.get("country_code", "").upper()}

    return _cached(key, 7 * 86400, make)


def _store_json(s: Store, d: float) -> dict:
    return {"id": s.id, "name": s.name, "lat": s.lat, "lng": s.lng, "km": round(d, 1), "address": ", ".join(x for x in (s.address, s.area, s.city) if x),
            "phone": s.phone or "", "rating": s.rating, "partner": True, "kind": s.kind, "home": bool(getattr(s, "home_collection", False)),
            "licence": getattr(s, "licence", "") or "", "hours": getattr(s, "hours", "") or ""}


@r.get("/places")
def places(kind: str = "hospital", lat: float | None = None, lng: float | None = None, radius: int = 5000, db: Session = Depends(get_db)):
    _check(lat, lng)
    if kind not in KINDS:
        raise HTTPException(400, "kind must be one of " + ", ".join(KINDS))
    radius = max(1000, min(20000, radius))
    cell = f"{round(lat, 2)}:{round(lng, 2)}:{radius}"

    def make():
        q = f'[out:json][timeout:20];(node{KINDS[kind]}(around:{radius},{lat},{lng});way{KINDS[kind]}(around:{radius},{lat},{lng}););out center tags 80;'
        try:
            j = _get(OVERPASS, data=urllib.parse.urlencode({"data": q}).encode(), timeout=25)
        except Exception as e:
            print("[places] overpass failed:", type(e).__name__, str(e)[:120], flush=True)
            return {"ok": False, "items": []}
        out = []
        for el in j.get("elements", []):
            t = el.get("tags") or {}
            la, lo = (el.get("lat"), el.get("lon")) if el.get("type") == "node" else ((el.get("center") or {}).get("lat"), (el.get("center") or {}).get("lon"))
            if la is None or not t.get("name"):
                continue
            addr = ", ".join(x for x in (t.get("addr:housenumber"), t.get("addr:street"), t.get("addr:suburb") or t.get("addr:neighbourhood"), t.get("addr:city")) if x)
            out.append({"id": f"osm:{el.get('type')}:{el.get('id')}", "name": t["name"], "lat": la, "lng": lo, "km": round(km(lat, lng, la, lo), 1),
                        "address": addr, "phone": t.get("phone") or t.get("contact:phone") or "", "website": t.get("website") or t.get("contact:website") or "",
                        "hours": t.get("opening_hours") or "", "emergency": t.get("emergency") == "yes", "operator": t.get("operator") or "",
                        "beds": t.get("beds") or "", "partner": False})
        out.sort(key=lambda x: x["km"])
        return {"ok": True, "items": out[:60]}

    osm = _cached(f"places:{kind}:{cell}", 6 * 3600, make)
    skind = {"hospital": "hospital", "clinic": "hospital", "lab": "lab", "pharmacy": "pharmacy", "blood": None}[kind]
    partners = []
    if skind:
        for s in db.scalars(select(Store).where(Store.kind == skind, Store.active == True)).all():  # noqa: E712
            d = km(lat, lng, s.lat, s.lng)
            if d <= radius / 1000 + 3:
                partners.append(_store_json(s, d))
    partners.sort(key=lambda x: x["km"])
    return {"kind": kind, "ok": osm["ok"], "partners": partners, "places": osm["items"],
            "note": None if osm["ok"] else "Live map data is not reachable right now; showing partners only."}

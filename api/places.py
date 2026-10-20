"""Where the family is, and what is around them — Google Maps Platform first, OpenStreetMap when no key is set.

* GET /api/v1/geo/where?lat&lng          → place, district, state, PIN (Geocoding API reverse; Nominatim fallback; cached ~1 km cells)
* GET /api/v1/geo/search?q               → type an area, city, PIN or landmark and pick it (Geocoding API; Nominatim fallback)
* GET /api/v1/places?kind&lat&lng&radius → hospitals / clinics / labs / pharmacies / blood banks nearby (Places API (New) Nearby
                                           Search; Overpass fallback), merged with the partner stores from the admin panel
                                           (marked partner=true, with prices and booking)

Set GOOGLE_MAPS_SERVER_KEY (a key restricted to the Geocoding and Places APIs, never shipped to the browser) to use Google; the
browser map itself uses GOOGLE_MAPS_KEY from /api/v1/config. Results are cached in memory per rounded cell so a family browsing
the map costs one request per area, not one per tap; the OSM path keeps its ~1 request/second politeness.
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
# Places API (New) types per kind; "blood" has no type and goes through text search
GTYPES = {"hospital": ["hospital"], "clinic": ["doctor"], "lab": ["medical_lab"], "pharmacy": ["pharmacy", "drugstore"], "blood": []}
GFIELDS = "places.id,places.displayName,places.location,places.formattedAddress,places.nationalPhoneNumber,places.internationalPhoneNumber,places.rating,places.userRatingCount,places.websiteUri,places.currentOpeningHours.openNow,places.regularOpeningHours.weekdayDescriptions,places.types"
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


def gkey() -> str:
    return os.getenv("GOOGLE_MAPS_SERVER_KEY") or os.getenv("GOOGLE_MAPS_KEY", "")


def provider() -> str:
    return "google" if gkey() else "osm"


def _gget(url: str, params: dict, timeout: int = 10) -> dict:
    req = urllib.request.Request(url + "?" + urllib.parse.urlencode({**params, "key": gkey()}), headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8", "ignore"))


def _gpost(url: str, body: dict, fields: str, timeout: int = 12) -> dict:
    req = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST",
                                 headers={"User-Agent": UA, "Content-Type": "application/json", "X-Goog-Api-Key": gkey(), "X-Goog-FieldMask": fields})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8", "ignore"))


def _gaddress(res: dict) -> dict:
    """One Geocoding result → the fields the app keeps (place = locality-level area, city, district, state, PIN)."""
    comp: dict[str, str] = {}
    for c in res.get("address_components") or []:
        for t in c.get("types") or []:
            comp.setdefault(t, c.get("long_name", ""))
    place = comp.get("sublocality_level_1") or comp.get("sublocality") or comp.get("neighborhood") or comp.get("sublocality_level_2") or comp.get("locality") or ""
    city = comp.get("locality") or comp.get("administrative_area_level_3") or comp.get("administrative_area_level_2") or ""
    state = comp.get("administrative_area_level_1") or ""
    loc = (res.get("geometry") or {}).get("location") or {}
    return {"ok": True, "place": place, "city": city, "district": comp.get("administrative_area_level_2") or "", "state": state, "stateCode": STATE_CODES.get(state, ""),
            "pin": comp.get("postal_code") or "", "country": comp.get("country", ""), "label": res.get("formatted_address", "")[:160],
            "lat": round(float(loc.get("lat", 0)), 5), "lng": round(float(loc.get("lng", 0)), 5)}


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
    key = f"where:{provider()}:{round(lat, 3)}:{round(lng, 3)}"

    def make():
        if gkey():
            try:
                j = _gget("https://maps.googleapis.com/maps/api/geocode/json", {"latlng": f"{lat},{lng}", "language": "en", "region": "in",
                                                                               "result_type": "street_address|sublocality|locality|postal_code"})
                res = j.get("results") or []
                if j.get("status") == "OK" and res:
                    out = _gaddress(res[0])
                    for x in res[1:]:   # the first hit is the finest; fill blanks from the coarser ones
                        o = _gaddress(x)
                        for k in ("place", "city", "district", "state", "pin"):
                            out[k] = out[k] or o[k]
                    out["stateCode"] = STATE_CODES.get(out["state"], "")
                    out["lat"], out["lng"] = round(lat, 5), round(lng, 5)
                    return out
                print("[geo] google reverse:", j.get("status"), (j.get("error_message") or "")[:100], flush=True)
            except Exception as e:
                print("[geo] google reverse failed:", type(e).__name__, str(e)[:120], flush=True)
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


@r.get("/geo/search")
def search(q: str = ""):
    """Type a locality, city or PIN and pick it: for people who deny GPS or are setting a family member's town."""
    q = q.strip()[:80]
    if len(q) < 2:
        return {"results": []}
    key = f"search:{provider()}:{q.lower()}"

    def make():
        if gkey():
            try:
                j = _gget("https://maps.googleapis.com/maps/api/geocode/json", {"address": q, "components": "country:IN", "language": "en", "region": "in"})
                if j.get("status") in ("OK", "ZERO_RESULTS"):
                    out = [_gaddress(x) for x in (j.get("results") or [])[:6]]
                    return {"ok": True, "results": [x for x in out if x["lat"] and x["lng"]]}
                print("[geo] google search:", j.get("status"), (j.get("error_message") or "")[:100], flush=True)
            except Exception as e:
                print("[geo] google search failed:", type(e).__name__, str(e)[:120], flush=True)
        try:
            j = _get(f"https://nominatim.openstreetmap.org/search?format=jsonv2&addressdetails=1&countrycodes=in&limit=6&q={urllib.parse.quote(q)}")
        except Exception as e:
            print("[geo] search failed:", type(e).__name__, str(e)[:120], flush=True)
            return {"ok": False, "results": []}
        out = []
        for x in j if isinstance(j, list) else []:
            a = x.get("address") or {}
            place = a.get("suburb") or a.get("neighbourhood") or a.get("village") or a.get("town") or a.get("city") or x.get("name") or ""
            city = a.get("city") or a.get("town") or a.get("village") or a.get("county") or a.get("state_district") or ""
            state = a.get("state") or ""
            out.append({"label": x.get("display_name", "")[:120], "place": place, "city": city, "state": state, "stateCode": STATE_CODES.get(state, ""),
                        "lat": round(float(x["lat"]), 5), "lng": round(float(x["lon"]), 5)})
        return {"ok": True, "results": out}

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

    def gmake():
        try:
            if GTYPES[kind]:
                j = _gpost("https://places.googleapis.com/v1/places:searchNearby",
                           {"includedTypes": GTYPES[kind], "maxResultCount": 20, "languageCode": "en", "regionCode": "IN", "rankPreference": "DISTANCE",
                            "locationRestriction": {"circle": {"center": {"latitude": lat, "longitude": lng}, "radius": float(radius)}}}, GFIELDS)
            else:
                j = _gpost("https://places.googleapis.com/v1/places:searchText",
                           {"textQuery": "blood bank", "maxResultCount": 20, "languageCode": "en", "regionCode": "IN",
                            "locationBias": {"circle": {"center": {"latitude": lat, "longitude": lng}, "radius": float(radius)}}}, GFIELDS)
        except Exception as e:
            print("[places] google failed:", type(e).__name__, str(e)[:160], flush=True)
            return None
        out = []
        for p in j.get("places") or []:
            loc = p.get("location") or {}
            la, lo = loc.get("latitude"), loc.get("longitude")
            name = (p.get("displayName") or {}).get("text") or ""
            if la is None or not name:
                continue
            hours = p.get("regularOpeningHours") or {}
            cur = p.get("currentOpeningHours") or {}
            out.append({"id": "g:" + str(p.get("id", "")), "name": name, "lat": la, "lng": lo, "km": round(km(lat, lng, la, lo), 1),
                        "address": p.get("formattedAddress") or "", "phone": p.get("nationalPhoneNumber") or p.get("internationalPhoneNumber") or "",
                        "website": p.get("websiteUri") or "", "hours": "; ".join(hours.get("weekdayDescriptions") or [])[:240],
                        "open": cur.get("openNow"), "rating": p.get("rating"), "ratings": p.get("userRatingCount"),
                        "emergency": kind == "hospital", "operator": "", "beds": "", "partner": False})
        out.sort(key=lambda x: x["km"])
        return {"ok": True, "items": out[:60], "src": "google"}

    def make():
        if gkey():
            g = gmake()
            if g is not None:
                return g
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
    return {"kind": kind, "ok": osm["ok"], "src": osm.get("src", "osm"), "partners": partners, "places": osm["items"],
            "note": None if osm["ok"] else "Live map data is not reachable right now; showing partners only."}

"""Fitbit (cloud) → TheHealthTracker (/api/v1/fitbit). For people on the web without the phone app, or with a Fitbit.

Google Fit's REST API was retired in 2025 and Garmin/Samsung require partner programmes, so Fitbit's public Web API
is the one wearable cloud a small Indian app can use today. OAuth 2.0 with PKCE; tokens are sealed with the data key
per family profile. `sync` pulls the last 7 days (steps per day, sleep hours, resting heart rate, SpO₂, weight) in the
same shape as the phone's Health Connect / HealthKit plugin, and the app merges it into the person's readings.
Register at https://dev.fitbit.com (Personal app type reads intraday too; Server type for several users),
callback https://thehealthtracker.com/api/v1/fitbit/callback, then set FITBIT_CLIENT_ID and FITBIT_CLIENT_SECRET.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import secrets
import time
import zlib
from datetime import date, timedelta
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from .auth import limit
from .db import get_db
from .family import _key, open_with_keys
from .models import DeviceLink, now
from .routes import household
from .security import sign, verify

r = APIRouter(prefix="/api/v1/fitbit")
AAD = b"tht-devlink-v1"
SCOPES = "activity heartrate sleep oxygen_saturation weight profile"
AUTH = "https://www.fitbit.com/oauth2/authorize"
TOKEN = "https://api.fitbit.com/oauth2/token"
API = "https://api.fitbit.com"


def enabled() -> bool:
    return bool(os.getenv("FITBIT_CLIENT_ID") and os.getenv("FITBIT_CLIENT_SECRET"))


def _seal(obj: dict) -> bytes:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    raw = zlib.compress(json.dumps(obj).encode())
    nonce = secrets.token_bytes(12)
    return b"v1" + nonce + AESGCM(_key()).encrypt(nonce, raw, AAD)


def _open(blob: bytes) -> dict:
    return json.loads(zlib.decompress(open_with_keys(blob[14:], blob[2:14], AAD)).decode())


def _origin(request: Request) -> str:
    o = (os.getenv("APP_ORIGIN") or "").split(",")[0].strip()
    if o:
        return o.rstrip("/")
    proto = request.headers.get("x-forwarded-proto", request.url.scheme)
    return f"{proto}://{request.headers.get('x-forwarded-host') or request.headers.get('host')}"


def _redirect(request: Request) -> str:
    return os.getenv("FITBIT_REDIRECT") or f"{_origin(request)}/api/v1/fitbit/callback"


def link_json(l: DeviceLink) -> dict:
    return {"id": l.id, "member": l.member_id, "provider": l.provider, "user": l.external_id, "lastSync": l.last_sync, "since": l.created}


@r.get("/status")
def status(db: Session = Depends(get_db), x_dokko_key: str | None = Header(None)):
    h = household(db, x_dokko_key, create=False)
    links = db.scalars(select(DeviceLink).where(DeviceLink.household_id == h.id, DeviceLink.provider == "fitbit")).all() if h else []
    return {"enabled": enabled(), "links": [link_json(l) for l in links],
            "message": "" if enabled() else "Fitbit linking opens once TheHealthTracker's Fitbit developer app is approved."}


@r.post("/start")
def start(request: Request, member: str = "", db: Session = Depends(get_db), x_dokko_key: str | None = Header(None)):
    if not enabled():
        raise HTTPException(503, "Fitbit linking is not switched on yet.")
    h = household(db, x_dokko_key)
    if not h:
        raise HTTPException(400, "missing household key")
    limit(request, f"fitbit:{h.id}", 10, 3600)
    verifier = secrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    state = sign({"k": "fb", "h": h.id, "m": member[:32], "v": verifier, "t": now()})
    q = {"response_type": "code", "client_id": os.getenv("FITBIT_CLIENT_ID"), "scope": SCOPES, "code_challenge": challenge, "code_challenge_method": "S256", "state": state, "redirect_uri": _redirect(request)}
    return {"url": f"{AUTH}?{urlencode(q)}"}


def _basic() -> str:
    return "Basic " + base64.b64encode(f"{os.getenv('FITBIT_CLIENT_ID')}:{os.getenv('FITBIT_CLIENT_SECRET')}".encode()).decode()


@r.get("/callback")
def callback(request: Request, code: str = "", state: str = "", error: str = "", db: Session = Depends(get_db)):
    import httpx
    app_url = f"{_origin(request)}/app"
    p = verify(state)
    if error or not p or p.get("k") != "fb" or now() - int(p.get("t", 0)) > 900:
        return RedirectResponse(f"{app_url}#fitbit=cancelled", status_code=303)
    try:
        with httpx.Client(timeout=20) as c:
            tok = c.post(TOKEN, data={"client_id": os.getenv("FITBIT_CLIENT_ID"), "grant_type": "authorization_code", "code": code, "code_verifier": p["v"], "redirect_uri": _redirect(request)},
                         headers={"Authorization": _basic(), "Content-Type": "application/x-www-form-urlencoded"}).json()
        if not tok.get("access_token"):
            raise RuntimeError(str(tok)[:200])
    except Exception as e:
        print("[fitbit] token failed:", str(e)[:200], flush=True)
        return RedirectResponse(f"{app_url}#fitbit=error", status_code=303)
    for old in db.scalars(select(DeviceLink).where(DeviceLink.household_id == p["h"], DeviceLink.member_id == p["m"], DeviceLink.provider == "fitbit")).all():
        db.delete(old)
    db.add(DeviceLink(household_id=p["h"], member_id=p["m"], provider="fitbit", external_id=tok.get("user_id", ""),
                      blob=_seal({"access": tok["access_token"], "refresh": tok.get("refresh_token", ""), "expires": now() + int(tok.get("expires_in", 28800)), "scope": tok.get("scope", "")})))
    return RedirectResponse(f"{app_url}#fitbit=done&member={p['m']}", status_code=303)


def _token(db: Session, l: DeviceLink) -> str:
    import httpx
    t = _open(l.blob)
    if t["expires"] - 120 > now():
        return t["access"]
    with httpx.Client(timeout=20) as c:
        tok = c.post(TOKEN, data={"grant_type": "refresh_token", "refresh_token": t["refresh"]}, headers={"Authorization": _basic(), "Content-Type": "application/x-www-form-urlencoded"}).json()
    if not tok.get("access_token"):
        raise HTTPException(401, "Fitbit needs to be linked again.")
    l.blob = _seal({"access": tok["access_token"], "refresh": tok.get("refresh_token", t["refresh"]), "expires": now() + int(tok.get("expires_in", 28800)), "scope": tok.get("scope", t.get("scope", ""))})
    return tok["access_token"]


def normalise(steps: dict, sleep: dict, heart: dict, spo2, weight: dict) -> dict:
    """Fitbit's shapes → the HealthSync contract the app already merges."""
    out = {"steps": [], "sleep": [], "heartRate": [], "weight": [], "bloodPressure": [], "glucose": [], "spo2": [], "ecg": []}
    for x in steps.get("activities-steps", []):
        if int(x.get("value") or 0) > 0:
            out["steps"].append({"date": x["dateTime"], "count": int(x["value"])})
    by_day: dict[str, float] = {}
    for s in sleep.get("sleep", []):
        by_day[s.get("dateOfSleep", "")] = by_day.get(s.get("dateOfSleep", ""), 0) + (s.get("minutesAsleep") or 0) / 60
    out["sleep"] = [{"date": d, "hours": round(h, 1)} for d, h in by_day.items() if d and h > 0]
    for x in heart.get("activities-heart", []):
        rhr = (x.get("value") or {}).get("restingHeartRate")
        if rhr:
            out["heartRate"].append({"t": int(time.mktime(time.strptime(x["dateTime"], "%Y-%m-%d"))) * 1000 + 8 * 3600000, "bpm": rhr, "id": "fb-rhr-" + x["dateTime"], "resting": True})
    rows = spo2 if isinstance(spo2, list) else [spo2] if spo2 else []
    for x in rows:
        v = (x.get("value") or {}).get("avg")
        if v:
            out["spo2"].append({"t": int(time.mktime(time.strptime(x["dateTime"], "%Y-%m-%d"))) * 1000 + 7 * 3600000, "pct": v, "id": "fb-spo2-" + x["dateTime"]})
    for x in weight.get("weight", []):
        if x.get("weight"):
            out["weight"].append({"t": int(time.mktime(time.strptime(x["date"] + " " + x.get("time", "08:00:00"), "%Y-%m-%d %H:%M:%S"))) * 1000, "kg": x["weight"], "id": "fb-w-" + str(x.get("logId", x["date"]))})
    return out


class SyncIn(BaseModel):
    member: str = ""
    days: int = 7


@r.post("/sync")
def sync(body: SyncIn, request: Request, db: Session = Depends(get_db), x_dokko_key: str | None = Header(None)):
    import httpx
    h = household(db, x_dokko_key, create=False)
    l = h and db.scalar(select(DeviceLink).where(DeviceLink.household_id == h.id, DeviceLink.member_id == body.member[:32], DeviceLink.provider == "fitbit"))
    if not l:
        raise HTTPException(404, "Fitbit is not linked for this profile.")
    limit(request, f"fbsync:{h.id}", 30, 3600)
    at = _token(db, l)
    days = max(1, min(30, body.days))
    end, start = date.today(), date.today() - timedelta(days=days)
    hdr = {"Authorization": f"Bearer {at}", "Accept-Language": "en_IN"}
    def get(c, path):
        res = c.get(API + path, headers=hdr)
        if res.status_code == 401:
            raise HTTPException(401, "Fitbit needs to be linked again.")
        return res.json() if res.status_code < 400 else {}
    with httpx.Client(timeout=25) as c:
        steps = get(c, f"/1/user/-/activities/steps/date/{start}/{end}.json")
        sleep = get(c, f"/1.2/user/-/sleep/date/{start}/{end}.json")
        heart = get(c, f"/1/user/-/activities/heart/date/{start}/{end}.json")
        spo2 = get(c, f"/1/user/-/spo2/date/{start}/{end}.json")
        weight = get(c, f"/1/user/-/body/log/weight/date/{start}/{end}.json")
    l.last_sync = now()
    return {"ok": True, "provider": "fitbit", "data": normalise(steps, sleep, heart, spo2, weight), "lastSync": l.last_sync}


@r.delete("/{member}")
def unlink(member: str, db: Session = Depends(get_db), x_dokko_key: str | None = Header(None)):
    h = household(db, x_dokko_key, create=False)
    l = h and db.scalar(select(DeviceLink).where(DeviceLink.household_id == h.id, DeviceLink.member_id == member[:32], DeviceLink.provider == "fitbit"))
    if not l:
        raise HTTPException(404)
    try:
        import httpx
        t = _open(l.blob)
        with httpx.Client(timeout=10) as c:
            c.post(f"{API}/oauth2/revoke", data={"token": t.get("access", "")}, headers={"Authorization": _basic()})
    except Exception:
        pass
    db.delete(l)
    return {"ok": True}

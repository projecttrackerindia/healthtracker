"""Watch and smart-device clouds → Urban Health (/api/v1/wear/<provider>): Withings and Oura, beside Fitbit.

Where a watch's readings can come from, and which route this app uses:

  * Any watch whose phone app writes to Health Connect (Android) or Apple Health (iPhone) — Samsung, Pixel, Garmin,
    Amazfit/Zepp, Mi/Xiaomi, Noise, boAt, Fire-Boltt, Huawei, Withings, Oura … → the phone app's HealthSync plugin.
    This is the main road: it covers almost every watch sold in India with no account linking at all.
  * Fitbit → api/fitbit.py (Fitbit Web API, OAuth).
  * Withings (ScanWatch, BPM Connect, Body scales, Sleep Analyzer) → this module. The Withings API also serves the
    watch's ECG recordings with their AFib classification, so a ScanWatch ECG lands in records like an Apple Watch one.
  * Oura (ring) → this module. Steps, sleep, resting/continuous heart rate, SpO₂.
  * Bluetooth LE devices with the standard health profiles (BP monitors, oximeters, scales, thermometers, HR straps)
    and the Polar H10 ECG stream → the web app directly (Web Bluetooth in Chrome; the native plugin in the phone app).
  * Google Fit's REST API was retired in 2025 (Health Connect replaced it); Garmin Health API and Samsung Health
    need partner approval and are not public; Apple exposes nothing outside the phone.

Tokens are sealed with the data key per family profile (same DeviceLink table as Fitbit). Each provider needs a
developer app: Withings at developer.withings.com (callback <origin>/api/v1/wear/withings/callback) → WITHINGS_CLIENT_ID /
WITHINGS_CLIENT_SECRET; Oura at cloud.ouraring.com/oauth/applications (callback <origin>/api/v1/wear/oura/callback) →
OURA_CLIENT_ID / OURA_CLIENT_SECRET. A provider without keys shows as "coming" in the app and refuses to start.
"""
from __future__ import annotations

import os
import time
from datetime import date, datetime, timedelta, timezone
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from .auth import limit
from .db import get_db
from .fitbit import _open, _origin, _seal, link_json
from .models import DeviceLink, now
from .routes import household
from .security import sign, verify

r = APIRouter(prefix="/api/v1/wear")

PROVIDERS = {
    "withings": {"label": "Withings", "env": "WITHINGS", "auth": "https://account.withings.com/oauth2_user/authorize2",
                 "token": "https://wbsapi.withings.net/v2/oauth2", "scope": "user.metrics,user.activity",
                 "about": "ScanWatch, BPM Connect blood-pressure monitors, Body scales and the Sleep Analyzer — steps, sleep, heart rate, SpO₂, weight, blood pressure, and the watch's ECG recordings with their rhythm classification."},
    "oura": {"label": "Oura", "env": "OURA", "auth": "https://cloud.ouraring.com/oauth/authorize",
             "token": "https://api.ouraring.com/oauth/token", "scope": "personal daily heartrate spo2",
             "about": "Oura ring — steps, sleep, resting and night-time heart rate, SpO₂."},
}
EMPTY = {"steps": [], "sleep": [], "heartRate": [], "weight": [], "bloodPressure": [], "glucose": [], "spo2": [], "ecg": []}


def _cfg(p: str) -> dict:
    c = PROVIDERS.get(p)
    if not c:
        raise HTTPException(404, "Unknown provider")
    return c


def _id(p: str) -> str:
    return os.getenv(f"{PROVIDERS[p]['env']}_CLIENT_ID", "")


def _secret(p: str) -> str:
    return os.getenv(f"{PROVIDERS[p]['env']}_CLIENT_SECRET", "")


def enabled(p: str) -> bool:
    return bool(_id(p) and _secret(p))


def _redirect(request: Request, p: str) -> str:
    return os.getenv(f"{PROVIDERS[p]['env']}_REDIRECT") or f"{_origin(request)}/api/v1/wear/{p}/callback"


def _link(db: Session, h, member: str, p: str) -> DeviceLink | None:
    return h and db.scalar(select(DeviceLink).where(DeviceLink.household_id == h.id, DeviceLink.member_id == member[:32], DeviceLink.provider == p))


# ---------------------------------------------------------------- OAuth
@r.get("/status")
def status(db: Session = Depends(get_db), x_dokko_key: str | None = Header(None)):
    h = household(db, x_dokko_key, create=False)
    links = db.scalars(select(DeviceLink).where(DeviceLink.household_id == h.id, DeviceLink.provider.in_(list(PROVIDERS)))).all() if h else []
    return {"providers": [{"id": p, "label": c["label"], "about": c["about"], "enabled": enabled(p)} for p, c in PROVIDERS.items()],
            "links": [link_json(l) for l in links]}


@r.post("/{p}/start")
def start(p: str, request: Request, member: str = "", db: Session = Depends(get_db), x_dokko_key: str | None = Header(None)):
    c = _cfg(p)
    if not enabled(p):
        raise HTTPException(503, f"{c['label']} linking is not switched on yet.")
    h = household(db, x_dokko_key)
    if not h:
        raise HTTPException(400, "missing household key")
    limit(request, f"wear:{p}:{h.id}", 10, 3600)
    state = sign({"k": "wear", "p": p, "h": h.id, "m": member[:32], "t": now()})
    q = {"response_type": "code", "client_id": _id(p), "scope": c["scope"], "state": state, "redirect_uri": _redirect(request, p)}
    return {"url": f"{c['auth']}?{urlencode(q)}"}


def _exchange(p: str, data: dict) -> dict:
    """Code or refresh-token exchange. Withings wraps its answer in {status, body} and wants an `action` field."""
    import httpx
    c = PROVIDERS[p]
    form = {"client_id": _id(p), "client_secret": _secret(p), **data}
    if p == "withings":
        form["action"] = "requesttoken"
    with httpx.Client(timeout=20) as cl:
        j = cl.post(c["token"], data=form, headers={"Content-Type": "application/x-www-form-urlencoded"}).json()
    if p == "withings":
        if j.get("status") != 0:
            raise RuntimeError(str(j)[:200])
        j = j.get("body") or {}
    if not j.get("access_token"):
        raise RuntimeError(str(j)[:200])
    return j


@r.get("/{p}/callback")
def callback(p: str, request: Request, code: str = "", state: str = "", error: str = "", db: Session = Depends(get_db)):
    _cfg(p)
    app_url = f"{_origin(request)}/app"
    s = verify(state)
    if error or not s or s.get("k") != "wear" or s.get("p") != p or now() - int(s.get("t", 0)) > 900:
        return RedirectResponse(f"{app_url}#wear={p}:cancelled", status_code=303)
    try:
        tok = _exchange(p, {"grant_type": "authorization_code", "code": code, "redirect_uri": _redirect(request, p)})
    except Exception as e:
        print(f"[wear:{p}] token failed:", str(e)[:200], flush=True)
        return RedirectResponse(f"{app_url}#wear={p}:error", status_code=303)
    for old in db.scalars(select(DeviceLink).where(DeviceLink.household_id == s["h"], DeviceLink.member_id == s["m"], DeviceLink.provider == p)).all():
        db.delete(old)
    db.add(DeviceLink(household_id=s["h"], member_id=s["m"], provider=p, external_id=str(tok.get("userid") or tok.get("user_id") or "")[:64],
                      blob=_seal({"access": tok["access_token"], "refresh": tok.get("refresh_token", ""), "expires": now() + int(tok.get("expires_in", 3600)), "scope": tok.get("scope", "")})))
    return RedirectResponse(f"{app_url}#wear={p}:done&member={s['m']}", status_code=303)


def _token(db: Session, l: DeviceLink) -> str:
    t = _open(l.blob)
    if t["expires"] - 120 > now():
        return t["access"]
    try:
        tok = _exchange(l.provider, {"grant_type": "refresh_token", "refresh_token": t["refresh"]})
    except Exception:
        raise HTTPException(401, f"{PROVIDERS[l.provider]['label']} needs to be linked again.")
    l.blob = _seal({"access": tok["access_token"], "refresh": tok.get("refresh_token", t["refresh"]), "expires": now() + int(tok.get("expires_in", 3600)), "scope": tok.get("scope", t.get("scope", ""))})
    return tok["access_token"]


# ---------------------------------------------------------------- normalisers (pure; unit-tested)
def _day_ms(d: str, hour: int) -> int:
    return int(time.mktime(time.strptime(d, "%Y-%m-%d"))) * 1000 + hour * 3600000


def normalise_withings(meas: dict, activity: dict, sleep: dict, ecgs: list[dict]) -> dict:
    """Withings shapes → the HealthSync contract. Measure types: 1 weight kg, 9 diastolic, 10 systolic, 11 pulse, 54 SpO₂, 71 body temp."""
    out = {k: list(v) for k, v in EMPTY.items()}
    for g in (meas.get("measuregrps") or []):
        t = int(g.get("date") or 0) * 1000
        gid = str(g.get("grpid") or t)
        vals: dict[int, float] = {}
        for m in g.get("measures") or []:
            try:
                vals[int(m["type"])] = float(m["value"]) * (10 ** int(m.get("unit", 0)))
            except (KeyError, TypeError, ValueError):
                continue
        if vals.get(1):
            out["weight"].append({"t": t, "kg": round(vals[1], 1), "id": "wi-w-" + gid})
        if vals.get(10) and vals.get(9):
            out["bloodPressure"].append({"t": t, "sys": round(vals[10]), "dia": round(vals[9]), "id": "wi-bp-" + gid})
        if vals.get(11):
            out["heartRate"].append({"t": t, "bpm": round(vals[11]), "id": "wi-hr-" + gid})
        if vals.get(54):
            out["spo2"].append({"t": t, "pct": round(vals[54]), "id": "wi-spo2-" + gid})
    for a in (activity.get("activities") or []):
        if a.get("date") and int(a.get("steps") or 0) > 0:
            out["steps"].append({"date": a["date"], "count": int(a["steps"])})
    for s in (sleep.get("series") or []):
        secs = ((s.get("data") or {}).get("total_sleep_time")) or 0
        if s.get("date") and secs > 0:
            out["sleep"].append({"date": s["date"], "hours": round(secs / 3600, 1)})
    cls = {0: "sinus_rhythm", 1: "atrial_fibrillation", 2: "inconclusive"}
    for e in ecgs:
        if e.get("samples"):
            out["ecg"].append({"id": "wi-ecg-" + str(e.get("signalid")), "t": int(e.get("timestamp") or 0) * 1000, "fs": int(e.get("fs") or 300), "samples": e["samples"],
                               "avgHr": e.get("heart_rate") or 0, "classification": cls.get(e.get("afib"), "")})
    return out


def normalise_oura(activity: dict, sleep: dict, heart: dict, spo2: dict) -> dict:
    out = {k: list(v) for k, v in EMPTY.items()}
    for a in (activity.get("data") or []):
        if a.get("day") and int(a.get("steps") or 0) > 0:
            out["steps"].append({"date": a["day"], "count": int(a["steps"])})
    by_day: dict[str, float] = {}
    for s in (sleep.get("data") or []):
        if s.get("day") and (s.get("total_sleep_duration") or 0) > 0:
            by_day[s["day"]] = by_day.get(s["day"], 0) + s["total_sleep_duration"] / 3600
        if s.get("day") and s.get("lowest_heart_rate"):
            out["heartRate"].append({"t": _day_ms(s["day"], 7), "bpm": int(s["lowest_heart_rate"]), "id": "ou-rhr-" + s["day"], "resting": True})
    out["sleep"] = [{"date": d, "hours": round(h, 1)} for d, h in sorted(by_day.items())]
    last = 0
    for x in sorted((heart.get("data") or []), key=lambda z: z.get("timestamp", "")):
        if x.get("source") not in ("rest", "awake", "sleep") or not x.get("bpm"):
            continue
        try:
            t = int(datetime.fromisoformat(x["timestamp"].replace("Z", "+00:00")).timestamp() * 1000)
        except (ValueError, AttributeError):
            continue
        if t - last < 1800_000:        # one sample per half hour is plenty for a chart; Oura sends one every 5 minutes
            continue
        last = t
        out["heartRate"].append({"t": t, "bpm": int(x["bpm"]), "id": "ou-hr-" + str(t // 1000)})
    for s in (spo2.get("data") or []):
        avg = ((s.get("spo2_percentage") or {}).get("average"))
        if s.get("day") and avg:
            out["spo2"].append({"t": _day_ms(s["day"], 7), "pct": round(avg), "id": "ou-spo2-" + s["day"]})
    return out


# ---------------------------------------------------------------- sync
class SyncIn(BaseModel):
    member: str = ""
    days: int = 7


def _withings(at: str, days: int) -> dict:
    import httpx
    hdr = {"Authorization": f"Bearer {at}"}
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=days)
    ymd = lambda d: d.strftime("%Y-%m-%d")  # noqa: E731

    def post(c, url, **form):
        res = c.post(url, data=form, headers=hdr)
        if res.status_code == 401:
            raise HTTPException(401, "Withings needs to be linked again.")
        j = res.json() if res.status_code < 400 else {}
        if j.get("status") in (401, 2555):   # invalid token / token expired
            raise HTTPException(401, "Withings needs to be linked again.")
        return j.get("body") or {}
    with httpx.Client(timeout=25) as c:
        meas = post(c, "https://wbsapi.withings.net/measure", action="getmeas", meastypes="1,9,10,11,54,71", category=1, startdate=int(start.timestamp()), enddate=int(end.timestamp()))
        act = post(c, "https://wbsapi.withings.net/v2/measure", action="getactivity", startdateymd=ymd(start), enddateymd=ymd(end), data_fields="steps,hr_average")
        slp = post(c, "https://wbsapi.withings.net/v2/sleep", action="getsummary", startdateymd=ymd(start), enddateymd=ymd(end), data_fields="total_sleep_time")
        ecgs: list[dict] = []
        try:
            lst = post(c, "https://wbsapi.withings.net/v2/heart", action="list", startdate=int(start.timestamp()), enddate=int(end.timestamp()))
            for s in (lst.get("series") or [])[:10]:
                sid = (s.get("ecg") or {}).get("signalid")
                if not sid:
                    continue
                sig = post(c, "https://wbsapi.withings.net/v2/heart", action="get", signalid=sid)
                if sig.get("signal"):
                    ecgs.append({"signalid": sid, "timestamp": s.get("timestamp"), "heart_rate": s.get("heart_rate"), "afib": (s.get("ecg") or {}).get("afib"),
                                 "fs": sig.get("sampling_frequency") or 300, "samples": sig["signal"]})
        except HTTPException:
            raise
        except Exception:
            pass
    return normalise_withings(meas, act, slp, ecgs)


def _oura(at: str, days: int) -> dict:
    import httpx
    hdr = {"Authorization": f"Bearer {at}"}
    end, start = date.today(), date.today() - timedelta(days=days)

    def get(c, path, **q):
        res = c.get("https://api.ouraring.com/v2/usercollection" + path, params=q, headers=hdr)
        if res.status_code == 401:
            raise HTTPException(401, "Oura needs to be linked again.")
        return res.json() if res.status_code < 400 else {}
    with httpx.Client(timeout=25) as c:
        act = get(c, "/daily_activity", start_date=str(start), end_date=str(end))
        slp = get(c, "/sleep", start_date=str(start), end_date=str(end))
        hr = get(c, "/heartrate", start_datetime=f"{start}T00:00:00+05:30", end_datetime=f"{end}T23:59:59+05:30")
        spo2 = get(c, "/daily_spo2", start_date=str(start), end_date=str(end))
    return normalise_oura(act, slp, hr, spo2)


@r.post("/{p}/sync")
def sync(p: str, body: SyncIn, request: Request, db: Session = Depends(get_db), x_dokko_key: str | None = Header(None)):
    c = _cfg(p)
    h = household(db, x_dokko_key, create=False)
    l = _link(db, h, body.member, p)
    if not l:
        raise HTTPException(404, f"{c['label']} is not linked for this profile.")
    limit(request, f"wearsync:{p}:{h.id}", 30, 3600)
    at = _token(db, l)
    days = max(1, min(30, body.days))
    data = _withings(at, days) if p == "withings" else _oura(at, days)
    l.last_sync = now()
    return {"ok": True, "provider": p, "data": data, "lastSync": l.last_sync}


@r.delete("/{p}/{member}")
def unlink(p: str, member: str, db: Session = Depends(get_db), x_dokko_key: str | None = Header(None)):
    _cfg(p)
    h = household(db, x_dokko_key, create=False)
    l = _link(db, h, member, p)
    if not l:
        raise HTTPException(404)
    db.delete(l)
    return {"ok": True}

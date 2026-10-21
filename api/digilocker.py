"""Identity from Aadhaar through DigiLocker (/api/v1/digilocker).

There is no public "Aadhaar login" an app may redirect to: UIDAI's OTP and e-KYC APIs are only for licensed AUA/KUA
entities. DigiLocker (MeitY) is the sanctioned route for everyone else — the person signs in to DigiLocker (which itself
uses Aadhaar OTP), consents, and we receive the Aadhaar e-KYC XML: name as on Aadhaar, date of birth, gender, address,
photo and the masked number. We keep only what the Aadhaar rules allow: the masked number (last 4), the demographic
fields and the photo, sealed in the family's encrypted document store, and we lock the account name to the Aadhaar
name. The mobile number is not part of e-KYC, so mobile verification stays our own OTP.

Switched on by DIGILOCKER_CLIENT_ID + DIGILOCKER_CLIENT_SECRET (register at partners.digilocker.gov.in; redirect URI
<origin>/api/v1/digilocker/callback). OAuth 2.0 authorization code with PKCE, per DigiLocker's Requester API v1.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import secrets
import time
import xml.etree.ElementTree as ET
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from . import storage
from .auth import limit, need_user
from .db import get_db
from .models import User, now
from .security import sign, verify

r = APIRouter(prefix="/api/v1/digilocker")
BASE = os.getenv("DIGILOCKER_BASE", "https://api.digitallocker.gov.in/public/oauth2")
FILE_ID = "aadhaar_{member}"


def enabled() -> bool:
    return bool(os.getenv("DIGILOCKER_CLIENT_ID") and os.getenv("DIGILOCKER_CLIENT_SECRET"))


def _origin(request: Request) -> str:
    o = (os.getenv("APP_ORIGIN") or "").split(",")[0].strip()
    if o:
        return o.rstrip("/")
    proto = request.headers.get("x-forwarded-proto", request.url.scheme)
    return f"{proto}://{request.headers.get('x-forwarded-host') or request.headers.get('host')}"


def _redirect(request: Request) -> str:
    return os.getenv("DIGILOCKER_REDIRECT") or f"{_origin(request)}/api/v1/digilocker/callback"


@r.get("/status")
def status():
    return {"enabled": enabled(), "provider": "DigiLocker (MeitY) · Aadhaar e-KYC",
            "message": "" if enabled() else "Aadhaar verification through DigiLocker opens once Urban Health's DigiLocker partner registration is approved. Until then, enter your name exactly as on Aadhaar."}


@r.post("/start")
def start(request: Request, member: str = "", db: Session = Depends(get_db), u: User = Depends(need_user)):
    """Returns the DigiLocker sign-in URL. The state is signed and carries the sealed PKCE verifier, so no server memory is needed."""
    if not enabled():
        raise HTTPException(503, "DigiLocker verification is not switched on yet.")
    limit(request, f"dl:{u.id}", 10, 3600)
    verifier = secrets.token_urlsafe(48)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    state = sign({"k": "dl", "u": u.id, "h": u.household_id or "", "m": (member or u.member_id or "")[:32], "v": verifier, "t": now()})
    q = {"response_type": "code", "client_id": os.getenv("DIGILOCKER_CLIENT_ID"), "redirect_uri": _redirect(request), "state": state, "code_challenge": challenge, "code_challenge_method": "S256"}
    return {"url": f"{BASE}/1/authorize?{urlencode(q)}"}


def _parse_ekyc(xml: bytes) -> dict:
    root = ET.fromstring(xml)
    def find(tag):
        for el in root.iter():
            if el.tag.split('}')[-1] == tag:
                return el
        return None
    uid = find("UidData")
    poi, poa, pht = find("Poi"), find("Poa"), find("Pht")
    masked = (uid.get("uid") if uid is not None else "") or ""
    addr = " ".join(x for x in [poa.get(k, "") for k in ("house", "street", "lm", "loc", "vtc", "subdist", "dist", "state", "pc")] if x) if poa is not None else ""
    return {"name": poi.get("name", "") if poi is not None else "", "dob": poi.get("dob", "") if poi is not None else "", "gender": poi.get("gender", "") if poi is not None else "",
            "last4": masked[-4:] if masked else "", "address": addr, "photo": (pht.text or "").strip() if pht is not None else ""}


@r.get("/callback")
def callback(request: Request, code: str = "", state: str = "", error: str = "", db: Session = Depends(get_db)):
    import httpx

    app_url = f"{_origin(request)}/app"
    p = verify(state)
    if error or not p or p.get("k") != "dl" or now() - int(p.get("t", 0)) > 900:
        return RedirectResponse(f"{app_url}#digilocker=cancelled", status_code=303)
    u = db.get(User, p["u"])
    if not u or (p["h"] and u.household_id != p["h"]):
        return RedirectResponse(f"{app_url}#digilocker=error", status_code=303)
    try:
        with httpx.Client(timeout=25) as c:
            tok = c.post(f"{BASE}/1/token", data={"grant_type": "authorization_code", "code": code, "client_id": os.getenv("DIGILOCKER_CLIENT_ID"), "client_secret": os.getenv("DIGILOCKER_CLIENT_SECRET"),
                                                   "redirect_uri": _redirect(request), "code_verifier": p["v"]}).json()
            at = tok.get("access_token")
            if not at:
                raise RuntimeError(f"token: {str(tok)[:200]}")
            if str(tok.get("eaadhaar", "Y")).upper() == "N":
                return RedirectResponse(f"{app_url}#digilocker=noaadhaar", status_code=303)
            x = c.get(f"{BASE}/3/xml/eaadhaar", headers={"Authorization": f"Bearer {at}"})
            if x.status_code >= 400:
                raise RuntimeError(f"eaadhaar {x.status_code}")
            kyc = _parse_ekyc(x.content)
    except Exception as e:
        print("[digilocker] failed:", type(e).__name__, str(e)[:200], flush=True)
        return RedirectResponse(f"{app_url}#digilocker=error", status_code=303)
    if not kyc["name"]:
        return RedirectResponse(f"{app_url}#digilocker=error", status_code=303)
    member = p.get("m") or u.member_id or "me"
    payload = {**kyc, "digilockerId": tok.get("digilockerid", ""), "verifiedAt": now(), "member": member, "user": u.id}
    if u.household_id:
        try:
            storage.put(db, u.household_id, FILE_ID.format(member=member), json.dumps(payload).encode(), "application/json", f"Aadhaar e-KYC · {kyc['name']}", u.id)
        except Exception as e:
            print("[digilocker] store failed:", str(e)[:200], flush=True)
            return RedirectResponse(f"{app_url}#digilocker=error", status_code=303)
    if member == (u.member_id or "me") or not u.member_id:
        # the account is the person: name and date of birth are Aadhaar's from here on
        u.name, u.aadhaar_verified, u.aadhaar_last4, u.aadhaar_dob = kyc["name"][:80], now(), kyc["last4"], kyc["dob"][:10]
    return RedirectResponse(f"{app_url}#digilocker=done&member={member}", status_code=303)


@r.get("/me")
def me(member: str = "", db: Session = Depends(get_db), u: User = Depends(need_user)):
    """The verified Aadhaar details for a profile (from our sealed store), for the app to show as the Aadhaar card."""
    got = storage.get(db, u.household_id, FILE_ID.format(member=(member or u.member_id or "me")[:32])) if u.household_id else None
    if not got:
        if u.aadhaar_verified:  # verified at sign-up, before the family record existed
            return {"aadhaar": {"name": u.name, "dob": u.aadhaar_dob, "gender": "", "last4": u.aadhaar_last4, "address": "", "verifiedAt": u.aadhaar_verified, "member": u.member_id or "me"}, "photo": ""}
        raise HTTPException(404, "Not verified yet.")
    row, data = got
    j = json.loads(data.decode())
    return {"aadhaar": {k: j.get(k, "") for k in ("name", "dob", "gender", "last4", "address", "verifiedAt", "member")}, "photo": ("data:image/jpeg;base64," + j["photo"]) if j.get("photo") else ""}

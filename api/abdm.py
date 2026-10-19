"""ABHA (Ayushman Bharat Health Account) linking — the ABDM scaffold (/api/v1/abha).

Switched on by ABDM_CLIENT_ID + ABDM_CLIENT_SECRET (sandbox or production; ABDM_ENV=sandbox|production). Without them
every endpoint reports {"enabled": false} and the app shows "ABHA linking is coming" instead of a broken form.

What is implemented against the ABDM v3 APIs:
  • gateway session (client credentials → bearer token, cached until expiry)
  • public certificate fetch + RSA-OAEP encryption of Aadhaar / OTP values, as ABDM requires
  • ABHA by Aadhaar: send OTP → verify OTP (+ mobile) → profile {abhaNumber, abhaAddress, name, gender, dob, mobile}
  • ABHA login by ABHA number / address (OTP) for people who already have one
The verified profile is returned to the app, which stores it as the person's ABHA card (Cards). Nothing from Aadhaar is
stored on our servers; the Aadhaar number is encrypted in memory and sent to ABDM only.
Record sharing (HIU/HIP consent flows) needs an ABDM-empanelled HIP registration and is the next step once this works.
"""
from __future__ import annotations

import base64
import os
import time
import uuid

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .auth import limit
from .db import get_db
from .routes import household

r = APIRouter(prefix="/api/v1/abha")
BASES = {"sandbox": {"gw": "https://dev.abdm.gov.in/gateway", "abha": "https://abhasbx.abdm.gov.in/abha/api/v3"},
         "production": {"gw": "https://live.abdm.gov.in/gateway", "abha": "https://abha.abdm.gov.in/abha/api/v3"}}
_TOKEN = {"t": "", "exp": 0}
_CERT = {"pem": "", "exp": 0}


def enabled() -> bool:
    return bool(os.getenv("ABDM_CLIENT_ID") and os.getenv("ABDM_CLIENT_SECRET"))


def env() -> str:
    return "production" if os.getenv("ABDM_ENV", "sandbox") == "production" else "sandbox"


def _hdr(extra: dict | None = None) -> dict:
    h = {"Content-Type": "application/json", "REQUEST-ID": str(uuid.uuid4()), "TIMESTAMP": time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime()), "X-CM-ID": "sbx" if env() == "sandbox" else "abdm"}
    if extra:
        h.update(extra)
    return h


def _post(url: str, body: dict, headers: dict | None = None, timeout: int = 20) -> dict:
    import httpx

    with httpx.Client(timeout=timeout) as c:
        res = c.post(url, json=body, headers=headers or _hdr())
    if res.status_code >= 400:
        try:
            detail = res.json()
        except Exception:
            detail = res.text[:300]
        raise HTTPException(502, {"abdm": res.status_code, "detail": detail})
    return res.json() if res.content else {}


def token() -> str:
    if _TOKEN["t"] and _TOKEN["exp"] > time.time() + 30:
        return _TOKEN["t"]
    out = _post(f"{BASES[env()]['gw']}/v0.5/sessions", {"clientId": os.getenv("ABDM_CLIENT_ID"), "clientSecret": os.getenv("ABDM_CLIENT_SECRET"), "grantType": "client_credentials"})
    _TOKEN["t"], _TOKEN["exp"] = out.get("accessToken", ""), time.time() + int(out.get("expiresIn", 600))
    if not _TOKEN["t"]:
        raise HTTPException(502, "ABDM did not issue a session token.")
    return _TOKEN["t"]


def public_cert() -> str:
    import httpx

    if _CERT["pem"] and _CERT["exp"] > time.time():
        return _CERT["pem"]
    with httpx.Client(timeout=20) as c:
        res = c.get(f"{BASES[env()]['abha']}/profile/public/certificate", headers=_hdr({"Authorization": f"Bearer {token()}"}))
    if res.status_code >= 400:
        raise HTTPException(502, "ABDM certificate could not be fetched.")
    pem = res.json().get("publicKey", "")
    if "BEGIN" not in pem:
        pem = "-----BEGIN PUBLIC KEY-----\n" + pem + "\n-----END PUBLIC KEY-----"
    _CERT["pem"], _CERT["exp"] = pem, time.time() + 3600
    return pem


def encrypt(value: str) -> str:
    """RSA-OAEP(SHA-1) with ABDM's public key, base64 — what the v3 APIs expect for Aadhaar, mobile and OTP values."""
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding

    key = serialization.load_pem_public_key(public_cert().encode())
    return base64.b64encode(key.encrypt(value.encode(), padding.OAEP(mgf=padding.MGF1(hashes.SHA1()), algorithm=hashes.SHA1(), label=None))).decode()


def _auth_hdr() -> dict:
    return _hdr({"Authorization": f"Bearer {token()}"})


@r.get("/status")
def status():
    return {"enabled": enabled(), "env": env() if enabled() else "", "scope": ["create-by-aadhaar", "login-by-abha"] if enabled() else [],
            "message": "" if enabled() else "ABHA linking opens once TheHealthTracker's ABDM registration is live. Until then, add your ABHA card in Cards by photo."}


class AadhaarIn(BaseModel):
    aadhaar: str


class OtpIn(BaseModel):
    txnId: str
    otp: str
    mobile: str = ""


class AbhaIn(BaseModel):
    abha: str   # 14-digit ABHA number or ABHA address


def _need(db: Session, request: Request, key: str | None):
    if not enabled():
        raise HTTPException(503, "ABHA linking is not switched on yet.")
    h = household(db, key)
    if not h:
        raise HTTPException(400, "missing household key")
    limit(request, f"abha:{h.id}", 12, 3600)
    return h


@r.post("/aadhaar/otp")
def aadhaar_otp(body: AadhaarIn, request: Request, db: Session = Depends(get_db), x_dokko_key: str | None = Header(None)):
    _need(db, request, x_dokko_key)
    a = "".join(ch for ch in body.aadhaar if ch.isdigit())
    if len(a) != 12:
        raise HTTPException(400, "Aadhaar has 12 digits.")
    out = _post(f"{BASES[env()]['abha']}/enrollment/request/otp", {"txnId": "", "scope": ["abha-enrol"], "loginHint": "aadhaar", "loginId": encrypt(a), "otpSystem": "aadhaar"}, _auth_hdr())
    return {"txnId": out.get("txnId", ""), "message": out.get("message", "OTP sent to the mobile linked with Aadhaar.")}


@r.post("/aadhaar/verify")
def aadhaar_verify(body: OtpIn, request: Request, db: Session = Depends(get_db), x_dokko_key: str | None = Header(None)):
    _need(db, request, x_dokko_key)
    if not body.txnId or len(body.otp.strip()) < 4:
        raise HTTPException(400, "Enter the OTP.")
    payload = {"authData": {"authMethods": ["otp"], "otp": {"timeStamp": time.strftime("%Y-%m-%d %H:%M:%S"), "txnId": body.txnId, "otpValue": encrypt(body.otp.strip()),
                                                            "mobile": "".join(ch for ch in body.mobile if ch.isdigit())[-10:]}}, "consent": {"code": "abha-enrollment", "version": "1.4"}}
    out = _post(f"{BASES[env()]['abha']}/enrollment/enrol/byAadhaar", payload, _auth_hdr())
    prof = out.get("ABHAProfile") or out.get("abhaProfile") or {}
    return {"abha": _profile(prof), "new": bool(out.get("isNew")), "message": out.get("message", "")}


@r.post("/login/otp")
def login_otp(body: AbhaIn, request: Request, db: Session = Depends(get_db), x_dokko_key: str | None = Header(None)):
    _need(db, request, x_dokko_key)
    v = body.abha.strip()
    hint = "abha-number" if v.replace("-", "").isdigit() else "abha-address"
    out = _post(f"{BASES[env()]['abha']}/profile/login/request/otp", {"scope": ["abha-login", "aadhaar-verify"], "loginHint": hint, "loginId": encrypt(v.replace("-", "")), "otpSystem": "aadhaar"}, _auth_hdr())
    return {"txnId": out.get("txnId", ""), "message": out.get("message", "OTP sent.")}


@r.post("/login/verify")
def login_verify(body: OtpIn, request: Request, db: Session = Depends(get_db), x_dokko_key: str | None = Header(None)):
    _need(db, request, x_dokko_key)
    out = _post(f"{BASES[env()]['abha']}/profile/login/verify", {"scope": ["abha-login", "aadhaar-verify"], "authData": {"authMethods": ["otp"], "otp": {"txnId": body.txnId, "otpValue": encrypt(body.otp.strip())}}}, _auth_hdr())
    tok = out.get("token", "")
    prof = {}
    if tok:
        import httpx

        with httpx.Client(timeout=20) as c:
            res = c.get(f"{BASES[env()]['abha']}/profile/account", headers=_hdr({"Authorization": f"Bearer {token()}", "X-Token": f"Bearer {tok}"}))
        if res.status_code < 400:
            prof = res.json()
    return {"abha": _profile(prof), "message": out.get("message", "")}


def _profile(p: dict) -> dict:
    name = p.get("name") or " ".join(x for x in (p.get("firstName"), p.get("middleName"), p.get("lastName")) if x)
    return {"abhaNumber": p.get("ABHANumber") or p.get("abhaNumber") or p.get("healthIdNumber") or "", "abhaAddress": (p.get("phrAddress") or [p.get("preferredAbhaAddress") or p.get("healthId") or ""])[0] if isinstance(p.get("phrAddress"), list) else (p.get("preferredAbhaAddress") or p.get("abhaAddress") or ""),
            "name": name or "", "gender": p.get("gender", ""), "dob": p.get("dob") or (f"{p.get('yearOfBirth', '')}-{str(p.get('monthOfBirth', '')).zfill(2)}-{str(p.get('dayOfBirth', '')).zfill(2)}" if p.get("yearOfBirth") else ""),
            "mobile": p.get("mobile", ""), "state": p.get("stateName", ""), "district": p.get("districtName", ""), "photo": p.get("photo") or p.get("profilePhoto") or ""}

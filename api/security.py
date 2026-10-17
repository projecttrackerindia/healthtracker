"""Password hashing (PBKDF2, stdlib only), signed admin session cookies and the household key header."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import time

SECRET = os.getenv("SECRET_KEY") or secrets.token_hex(32)  # set SECRET_KEY on Railway so logins survive restarts
SESSION_HOURS = 12


def hash_pw(pw: str) -> str:
    salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", pw.encode(), salt, 200_000)
    return "pbkdf2$" + base64.b64encode(salt).decode() + "$" + base64.b64encode(dk).decode()


def check_pw(pw: str, stored: str) -> bool:
    try:
        _, s, d = stored.split("$")
        salt, dk = base64.b64decode(s), base64.b64decode(d)
    except Exception:
        return False
    return hmac.compare_digest(hashlib.pbkdf2_hmac("sha256", pw.encode(), salt, 200_000), dk)


def _b64(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).decode().rstrip("=")


def _unb64(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def sign(payload: dict, hours: float = SESSION_HOURS) -> str:
    payload = dict(payload, exp=int(time.time() + hours * 3600))
    body = _b64(json.dumps(payload, separators=(",", ":")).encode())
    mac = _b64(hmac.new(SECRET.encode(), body.encode(), hashlib.sha256).digest())
    return body + "." + mac


def verify(token: str | None) -> dict | None:
    if not token or "." not in token:
        return None
    body, mac = token.rsplit(".", 1)
    good = _b64(hmac.new(SECRET.encode(), body.encode(), hashlib.sha256).digest())
    if not hmac.compare_digest(good, mac):
        return None
    try:
        p = json.loads(_unb64(body))
    except Exception:
        return None
    if p.get("exp", 0) < time.time():
        return None
    return p


def valid_key(k: str | None) -> str | None:
    """The app's anonymous household key: 16–64 chars of [A-Za-z0-9_-]."""
    if not k:
        return None
    k = k.strip()
    if 16 <= len(k) <= 64 and all(c.isalnum() or c in "-_" for c in k):
        return k
    return None

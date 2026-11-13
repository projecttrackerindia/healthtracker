"""Authenticator-app codes (RFC 6238 TOTP): the second step for admins, doctors, pharmacists and partner staff.

Works with Google Authenticator, Microsoft Authenticator, 1Password and Apple Passwords. No SMS or email needed, so
the second step cannot be skipped because a provider is down. Secrets are stored encrypted with the app key.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets
import struct
import time
import urllib.parse

ISSUER = "Urban Health"


def new_secret() -> str:
    return base64.b32encode(secrets.token_bytes(20)).decode().rstrip("=")


def _code(secret: str, counter: int) -> str:
    key = base64.b32decode(secret + "=" * (-len(secret) % 8), casefold=True)
    h = hmac.new(key, struct.pack(">Q", counter), hashlib.sha1).digest()
    o = h[-1] & 0x0F
    return f"{(struct.unpack('>I', h[o:o + 4])[0] & 0x7FFFFFFF) % 1_000_000:06d}"


def verify(secret: str, code: str, last_step: int = 0, at: float | None = None) -> int:
    """Return the time step the code matched (to block reuse), or 0. Accepts one step either side for clock drift."""
    code = "".join(ch for ch in str(code or "") if ch.isdigit())
    if not secret or len(code) != 6:
        return 0
    step = int((at or time.time()) // 30)
    for s in (step - 1, step, step + 1):
        if s > last_step and hmac.compare_digest(_code(secret, s), code):
            return s
    return 0


def uri(secret: str, account: str, issuer: str = ISSUER) -> str:
    label = urllib.parse.quote(f"{issuer}:{account}")
    return f"otpauth://totp/{label}?secret={secret}&issuer={urllib.parse.quote(issuer)}&algorithm=SHA1&digits=6&period=30"


# ---- storage: encrypt the secret at rest with the app key -------------------------------------------------------------
def _key() -> bytes:
    return hashlib.sha256(("totp|" + (os.getenv("SECRET_KEY") or os.getenv("SECRET") or "dev")).encode()).digest()


def seal(secret: str) -> str:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    n = secrets.token_bytes(12)
    return base64.urlsafe_b64encode(n + AESGCM(_key()).encrypt(n, secret.encode(), b"totp")).decode()


def unseal(blob: str) -> str:
    if not blob:
        return ""
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    raw = base64.urlsafe_b64decode(blob.encode())
    return AESGCM(_key()).decrypt(raw[:12], raw[12:], b"totp").decode()


def required() -> bool:
    """On by default in production. TOTP_REQUIRED=0 turns it off for local development only."""
    if os.getenv("APP_ENV", "production") == "production":
        return True
    return os.getenv("TOTP_REQUIRED", "0") == "1"


def qr_svg(text: str) -> str:
    """The set-up QR as inline SVG (no image request, nothing leaves the page)."""
    import io
    import qrcode
    import qrcode.image.svg
    img = qrcode.make(text, image_factory=qrcode.image.svg.SvgPathImage, box_size=10, border=2)
    buf = io.BytesIO()
    img.save(buf)
    return buf.getvalue().decode()

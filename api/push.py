"""Web Push without extra dependencies: VAPID (RFC 8292) + aes128gcm message encryption (RFC 8291) on `cryptography`.

Set VAPID_PRIVATE_KEY (base64url raw 32-byte EC P-256 private key) and VAPID_SUBJECT (mailto:...). Generate once with:
    python -c "from api.push import make_keys; print(make_keys())"
The public key is derived from the private key and served to the browser from /api/v1/push/key.
"""
from __future__ import annotations

import base64
import json
import os
import time
import urllib.error
import urllib.request

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF


def b64u(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def ub64(s: str) -> bytes:
    s = s.strip()
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def make_keys() -> dict:
    k = ec.generate_private_key(ec.SECP256R1())
    d = k.private_numbers().private_value.to_bytes(32, "big")
    pub = k.public_key().public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)
    return {"VAPID_PRIVATE_KEY": b64u(d), "public_key": b64u(pub)}


def _priv():
    raw = os.getenv("VAPID_PRIVATE_KEY", "").strip()
    if not raw:
        return None
    return ec.derive_private_key(int.from_bytes(ub64(raw), "big"), ec.SECP256R1())


def ready() -> bool:
    return bool(os.getenv("VAPID_PRIVATE_KEY")) or fcm_ready()


# ---- native Android push through Firebase Cloud Messaging (HTTP v1, service-account JWT; no firebase SDK needed) ----
_FCM: dict = {"token": None, "exp": 0}


def fcm_ready() -> bool:
    return bool(os.getenv("FCM_SERVICE_ACCOUNT_JSON"))


def _fcm_token() -> tuple[str, str]:
    """Returns (access_token, project_id). The service account signs a JWT (RS256) and exchanges it for a one-hour token."""
    sa = json.loads(os.getenv("FCM_SERVICE_ACCOUNT_JSON", "{}"))
    if _FCM["token"] and _FCM["exp"] > time.time() + 60:
        return _FCM["token"], sa["project_id"]
    from cryptography.hazmat.primitives.asymmetric import padding

    key = serialization.load_pem_private_key(sa["private_key"].encode(), password=None)
    now = int(time.time())
    header = b64u(json.dumps({"alg": "RS256", "typ": "JWT"}).encode())
    claims = b64u(json.dumps({"iss": sa["client_email"], "scope": "https://www.googleapis.com/auth/firebase.messaging", "aud": sa["token_uri"], "iat": now, "exp": now + 3600}).encode())
    sig = b64u(key.sign(f"{header}.{claims}".encode(), padding.PKCS1v15(), hashes.SHA256()))
    body = f"grant_type=urn%3Aietf%3Aparams%3Aoauth%3Agrant-type%3Ajwt-bearer&assertion={header}.{claims}.{sig}".encode()
    req = urllib.request.Request(sa["token_uri"], data=body, method="POST", headers={"Content-Type": "application/x-www-form-urlencoded"})
    with urllib.request.urlopen(req, timeout=10) as r:
        j = json.loads(r.read().decode())
    _FCM["token"], _FCM["exp"] = j["access_token"], time.time() + int(j.get("expires_in", 3600))
    return _FCM["token"], sa["project_id"]


def send_fcm(device_token: str, data: dict, ttl: int = 3600) -> tuple[bool, int, str]:
    if not fcm_ready():
        return False, 0, "fcm not configured"
    try:
        tok, project = _fcm_token()
        msg = {"message": {"token": device_token, "notification": {"title": str(data.get("title", ""))[:100], "body": str(data.get("body", ""))[:240]},
                           "data": {k: str(v) for k, v in data.items() if k in ("url", "tag")}, "android": {"ttl": f"{ttl}s", "priority": "high"}}}
        req = urllib.request.Request(f"https://fcm.googleapis.com/v1/projects/{project}/messages:send", data=json.dumps(msg).encode(), method="POST",
                                     headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as r:
            return True, r.status, ""
    except urllib.error.HTTPError as e:
        code = e.code
        body = e.read().decode("utf-8", "ignore")[:200]
        # UNREGISTERED means the app was uninstalled: the caller deletes the subscription like a 410
        return False, 410 if ("UNREGISTERED" in body or code == 404) else code, body
    except Exception as e:
        return False, 0, str(e)[:200]


def public_key() -> str:
    k = _priv()
    if not k:
        return ""
    return b64u(k.public_key().public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint))


def _vapid(endpoint: str) -> str:
    from urllib.parse import urlsplit

    k = _priv()
    u = urlsplit(endpoint)
    header = b64u(json.dumps({"typ": "JWT", "alg": "ES256"}).encode())
    claims = b64u(json.dumps({"aud": f"{u.scheme}://{u.netloc}", "exp": int(time.time()) + 12 * 3600, "sub": os.getenv("VAPID_SUBJECT", "mailto:support@thehealthtracker.com")}).encode())
    signing = f"{header}.{claims}".encode()
    der = k.sign(signing, ec.ECDSA(hashes.SHA256()))
    from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature

    r, s = decode_dss_signature(der)
    sig = b64u(r.to_bytes(32, "big") + s.to_bytes(32, "big"))
    return f"vapid t={header}.{claims}.{sig}, k={public_key()}"


def _encrypt(p256dh: str, auth: str, payload: bytes) -> bytes:
    """RFC 8291 aes128gcm content encoding, single record."""
    ua_pub = ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), ub64(p256dh))
    auth_secret = ub64(auth)
    ephem = ec.generate_private_key(ec.SECP256R1())
    as_pub = ephem.public_key().public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)
    ua_pub_raw = ua_pub.public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)
    shared = ephem.exchange(ec.ECDH(), ua_pub)
    ikm = HKDF(hashes.SHA256(), 32, auth_secret, b"WebPush: info\x00" + ua_pub_raw + as_pub).derive(shared)
    salt = os.urandom(16)
    cek = HKDF(hashes.SHA256(), 16, salt, b"Content-Encoding: aes128gcm\x00").derive(ikm)
    nonce = HKDF(hashes.SHA256(), 12, salt, b"Content-Encoding: nonce\x00").derive(ikm)
    rs = 4096
    body = AESGCM(cek).encrypt(nonce, payload + b"\x02", None)
    header = salt + rs.to_bytes(4, "big") + bytes([len(as_pub)]) + as_pub
    return header + body


def send(sub: dict, data: dict, ttl: int = 3600) -> tuple[bool, int, str]:
    """Returns (ok, status, note). Status 404/410 means the subscription is gone and should be deleted."""
    if not ready():
        return False, 0, "push not configured"
    endpoint = sub["endpoint"]
    if endpoint.startswith("fcm:"):
        return send_fcm(endpoint[4:], data, ttl)
    if not os.getenv("VAPID_PRIVATE_KEY"):
        return False, 0, "web push not configured"
    body = _encrypt(sub["keys"]["p256dh"], sub["keys"]["auth"], json.dumps(data, ensure_ascii=False).encode())
    req = urllib.request.Request(endpoint, data=body, method="POST", headers={
        "Content-Encoding": "aes128gcm", "Content-Type": "application/octet-stream", "TTL": str(ttl), "Urgency": "high",
        "Authorization": _vapid(endpoint), "User-Agent": "TheHealthTracker/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return True, r.status, ""
    except urllib.error.HTTPError as e:
        return False, e.code, e.read().decode("utf-8", "ignore")[:200]
    except Exception as e:
        return False, 0, str(e)[:200]

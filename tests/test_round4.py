"""Documents, share links, push encryption, reminders, client errors."""
import base64
import json
import os
import uuid
from datetime import datetime

os.environ.setdefault("OTP_DEMO", "1")
os.environ.setdefault("PWNED_CHECK", "0")
os.environ["DATABASE_URL"] = "sqlite:///./data/test_r4.db"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import server  # noqa: E402
from api import push as PUSH  # noqa: E402
from api import reminders  # noqa: E402

H = {"x-tht": "1"}
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 200


def client():
    c = TestClient(server.app)
    c.__enter__()
    return c


def signup(c):
    u = uuid.uuid4().hex[:8]
    r = c.post("/api/v1/auth/signup/start", headers=H, json={"name": "Owner " + u, "email": f"{u}@example.com", "phone": "9" + str(uuid.uuid4().int)[-9:].zfill(9), "password": "Zq!8vB#2mLp@9xT", "terms": True})
    r = c.post("/api/v1/auth/signup/verify", headers=H, json={"flow": r.json()["flow"], "code": r.json()["demo"]})
    assert r.status_code == 200, r.text
    c.headers["X-DoKKo-Key"] = uuid.uuid4().hex
    assert c.post("/api/v1/hello", json={"name": "T", "members": 1}).status_code == 200
    return r.json()["user"]


def test_file_roundtrip_share_and_delete():
    c = client(); signup(c)
    r = c.put("/api/v1/files/v_abc", headers={**H, "content-type": "image/png", "x-file-name": "scan.png"}, content=PNG)
    assert r.status_code == 200 and r.json()["size"] == len(PNG)
    g = c.get("/api/v1/files/v_abc")
    assert g.status_code == 200 and g.content == PNG and g.headers["content-type"].startswith("image/png")
    assert c.get("/api/v1/files").json()["files"][0]["name"] == "scan.png"
    assert c.put("/api/v1/files/v_bad", headers={**H, "content-type": "text/plain"}, content=b"hi").status_code == 415
    sh = c.post("/api/v1/share", headers=H, json={"file_id": "v_abc", "label": "Lipid report", "hours": 24})
    assert sh.status_code == 200 and "/d/" in sh.json()["url"]
    tok = sh.json()["token"]
    anon = TestClient(server.app)
    page = anon.get(f"/d/{tok}")
    assert page.status_code == 200 and "Lipid report" in page.text and "noindex" in page.text
    raw = anon.get(f"/d/{tok}?raw=1")
    assert raw.status_code == 200 and raw.content == PNG
    assert c.get("/api/v1/share").json()[0]["views"] == 1
    assert c.delete(f"/api/v1/share/{tok}", headers=H).json()["revoked"] is True
    assert anon.get(f"/d/{tok}").status_code == 404
    assert c.delete("/api/v1/files/v_abc", headers=H).json()["deleted"] is True
    assert c.get("/api/v1/files/v_abc").status_code == 404


def test_files_need_sign_in_and_are_per_household():
    a, b = client(), client()
    signup(a); signup(b)
    a.put("/api/v1/files/v1", headers={**H, "content-type": "image/png"}, content=PNG)
    assert b.get("/api/v1/files/v1").status_code == 404
    assert TestClient(server.app).get("/api/v1/files/v1").status_code == 401


def test_push_encryption_matches_rfc8291_shape(monkeypatch):
    keys = PUSH.make_keys()
    monkeypatch.setenv("VAPID_PRIVATE_KEY", keys["VAPID_PRIVATE_KEY"])
    assert PUSH.public_key() == keys["public_key"]
    # a fake browser subscription: P-256 key pair + 16-byte auth secret, then decrypt what send() would post
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.hazmat.primitives.kdf.hkdf import HKDF
    ua = ec.generate_private_key(ec.SECP256R1())
    ua_pub = ua.public_key().public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)
    auth = os.urandom(16)
    body = PUSH._encrypt(PUSH.b64u(ua_pub), PUSH.b64u(auth), b'{"title":"hi"}')
    salt, rs, idlen = body[:16], int.from_bytes(body[16:20], "big"), body[20]
    as_pub = body[21:21 + idlen]
    shared = ua.exchange(ec.ECDH(), ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), as_pub))
    ikm = HKDF(hashes.SHA256(), 32, auth, b"WebPush: info\x00" + ua_pub + as_pub).derive(shared)
    cek = HKDF(hashes.SHA256(), 16, salt, b"Content-Encoding: aes128gcm\x00").derive(ikm)
    nonce = HKDF(hashes.SHA256(), 12, salt, b"Content-Encoding: nonce\x00").derive(ikm)
    plain = AESGCM(cek).decrypt(nonce, body[21 + idlen:], None)
    assert plain == b'{"title":"hi"}\x02' and rs == 4096
    vap = PUSH._vapid("https://fcm.googleapis.com/fcm/send/abc")
    assert vap.startswith("vapid t=") and ", k=" in vap


def test_push_subscribe_requires_config_and_stores(monkeypatch):
    c = client(); signup(c)
    sub = {"endpoint": "https://example.test/push/" + uuid.uuid4().hex, "keys": {"p256dh": "x", "auth": "y"}}
    assert c.post("/api/v1/push/subscribe", headers=H, json={"subscription": sub}).status_code == 503
    monkeypatch.setenv("VAPID_PRIVATE_KEY", PUSH.make_keys()["VAPID_PRIVATE_KEY"])
    assert c.post("/api/v1/push/subscribe", headers=H, json={"subscription": sub}).json() == {"ok": True}
    assert c.get("/api/v1/push/key").json()["enabled"] is True
    assert c.post("/api/v1/push/unsubscribe", headers=H, json={"subscription": sub}).json()["removed"] == 1


def test_reminder_due_logic():
    state = {"meds": {"m1": [{"id": "a", "n": "Metformin", "when": ["Morning", "Night"]}, {"id": "b", "n": "Vit D", "when": ["Sunday"]}]},
             "taken": {"m1": {"d": "2026-10-18", "s": {"a:1": 1}}}, "rem": {"off": {}}}
    m = {"id": "m1", "name": "Suresh"}
    assert reminders.due_doses(state, m, "Morning", "2026-10-18") == ["Metformin"]
    assert reminders.due_doses(state, m, "Night", "2026-10-18") == []          # ticked
    assert reminders.due_doses(state, m, "Night", "2026-10-19") == ["Metformin"]  # new day
    state["rem"]["off"]["a"] = True
    assert reminders.due_doses(state, m, "Morning", "2026-10-18") == []


def test_reminder_tick_sends_and_dedupes(monkeypatch):
    monkeypatch.setenv("VAPID_PRIVATE_KEY", PUSH.make_keys()["VAPID_PRIVATE_KEY"])
    c = client(); u = signup(c)
    c.put("/api/v1/sync", headers=H, json={"base": 0, "state": {"members": [{"id": "m1", "name": "Owner", "rel": "You"}], "meds": {"m1": [{"id": "a", "n": "Metformin", "when": ["Morning"]}]}, "rem": {"on": True, "times": {"Morning": "08:00"}}}})
    c.post("/api/v1/family/me", headers=H, json={"member_id": "m1"})
    sub = {"endpoint": "https://example.test/push/" + uuid.uuid4().hex, "keys": {"p256dh": "x", "auth": "y"}}
    c.post("/api/v1/push/subscribe", headers=H, json={"subscription": sub})
    sent = []
    monkeypatch.setattr(PUSH, "send", lambda s, d, ttl=3600: (sent.append(d) or (True, 201, "")))
    at = datetime(2026, 10, 18, 8, 5, tzinfo=reminders.IST)
    assert reminders.tick(at) >= 1 and sent[-1]["body"] == "Metformin" and sent[-1]["title"] == "Morning medicines"
    n = len(sent)
    assert reminders.tick(at) == 0 and len(sent) == n                         # same slot, same day: once
    assert reminders.tick(datetime(2026, 10, 18, 9, 10, tzinfo=reminders.IST)) >= 1  # an hour later: missed-dose nudge
    assert sent[-1]["title"].startswith("Still to take")


def test_client_error_dedupes_and_admin_reads():
    c = TestClient(server.app)
    for _ in range(3):
        assert c.post("/api/v1/client-error", json={"message": "TypeError: x is null", "stack": "at a", "page": "dash", "version": "dev"}).json() == {"ok": True}
    assert c.get("/api/v1/settings").json()["env"] in ("production", "staging", "test")


def test_site_assets_still_served_next_to_share_pages():
    c = TestClient(server.app)
    assert c.get("/s/auth.js").status_code == 200 and "THT" in c.get("/s/auth.js").text
    assert c.get("/d/not-a-token").status_code == 404


def test_fcm_subscription_shape_and_send_path(monkeypatch):
    from api import push as PUSH
    monkeypatch.delenv("FCM_SERVICE_ACCOUNT_JSON", raising=False)
    monkeypatch.setenv("VAPID_PRIVATE_KEY", PUSH.make_keys()["VAPID_PRIVATE_KEY"])
    c = client(); signup(c)
    assert c.post("/api/v1/push/subscribe", headers=H, json={"subscription": {"endpoint": "fcm:abc"}}).status_code == 503
    assert PUSH.send({"endpoint": "fcm:abc"}, {"title": "x"})[2] == "fcm not configured"
    monkeypatch.setenv("FCM_SERVICE_ACCOUNT_JSON", '{"project_id":"p","client_email":"e","token_uri":"https://x","private_key":"k"}')
    assert c.post("/api/v1/push/subscribe", headers=H, json={"subscription": {"endpoint": "fcm:abc"}}).json() == {"ok": True}
    monkeypatch.setattr(PUSH, "_fcm_token", lambda: ("tok", "p"))
    sent = {}

    class R:
        status = 200
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def read(self): return b"{}"

    def fake_open(req, timeout=10):
        sent["url"] = req.full_url; sent["body"] = json.loads(req.data); sent["auth"] = req.get_header("Authorization"); return R()
    monkeypatch.setattr(PUSH.urllib.request, "urlopen", fake_open)
    ok, status, _ = PUSH.send({"endpoint": "fcm:abc"}, {"title": "Hi", "body": "there", "url": "/app", "tag": "t"})
    assert ok and sent["url"].endswith("/v1/projects/p/messages:send") and sent["body"]["message"]["token"] == "abc" and sent["auth"] == "Bearer tok"

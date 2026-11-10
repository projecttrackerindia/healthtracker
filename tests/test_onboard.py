import os
os.environ.setdefault("OTP_DEMO", "1")
os.environ.setdefault("PWNED_CHECK", "0")
os.environ.setdefault("DATABASE_URL", "sqlite:///./data/test_onboard.db")
import io
from fastapi.testclient import TestClient
from PIL import Image


def _jpg():
    b = io.BytesIO(); im = Image.new("RGB", (40, 30), (200, 10, 10))
    ex = im.getexif(); ex[0x010F] = "SecretCam"
    im.save(b, "JPEG", exif=ex); return b.getvalue()


def test_admin_mobile_login_and_lab_onboarding(monkeypatch):
    import server
    from api.db import SessionLocal
    from api.models import Admin, Store, PartnerUser
    from api.security import hash_pw
    c = TestClient(server.app).__enter__(); H = {"x-tht": "1"}
    with SessionLocal() as db:
        if not db.query(Admin).filter_by(email="ob@x.in").first():
            db.add(Admin(email="ob@x.in", pw_hash=hash_pw("Passw0rd-long-1"), role="owner"))
        s = Store(kind="lab", name="Test Lab", city="Hyderabad", lat=17.49, lng=78.39, address="Plot 1", pin="500072", phone="+914012345678", owner_email="o@lab.in")
        db.add(s); db.flush(); sid = s.id
        db.add(PartnerUser(store_id=sid, email="o@lab.in", name="Owner", role="owner", pw_hash=hash_pw("Partner-pass-123"), must_change=False))
        db.commit()
    assert c.post("/api/admin/login", json={"email": "ob@x.in", "password": "Passw0rd-long-1"}, headers=H).status_code == 200
    assert c.put("/api/admin/me/phone", json={"phone": "98765 43210", "password": "nope"}, headers=H).status_code == 401
    assert c.put("/api/admin/me/phone", json={"phone": "98765 43210", "password": "Passw0rd-long-1"}, headers=H).json()["phone"] == "+919876543210"
    c.post("/api/admin/logout", headers=H)
    assert c.post("/api/admin/login", json={"email": "9876543210", "password": "Passw0rd-long-1"}, headers=H).status_code == 200
    assert c.post("/api/admin/login", json={"email": "9876543211", "password": "Passw0rd-long-1"}, headers=H).status_code == 401

    b = c.get("/api/admin/onboard?kind=lab&tab=review", headers=H).json()
    assert any(r["id"] == sid for r in b["rows"])
    d = c.get(f"/api/admin/onboard/{sid}", headers=H).json()
    assert d["checks"][1]["done"] is False
    assert c.post(f"/api/admin/onboard/{sid}/state", json={"action": "live"}, headers=H).status_code == 409
    assert c.put(f"/api/admin/onboard/{sid}", json={"gstin": "bad"}, headers=H).status_code == 400

    p = TestClient(server.app)
    assert p.post("/api/partner/login", json={"email": "o@lab.in", "password": "Partner-pass-123"}, headers=H).status_code == 200
    assert p.post("/api/partner/onboarding/location", json={"lat": 17.4901, "lng": 78.3901, "acc": 900}, headers=H).status_code == 400
    r = p.post("/api/partner/onboarding/location", json={"lat": 17.4901, "lng": 78.3901, "acc": 8, "landmark": "Opp. JNTU metro <b>"}, headers=H).json()
    assert r["ok"] and r["moved"] < 50
    for slot in ("front", "reception", "inside", "licence"):
        x = p.post("/api/partner/onboarding/photos", data={"slot": slot, "lat": "17.4901", "lng": "78.3901", "acc": "9"}, files={"file": ("a.jpg", _jpg(), "image/jpeg")}, headers=H)
        assert x.status_code == 200, x.text
    assert p.post("/api/partner/onboarding/photos", data={"slot": "front"}, files={"file": ("a.jpg", b"<script>", "image/jpeg")}, headers=H).status_code == 400
    d = c.get(f"/api/admin/onboard/{sid}", headers=H).json()
    assert d["landmark"] == "Opp. JNTU metro b" and d["checks"][1]["done"]
    pid = d["photos"][0]["id"]
    img = c.get(f"/api/admin/onboard/{sid}/photos/{pid}", headers=H).content
    assert b"SecretCam" not in img and img[:2] == b"\xff\xd8"
    assert TestClient(server.app).get(f"/api/v2/stores/{sid}/photos/{pid}").status_code == 404   # not live yet

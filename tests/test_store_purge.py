import os
os.environ.setdefault("OTP_DEMO", "1")
os.environ.setdefault("PWNED_CHECK", "0")
os.environ.setdefault("DATABASE_URL", "sqlite:///./data/test_purge.db")
from fastapi.testclient import TestClient


def test_purge_only_paused_named_and_moneyless():
    import server
    from api.db import SessionLocal
    from api.models import Admin, Household, LabTest, Order, Payment, PartnerUser, Store
    from api.security import hash_pw
    c = TestClient(server.app).__enter__(); H = {"x-tht": "1"}
    with SessionLocal() as db:
        for e, role in (("pg-own@x.in", "owner"), ("pg-ops@x.in", "ops")):
            if not db.query(Admin).filter_by(email=e).first():
                db.add(Admin(email=e, pw_hash=hash_pw("Passw0rd-long-1"), role=role))
        import secrets; h = Household(name="Purge fam", key=secrets.token_hex(8)); db.add(h); db.flush()
        a = Store(kind="lab", name="QA Test Lab", city="Chennai", lat=13.1, lng=80.29, active=True)
        b = Store(kind="pharmacy", name="Paid Pharmacy", city="Chennai", lat=13.1, lng=80.29, active=False)
        db.add_all([a, b]); db.flush()
        db.add(LabTest(store_id=a.id, code="CBC", name="CBC", price=300))
        db.add(PartnerUser(store_id=a.id, email="t@qa.in", name="T", role="owner", pw_hash=hash_pw("Partner-pass-123")))
        db.add(Order(id="OQA1", household_id=h.id, store_id=a.id, kind="lab"))
        db.add(Order(id="OPD1", household_id=h.id, store_id=b.id))
        db.add(Payment(household_id=h.id, kind="order", ref="OPD1", amount=100, status="confirmed"))
        db.commit(); sa, sb = a.id, b.id
    ops = TestClient(server.app)
    assert ops.post("/api/admin/login", json={"email": "pg-ops@x.in", "password": "Passw0rd-long-1"}, headers=H).status_code == 200
    assert ops.post(f"/api/admin/stores/{sa}/purge", json={"confirm": "QA Test Lab"}, headers=H).status_code == 403
    assert c.post("/api/admin/login", json={"email": "pg-own@x.in", "password": "Passw0rd-long-1"}, headers=H).status_code == 200
    assert c.post(f"/api/admin/stores/{sa}/purge", json={"confirm": "QA Test Lab"}, headers=H).status_code == 409   # still live
    c.delete(f"/api/admin/stores/{sa}", headers=H)
    assert c.post(f"/api/admin/stores/{sa}/purge", json={"confirm": "QA Lab"}, headers=H).status_code == 400
    r = c.post(f"/api/admin/stores/{sa}/purge", json={"confirm": "QA Test Lab"}, headers=H)
    assert r.status_code == 200 and r.json()["orders"] == 1
    assert c.post(f"/api/admin/stores/{sb}/purge", json={"confirm": "Paid Pharmacy"}, headers=H).status_code == 409
    with SessionLocal() as db:
        assert db.get(Store, sa) is None and db.get(Order, "OQA1") is None
        assert not db.query(LabTest).filter_by(store_id=sa).count() and not db.query(PartnerUser).filter_by(store_id=sa).count()
        assert db.get(Store, sb) is not None

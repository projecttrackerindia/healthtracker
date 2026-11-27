"""Blood donor on the You menu: log a donation, pause, choose who can find me, history from hospitals, and the SOS
"Need blood?" ask that goes to a hospital (families never broadcast to donors themselves).
Run: python -m pytest -q tests/test_donor_profile.py"""
import os
import time
import uuid

os.environ.setdefault("OTP_DEMO", "1")
os.environ.setdefault("PWNED_CHECK", "0")
os.environ["DATABASE_URL"] = "sqlite:///./data/test_donor_profile.db"

from fastapi.testclient import TestClient  # noqa: E402

import server  # noqa: E402
from api.db import Base, engine, session  # noqa: E402
from api.models import BloodRequest, Donor, Store  # noqa: E402

Base.metadata.create_all(engine)


def fam():
    c = TestClient(server.app)
    c.__enter__()
    key = "k" + uuid.uuid4().hex + uuid.uuid4().hex[:8]
    c.headers.update({"x-tht": "1", "x-dokko-key": key, "x-forwarded-for": f"10.7.{uuid.uuid4().int % 250}.{uuid.uuid4().int % 250}"})
    m = "p" + uuid.uuid4().hex[:10]
    r = c.put("/api/v1/donor", json={"member": m, "name": "Daddala P", "group": "O+", "phone": "9876500000", "lat": 13.08, "lng": 80.27, "sex": "male", "consent": True})
    assert r.status_code == 200, r.text
    return c, m


def test_log_pause_and_radius():
    c, m = fam()
    d = c.post(f"/api/v1/donor/{m}/log", json={"date": "2026-08-12", "place": "Apollo", "kind": "whole"}).json()
    assert d["lastDonation"] == "2026-08-12" and d["donations"] == 1 and d["history"][0]["by"] == "you"
    assert c.post(f"/api/v1/donor/{m}/log", json={"date": "2026-08-12"}).status_code == 400
    assert c.post(f"/api/v1/donor/{m}/log", json={"date": "2099-01-01"}).status_code == 400
    d = c.post(f"/api/v1/donor/{m}/log", json={"date": "2026-04-03", "place": "Rotary camp"}).json()
    assert d["lastDonation"] == "2026-08-12" and d["donations"] == 2 and [x["d"] for x in d["history"]] == ["2026-04-03", "2026-08-12"]
    d = c.post(f"/api/v1/donor/{m}/settings", json={"pauseDays": 30}).json()
    assert d["pausedUntil"] > time.strftime("%Y-%m-%d")
    assert c.post(f"/api/v1/donor/{m}/settings", json={"pauseDays": 0}).json()["pausedUntil"] == ""
    assert c.post(f"/api/v1/donor/{m}/settings", json={"radiusKm": 30}).json()["radiusKm"] == 30
    assert c.post(f"/api/v1/donor/{m}/settings", json={"radiusKm": 12}).status_code == 400


def test_paused_or_far_donors_are_not_asked():
    from api.blood import notify_donors
    c, m = fam()
    c.post(f"/api/v1/donor/{m}/settings", json={"radiusKm": 5})
    with session() as db:
        st = Store(kind="hospital", name="Far " + m, city="Chennai", lat=13.16, lng=80.27, active=True, verified=True)  # ~9 km
        db.add(st)
        db.flush()
        q = BloodRequest(store_id=st.id, group="O+", component="whole", units=1, urgency="24h", hospital=st.name, lat=st.lat, lng=st.lng, radius_km=25, expires=int(time.time()) + 3600)
        db.add(q)
        db.flush()
        d = db.query(Donor).filter_by(member_id=m).one()
        only = {d.id}
        assert notify_donors(db, q, only) == 0          # 9 km is beyond the donor's 5 km
        d.radius_km = 15
        assert notify_donors(db, q, only) == 1
        d.paused_until = "2999-01-01"
        assert notify_donors(db, q, only) == 0


def test_sos_ask_goes_to_a_verified_hospital():
    c, m = fam()
    with session() as db:
        ok = Store(kind="hospital", name="Apollo " + m, city="Chennai", lat=13.081, lng=80.271, phone="04428290200", active=True, verified=True)
        no = Store(kind="pharmacy", name="Med " + m, city="Chennai", lat=13.08, lng=80.27, active=True, verified=True)
        db.add_all([ok, no])
        db.flush()
        oid, nid = ok.id, no.id
    h = c.get("/api/v1/blood/help?group=A%2B&lat=13.08&lng=80.27").json()
    assert h["givers"] == ["A+", "A-", "O+", "O-"] and any(p["id"] == oid for p in h["places"]) and not any(p["id"] == nid for p in h["places"])
    assert h["donors"] >= 1
    assert c.post("/api/v1/blood/ask", json={"store": nid, "group": "A+"}).status_code == 400
    r = c.post("/api/v1/blood/ask", json={"store": oid, "group": "A+", "patient": "Vadlamudi", "lat": 13.08, "lng": 80.27}).json()
    assert r["ok"] and r["phone"] == "04428290200"

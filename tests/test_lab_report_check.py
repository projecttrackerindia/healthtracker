"""Board 9: a lab report is read on our server, shown with ranges and jumps, then signed and sent.
Run: python -m pytest -q tests/test_lab_report_check.py"""
import io
import os
import uuid

os.environ.setdefault("OTP_DEMO", "1")
os.environ.setdefault("PWNED_CHECK", "0")
os.environ["DATABASE_URL"] = "sqlite:///./data/test_labcheck.db"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

canvas = pytest.importorskip("reportlab.pdfgen.canvas")  # the CI image may not have reportlab

import server  # noqa: E402
from api import storage  # noqa: E402
from api.db import Base, engine, session  # noqa: E402
from api.models import Household, Order, PartnerUser, Store, now  # noqa: E402
from api.security import hash_pw  # noqa: E402

H = {"x-tht": "1"}
PW = "Zq!8vB#2mLp@9xT"
Base.metadata.create_all(engine)


def pdf(lines):
    b = io.BytesIO()
    c = canvas.Canvas(b)
    y = 800
    for line in ["Lucid Labs report", "Dr Priya N, MD Pathology, Reg No TNMC 22814", "Test Result Reference range"] + lines:
        c.drawString(60, y, line)
        y -= 20
    c.save()
    return b.getvalue()


def setup():
    tag = uuid.uuid4().hex[:8]
    with session() as db:
        s = Store(kind="lab", name=f"Lucid {tag}", city="Chennai", lat=13.0, lng=80.2, active=True)
        h = Household(key=uuid.uuid4().hex, name="Ravi's family", city="Chennai")
        db.add_all([s, h])
        db.flush()
        owner = PartnerUser(store_id=s.id, email=f"o{tag}@lab.test", name="Dr Priya N", role="owner", reg_no="TNMC 22814",
                            pw_hash=hash_pw(PW), active=True, must_change=False)
        tech = PartnerUser(store_id=s.id, email=f"t{tag}@lab.test", name="Ravi", role="tech", pw_hash=hash_pw(PW), active=True, must_change=False)
        db.add_all([owner, tech])
        db.flush()
        # two earlier HbA1c reports at this lab for the same person
        for ago, val in ((240, "6.4"), (120, "6.9")):
            o = Order(household_id=h.id, store_id=s.id, kind="lab", status="ready", items=[{"name": "HbA1c"}], total=400,
                      member="Ravi P", member_id="p" + tag, created=now() - ago * 86400)
            db.add(o)
            db.flush()
            storage.put(db, h.id, f"labrep_{o.id}", pdf([f"HbA1c {val} %", "Creatinine 0.9 mg/dL"]), "application/pdf", "r.pdf", "test")
        cur = Order(household_id=h.id, store_id=s.id, kind="lab", status="processing", items=[{"name": "HbA1c"}, {"name": "Creatinine"}],
                    total=600, member="Ravi P", member_id="p" + tag, created=now(), timeline=[{"s": "collected", "t": now() - 3600}])
        db.add(cur)
        db.flush()
        return s.id, owner.email, tech.email, cur.id


def login(email):
    c = TestClient(server.app)
    c.__enter__()
    c.headers.update({**H, "x-forwarded-for": f"10.7.{uuid.uuid4().int % 250}.{uuid.uuid4().int % 250}"})
    assert c.post("/api/partner/login", json={"email": email, "password": PW}).status_code == 200
    return c


def test_report_is_read_with_ranges_jumps_and_history_and_nothing_is_sent():
    sid, owner, tech, oid = setup()
    c = login(owner)
    r = c.post(f"/api/partner/orders/{oid}/report/read", content=pdf(["HbA1c 7.8 %", "Creatinine 0.9 mg/dL"]),
               headers={"content-type": "application/pdf"})
    assert r.status_code == 200, r.text
    j = r.json()
    v = {x["code"]: x for x in j["values"]}
    assert v["hba1c"]["value"] == 7.8 and v["hba1c"]["flag"] == "high" and v["hba1c"]["organ"] == "pancreas"
    assert v["creat"]["flag"] == "normal" and v["creat"]["organ"] == "kidneys"
    assert [x["code"] for x in j["jumps"]] == ["hba1c"] and j["jumps"][0]["from"] == 6.9
    assert [h["value"] for h in j["history"]["hba1c"]] == [6.4, 6.9]
    with session() as db:
        o = db.get(Order, oid)
        assert o.status == "processing" and not any(t.get("s") == "report_uploaded" for t in o.timeline or [])
        assert storage.get(db, o.household_id, f"labrep_{oid}") is None


def test_a_technician_cannot_read_or_rerun_reports():
    sid, owner, tech, oid = setup()
    c = login(tech)
    assert c.post(f"/api/partner/orders/{oid}/report/read", content=pdf(["HbA1c 7.8 %"]), headers={"content-type": "application/pdf"}).status_code == 403
    assert c.post(f"/api/partner/orders/{oid}/rerun", json={"note": "x"}).status_code == 403


def test_an_unreadable_file_says_so():
    sid, owner, tech, oid = setup()
    r = login(owner).post(f"/api/partner/orders/{oid}/report/read", content=b"\x89PNG\r\n\x1a\n" + b"0" * 100, headers={"content-type": "image/png"})
    assert r.status_code == 200 and r.json()["read"] is False and "by eye" in r.json()["why"]


def test_rerun_keeps_the_sample_in_the_lab_and_is_on_the_board():
    sid, owner, tech, oid = setup()
    c = login(owner)
    r = c.post(f"/api/partner/orders/{oid}/rerun", json={"note": "haemolysed"})
    assert r.status_code == 200 and r.json()["status"] == "processing" and r.json()["rerunAt"]
    assert c.get("/api/partner/me").json()["counts"]["reportsDue"] >= 1
    with session() as db:
        o = db.get(Order, oid)
        o.status = "ready"
    assert c.post(f"/api/partner/orders/{oid}/rerun", json={}).status_code == 409


def test_sign_and_send_delivers_and_moves_the_booking_to_report_out():
    sid, owner, tech, oid = setup()
    c = login(owner)
    r = c.put(f"/api/partner/orders/{oid}/report", content=pdf(["HbA1c 7.8 %"]), headers={"content-type": "application/pdf", "x-file-name": "r.pdf"})
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["status"] == "ready" and j["reportAt"] and j["collectedAt"]

"""Partner portal: sign-in, orders through their statuses, prescriptions, lab reports into the family's documents,
visit requests, messages, price lists — and the family's inbox seeing all of it."""
import os
import uuid

os.environ.setdefault("OTP_DEMO", "1")
os.environ.setdefault("PWNED_CHECK", "0")
os.environ["DATABASE_URL"] = "sqlite:///./data/test_r7.db"

from fastapi.testclient import TestClient  # noqa: E402

import server  # noqa: E402
from api import db as DB  # noqa: E402
from api.models import Admin, LabTest, Store, StoreItem  # noqa: E402
from api.security import hash_pw  # noqa: E402

H = {"x-tht": "1"}
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100


def family():
    c = TestClient(server.app)
    c.__enter__()
    u = uuid.uuid4().hex[:8]
    r = c.post("/api/v1/auth/signup/start", headers=H, json={"name": "Owner " + u, "email": f"{u}@example.com", "phone": "9" + str(uuid.uuid4().int)[-9:].zfill(9), "password": "Zq!8vB#2mLp@9xT", "terms": True})
    r = c.post("/api/v1/auth/signup/verify", headers=H, json={"flow": r.json()["flow"], "code": r.json()["demo"]})
    assert r.status_code == 200, r.text
    c.headers["X-DoKKo-Key"] = uuid.uuid4().hex
    assert c.post("/api/v1/hello", json={"name": "Daddala", "members": 2}).status_code == 200
    return c


def admin():
    a = TestClient(server.app)
    email = f"adm{uuid.uuid4().hex[:6]}@example.com"
    with DB.session() as db:
        db.add(Admin(email=email, role="owner", pw_hash=hash_pw("Adm!n-pass-123")))
    assert a.post("/api/admin/login", json={"email": email, "password": "Adm!n-pass-123"}).status_code == 200
    return a


def stores():
    TestClient(server.app).__enter__()   # tables are created on startup
    with DB.session() as db:
        lab = Store(kind="lab", name="Vijaya Diagnostics", city="Hyderabad", area="Madhapur", lat=17.448, lng=78.391, home_collection=True, verified=True, licence="NABL MC-1234")
        ph = Store(kind="pharmacy", name="Apollo Pharmacy", city="Hyderabad", area="Madhapur", lat=17.449, lng=78.392, verified=True)
        hosp = Store(kind="hospital", name="Care Hospital", city="Hyderabad", area="Banjara Hills", lat=17.414, lng=78.435, verified=True, phone="04030418888")
        db.add_all([lab, ph, hosp]); db.flush()
        db.add(LabTest(store_id=lab.id, code="hba1c", name="HbA1c", price=450, tat_hours=24, fasting=False))
        db.add(StoreItem(store_id=ph.id, sku="ator10", name="Atorvastatin 10", price=90, mrp=100, stock=10))
        return lab.id, ph.id, hosp.id


def partner(a, sid):
    r = a.post(f"/api/admin/stores/{sid}/users", json={"email": f"p{uuid.uuid4().hex[:6]}@lab.in", "name": "Front desk", "role": "owner"})
    assert r.status_code == 200, r.text
    p = TestClient(server.app)
    assert p.post("/api/partner/login", json={"email": r.json()["email"], "password": "wrong"}).status_code == 401
    me = p.post("/api/partner/login", json={"email": r.json()["email"], "password": r.json()["tempPassword"]})
    assert me.status_code == 200 and me.json()["user"]["mustChange"] is True
    return p


def test_lab_booking_report_reaches_family():
    lab, ph, hosp = stores()
    f, a = family(), admin()
    p = partner(a, lab)
    assert p.get("/api/partner/me").json()["store"]["kind"] == "lab"
    o = f.post("/api/v1/orders", json={"store": lab, "kind": "lab", "items": [{"code": "hba1c"}], "address": "12 Road", "member": "Prasanna", "memberId": "m1", "slot": "Mon 08:00"}).json()
    lst = p.get("/api/partner/orders").json()["orders"]
    assert lst and lst[0]["id"] == o["id"] and lst[0]["memberId"] == "m1" and lst[0]["next"] == ["confirmed", "cancelled"]
    assert p.post(f"/api/partner/orders/{o['id']}/status", json={"status": "ready"}).status_code == 400          # not before the report, and not out of order
    p.post(f"/api/partner/orders/{o['id']}/status", json={"status": "confirmed"})
    p.post(f"/api/partner/orders/{o['id']}/status", json={"status": "collected"})
    r = p.put(f"/api/partner/orders/{o['id']}/report", headers={"content-type": "application/pdf", "x-file-name": "HbA1c.pdf"}, content=b"%PDF-1.4 report")
    assert r.status_code == 200 and r.json()["status"] == "ready" and r.json()["hasReport"] is True
    inbox = f.get("/api/v1/inbox").json()
    kinds = [n["kind"] for n in inbox["notices"]]
    assert kinds[0] == "lab_result" and "order" in kinds
    ref = inbox["notices"][0]["ref"]
    assert ref["fileId"] == f"labrep_{o['id']}" and ref["tests"] == ["HbA1c"]
    got = f.get(f"/api/v1/files/{ref['fileId']}")                      # the family downloads it like any of their documents
    assert got.status_code == 200 and got.content.startswith(b"%PDF")
    other = family()
    assert other.get(f"/api/v1/files/{ref['fileId']}").status_code == 404
    assert f.get("/api/v1/orders").json()["orders"][0]["status"] == "ready"
    f.post("/api/v1/inbox/read", json={"ids": [inbox["notices"][0]["id"]]})
    assert f.get("/api/v1/inbox").json()["notices"][0]["read"] is True


def test_pharmacy_sees_only_the_shared_prescription():
    lab, ph, hosp = stores()
    f, a = family(), admin()
    p = partner(a, ph)
    f.put("/api/v1/files/v_rx1", headers={**H, "content-type": "image/png", "x-file-name": "rx.png"}, content=PNG)
    f.put("/api/v1/files/v_secret", headers={**H, "content-type": "image/png"}, content=PNG)
    o = f.post("/api/v1/orders", json={"store": ph, "kind": "medicine", "items": [{"sku": "ator10", "qty": 1}], "address": "12 Road, Madhapur", "member": "Prasanna", "rxShared": True, "rxDocs": ["v_rx1"]}).json()
    lst = p.get("/api/partner/orders").json()["orders"][0]
    assert lst["rxFiles"] == ["v_rx1"] and lst["items"][0]["rx"] is True
    assert p.get(f"/api/partner/orders/{o['id']}/rx/v_rx1").status_code == 200
    assert p.get(f"/api/partner/orders/{o['id']}/rx/v_secret").status_code == 404
    for st in ("checking", "packing", "out", "delivered"):
        assert p.post(f"/api/partner/orders/{o['id']}/status", json={"status": st}).status_code == 200, st
    assert p.get("/api/partner/orders").json()["orders"] == [] and p.get("/api/partner/orders?status=closed").json()["orders"][0]["status"] == "delivered"
    assert f.get("/api/v1/orders").json()["orders"][0]["status"] == "delivered"
    titles = [n["title"] for n in f.get("/api/v1/inbox").json()["notices"]]
    assert any("Delivered" in t for t in titles)


def test_visit_request_and_messages():
    lab, ph, hosp = stores()
    f, a = family(), admin()
    p = partner(a, hosp)
    assert f.post("/api/v1/appointments", json={"store": lab, "date": "2026-11-02"}).status_code == 404        # only hospitals take visits
    ap = f.post("/api/v1/appointments", json={"store": hosp, "member": "m1", "memberName": "Prasanna", "date": "2026-11-02", "time": "10:00", "why": "Diabetes review"}).json()
    assert ap["status"] == "requested"
    req = p.get("/api/partner/appointments").json()["appointments"]
    assert req[0]["id"] == ap["id"] and p.get("/api/partner/me").json()["counts"]["pendingAppointments"] == 1
    assert p.post(f"/api/partner/appointments/{ap['id']}", json={"status": "confirmed"}).status_code == 400   # needs a slot
    r = p.post(f"/api/partner/appointments/{ap['id']}", json={"status": "confirmed", "slotDate": "2026-11-02", "slotTime": "10:30", "doctor": "Dr. Rao"})
    assert r.json()["status"] == "confirmed" and r.json()["doctor"] == "Dr. Rao"
    ib = f.get("/api/v1/inbox").json()
    assert ib["appointments"][0]["slotTime"] == "10:30" and ib["notices"][0]["kind"] == "appointment"
    # messages both ways, with a document attached by the family
    f.put("/api/v1/files/v_sum", headers={**H, "content-type": "image/png"}, content=PNG)
    assert f.post("/api/v1/messages", json={"store": hosp, "text": "", "fileId": "v_nope"}).status_code == 400
    f.post("/api/v1/messages", json={"store": hosp, "text": "Here is the last report", "fileId": "v_sum", "name": "Prasanna"})
    th = p.get("/api/partner/threads").json()["threads"]
    assert th and th[0]["unread"] == 1 and th[0]["family"] == "Daddala"
    hid = th[0]["household"]
    assert p.get(f"/api/partner/thread-file/{hid}/v_sum").status_code == 200
    assert p.get(f"/api/partner/thread-file/{hid}/v_rx1").status_code == 404
    p.post(f"/api/partner/threads/{hid}", json={"text": "Thanks, see you at 10:30."})
    fam = f.get(f"/api/v1/messages?store={hosp}").json()
    assert [m["sender"] for m in fam["messages"]] == ["family", "partner"] and f.get("/api/v1/inbox").json()["unreadMessages"] == 0
    assert f.get("/api/v1/messages/threads").json()["threads"][0]["store"]["name"] == "Care Hospital"
    stranger = family()
    assert p.post(f"/api/partner/threads/{uuid.uuid4().hex}", json={"text": "hi"}).status_code == 403


def test_prices_profile_and_password():
    lab, ph, hosp = stores()
    a = admin()
    p = partner(a, lab)
    pr = p.get("/api/partner/prices").json()
    assert pr["kind"] == "lab" and next(t for t in pr["tests"] if t["code"] == "hba1c")["price"] == 450
    r = p.put("/api/partner/prices", json={"tests": [{"code": "hba1c", "price": "", "tat": 24}, {"code": "lipid", "price": 700, "tat": 12}, {"code": "nope", "price": 1}]})
    assert r.json()["changed"] == 2
    pr = {t["code"]: t for t in p.get("/api/partner/prices").json()["tests"]}
    assert pr["hba1c"]["price"] is None and pr["lipid"]["price"] == 700 and pr["lipid"]["tat"] == 12
    s = p.put("/api/partner/profile", json={"phone": "04011112222", "homeCollection": False, "collectionFee": 99999}).json()
    assert s["phone"] == "04011112222" and s["homeCollection"] is False and s["collectionFee"] == 2000
    assert p.post("/api/partner/password", json={"current": "nope", "new": "Long-enough-pass"}).status_code == 400
    q = partner(a, ph)
    items = q.get("/api/partner/prices").json()["items"]
    assert any(i["sku"] == "ator10" and i["price"] == 90 and i["rx"] for i in items)
    assert q.post("/api/partner/logout", json={}).json() == {"ok": True}
    assert q.get("/api/partner/me").status_code == 401
    users = a.get(f"/api/admin/stores/{lab}/users").json()["users"]
    assert users and a.delete(f"/api/admin/stores/{lab}/users/{users[0]['id']}").json() == {"ok": True}
    assert p.get("/api/partner/me").status_code == 401

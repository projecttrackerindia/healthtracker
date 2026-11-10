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
    assert c.put("/api/admin/me/phone", json={"phone": "98765 43210", "password": "nope"}, headers=H).status_code == 403
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


def test_admin_login_errors_lockout_and_reset(capsys):
    import server
    from api import admin_cli
    from api.db import SessionLocal
    from api.models import Admin
    from api.security import hash_pw
    c = TestClient(server.app).__enter__(); H = {"x-tht": "1", "x-forwarded-for": "10.9.9.9"}
    with SessionLocal() as db:
        db.add(Admin(email="lock@x.in", pw_hash=hash_pw("Right-password-99"), role="ops")); db.commit()
    assert c.post("/api/admin/login", json={"email": "", "password": ""}, headers=H).status_code == 400
    assert "10-digit" in c.post("/api/admin/login", json={"email": "12ab", "password": "x"}, headers=H).json()["detail"]
    for i in range(10):
        r = TestClient(server.app).post("/api/admin/login", json={"email": "lock@x.in", "password": "nope"}, headers={"x-tht": "1", "x-forwarded-for": f"10.8.0.{i}"})
        if i == 6:
            assert r.status_code == 401 and "1 attempt left" in r.json()["detail"]
    assert r.status_code == 423
    assert TestClient(server.app).post("/api/admin/login", json={"email": "lock@x.in", "password": "Right-password-99"}, headers={"x-tht": "1", "x-forwarded-for": "10.7.0.1"}).status_code == 423
    with SessionLocal() as db:
        assert db.query(Admin).filter_by(email="lock@x.in").one().locked_until > 0
    assert admin_cli.main(["reset", "lock@x.in"]) == 0
    pw = [l for l in capsys.readouterr().out.splitlines() if l.startswith("Password:")][0].split()[-1]
    with SessionLocal() as db:
        a = db.query(Admin).filter_by(email="lock@x.in").one(); assert a.locked_until == 0 and a.fails == 0


def test_console_today_board_search():
    import server, time
    from api.db import SessionLocal
    from api.models import Admin, Household, Store, Order
    from api.security import hash_pw
    from api.console import late_by
    c = TestClient(server.app).__enter__(); H = {"x-tht": "1", "x-forwarded-for": "10.6.0.1"}
    with SessionLocal() as db:
        db.add(Admin(email="con@x.in", pw_hash=hash_pw("Right-password-99"), role="owner"))
        h = Household(key="kcon1", name="Asha Rao"); s = Store(kind="lab", name="Board Lab", city="Hyd", lat=17.4, lng=78.4, verified=True)
        db.add_all([h, s]); db.flush(); t = int(time.time())
        o = Order(household_id=h.id, store_id=s.id, kind="lab", items=[{"name": "CBC"}], status="en_route", timeline=[{"s": "en_route", "t": t - 3600}], created=t - 4000, member="Asha")
        db.add(o); db.commit(); oid = o.id
        assert late_by(o, t) >= 40
    assert c.post("/api/admin/login", json={"email": "con@x.in", "password": "Right-password-99"}, headers=H).status_code == 200
    d = c.get("/api/admin/console/today", headers=H).json()
    assert any("late" in n["title"] for n in d["needs"]) and d["now"]["late"] >= 1
    b = c.get("/api/admin/console/board", headers=H).json()
    card = [x for x in b["lanes"]["way"] if x["id"] == oid][0]
    assert card["late"] > 0 and card["who"] == "A••••" and "Asha" not in str(card)
    sr = c.get("/api/admin/console/search?q=board", headers=H).json()
    assert sr["groups"][0]["items"][0]["title"] == "Board Lab"
    assert TestClient(server.app).get("/api/admin/console/today").status_code == 401


def test_phase2_rx_approvals_refund_complaints():
    import server, time
    from api.db import SessionLocal
    from api.models import Admin, Household, Store, Order, User
    from api.security import hash_pw
    c1 = TestClient(server.app).__enter__(); c2 = TestClient(server.app)
    H1 = {"x-tht": "1", "x-forwarded-for": "10.5.0.1"}; H2 = {"x-tht": "1", "x-forwarded-for": "10.5.0.2"}
    with SessionLocal() as db:
        db.add_all([Admin(email="p2a@x.in", pw_hash=hash_pw("Right-password-99"), role="owner"), Admin(email="p2b@x.in", pw_hash=hash_pw("Right-password-99"), role="owner")])
        h = Household(key="kp2", name="Kiran S"); s = Store(kind="pharmacy", name="P2 Pharmacy", city="Hyd", lat=17.4, lng=78.4, verified=True)
        db.add_all([h, s]); db.flush()
        rx = Order(household_id=h.id, store_id=s.id, kind="medicine", items=[{"name": "Alprazolam 0.25", "rx": True, "qty": 1}], status="placed", total=120, rx_shared=True, rx_files=["f1"])
        big = Order(household_id=h.id, store_id=s.id, kind="lab", items=[{"name": "Full body"}], status="ready", total=7000)
        small = Order(household_id=h.id, store_id=s.id, kind="lab", items=[{"name": "CBC"}], status="ready", total=300)
        db.add_all([rx, big, small]); db.commit(); rid, bid, sid_, hid = rx.id, big.id, small.id, h.id
    assert c1.post("/api/admin/login", json={"email": "p2a@x.in", "password": "Right-password-99"}, headers=H1).status_code == 200
    assert c2.post("/api/admin/login", json={"email": "p2b@x.in", "password": "Right-password-99"}, headers=H2).status_code == 200
    q = c1.get("/api/admin/rx", headers=H1).json()
    row = [r for r in q["rows"] if r["id"] == rid][0]
    assert row["flag"] and any("Habit-forming" in x["text"] for x in row["checks"])
    old = time.strftime("%Y-%m-%d", time.gmtime(time.time() - 60 * 86400))
    body = {"decision": "approve", "doctor": "Dr A Mehta", "regNo": "TSMC 61204", "rxDate": old, "pharmacist": "S Reddy", "pharmacistReg": "TSPC 22814"}
    assert "30 days" in c1.post(f"/api/admin/rx/{rid}", json=body, headers=H1).json()["detail"]
    body["rxDate"] = time.strftime("%Y-%m-%d")
    assert c1.post(f"/api/admin/rx/{rid}", json=body, headers=H1).status_code == 200
    assert c1.post(f"/api/admin/rx/{rid}", json=body, headers=H1).status_code == 409
    # small refund goes through, big one needs a second admin, asker can't approve
    assert c1.post(f"/api/admin/orders/{sid_}/refund", json={"amount": 300, "reason": "no-show tech"}, headers=H1).json()["ok"]
    r = c1.post(f"/api/admin/orders/{bid}/refund", json={"amount": 7000, "reason": "lab lost sample"}, headers=H1).json()
    ap = r["approval"]
    assert c1.post(f"/api/admin/approvals/{ap}", json={"approve": True}, headers=H1).status_code == 403
    assert c2.post(f"/api/admin/approvals/{ap}", json={"approve": True}, headers=H2).json()["status"] == "approved"
    with SessionLocal() as db:
        assert db.get(Order, bid).status == "refunded"
    # complaint from a family, answered by admin
    with SessionLocal() as db:
        u = User(email="fam2@x.in", household_id=hid, pw_hash="x"); db.add(u); db.commit(); uid = u.id
    import api.auth as A
    orig = A.current_user
    A.current_user = lambda req, db: db.get(User, uid)
    try:
        f = TestClient(server.app)
        assert f.post("/api/v2/complaints", json={"orderId": rid, "kind": "wrong_medicine", "text": "got 1000 instead of 500"}, headers={"x-tht": "1"}).status_code == 200
        assert f.post("/api/v2/complaints", json={"orderId": bid, "kind": "nonsense", "text": "abcdef"}, headers={"x-tht": "1"}).status_code == 400
    finally:
        A.current_user = orig
    cs = c1.get("/api/admin/complaints", headers=H1).json()["rows"]
    cm = [x for x in cs if x["orderId"] == rid][0]
    assert cm["left"] <= 120 and "te" in cm["replies"] and cm["who"].startswith("K")
    assert c1.post(f"/api/admin/complaints/{cm['id']}", json={"text": cm["replies"]["en"], "resolve": True}, headers=H1).json()["status"] == "resolved"
    td = c1.get("/api/admin/console/today", headers=H1).json()
    assert isinstance(td["needs"], list)


def test_phase3_invites_signins_scorecard_quality():
    import server, time
    from api.db import SessionLocal
    from api.models import Admin, Household, Store, Order, PartnerUser
    from api.security import hash_pw
    from api.partners2 import check_report
    c = TestClient(server.app).__enter__(); H = {"x-tht": "1", "x-forwarded-for": "10.4.0.1"}
    with SessionLocal() as db:
        db.add(Admin(email="p3@x.in", pw_hash=hash_pw("Right-password-99"), role="owner"))
        s = Store(kind="lab", name="P3 Lab", city="Hyd", lat=17.4, lng=78.4, verified=True, profile={"pins": "500072 500085"}, pin="500072")
        h = Household(key="kp3", name="Meena V"); db.add_all([s, h]); db.commit(); sid, hid = s.id, h.id
    assert c.post("/api/admin/login", json={"email": "p3@x.in", "password": "Right-password-99"}, headers=H).status_code == 200
    r = c.post(f"/api/admin/stores/{sid}/invite", json={"name": "Ravi Kumar", "phone": "90000 11182", "role": "technician"}, headers=H).json()
    assert r["status"] == "invited" and r["demoLink"].startswith("/partner/join/")
    tok = r["demoLink"].rsplit("/", 1)[1]
    assert c.post(f"/api/admin/stores/{sid}/invite", json={"name": "Dup", "phone": "9000011182", "role": "staff"}, headers=H).status_code == 409
    p = TestClient(server.app)
    assert p.post("/api/partner/login", json={"email": "9000011182", "password": "anything-long-1"}, headers={"x-tht": "1"}).status_code == 401
    assert p.get(f"/api/partner/join/{tok}").json()["store"] == "P3 Lab"
    assert p.post("/api/partner/join", json={"token": tok, "password": "short"}).status_code == 400
    assert p.post("/api/partner/join", json={"token": tok, "password": "Lab-tech-pass-2026"}).status_code == 200
    assert p.post("/api/partner/join", json={"token": tok, "password": "Lab-tech-pass-2026"}).status_code == 404   # once only
    assert p.post("/api/partner/login", json={"email": "9000011182", "password": "Lab-tech-pass-2026"}, headers={"x-tht": "1"}).status_code == 200
    assert p.get("/api/partner/me").status_code == 200
    uid = r["id"]
    assert c.post(f"/api/admin/partner-users/{uid}", json={"action": "signout"}, headers=H).status_code == 200
    assert p.get("/api/partner/me").status_code == 401      # signed out everywhere
    for i in range(10):
        TestClient(server.app).post("/api/partner/login", json={"email": "9000011182", "password": "wrong-pass-123"}, headers={"x-tht": "1", "x-forwarded-for": f"10.3.0.{i}"})
    assert "locked" in TestClient(server.app).post("/api/partner/login", json={"email": "9000011182", "password": "Lab-tech-pass-2026"}, headers={"x-tht": "1", "x-forwarded-for": "10.3.1.1"}).json()["detail"]
    assert c.post(f"/api/admin/partner-users/{uid}", json={"action": "unlock"}, headers=H).json()["status"] == "active"
    # quality: same file for two people is flagged
    with SessionLocal() as db:
        o1 = Order(household_id=hid, store_id=sid, kind="lab", items=[{"name": "CBC"}], status="ready", total=300, addr={"pin": "500049"})
        o2 = Order(household_id=hid, store_id=sid, kind="lab", items=[{"name": "CBC"}], status="ready", total=300, addr={"pin": "500049"})
        db.add_all([o1, o2]); db.flush(); s = db.get(Store, sid)
        assert not [f for f in check_report(db, o1, s, b"%PDF-same", "image/png") if f.kind == "copied"]
        db.flush()
        assert [f for f in check_report(db, o2, s, b"%PDF-same", "image/png") if f.kind == "copied"]
        db.commit()
    q = c.get("/api/admin/quality", headers=H).json()
    assert any(r["kind"] == "copied" for r in q["rows"])
    sc = c.get(f"/api/admin/stores/{sid}/scorecard", headers=H).json()
    assert sc["m"]["corrections"] >= 1 and len(sc["series"]) == 30
    cv = c.get("/api/admin/coverage?kind=lab", headers=H).json()
    assert any(g["pin"] == "500049" for g in cv["gaps"]) and any(x["pin"] == "500072" and x["partners"] == 1 for x in cv["rows"])


def test_phase4_catalogue_public_pages_sitemap():
    import server, io
    from PIL import Image
    from api.db import SessionLocal
    from api.models import Admin, Store, LabTest
    from api.security import hash_pw
    c = TestClient(server.app).__enter__(); H = {"x-tht": "1", "x-forwarded-for": "10.2.0.1"}
    with SessionLocal() as db:
        db.add(Admin(email="p4@x.in", pw_hash=hash_pw("Right-password-99"), role="owner"))
        live = Store(kind="lab", name="Vijaya Diagnostics", area="Kukatpally", city="Hyderabad", lat=17.49, lng=78.39, verified=True, active=True, licence="MC-4512",
                     home_collection=True, landmark="Opp JNTU metro", rating=4.8, rating_n=12, profile={"hoursWeek": "6:30 am–9 pm"})
        hidden = Store(kind="lab", name="Paused Lab", area="Kukatpally", city="Hyderabad", lat=17.4, lng=78.4, verified=True, active=False)
        db.add_all([live, hidden]); db.flush()
        db.add(LabTest(store_id=live.id, code="cbc", name="Complete blood count (CBC)", price=249)); db.commit()
        lid, hid = live.id, hidden.id
    assert c.post("/api/admin/login", json={"email": "p4@x.in", "password": "Right-password-99"}, headers=H).status_code == 200
    m = c.get("/api/admin/catalog/meds?tab=rx", headers=H).json()
    assert m["counts"]["all"] >= 40 and all(r["rx"] for r in m["rows"])
    sku = m["rows"][0]["sku"]
    assert c.put(f"/api/admin/catalog/meds/{sku}", json={"name": "X", "schedule": "H1", "rx": False}, headers=H).status_code == 400
    b = io.BytesIO(); Image.new("RGB", (30, 20), (0, 0, 255)).save(b, "PNG")
    ph = c.post(f"/api/admin/catalog/meds/{sku}/photo", data={"side": "front"}, files={"file": ("a.png", b.getvalue(), "image/png")}, headers=H).json()["photos"]
    assert TestClient(server.app).get(f"/api/v2/catalog/meds/{sku}/photo/{ph[0]['id']}").status_code == 200
    pk = c.get("/api/admin/catalog/packages", headers=H).json()
    assert any(p["code"] == "heartdia" for p in pk["rows"])
    bad = c.put("/api/admin/catalog/packages/cheapx", json={"name": "Too dear", "tests": ["cbc", "hba1c"], "price": 99999, "active": True}, headers=H)
    assert bad.status_code == 400
    city = TestClient(server.app).get("/labs/hyderabad")
    assert city.status_code == 200 and "Vijaya Diagnostics" in city.text and "Paused Lab" not in city.text
    import re
    link = re.search(r'href="(/labs/hyderabad/kukatpally/vijaya-diagnostics-[a-z0-9]{6})"', city.text).group(1)
    pg = TestClient(server.app).get(link)
    assert pg.status_code == 200 and '"@type": "DiagnosticLab"' in pg.text and "₹249" in pg.text and "application/ld+json" in pg.text
    assert TestClient(server.app).get(f"/labs/hyderabad/kukatpally/paused-lab-{hid[-6:]}").status_code == 404
    sm = TestClient(server.app).get("/sitemap.xml").text
    assert link in sm and "paused-lab" not in sm
    assert TestClient(server.app).get("/partner/join/abcdefghijklmnop").status_code == 200   # not swallowed by the public routes


def test_phase5_families_requests_companies_offers_devices_practice():
    import server, time
    from api.db import SessionLocal
    from api.models import Admin, Household, User, Person
    from api.security import hash_pw
    import api.auth as A
    c = TestClient(server.app).__enter__(); H = {"x-tht": "1", "x-forwarded-for": "10.1.0.1"}
    with SessionLocal() as db:
        db.add(Admin(email="p5@x.in", pw_hash=hash_pw("Right-password-99"), role="owner"))
        h = Household(key="kp5", name="Asha Rao", city="Hyderabad"); db.add(h); db.flush()
        u = User(email="asha5@x.in", phone="+919849004410", household_id=h.id, pw_hash="x"); db.add(u); db.flush()
        from api.family import encrypt
        db.add(Person(household_id=h.id, name="Asha Rao", owner_user=u.id, blob=encrypt({}))); db.commit(); hid, uid = h.id, u.id
    assert c.post("/api/admin/login", json={"email": "p5@x.in", "password": "Right-password-99"}, headers=H).status_code == 200
    # devices: a second device needs a code
    c2 = TestClient(server.app)
    r = c2.post("/api/admin/login", json={"email": "p5@x.in", "password": "Right-password-99"}, headers={"x-tht": "1", "x-forwarded-for": "10.1.0.2"})
    assert r.status_code == 428 and r.json()["detail"]["needCode"]
    code = r.json()["detail"].get("demo")
    if code:
        assert c2.post("/api/admin/login", json={"email": "p5@x.in", "password": "Right-password-99", "code": code}, headers={"x-tht": "1", "x-forwarded-for": "10.1.0.2"}).status_code == 200
    # families: partial search finds nothing, full mobile finds masked family
    assert c.get("/api/admin/families?q=98490", headers=H).json()["rows"] == []
    f = c.get("/api/admin/families?q=9849004410", headers=H).json()["rows"]
    assert f and f[0]["name"] == "A•••• R." and "Asha" not in str(f)
    fam = c.get(f"/api/admin/families/{hid}", headers=H).json()
    assert "records" not in fam and fam["account"]["mobile"].startswith("+91")
    assert c.post(f"/api/admin/families/{hid}/ask-access", json={"reason": "Report not showing for her"}, headers=H).status_code == 200
    orig = A.current_user
    A.current_user = lambda req, db: db.get(User, uid)
    try:
        f2 = TestClient(server.app)
        from api.models import AccessGrant
        with SessionLocal() as db:
            gid = db.query(AccessGrant).filter_by(household_id=hid).one().id
        assert f2.post(f"/api/v2/access/{gid}", json={"allow": True}).json()["status"] == "granted"
        assert f2.post("/api/v2/data-requests", json={"kind": "copy"}).status_code == 200
        assert f2.post("/api/v2/data-requests", json={"kind": "copy"}).status_code == 409
        co = c.post("/api/admin/companies", json={"name": "Acme Software", "invited": 420, "price": 1800}, headers=H).json()
        assert f2.post("/api/v2/company/join", json={"code": co["code"]}).json()["company"] == "Acme Software"
        assert c.get("/api/admin/companies", headers=H).json()["rows"][0]["stats"] is None   # fewer than 20: no totals
        # offers: never on medicines, budget and once-per-family
        end = time.strftime("%Y-%m-%d", time.gmtime(time.time() + 10 * 86400))
        assert c.post("/api/admin/offers", json={"code": "FIRST100", "title": "₹100 off", "applies": "medicine", "flat": 100, "budget": 50000, "ends": end}, headers=H).status_code == 400
        assert c.post("/api/admin/offers", json={"code": "FIRST100", "title": "₹100 off", "applies": "lab", "flat": 100, "budget": 50000, "ends": end}, headers=H).status_code == 200
        assert f2.post("/api/v2/offers/check", json={"code": "first100", "kind": "lab", "items": [{"name": "CBC"}], "subtotal": 400}).json()["off"] == 100
        assert f2.post("/api/v2/offers/check", json={"code": "FIRST100", "kind": "medicine", "items": [{"name": "X", "rx": True}], "subtotal": 400}).status_code == 400
    finally:
        A.current_user = orig
    fam = c.get(f"/api/admin/families/{hid}", headers=H).json()
    assert "records" in fam
    dr = c.get("/api/admin/data-requests", headers=H).json()["rows"][0]
    assert c.post(f"/api/admin/data-requests/{dr['id']}", json={"note": "ready"}, headers=H).status_code == 200
    # messages: pause one, sign-in codes can't be paused
    assert c.post("/api/admin/messages", json={"kind": "otp", "on": False}, headers=H).status_code == 400
    assert c.post("/api/admin/messages", json={"kind": "refill", "on": False}, headers=H).status_code == 200
    assert not [m for m in c.get("/api/admin/messages", headers=H).json()["rows"] if m["kind"] == "refill"][0]["on"]
    # practice
    assert c.post("/api/admin/practice/late", headers=H).status_code == 200
    assert any("practice" in x["what"].lower() for x in c.get("/api/admin/console/board", headers=H).json()["lanes"]["way"])
    assert c.post("/api/admin/practice/clear", headers=H).status_code == 200
    assert "Yesterday" in c.get("/api/admin/summary", headers=H).json()["text"]
    # sign out everywhere ends the session
    assert c.post("/api/admin/signout-everywhere", headers=H).status_code == 200
    assert c.get("/api/admin/me", headers=H).status_code == 401

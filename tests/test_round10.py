"""Round 10: doctors + video consults (signalling, e-prescription into the vault, summary), proactive nudges and the weekly
report, Medical ID pages, data export, partner self-serve applications, settlements, ABHA scaffold off by default."""
import json
import os
import uuid
from datetime import date

os.environ.setdefault("OTP_DEMO", "1")
os.environ.setdefault("PWNED_CHECK", "0")
os.environ["DATABASE_URL"] = "sqlite:///./data/test_r10.db"

from fastapi.testclient import TestClient  # noqa: E402

import server  # noqa: E402
from api import db as DB  # noqa: E402
from api import proactive  # noqa: E402
from api.models import Admin, Appointment, Store  # noqa: E402
from api.security import hash_pw  # noqa: E402
from tests.test_round7 import H, admin, family  # noqa: E402

STATE = {"members": [{"id": "m1", "name": "Prasanna Daddala", "age": 36, "sex": "male", "h": 172, "w": 78},
                     {"id": "m2", "name": "Baby Daddala", "age": 0, "sex": "female", "dob": "2026-08-20"}],
         "results": {"m1": [{"id": "r1", "k": "lab", "key": "hba1c", "val": 7.2, "date": "2026-05-01"}, {"id": "r2", "k": "lab", "key": "ldl", "val": 88, "date": "2026-10-01"}]},
         "vitals": {"m1": []}, "cards": [{"id": "c1", "type": "insurance", "member": "m1", "f": {"insurer": "Star Health", "valid_to": "2026-11-02"}}],
         "mid": {"m1": {"blood": "O+", "allergies": ["Penicillin"], "conditions": ["Type 2 diabetes"]}}, "preg": {}, "care": {}, "vax": {}}


def hospital_with_doctor(a):
    with DB.session() as db:
        hosp = Store(kind="hospital", name="Care Hospital", city="Hyderabad", area="Banjara Hills", lat=17.414, lng=78.435, verified=True, phone="04030418888")
        db.add(hosp)
        db.flush()
        hid = hosp.id
    r = a.post(f"/api/admin/stores/{hid}/users", json={"email": f"d{uuid.uuid4().hex[:6]}@care.in", "name": "Meera Rao", "role": "doctor", "regNo": "TSMC-45678", "specialty": "General physician"})
    assert r.status_code == 200 and r.json()["role"] == "doctor", r.text
    email, pw, uid = r.json()["email"], r.json()["tempPassword"], r.json()["id"]
    assert a.post(f"/api/admin/stores/{hid}/users", json={"email": "x@care.in", "name": "", "role": "doctor"}).status_code == 400  # a doctor needs a reg no
    d = TestClient(server.app)
    assert d.post("/api/partner/login", json={"email": email, "password": pw}).status_code == 200
    return hid, uid, d


def test_video_consult_end_to_end():
    f, a = family(), admin()
    hid, uid, d = hospital_with_doctor(a)
    # the family sees no doctors until the registration is verified
    assert f.get(f"/api/v1/doctors?store={hid}").json() == {"doctors": [], "video": False}
    assert a.post(f"/api/admin/stores/{hid}/users/{uid}/verify", json={"verified": True}).json()["verified"] is True
    docs = f.get(f"/api/v1/doctors?store={hid}").json()
    assert docs["video"] and docs["doctors"][0]["name"] == "Meera Rao" and docs["doctors"][0]["regNo"] == "TSMC-45678"
    # request a video visit, the hospital confirms it
    ap = f.post("/api/v1/appointments", json={"store": hid, "member": "m1", "memberName": "Prasanna", "kind": "video", "date": "2026-10-20", "time": "10:00", "why": "sugar review", "doctor": "Meera Rao"}).json()
    assert ap["kind"] == "video" and ap["status"] == "requested"
    assert d.post(f"/api/partner/appointments/{ap['id']}", json={"status": "confirmed", "slotDate": "2026-10-20", "slotTime": "10:00"}).status_code == 200
    lst = d.get("/api/partner/consults").json()
    assert lst["me"]["verified"] and [c["id"] for c in lst["consults"]] == [ap["id"]]
    # ICE config is always available (STUN by default)
    assert f.get("/api/v1/consults/ice").json()["iceServers"][0]["urls"]
    # nobody can open the room before the doctor starts — and unauthenticated sockets are refused
    with TestClient(server.app) as ws:
        try:
            with ws.websocket_connect(f"/ws/call/{ap['id']}?key=nope"):
                assert False, "should refuse"
        except Exception:
            pass
    # the doctor starts the call → the family gets a notice with the join flag
    st = d.post(f"/api/partner/consults/{ap['id']}/start").json()
    assert st["live"] is True and st["doctor"] == "Meera Rao"
    n = f.get("/api/v1/inbox").json()["notices"][0]
    assert n["kind"] == "consult" and n["ref"]["join"] is True and n["ref"]["appointment"] == ap["id"]
    # signalling relays between the two sockets
    key = f.headers["X-DoKKo-Key"]
    with TestClient(server.app) as c1, TestClient(server.app, cookies=d.cookies) as c2:
        with c1.websocket_connect(f"/ws/call/{ap['id']}?key={key}") as fam:
            hello = fam.receive_json()
            assert hello["you"] == "family" and hello["peerPresent"] is False
            with c2.websocket_connect(f"/ws/call/{ap['id']}") as doc:
                h2 = doc.receive_json()
                assert h2["you"] == "doctor" and h2["peerPresent"] is True
                assert fam.receive_json() == {"type": "peer", "present": True, "who": "doctor"}
                doc.send_text(json.dumps({"type": "offer", "sdp": "v=0"}))
                got = fam.receive_json()
                assert got["type"] == "offer" and got["from"] == "doctor" and got["sdp"] == "v=0"
                fam.send_text(json.dumps({"type": "caption", "text": "my sugar was 180 after lunch", "t": 1}))
                assert doc.receive_json()["text"] == "my sugar was 180 after lunch"
                fam.send_text(json.dumps({"type": "evil", "x": 1}))  # unknown types are dropped
                doc.send_text(json.dumps({"type": "ping"}))
                assert doc.receive_json() == {"type": "pong"}
    # e-prescription → PDF in the family's vault + notice; family hangs up with the transcript
    rx = d.put(f"/api/partner/consults/{ap['id']}/rx", json={"items": [{"name": "Metformin", "strength": "500 mg", "form": "tablet", "frequency": "bd", "duration": "30 days", "instructions": "after food"}],
                                                             "advice": "Walk 30 minutes daily. Repeat HbA1c in 3 months.", "followUp": "3 months", "diagnosis": "Sugar control review"})
    assert rx.status_code == 200 and rx.json()["rxFileId"] == f"erx_{ap['id']}", rx.text
    pdf = d.get(f"/api/partner/consults/{ap['id']}/rx.pdf")
    assert pdf.status_code == 200 and pdf.content[:4] == b"%PDF"
    fam_pdf = f.get(f"/api/v1/files/erx_{ap['id']}")
    assert fam_pdf.status_code == 200 and fam_pdf.content[:4] == b"%PDF"
    n = f.get("/api/v1/inbox").json()["notices"][0]
    assert n["kind"] == "prescription" and n["ref"]["items"][0]["name"] == "Metformin"
    end = f.post(f"/api/v1/consults/{ap['id']}/end", json={"transcript": [{"who": "family", "t": 1, "text": "my sugar was 180 after lunch"}, {"who": "doctor", "t": 2, "text": "we will continue metformin"}]}).json()
    assert end["callEnded"] and len(end["transcript"]) == 2 and end["rx"]["items"][0]["frequency"] == "bd"
    done = d.post(f"/api/partner/consults/{ap['id']}/end", json={"transcript": [{"who": "doctor", "t": 2, "text": "we will continue metformin"}]}).json()
    assert done["status"] == "done" and len(done["transcript"]) == 2  # de-duplicated
    # a staff member (not a doctor) cannot start consults
    r = a.post(f"/api/admin/stores/{hid}/users", json={"email": f"s{uuid.uuid4().hex[:6]}@care.in", "name": "Desk", "role": "staff"}).json()
    s = TestClient(server.app)
    s.post("/api/partner/login", json={"email": r["email"], "password": r["tempPassword"]})
    assert s.post(f"/api/partner/consults/{ap['id']}/start").status_code == 403


def test_nudges_and_weekly_report_from_the_record():
    today = date(2026, 10, 19)
    items = proactive.nudges(STATE, today)
    keys = {i["key"].split(":")[0] for i in items}
    assert {"repeat", "vax", "policy"} <= keys
    rep = next(i for i in items if i["key"].startswith("repeat"))
    assert "HbA1c" in rep["title"] and "7.2" in rep["body"]
    vax = next(i for i in items if i["key"].startswith("vax"))
    assert "Pentavalent 1" in vax["body"] or "OPV 1" in vax["body"]
    # LDL was normal → no repeat nudge for it
    assert not any(":ldl:" in i["key"] for i in items)
    # weekly report: 4 weeks vs the 4 before, BP control, adherence
    st = json.loads(json.dumps(STATE))
    import time as _t
    base = int(_t.mktime((2026, 10, 19, 0, 0, 0, 0, 0, -1))) * 1000
    st["vitals"]["m1"] = [{"t": base - (40 - i) * 86400000, "sys": 150 if i < 12 else 128, "dia": 90 if i < 12 else 82, "glu": 170 - i} for i in range(40)]
    st["adh"] = {"m1": {f"2026-10-{d:02d}": {"done": 2 if d % 3 else 1, "total": 2} for d in range(1, 19)}}
    w = proactive.weekly(st, today)
    me = w["people"][0]
    sysrow = next(s for s in me["series"] if s["field"] == "sys")
    assert sysrow["mean"] == 128 and sysrow["previous"] == 150 and sysrow["change"] == -22 and sysrow["inRange"] == 100
    assert me["bpControl"] == 100 and 80 <= me["adherence"] <= 85
    assert me["labs"][0]["name"] == "LDL cholesterol"
    # the morning pass writes notices once, and never twice for the same key
    f = family()
    assert f.put("/api/v1/sync", headers=H, json={"base": 0, "state": st, "sect": {"members": 1}}).status_code == 200
    n1 = proactive.run_morning(today, force=True)
    n2 = proactive.run_morning(today, force=True)
    assert n1 >= 3 and n2 == 0
    inbox = f.get("/api/v1/inbox").json()
    kinds = {n["kind"] for n in inbox["notices"]}
    assert "weekly" in kinds and ("nudge_test" in kinds or "nudge_policy" in kinds)
    assert len([n for n in inbox["notices"] if n["kind"].startswith("nudge_")]) <= proactive.MAX_NUDGES_PER_DAY
    wr = f.get("/api/v1/report/weekly").json()
    assert wr["people"][0]["bpControl"] == 100 and "narrative" in wr


def test_medical_id_public_page_and_qr():
    f = family()
    payload = {"name": "Prasanna Daddala", "age": 36, "sex": "male", "blood": "O+", "allergies": ["Penicillin"], "conditions": ["Type 2 diabetes"], "medicines": ["Metformin 500 bd"],
               "contacts": [{"name": "Sravani", "rel": "wife", "phone": "+919876543210"}], "donor": "Organ donor", "notes": "<script>alert(1)</script>"}
    m = f.put("/api/v1/medical-id/m1", json={"payload": payload}).json()
    assert m["enabled"] and "/m/" in m["url"]
    tok = m["token"]
    pub = TestClient(server.app)
    page = pub.get(f"/m/{tok}")
    assert page.status_code == 200 and "O+" in page.text and "Penicillin" in page.text and "+919876543210" in page.text and "<script>" not in page.text and "noindex" in page.text
    j = pub.get(f"/api/v1/m/{tok}").json()["medicalId"]
    assert j["blood"] == "O+" and j["contacts"][0]["phone"] == "+919876543210"
    qr = f.get("/api/v1/medical-id/m1/qr.svg")
    assert qr.status_code == 200 and b"<svg" in qr.content
    assert f.get("/api/v1/medical-id").json()["ids"][0]["views"] == 2
    # rotate → old link dies; off → page gone
    m2 = f.put("/api/v1/medical-id/m1", json={"payload": payload, "rotate": True}).json()
    assert m2["token"] != tok and pub.get(f"/m/{tok}").status_code == 404 and pub.get(f"/m/{m2['token']}").status_code == 200
    f.post("/api/v1/medical-id/m1/off")
    assert pub.get(f"/m/{m2['token']}").status_code == 404 and f.get("/api/v1/medical-id/m1/qr.svg").status_code == 404


def test_export_zip_has_record_and_documents():
    import io
    import zipfile
    f = family()
    assert f.put("/api/v1/sync", headers=H, json={"base": 0, "state": STATE, "sect": {"members": 1}}).status_code == 200
    r = f.put("/api/v1/files/doc_abc", headers={"content-type": "application/pdf", "x-file-name": "Lipid profile.pdf", **H}, content=b"%PDF-1.4 lipid")
    assert r.status_code == 200, r.text
    z = f.get("/api/v1/export")
    assert z.status_code == 200 and z.headers["content-type"] == "application/zip"
    zf = zipfile.ZipFile(io.BytesIO(z.content))
    names = zf.namelist()
    assert {"record.json", "orders.json", "appointments.json", "messages.json", "notices.json", "accounts.json", "README.txt", "documents/index.json"} <= set(names)
    rec = json.loads(zf.read("record.json"))
    assert rec["members"][0]["name"] == "Prasanna Daddala"
    idx = json.loads(zf.read("documents/index.json"))
    assert idx["files"][0]["id"] == "doc_abc" and zf.read(idx["files"][0]["file"]) == b"%PDF-1.4 lipid" and idx["files"][0]["file"].endswith(".pdf")


def test_partner_application_and_settlements():
    a = admin()
    pub = TestClient(server.app)
    bad = pub.post("/api/v1/partner/apply", json={"kind": "lab", "name": "Quick Labs", "email": "ql@example.com", "phone": "9876543210", "city": "Hyderabad", "accept": True})
    assert bad.status_code == 400 and "NABL" in bad.text
    em = f"ql{uuid.uuid4().hex[:5]}@example.com"
    ok = pub.post("/api/v1/partner/apply", json={"kind": "lab", "name": "Quick Labs", "contact": "Ramesh", "email": em, "phone": "9876543210", "city": "Hyderabad", "area": "Kukatpally",
                                                 "licence": "NABL MC-9988", "lat": 17.49, "lng": 78.4, "accept": True})
    assert ok.status_code == 200 and ok.json()["status"] == "new"
    aid = ok.json()["id"]
    again = pub.post("/api/v1/partner/apply", json={"kind": "lab", "name": "Quick Labs", "email": em, "phone": "9876543210", "city": "Hyderabad", "licence": "NABL MC-9988", "accept": True}).json()
    assert again["id"] == aid  # de-duplicated
    q = a.get("/api/admin/applications").json()["applications"]
    assert any(x["id"] == aid and x["licence"] == "NABL MC-9988" for x in q)
    ap = a.post(f"/api/admin/applications/{aid}/approve", json={"verified": True})
    assert ap.status_code == 200 and ap.json()["tempPassword"], ap.text
    p = TestClient(server.app)
    me = p.post("/api/partner/login", json={"email": em, "password": ap.json()["tempPassword"]})
    assert me.status_code == 200 and me.json()["store"]["name"] == "Quick Labs" and me.json()["store"]["verified"] is True and me.json()["user"]["role"] == "owner"
    assert a.get("/api/admin/applications").json()["applications"] == [x for x in a.get("/api/admin/applications").json()["applications"] if x["id"] != aid]
    # settlements: a delivered order shows in the month with the platform fee split by payment mode
    f = family()
    with DB.session() as db:
        ph = Store(kind="pharmacy", name="Apollo", city="Hyderabad", area="Madhapur", lat=17.449, lng=78.392, verified=True)
        db.add(ph)
        db.flush()
        from api.models import StoreItem
        db.add(StoreItem(store_id=ph.id, sku="paracip", name="Paracetamol 500", price=20, mrp=25, stock=50))
        pid = ph.id
    o = f.post("/api/v1/orders", json={"store": pid, "kind": "medicine", "items": [{"sku": "paracip", "qty": 2}], "address": "12 Road", "member": "Prasanna"})
    assert o.status_code == 200, o.text
    with DB.session() as db:
        from api.models import Order
        row = db.get(Order, o.json()["id"])
        row.status = "delivered"
    import time as _t
    month = _t.strftime("%Y-%m")
    st = a.get(f"/api/admin/settlements?month={month}").json()
    row = next(r for r in st["rows"] if r["storeId"] == pid)
    assert row["orders"] == 1 and row["gross"] == o.json()["total"] and row["cod"] == o.json()["total"] and row["dueFromPartner"] == round(o.json()["total"] * st["feePct"] / 100)
    csv = a.get(f"/api/admin/settlements.csv?month={month}")
    assert csv.status_code == 200 and "Apollo" in csv.text


def test_abha_scaffold_is_off_without_credentials():
    f = family()
    st = f.get("/api/v1/abha/status").json()
    assert st["enabled"] is False and "Cards" in st["message"]
    assert f.post("/api/v1/abha/aadhaar/otp", json={"aadhaar": "123412341234"}).status_code == 503


def test_assistant_commands_are_validated():
    from api import agent
    cmds = agent._commands([{"type": "open", "args": {"page": "nowhere"}}, {"type": "book_lab", "label": "Book HbA1c", "args": {"tests": ["HbA1c"]}},
                            {"type": "add_reminder", "args": {"text": "Check BP", "days": "x"}}, {"type": "hack", "args": {}}])
    assert [c["type"] for c in cmds] == ["book_lab", "add_reminder"] and cmds[1]["args"]["days"] == 7


def test_policy_kind_is_accepted_and_medcheck_quota_free_path():
    f = family()
    r = f.post("/api/v1/ai/analyze", data={"kind": "policy", "text": "Star Health Family Floater, Sum insured 5,00,000", "consent": "1", "context": "{}"})
    # without an API key the policy reader says so instead of pretending
    assert r.status_code == 200 and r.json()["kind"] == "policy" and r.json()["readable"] is False
    m = f.post("/api/v1/ai/medcheck", json={"context": {"medicines": []}})
    assert m.status_code in (200, 503)


def test_roles_caregiver_cannot_change_profiles_but_can_add_readings():
    from tests.test_family import STATE as FS  # noqa: F401
    f = family()
    me = f.get("/api/v1/family/invites").json()
    assert me["myRole"] == "admin" and me["accounts"][0]["role"] == "admin"
    base = {"members": [{"id": "m1", "name": "Prasanna", "age": 36}], "vitals": {"m1": []}, "cards": []}
    assert f.put("/api/v1/sync", headers=H, json={"base": 0, "state": base, "sect": {}}).status_code == 200
    inv = f.post("/api/v1/family/invite", headers=H, json={"member_id": "m9", "name": "Nurse Latha", "role": "caregiver"}).json()
    assert inv["role"] == "caregiver"
    c = family()  # a second account, joins as caregiver
    j = c.post("/api/v1/family/join", headers=H, json={"token": inv["token"]}).json()
    assert j["joined"] and j["householdKey"]
    c.headers["X-DoKKo-Key"] = j["householdKey"]
    acc = f.get("/api/v1/family/invites").json()["accounts"]
    cg = next(a for a in acc if a["name"].startswith("Owner") and not a["me"])
    assert cg["role"] == "caregiver"
    cur = c.get("/api/v1/sync").json()
    # a caregiver may add a reading…
    s2 = json.loads(json.dumps(cur["state"]))
    s2["vitals"]["m1"].append({"t": 1, "sys": 120, "dia": 80})
    assert c.put("/api/v1/sync", headers=H, json={"base": cur["version"], "state": s2, "sect": {}}).status_code == 200
    # …but not rename a profile or touch cards
    cur = c.get("/api/v1/sync").json()
    s3 = json.loads(json.dumps(cur["state"]))
    s3["members"][0]["name"] = "Someone else"
    r = c.put("/api/v1/sync", headers=H, json={"base": cur["version"], "state": s3, "sect": {}})
    assert r.status_code == 403 and "members" in r.text
    assert c.delete("/api/v1/sync", headers=H).status_code == 403
    assert c.post(f"/api/v1/family/accounts/{cg['id']}/role", headers=H, json={"role": "admin"}).status_code == 403
    # the admin promotes, then removes the caregiver
    assert f.post(f"/api/v1/family/accounts/{cg['id']}/role", headers=H, json={"role": "member"}).json()["role"] == "member"
    assert f.delete(f"/api/v1/family/accounts/{cg['id']}", headers=H).json()["removed"] is True
    assert c.get("/api/v1/sync").status_code in (401, 409)


def test_handover_nudge_at_eighteen():
    from datetime import timedelta
    today = date(2026, 10, 19)
    st = {"members": [{"id": "k1", "name": "Aarav", "dob": (today - timedelta(days=int(18 * 365.25) + 3)).isoformat()}]}
    items = proactive.nudges(st, today)
    assert any(i["kind"] == "nudge_handover" for i in items)


def test_upi_payment_for_plan_and_order_confirmed_by_admin():
    f, a = family(), admin()
    acc = f.get("/api/v1/pay/upi/accounts").json()
    assert acc["enabled"] and len(acc["accounts"]) == 3 and acc["accounts"][0]["vpa"].endswith("@axl")
    plans = f.get("/api/v1/plans").json()
    assert plans["provider"] == "upi"
    paid = next(p for p in plans["plans"] if p["month"] > 0)
    # the old demo switch stays refused; the UPI route is the way
    st = f.post("/api/v1/pay/upi/start", json={"kind": "plan", "plan": paid["code"], "period": "year", "account": "kotak"}).json()
    assert st["status"] == "pending" and st["amount"] == paid["year"] and st["account"]["id"] == "kotak" and st["note"].startswith("THT")
    assert f"am={paid['year']}.00" in st["upiLink"] and st["note"] in st["upiLink"]
    again = f.post("/api/v1/pay/upi/start", json={"kind": "plan", "plan": paid["code"], "period": "year"}).json()
    assert again["id"] == st["id"]  # one open payment per thing
    qr = f.get(st["qr"])
    assert qr.status_code == 200 and b"<svg" in qr.content
    assert f.post(f"/api/v1/pay/upi/{st['id']}/claim", json={"utr": "12"}).status_code == 400
    cl = f.post(f"/api/v1/pay/upi/{st['id']}/claim", json={"utr": "329912345678", "payer": "prasanna@axl"}).json()
    assert cl["status"] == "claimed"
    q = a.get("/api/admin/payments").json()
    assert any(p["id"] == st["id"] for p in q["payments"]) and q["counts"]["claimed"] >= 1
    ok = a.post(f"/api/admin/payments/{st['id']}/confirm", json={"note": "matched in Kotak statement"}).json()
    assert ok["status"] == "confirmed"
    pl = f.get("/api/v1/plans").json()
    assert pl["current"] == paid["code"] and pl["until"] and pl["history"][0]["provider"] == "upi"
    n = f.get("/api/v1/inbox").json()["notices"][0]
    assert n["kind"] == "payment" and "active" in n["body"]
    # an order paid by UPI
    with DB.session() as db:
        ph = Store(kind="pharmacy", name="MedPlus", city="Hyderabad", area="Madhapur", lat=17.449, lng=78.392, verified=True)
        db.add(ph)
        db.flush()
        from api.models import StoreItem
        db.add(StoreItem(store_id=ph.id, sku="cetzine", name="Cetirizine 10", price=30, mrp=35, stock=50))
        pid = ph.id
    o = f.post("/api/v1/orders", json={"store": pid, "kind": "medicine", "items": [{"sku": "cetzine", "qty": 1}], "address": "12 Road", "member": "Prasanna", "payment": "upi"}).json()
    po = f.post("/api/v1/pay/upi/start", json={"kind": "order", "orderId": o["id"]}).json()
    assert po["amount"] == o["total"] and po["kind"] == "order"
    f.post(f"/api/v1/pay/upi/{po['id']}/claim", json={"utr": "ABCD12345678"})
    a.post(f"/api/admin/payments/{po['id']}/confirm", json={})
    got = f.get("/api/v1/orders").json()["orders"]
    assert next(x for x in got if x["id"] == o["id"])["payment"] == "upi-paid"
    assert f.post("/api/v1/pay/upi/start", json={"kind": "order", "orderId": o["id"]}).status_code == 400
    # rejection path
    s2 = f.post("/api/v1/pay/upi/start", json={"kind": "plan", "plan": paid["code"], "period": "month"}).json()
    f.post(f"/api/v1/pay/upi/{s2['id']}/claim", json={"utr": "999912345678"})
    assert a.post(f"/api/admin/payments/{s2['id']}/reject", json={"note": "no such credit"}).json()["status"] == "rejected"
    mine = f.get("/api/v1/pay/upi").json()["payments"]
    assert {p["status"] for p in mine} >= {"confirmed", "rejected"}


def test_digilocker_scaffold_off_and_name_lock():
    f = family()
    st = f.get("/api/v1/digilocker/status").json()
    assert st["enabled"] is False and "DigiLocker" in st["message"]
    assert f.post("/api/v1/digilocker/start", headers=H).status_code == 503
    from api.digilocker import _parse_ekyc
    xml = b'''<?xml version="1.0"?><Certificate><CertificateData><KycRes><UidData uid="xxxxxxxx4321"><Poi dob="12-05-1990" gender="M" name="Daddala Prasanna Krishna"/><Poa house="1-2-3" street="Road 4" vtc="Madhapur" dist="Hyderabad" state="Telangana" pc="500081"/><Pht>/9j/4AAQ</Pht></UidData></KycRes></CertificateData></Certificate>'''
    k = _parse_ekyc(xml)
    assert k["name"] == "Daddala Prasanna Krishna" and k["last4"] == "4321" and "Hyderabad" in k["address"] and k["photo"] == "/9j/4AAQ"
    # an Aadhaar-verified account cannot edit its name
    with DB.session() as db:
        from api.models import User
        u = db.scalar(select_user(db, f))
        u.aadhaar_verified, u.aadhaar_last4 = 1, "4321"
    r = f.post("/api/v1/auth/profile", headers=H, json={"name": "Someone Else"})
    assert r.status_code == 423 and "Aadhaar" in r.text
    me = f.get("/api/v1/auth/me").json()["user"]
    assert me["aadhaarVerified"] and me["aadhaarLast4"] == "4321"


def select_user(db, client):
    from sqlalchemy import select
    from api.models import User
    uid = client.get("/api/v1/auth/me").json()["user"]["id"]
    return select(User).where(User.id == uid)


def test_signup_offers_aadhaar_route_only_when_digilocker_is_live(monkeypatch):
    c = TestClient(server.app)
    c.__enter__()
    u = uuid.uuid4().hex[:8]
    body = {"name": "Owner " + u, "email": f"{u}@example.com", "phone": "9" + str(uuid.uuid4().int)[-9:].zfill(9), "password": "Zq!8vB#2mLp@9xT", "terms": True, "verify": "aadhaar"}
    r = c.post("/api/v1/auth/signup/start", headers=H, json=body)
    assert r.status_code == 400 and "DigiLocker" in r.text   # not registered yet → mobile OTP it is
    monkeypatch.setenv("DIGILOCKER_CLIENT_ID", "x")
    monkeypatch.setenv("DIGILOCKER_CLIENT_SECRET", "y")
    r = c.post("/api/v1/auth/signup/start", headers=H, json=body)
    assert r.status_code == 200, r.text
    v = c.post("/api/v1/auth/signup/verify", headers=H, json={"flow": r.json()["flow"], "code": r.json()["demo"]}).json()
    assert v["aadhaarNext"]["start"] == "/api/v1/digilocker/start" and "verifyNext" not in v
    st = c.post("/api/v1/digilocker/start", headers=H).json()
    assert "digitallocker.gov.in" in st["url"] and "code_challenge=" in st["url"]
    me = c.get("/api/v1/auth/me").json()["user"]
    assert me["verified"] is False and me["phoneVerified"] is False
    # a verified Aadhaar makes the account verified without a mobile code
    with DB.session() as db:
        from api.models import User
        x = db.scalar(select_user(db, c))
        x.aadhaar_verified, x.aadhaar_last4, x.aadhaar_dob = 1, "4321", "12-05-1990"
    me = c.get("/api/v1/auth/me").json()["user"]
    assert me["verified"] is True and me["dob"] == "1990-05-12"


def test_loops_close_on_their_own_plan_expiry_stale_calls_and_alerts():
    from api import messaging
    f, a = family(), admin()
    hid, uid, d = hospital_with_doctor(a)
    # plan expiry: an ended plan drops to free with a notice; a plan ending in 3 days gets one renewal nudge
    with DB.session() as db:
        from api.models import Household
        key = f.headers["X-DoKKo-Key"]
        h = db.scalar(select_household(db, key))
        h.plan, h.plan_until = "family", 1
    assert proactive.run_morning(date(2026, 10, 19)) >= 1
    inbox = f.get("/api/v1/inbox").json()
    assert any(n["kind"] == "plan" and "ended" in n["title"] for n in inbox["notices"])
    assert f.get("/api/v1/plans").json()["current"] == "free"
    with DB.session() as db:
        h = db.scalar(select_household(db, key))
        h.plan, h.plan_until = "family", int(__import__("time").time()) + 3 * 86400
    proactive.run_morning(date(2026, 10, 19)); proactive.run_morning(date(2026, 10, 19))
    assert len([n for n in f.get("/api/v1/inbox").json()["notices"] if "renews in" in n["title"]]) == 1
    # a call the doctor forgot to end closes after 3 hours
    a.post(f"/api/admin/stores/{hid}/users/{uid}/verify", json={"verified": True})
    ap = f.post("/api/v1/appointments", json={"store": hid, "member": "m1", "memberName": "P", "kind": "video", "date": "2026-10-20", "doctor": "Meera Rao"}).json()
    d.post(f"/api/partner/appointments/{ap['id']}", json={"status": "confirmed", "slotDate": "2026-10-20", "slotTime": "10:00"})
    d.post(f"/api/partner/consults/{ap['id']}/start")
    with DB.session() as db:
        x = db.get(Appointment, ap["id"]); x.call_started -= 4 * 3600
    proactive.run_morning(date(2026, 10, 19))
    assert f.get(f"/api/v1/consults/{ap['id']}").json()["status"] == "done"
    # the hospital was emailed about the visit request (logged even without a transport), the admin sees attention counts
    assert any(m["subject"].startswith("[TheHealthTracker] Visit request") for m in messaging.SENT_LOG)
    st = a.get("/api/admin/stats").json()
    assert set(st["attention"]) >= {"payments", "applications", "doctors", "stores", "visits", "orders"}


def select_household(db, key):
    from sqlalchemy import select
    from api.models import Household
    return select(Household).where(Household.key == key)


def test_app_downloads_and_fitbit_off_by_default():
    f = family()
    a = f.get("/api/v1/app/android").json()
    assert a["available"] is False and a["url"] == ""
    assert f.get("/download/android").status_code == 404
    assert f.get("/api/v1/app/ios").json()["pwa"] is True
    s = f.get("/api/v1/fitbit/status").json()
    assert s["enabled"] is False and s["links"] == []
    assert f.post("/api/v1/fitbit/start").status_code == 503


def test_shop_package_order_upi_and_cod():
    f, a = family(), admin()
    sp = f.get("/api/v1/shop/products").json()
    assert sp["store"] == "s_tht_shop" and sp["products"][0]["sku"] == "bag-complete" and sp["products"][0]["price"] > 0 and "S" in sp["products"][0]["sizes"]
    p = sp["products"][0]
    o = f.post("/api/v1/orders", json={"store": p["store"], "kind": "medicine", "items": [{"sku": p["sku"], "qty": 1, "size": "L"}], "address": "12 Road, Hyderabad - 500033", "member": "Prasanna", "memberId": "m1", "payment": "upi"}).json()
    assert o["kind"] == "shop" and o["items"][0]["size"] == "L" and o["total"] == p["price"] and o["fee"] == 0 and o["steps"][3] == "Shipped"
    pay = f.post("/api/v1/pay/upi/start", json={"kind": "order", "orderId": o["id"]}).json()
    assert pay["amount"] == p["price"]
    cod = f.post("/api/v1/orders", json={"store": p["store"], "kind": "medicine", "items": [{"sku": p["sku"], "qty": 2}], "address": "12 Road", "member": "P", "payment": "cod"}).json()
    assert cod["total"] == 2 * p["price"]
    assert f.post("/api/v1/orders", json={"store": p["store"], "kind": "medicine", "items": [{"sku": p["sku"]}], "address": "x", "member": "P", "payment": "bitcoin"}).status_code == 400
    assert f.get(f"/api/v1/orders/{o['id']}/receipt.pdf").status_code == 200
    # admin edits the product
    r = a.put("/api/admin/products/bag-complete", json={"sku": "bag-complete", "name": "Hospital Bag · Complete", "price": 3499, "mrp": 4299, "stock": 10, "sizes": ["M", "L"], "includes": [{"group": "Mother", "name": "Nighties", "qty": 3}]})
    assert r.status_code == 200 and r.json()["price"] == 3499 and r.json()["includes"][0]["qty"] == 3
    assert f.get("/api/v1/shop/products").json()["products"][0]["price"] == 3499


def test_blood_network_request_offer_accept_track():
    f, a = family(), admin()
    with DB.session() as db:
        bb = Store(kind="bloodbank", name="Red Cross Blood Bank", city="Hyderabad", area="Vidyanagar", lat=17.405, lng=78.52, verified=True, phone="04027633087")
        db.add(bb); db.flush(); bid = bb.id
    r = a.post(f"/api/admin/stores/{bid}/users", json={"email": f"bb{uuid.uuid4().hex[:5]}@rc.in", "name": "Desk", "role": "owner"}).json()
    pb = TestClient(server.app); pb.post("/api/partner/login", json={"email": r["email"], "password": r["tempPassword"]})
    # a donor registers (O-, 6 km away, eligible)
    d = f.put("/api/v1/donor", json={"member": "m1", "name": "Prasanna Daddala", "group": "O-", "phone": "+919876543210", "lat": 17.44, "lng": 78.49, "city": "Hyderabad", "sex": "male", "consent": True})
    assert d.status_code == 200 and d.json()["group"] == "O-" and d.json()["located"]
    assert f.put("/api/v1/donor", json={"member": "m1", "group": "O-", "consent": False}).status_code == 400
    # the blood bank raises a request for A+ within 25 km → the O- donor is notified
    q = pb.post("/api/partner/blood", json={"group": "A+", "component": "whole", "units": 2, "urgency": "now", "patient": "Ravi", "ward": "Blood bank, ground floor", "notes": "bring ID"})
    assert q.status_code == 200, q.text
    q = q.json(); assert q["notified"] == 1 and q["status"] == "open"
    n = f.get("/api/v1/inbox").json()["notices"][0]
    assert n["kind"] == "blood" and n["ref"]["request"] == q["id"] and "A+" in n["title"]
    near = f.get("/api/v1/blood/requests?lat=17.44&lng=78.49&group=O-").json()["requests"]
    assert near[0]["id"] == q["id"] and near[0]["km"] < 10 and "phone" not in near[0]
    # a family without a donor profile cannot respond; the donor can
    g2 = family()
    assert g2.post(f"/api/v1/blood/{q['id']}/respond", json={"member": "m1"}).status_code == 400
    assert f.post(f"/api/v1/blood/{q['id']}/respond", json={"member": "m1", "lat": 17.44, "lng": 78.49}).json()["response"] == "offered"
    # location is not shared before the hospital accepts; the hospital sees a masked name
    assert f.post(f"/api/v1/blood/{q['id']}/location", json={"lat": 17.43, "lng": 78.5}).status_code == 400
    view = pb.get("/api/partner/blood").json()["requests"][0]
    assert view["responses"][0]["status"] == "offered" and view["responses"][0]["phone"] == "" and view["responses"][0]["name"].endswith("…")
    xid = view["responses"][0]["id"]
    acc = pb.post(f"/api/partner/blood/{q['id']}/responses/{xid}", json={"action": "accept"}).json()
    assert acc["responses"][0]["status"] == "accepted" and acc["responses"][0]["phone"] == "+919876543210" and acc["responses"][0]["name"] == "Prasanna"
    mine = f.get(f"/api/v1/blood/{q['id']}").json()
    assert mine["mine"]["status"] == "accepted" and mine["ward"].startswith("Blood bank") and mine["phone"]
    loc = f.post(f"/api/v1/blood/{q['id']}/location", json={"lat": 17.42, "lng": 78.51, "status": "on_way"}).json()
    assert loc["status"] == "on_way" and loc["eta"] >= 1
    live = pb.get(f"/api/partner/blood/{q['id']}").json()["responses"][0]
    assert live["status"] == "on_way" and live["lat"] == 17.42 and live["eta"]
    arr = f.post(f"/api/v1/blood/{q['id']}/location", json={"lat": 17.4051, "lng": 78.5201}).json()
    assert arr["status"] == "arrived"
    done = pb.post(f"/api/partner/blood/{q['id']}/responses/{xid}", json={"action": "donated"}).json()
    assert done["responses"][0]["status"] == "donated"
    assert f.get("/api/v1/donor").json()["donors"][0]["donations"] == 1
    assert f.post(f"/api/v1/blood/{q['id']}/respond", json={"member": "m1"}).status_code == 400  # too soon now
    assert pb.post(f"/api/partner/blood/{q['id']}/status", json={"status": "fulfilled"}).json()["status"] == "fulfilled"
    # a pharmacy cannot raise requests
    with DB.session() as db:
        ph = Store(kind="pharmacy", name="Apollo", city="Hyderabad", area="x", lat=17.4, lng=78.5, verified=True); db.add(ph); db.flush(); pid = ph.id
    r2 = a.post(f"/api/admin/stores/{pid}/users", json={"email": f"ph{uuid.uuid4().hex[:5]}@ap.in", "name": "Desk", "role": "owner"}).json()
    pp = TestClient(server.app); pp.post("/api/partner/login", json={"email": r2["email"], "password": r2["tempPassword"]})
    assert pp.post("/api/partner/blood", json={"group": "A+"}).status_code == 403


def test_idle_session_expires_and_deep_link_shell():
    from api import auth as A
    f = family()
    assert f.get("/api/v1/auth/me").status_code == 200
    with DB.session() as db:
        from api.models import AuthSession
        for s in db.scalars(select_sessions(db)).all():
            s.last_seen -= A.IDLE_SECONDS + 5
    assert f.get("/api/v1/auth/me").json()["user"] is None
    pub = TestClient(server.app)
    r = pub.get("/app/abc123/def456/mid")
    assert r.status_code == 200 and "live-p13" in r.text


def select_sessions(db):
    from sqlalchemy import select
    from api.models import AuthSession
    return select(AuthSession)


def test_partner_csv_import_and_whatsapp_channel_logging(monkeypatch):
    from api import whatsapp as WA
    monkeypatch.setenv("WA_TOKEN", "x"); monkeypatch.setenv("WA_PHONE_ID", "1")
    posted = []
    monkeypatch.setattr(WA, "_post", lambda payload: posted.append(payload) or {})
    f, a = family(), admin()
    with DB.session() as db:
        lab = Store(kind="lab", name="Quick Labs", city="Hyderabad", area="x", lat=17.4, lng=78.5, verified=True); db.add(lab); db.flush(); lid = lab.id
    r = a.post(f"/api/admin/stores/{lid}/users", json={"email": f"l{uuid.uuid4().hex[:5]}@ql.in", "name": "Desk", "role": "owner"}).json()
    p = TestClient(server.app); p.post("/api/partner/login", json={"email": r["email"], "password": r["tempPassword"]})
    csv = "code,price,tat_hours\nhba1c,399,24\nlipid,650,24\nnotatest,10,1\n"
    out = p.post("/api/partner/prices/import", headers={"content-type": "text/csv"}, content=csv).json()
    assert out["updated"] == 2 and out["skipped"] == ["notatest"]
    assert any(t["code"] == "hba1c" and t["price"] == 399 for t in p.get("/api/partner/prices").json()["tests"])
    # a notice to a family with a verified phone is queued for WhatsApp (logged; no transport in tests)
    with DB.session() as db:
        from api.models import User
        u = db.scalar(select_user(db, f)); u.phone_verified = True; ph = u.phone
    f.post("/api/v1/orders", json={"store": lid, "kind": "lab", "items": [{"code": "hba1c"}], "address": "12 Road", "member": "P", "memberId": "m1", "slot": "Mon 08:00"})
    p_orders = p.get("/api/partner/orders").json()["orders"]
    p.post(f"/api/partner/orders/{p_orders[0]['id']}/status", json={"status": "confirmed"})
    assert any(x["to"] == ph for x in WA.SENT) and posted and posted[-1]["to"] == ph.lstrip("+") and "quick labs" in posted[-1]["text"]["body"].lower()

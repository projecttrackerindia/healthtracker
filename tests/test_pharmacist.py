"""A registered pharmacist checks the prescription, or it does not go out.

The family's status line has read "Pharmacist checking" since the first version of this app. Until now no
pharmacist was named, registered or recorded anywhere — the same shape of claim as the lab's old
"Phlebotomist assigned", and the same fix: make it true or stop saying it.

Run: python -m pytest -q tests/test_pharmacist.py
"""
import os
import uuid

os.environ.setdefault("OTP_DEMO", "1")
os.environ.setdefault("PWNED_CHECK", "0")
os.environ["DATABASE_URL"] = "sqlite:///./data/test_pharmacist.db"

from fastapi.testclient import TestClient  # noqa: E402

import server  # noqa: E402
from api.db import Base, engine, session  # noqa: E402
from api.models import Household, Order, PartnerUser, Store, StoredFile, now  # noqa: E402
from api.security import hash_pw  # noqa: E402

H = {"x-tht": "1"}
PW = "Zq!8vB#2mLp@9xT"
Base.metadata.create_all(engine)
_n = iter(range(10, 99))


def mobile():
    return f"98761{next(_n):02d}{uuid.uuid4().int % 1000:03d}"


def a_pharmacy(kind="pharmacy", owner_reg=""):
    tag = uuid.uuid4().hex[:8]
    with session() as db:
        s = Store(kind=kind, name=f"Apollo {tag}", city="Hyderabad", lat=17.44, lng=78.35, active=True)
        db.add(s)
        db.flush()
        owner = PartnerUser(store_id=s.id, email=f"o{tag}@ph.test", name="Owner", role="owner",
                            reg_no=owner_reg, pw_hash=hash_pw(PW), active=True, must_change=False)
        desk = PartnerUser(store_id=s.id, email=f"d{tag}@ph.test", name="Desk", role="staff",
                           pw_hash=hash_pw(PW), active=True, must_change=False)
        h = Household(key=uuid.uuid4().hex, name="Meera's family", city="Hyderabad")
        db.add_all([owner, desk, h])
        db.flush()
        return s.id, owner.email, desk.email, h.id


def an_order(sid, hid, rx=True, shared=True, status="checking"):
    with session() as db:
        fid = f"rx_{uuid.uuid4().hex[:8]}"
        if shared:
            db.add(StoredFile(household_id=hid, file_id=fid, name="rx.pdf", mime="application/pdf", blob=b"x", size=1))
        o = Order(household_id=hid, store_id=sid, kind="medicine", status=status,
                  items=[{"sku": "AMOX500", "name": "Amoxicillin 500mg", "price": 85, "qty": 10, "rx": rx},
                         {"sku": "PARA", "name": "Paracetamol 500mg", "price": 20, "qty": 10}],
                  total=105, payment="cod", rx_shared=shared, rx_files=[fid] if shared else [],
                  created=now())
        db.add(o)
        db.flush()
        return o.id


def signed_in(email):
    c = TestClient(server.app)
    c.__enter__()
    assert c.post("/api/partner/login", headers=H, json={"email": email, "password": PW}).status_code == 200
    return c


def add_pharmacist(owner_client, reg="AP/12345"):
    ph = mobile()
    r = owner_client.post("/api/partner/techs", json={"name": "Priya Nair", "phone": ph, "regNo": reg,
                                                      "role": "pharmacist"})
    assert r.status_code == 200, r.text
    return r.json(), ph


# ---------------------------------------------------------------- the roster
def test_a_pharmacy_owner_adds_a_registered_pharmacist():
    sid, owner, desk, hid = a_pharmacy()
    c = signed_in(owner)
    g, ph = add_pharmacist(c)
    assert g["regNo"] == "AP/12345" and g["role"] == "pharmacist"
    assert c.get("/api/partner/pharmacists").json()["pharmacists"][0]["name"] == "Priya Nair"


def test_a_pharmacist_without_a_registration_number_cannot_be_added():
    """Dispensing without a registered pharmacist is the offence; the number is who answers for it."""
    sid, owner, desk, hid = a_pharmacy()
    r = signed_in(owner).post("/api/partner/techs",
                              json={"name": "Priya Nair", "phone": mobile(), "role": "pharmacist"})
    assert r.status_code == 400 and "registration" in r.json()["detail"].lower()


def test_a_lab_has_no_pharmacists_and_a_pharmacy_has_no_technicians():
    lab_sid, lab_owner, _, _ = a_pharmacy(kind="lab")
    ph_sid, ph_owner, _, _ = a_pharmacy()
    assert signed_in(lab_owner).post("/api/partner/techs",
                                     json={"name": "Priya Nair", "phone": mobile(), "regNo": "AP/1",
                                           "role": "pharmacist"}).status_code == 400
    assert signed_in(ph_owner).post("/api/partner/techs",
                                    json={"name": "Ravi K", "phone": mobile(), "role": "tech"}).status_code == 400


def test_the_pharmacist_signs_in_with_their_mobile_and_must_choose_a_password():
    sid, owner, desk, hid = a_pharmacy()
    g, ph = add_pharmacist(signed_in(owner))
    c = TestClient(server.app)
    c.__enter__()
    me = c.post("/api/partner/login", headers=H, json={"email": ph, "password": g["tempPassword"]})
    assert me.status_code == 200 and me.json()["user"]["mustChange"] is True
    assert me.json()["user"]["regNo"] == "AP/12345"


# ---------------------------------------------------------------- the sign-off
def ready_pharmacist(sid, owner):
    """A pharmacist who has signed in and chosen a password, ready to work."""
    g, ph = add_pharmacist(signed_in(owner))
    c = TestClient(server.app)
    c.__enter__()
    c.post("/api/partner/login", headers=H, json={"email": ph, "password": g["tempPassword"]})
    c.post("/api/partner/password", json={"current": g["tempPassword"], "new": "MyOwnPass#2026"})
    return c, g


def test_a_prescription_order_cannot_be_packed_before_it_is_checked():
    sid, owner, desk, hid = a_pharmacy()
    oid = an_order(sid, hid)
    c = signed_in(owner)
    r = c.post(f"/api/partner/orders/{oid}/status", json={"status": "packing"})
    assert r.status_code == 400 and "registered pharmacist" in r.json()["detail"]
    with session() as db:
        assert db.get(Order, oid).status == "checking"


def test_an_order_with_nothing_prescription_only_needs_no_sign_off():
    sid, owner, desk, hid = a_pharmacy()
    oid = an_order(sid, hid, rx=False, shared=False)
    row = next(o for o in signed_in(owner).get("/api/partner/orders").json()["orders"] if o["id"] == oid)
    assert row["needsVerify"] is False
    assert signed_in(owner).post(f"/api/partner/orders/{oid}/status", json={"status": "packing"}).status_code == 200


def test_checking_it_records_who_checked_it_and_what_they_checked():
    sid, owner, desk, hid = a_pharmacy()
    oid = an_order(sid, hid)
    c, g = ready_pharmacist(sid, owner)
    r = c.post(f"/api/partner/orders/{oid}/verify",
               json={"doctor": "Dr A Sharma", "regNo": "TSMC/55512", "rxDate": "2026-10-19", "note": "Queried the dose; confirmed"})
    assert r.status_code == 200, r.text
    v = r.json()["verified"]
    assert v["by"] == "Priya Nair" and v["regNo"] == "AP/12345"
    assert v["doctor"] == "Dr A Sharma" and v["doctorReg"] == "TSMC/55512" and v["rxDate"] == "2026-10-19"
    assert r.json()["needsVerify"] is False
    # and now it can be packed
    assert signed_in(owner).post(f"/api/partner/orders/{oid}/status", json={"status": "packing"}).status_code == 200


def test_the_prescriber_and_their_registration_are_both_required():
    sid, owner, desk, hid = a_pharmacy()
    oid = an_order(sid, hid)
    c, g = ready_pharmacist(sid, owner)
    assert c.post(f"/api/partner/orders/{oid}/verify", json={"doctor": "", "regNo": "TSMC/5"}).status_code == 400
    assert c.post(f"/api/partner/orders/{oid}/verify", json={"doctor": "Dr A Sharma", "regNo": ""}).status_code == 400


def test_there_is_nothing_to_check_until_the_family_shares_the_prescription():
    sid, owner, desk, hid = a_pharmacy()
    oid = an_order(sid, hid, shared=False)
    c, g = ready_pharmacist(sid, owner)
    r = c.post(f"/api/partner/orders/{oid}/verify", json={"doctor": "Dr A Sharma", "regNo": "TSMC/5551"})
    assert r.status_code == 400 and "not shared" in r.json()["detail"]


def test_it_cannot_be_checked_twice():
    sid, owner, desk, hid = a_pharmacy()
    oid = an_order(sid, hid)
    c, g = ready_pharmacist(sid, owner)
    body = {"doctor": "Dr A Sharma", "regNo": "TSMC/55512"}
    assert c.post(f"/api/partner/orders/{oid}/verify", json=body).status_code == 200
    assert c.post(f"/api/partner/orders/{oid}/verify", json=body).status_code == 409


def test_the_counter_assistant_cannot_sign_a_prescription_off():
    """Which is the entire point of recording a registration number."""
    sid, owner, desk, hid = a_pharmacy()
    oid = an_order(sid, hid)
    r = signed_in(desk).post(f"/api/partner/orders/{oid}/verify",
                             json={"doctor": "Dr A Sharma", "regNo": "TSMC/55512"})
    assert r.status_code == 403


def test_an_owner_without_a_registration_number_is_asked_for_one_first():
    sid, owner, desk, hid = a_pharmacy()           # owner_reg deliberately blank
    oid = an_order(sid, hid)
    c = signed_in(owner)
    r = c.post(f"/api/partner/orders/{oid}/verify", json={"doctor": "Dr A Sharma", "regNo": "TSMC/55512"})
    assert r.status_code == 403 and "registration number" in r.json()["detail"]
    assert c.post("/api/partner/my-registration", json={"regNo": "ap/99887"}).json()["regNo"] == "AP/99887"
    assert c.post(f"/api/partner/orders/{oid}/verify",
                  json={"doctor": "Dr A Sharma", "regNo": "TSMC/55512"}).status_code == 200


def test_a_pharmacist_who_has_not_chosen_a_password_cannot_sign_anything_off():
    sid, owner, desk, hid = a_pharmacy()
    oid = an_order(sid, hid)
    g, ph = add_pharmacist(signed_in(owner))
    c = TestClient(server.app)
    c.__enter__()
    c.post("/api/partner/login", headers=H, json={"email": ph, "password": g["tempPassword"]})
    r = c.post(f"/api/partner/orders/{oid}/verify", json={"doctor": "Dr A Sharma", "regNo": "TSMC/55512"})
    assert r.status_code == 403 and "password" in r.json()["detail"].lower()


# ---------------------------------------------------------------- refusing
def test_refusing_tells_the_family_why():
    """"Cancelled" with no reason just sends them to the next pharmacy with the same prescription."""
    sid, owner, desk, hid = a_pharmacy()
    oid = an_order(sid, hid)
    c, g = ready_pharmacist(sid, owner)
    r = c.post(f"/api/partner/orders/{oid}/refuse",
               json={"reason": "The prescription is six months old; please get a fresh one."})
    assert r.status_code == 200 and r.json()["status"] == "cancelled"
    with session() as db:
        last = db.get(Order, oid).timeline[-1]
        assert "six months old" in last["reason"] and "Priya Nair" in last["note"]


def test_a_refusal_needs_an_actual_reason():
    sid, owner, desk, hid = a_pharmacy()
    oid = an_order(sid, hid)
    c, g = ready_pharmacist(sid, owner)
    assert c.post(f"/api/partner/orders/{oid}/refuse", json={"reason": "no"}).status_code == 400


def test_one_pharmacy_cannot_check_anothers_orders():
    sid_a, owner_a, _, hid_a = a_pharmacy()
    sid_b, owner_b, _, _ = a_pharmacy()
    oid = an_order(sid_a, hid_a)
    c, g = ready_pharmacist(sid_b, owner_b)
    assert c.post(f"/api/partner/orders/{oid}/verify",
                  json={"doctor": "Dr A Sharma", "regNo": "TSMC/55512"}).status_code == 404

"""Picking several orders at once, without letting an unchecked prescription slip through with them.

Run: python -m pytest -q tests/test_pharmacy_batch.py
"""
import os
import uuid

os.environ.setdefault("OTP_DEMO", "1")
os.environ.setdefault("PWNED_CHECK", "0")
os.environ["DATABASE_URL"] = "sqlite:///./data/test_pharmbatch.db"

from fastapi.testclient import TestClient  # noqa: E402

import server  # noqa: E402
from api.db import Base, engine, session  # noqa: E402
from api.models import Household, Order, PartnerUser, Store, StoredFile, now  # noqa: E402
from api.security import hash_pw  # noqa: E402

H = {"x-tht": "1"}
PW = "Zq!8vB#2mLp@9xT"
Base.metadata.create_all(engine)


def a_pharmacy(kind="pharmacy", reg="AP/40021"):
    tag = uuid.uuid4().hex[:8]
    with session() as db:
        s = Store(kind=kind, name=f"Apollo {tag}", city="Hyderabad", lat=17.44, lng=78.35, active=True)
        db.add(s)
        db.flush()
        owner = PartnerUser(store_id=s.id, email=f"o{tag}@ph.test", name="Owner", role="owner",
                            reg_no=reg, pw_hash=hash_pw(PW), active=True, must_change=False)
        h = Household(key=uuid.uuid4().hex, name="Meera's family", city="Hyderabad")
        db.add_all([owner, h])
        db.flush()
        return s.id, owner.email, h.id


def order(sid, hid, member, items, status="checking", shared=True, verified=False):
    with session() as db:
        fid = f"rx_{uuid.uuid4().hex[:8]}"
        needs_rx = any(i.get("rx") for i in items)
        if shared and needs_rx:
            db.add(StoredFile(household_id=hid, file_id=fid, name="rx.pdf", mime="application/pdf",
                              blob=b"x", size=1))
        o = Order(household_id=hid, store_id=sid, kind="medicine", status=status, member=member,
                  items=items, total=sum(i.get("price", 0) * i.get("qty", 1) for i in items),
                  payment="cod", rx_shared=bool(shared and needs_rx),
                  rx_files=[fid] if (shared and needs_rx) else [],
                  verified_at=now() if verified else None, created=now())
        db.add(o)
        db.flush()
        return o.id


def signed_in(email):
    c = TestClient(server.app)
    c.__enter__()
    assert c.post("/api/partner/login", headers=H, json={"email": email, "password": PW}).status_code == 200
    return c


AMOX = {"sku": "AMOX500", "name": "Amoxicillin 500mg", "price": 85, "qty": 2, "rx": True}
PARA = {"sku": "PARA", "name": "Paracetamol 500mg", "price": 20, "qty": 3}


def test_the_list_is_gathered_by_medicine_not_by_order():
    """A pharmacist with fifteen orders open does not walk the shelves fifteen times."""
    sid, owner, hid = a_pharmacy()
    order(sid, hid, "Meera", [dict(PARA, qty=3)])
    order(sid, hid, "Arjun", [dict(PARA, qty=5)])
    order(sid, hid, "Lakshmi", [dict(PARA, qty=1)])
    p = signed_in(owner).get("/api/partner/picklist").json()
    line = next(l for l in p["lines"] if l["sku"] == "PARA")
    assert line["qty"] == 9 and len(line["orders"]) == 3
    assert {o["member"] for o in line["orders"]} == {"Meera", "Arjun", "Lakshmi"}


def test_prescription_lines_come_first_so_they_are_picked_with_the_paperwork_in_hand():
    sid, owner, hid = a_pharmacy()
    order(sid, hid, "Meera", [dict(PARA, qty=20), dict(AMOX, qty=1)], verified=True)
    lines = signed_in(owner).get("/api/partner/picklist").json()["lines"]
    assert lines[0]["rx"] is True and lines[0]["sku"] == "AMOX500"


def test_an_unchecked_order_stays_on_the_list_and_says_it_is_waiting():
    """A picker who cannot see why an order is missing will assume the list is wrong."""
    sid, owner, hid = a_pharmacy()
    order(sid, hid, "Meera", [AMOX])                       # not verified
    p = signed_in(owner).get("/api/partner/picklist").json()
    assert p["waiting"] == 1 and p["ready"] == 0
    assert p["orders"][0]["waiting"] is True
    line = p["lines"][0]
    assert line["qty"] == 2 and line["waiting"] == 2       # counted, and held


def test_only_what_is_being_packed_appears():
    sid, owner, hid = a_pharmacy()
    order(sid, hid, "Meera", [PARA], status="placed")
    order(sid, hid, "Arjun", [PARA], status="delivered")
    order(sid, hid, "Lakshmi", [PARA], status="checking")
    p = signed_in(owner).get("/api/partner/picklist").json()
    assert len(p["orders"]) == 1 and p["orders"][0]["member"] == "Lakshmi"


def test_packing_the_batch_moves_every_ready_order():
    sid, owner, hid = a_pharmacy()
    a = order(sid, hid, "Meera", [PARA])
    b = order(sid, hid, "Arjun", [PARA])
    c = signed_in(owner)
    g = c.post("/api/partner/batch/pack", json={"orders": [a, b]}).json()
    assert sorted(g["packed"]) == sorted([a, b]) and g["skipped"] == []
    with session() as db:
        assert db.get(Order, a).status == "packing" and db.get(Order, b).status == "packing"


def test_one_unchecked_prescription_does_not_sink_the_whole_batch():
    """A batch that rolls everything back because of one order means doing the batch again by hand."""
    sid, owner, hid = a_pharmacy()
    good = order(sid, hid, "Meera", [PARA])
    bad = order(sid, hid, "Arjun", [AMOX])                 # not checked
    g = signed_in(owner).post("/api/partner/batch/pack", json={"orders": [good, bad]}).json()
    assert g["packed"] == [good]
    assert g["skipped"][0]["id"] == bad and "not been checked" in g["skipped"][0]["why"]
    with session() as db:
        assert db.get(Order, bad).status == "checking"


def test_a_checked_prescription_packs_with_the_rest():
    sid, owner, hid = a_pharmacy()
    a = order(sid, hid, "Meera", [PARA])
    b = order(sid, hid, "Arjun", [AMOX], verified=True)
    g = signed_in(owner).post("/api/partner/batch/pack", json={"orders": [a, b]}).json()
    assert sorted(g["packed"]) == sorted([a, b])


def test_packing_the_same_batch_twice_is_a_tap_not_an_error():
    sid, owner, hid = a_pharmacy()
    a = order(sid, hid, "Meera", [PARA])
    c = signed_in(owner)
    c.post("/api/partner/batch/pack", json={"orders": [a]})
    g = c.post("/api/partner/batch/pack", json={"orders": [a]}).json()
    assert g["packed"] == [a] and g["skipped"] == []


def test_an_order_at_the_wrong_step_is_named_with_the_reason():
    sid, owner, hid = a_pharmacy()
    a = order(sid, hid, "Meera", [PARA], status="placed")
    g = signed_in(owner).post("/api/partner/batch/pack", json={"orders": [a]}).json()
    assert g["packed"] == [] and "not checking" in g["skipped"][0]["why"]


def test_one_pharmacy_cannot_pack_anothers_orders():
    sid_a, owner_a, hid_a = a_pharmacy()
    sid_b, owner_b, _ = a_pharmacy()
    a = order(sid_a, hid_a, "Meera", [PARA])
    g = signed_in(owner_b).post("/api/partner/batch/pack", json={"orders": [a]}).json()
    assert g["packed"] == [] and g["skipped"][0]["why"] == "not one of your orders"
    with session() as db:
        assert db.get(Order, a).status == "checking"


def test_the_family_is_told_their_medicines_are_being_packed():
    sid, owner, hid = a_pharmacy()
    a = order(sid, hid, "Meera", [PARA])
    signed_in(owner).post("/api/partner/batch/pack", json={"orders": [a]})
    with session() as db:
        o = db.get(Order, a)
        assert o.timeline[-1]["s"] == "packing" and o.timeline[-1]["note"] == "picked in a batch"
    from api.models import Notice
    with session() as db:
        import sqlalchemy as sa
        n = db.scalars(sa.select(Notice).where(Notice.household_id == hid)).all()
        assert any("Packing" in x.title for x in n)


def test_a_lab_has_no_pick_list():
    sid, owner, hid = a_pharmacy(kind="lab")
    assert signed_in(owner).get("/api/partner/picklist").status_code == 400


def test_a_packed_order_leaves_the_list():
    """A list that does not shrink as you work it is one nobody trusts by the third batch of the morning."""
    sid, owner, hid = a_pharmacy()
    a = order(sid, hid, "Meera", [PARA])
    b = order(sid, hid, "Arjun", [AMOX])              # held: not checked
    c = signed_in(owner)
    assert len(c.get("/api/partner/picklist").json()["orders"]) == 2
    c.post("/api/partner/batch/pack", json={"orders": [a]})
    p = c.get("/api/partner/picklist").json()
    assert [o["id"] for o in p["orders"]] == [b]
    assert p["ready"] == 0 and p["waiting"] == 1
    # and the line it contributed went with it
    assert not any(l["sku"] == "PARA" for l in p["lines"])

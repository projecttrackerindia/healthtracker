"""Money: what each partner is owed, which way it flows, and whether it actually moved.

The monthly figures could always be recomputed from the orders. What could not was whether anybody had paid
them — so a month settled in March looked identical to one nobody had touched.

Run: python -m pytest -q tests/test_settlements.py
"""
import os
import uuid
from datetime import datetime, timedelta, timezone

os.environ.setdefault("OTP_DEMO", "1")
os.environ.setdefault("PWNED_CHECK", "0")
os.environ["PARTNER_FEE_PCT"] = "8"
os.environ["DATABASE_URL"] = "sqlite:///./data/test_settlements.db"

from fastapi.testclient import TestClient  # noqa: E402

import server  # noqa: E402
from api.db import Base, engine, session  # noqa: E402
from api.models import Admin, Household, Order, PartnerUser, Payout, Store, now  # noqa: E402
from api.security import hash_pw  # noqa: E402

H = {"x-tht": "1"}
PW = "Zq!8vB#2mLp@9xT"
IST = timezone(timedelta(hours=5, minutes=30))
Base.metadata.create_all(engine)
THIS_MONTH = datetime.now(IST).strftime("%Y-%m")


def a_store(kind="lab", pct=None):
    tag = uuid.uuid4().hex[:8]
    with session() as db:
        s = Store(kind=kind, name=f"Lucid {tag}", city="Hyderabad", lat=17.44, lng=78.35, active=True,
                  commission_pct=pct)
        db.add(s)
        db.flush()
        owner = PartnerUser(store_id=s.id, email=f"o{tag}@lab.test", name="Owner", role="owner",
                            pw_hash=hash_pw(PW), active=True, must_change=False)
        staff = PartnerUser(store_id=s.id, email=f"s{tag}@lab.test", name="Desk", role="staff",
                            pw_hash=hash_pw(PW), active=True, must_change=False)
        h = Household(key=uuid.uuid4().hex, name="Meera's family", city="Hyderabad")
        db.add_all([owner, staff, h])
        db.flush()
        return s.id, owner.email, staff.email, h.id


def completed(sid, hid, total, payment="cod", status="ready", kind="lab"):
    with session() as db:
        o = Order(household_id=hid, store_id=sid, kind=kind, status=status, items=[], total=total,
                  payment=payment, created=now())
        db.add(o)
        db.flush()
        return o.id


def admin():
    tag = uuid.uuid4().hex[:8]
    with session() as db:
        db.add(Admin(email=f"a{tag}@tht.test", pw_hash=hash_pw(PW), role="owner"))
    c = TestClient(server.app)
    c.__enter__()
    r = c.post("/api/admin/login", headers=H, json={"email": f"a{tag}@tht.test", "password": PW})
    assert r.status_code == 200, r.text
    return c


def partner(email):
    c = TestClient(server.app)
    c.__enter__()
    assert c.post("/api/partner/login", headers=H, json={"email": email, "password": PW}).status_code == 200
    return c


def row(adm, sid, month=THIS_MONTH):
    rows = adm.get(f"/api/admin/settlements?month={month}").json()["rows"]
    return next((r for r in rows if r["storeId"] == sid), None)


# ---------------------------------------------------------------- which way the money goes
def test_cash_at_the_door_is_owed_to_us_and_online_money_is_owed_to_them():
    sid, owner, staff, hid = a_store()
    completed(sid, hid, 1000, payment="cod")          # the lab already holds this
    completed(sid, hid, 2000, payment="upi-paid")     # we hold this
    r = row(admin(), sid)
    assert r["gross"] == 3000 and r["cod"] == 1000 and r["online"] == 2000
    assert r["dueFromPartner"] == 80                  # 8% of the cash they took
    assert r["payableToPartner"] == 1840              # 2000 less 8%
    assert r["net"] == 1760


def test_a_partner_on_their_own_rate_is_charged_that_rate():
    """Contracts differ. A launch partner on 0% is a real contract, so 0 cannot mean "unset"."""
    free_sid, free_owner, _, free_hid = a_store(pct=0)
    paid_sid, paid_owner, _, paid_hid = a_store(pct=12)
    completed(free_sid, free_hid, 1000, payment="cod")
    completed(paid_sid, paid_hid, 1000, payment="cod")
    adm = admin()
    assert row(adm, free_sid)["feePct"] == 0 and row(adm, free_sid)["dueFromPartner"] == 0
    assert row(adm, paid_sid)["feePct"] == 12 and row(adm, paid_sid)["dueFromPartner"] == 120


def test_an_admin_can_set_and_clear_a_partners_rate():
    sid, owner, staff, hid = a_store()
    adm = admin()
    assert adm.post(f"/api/admin/stores/{sid}/commission", json={"pct": 5}).json()["effective"] == 5
    assert adm.post(f"/api/admin/stores/{sid}/commission", json={"pct": None}).json()["effective"] == 8
    assert adm.post(f"/api/admin/stores/{sid}/commission", json={"pct": 90}).status_code == 400


def test_only_completed_work_counts():
    sid, owner, staff, hid = a_store()
    completed(sid, hid, 1000, status="collected")     # sample taken, no report: not done
    completed(sid, hid, 500, status="en_route")
    assert row(admin(), sid) is None
    completed(sid, hid, 1000, status="ready")
    assert row(admin(), sid)["gross"] == 1000


def test_a_refund_comes_out_of_the_month_it_falls_in():
    sid, owner, staff, hid = a_store()
    completed(sid, hid, 1000, payment="cod")
    completed(sid, hid, 400, payment="cod", status="refunded")
    r = row(admin(), sid)
    assert r["gross"] == 1000 and r["refunds"] == 400 and r["orders"] == 1


# ---------------------------------------------------------------- settling it
def test_settling_freezes_the_figures_and_records_who_paid_what():
    sid, owner, staff, hid = a_store()
    completed(sid, hid, 2000, payment="upi-paid")
    adm = admin()
    assert row(adm, sid)["settled"] is False

    p = adm.post(f"/api/admin/settlements/{THIS_MONTH}/{sid}", json={"ref": "UTR123456789", "note": "NEFT"})
    assert p.status_code == 200, p.text
    assert p.json()["net"] == 1840 and p.json()["ref"] == "UTR123456789"

    r = row(adm, sid)
    assert r["settled"] is True and r["settledRef"] == "UTR123456789" and r["settledNet"] == 1840

    # a later order does not quietly rewrite what was paid
    completed(sid, hid, 5000, payment="upi-paid")
    with session() as db:
        frozen = db.scalar(__import__("sqlalchemy").select(Payout).where(Payout.store_id == sid))
        assert frozen.net == 1840


def test_a_month_can_only_be_settled_once():
    sid, owner, staff, hid = a_store()
    completed(sid, hid, 1000, payment="upi-paid")
    adm = admin()
    assert adm.post(f"/api/admin/settlements/{THIS_MONTH}/{sid}", json={"ref": "A"}).status_code == 200
    again = adm.post(f"/api/admin/settlements/{THIS_MONTH}/{sid}", json={"ref": "B"})
    assert again.status_code == 409 and "already settled" in again.json()["detail"]


def test_a_settlement_recorded_in_error_can_be_undone():
    sid, owner, staff, hid = a_store()
    completed(sid, hid, 1000, payment="upi-paid")
    adm = admin()
    adm.post(f"/api/admin/settlements/{THIS_MONTH}/{sid}", json={"ref": "A"})
    assert adm.delete(f"/api/admin/settlements/{THIS_MONTH}/{sid}").status_code == 200
    assert row(adm, sid)["settled"] is False
    assert adm.post(f"/api/admin/settlements/{THIS_MONTH}/{sid}", json={"ref": "B"}).status_code == 200


def test_there_is_nothing_to_settle_for_a_month_with_no_completed_work():
    sid, owner, staff, hid = a_store()
    r = admin().post(f"/api/admin/settlements/{THIS_MONTH}/{sid}", json={"ref": "A"})
    assert r.status_code == 400 and "nothing to settle" in r.json()["detail"]


# ---------------------------------------------------------------- what the partner sees
def test_the_owner_sees_their_own_statement():
    sid, owner, staff, hid = a_store()
    completed(sid, hid, 1000, payment="cod")
    completed(sid, hid, 2000, payment="upi-paid")
    e = partner(owner).get("/api/partner/earnings?months=3").json()
    assert e["commissionPct"] == 8 and len(e["months"]) == 3
    m = e["months"][0]
    assert m["month"] == THIS_MONTH and m["gross"] == 3000
    assert m["weOweYou"] == 1840 and m["youOweUs"] == 80 and m["settled"] is False


def test_the_partner_statement_says_when_it_was_settled():
    sid, owner, staff, hid = a_store()
    completed(sid, hid, 2000, payment="upi-paid")
    admin().post(f"/api/admin/settlements/{THIS_MONTH}/{sid}", json={"ref": "UTR999"})
    m = partner(owner).get("/api/partner/earnings").json()["months"][0]
    assert m["settled"] is True and m["settledRef"] == "UTR999"


def test_the_statement_is_the_same_arithmetic_the_admin_settles_against():
    """Two computations would eventually disagree, and the partner would be the one who noticed."""
    sid, owner, staff, hid = a_store(pct=11)
    completed(sid, hid, 1700, payment="cod")
    completed(sid, hid, 2300, payment="upi-paid")
    a_row = row(admin(), sid)
    p_row = partner(owner).get("/api/partner/earnings").json()["months"][0]
    assert p_row["gross"] == a_row["gross"] and p_row["fee"] == a_row["fee"]
    assert p_row["weOweYou"] == a_row["payableToPartner"] and p_row["youOweUs"] == a_row["dueFromPartner"]


def test_money_is_the_owners_business_not_the_desks():
    sid, owner, staff, hid = a_store()
    assert partner(staff).get("/api/partner/earnings").status_code == 403
    assert partner(owner).get("/api/partner/earnings").status_code == 200


def test_one_store_cannot_see_anothers_earnings():
    sid_a, owner_a, _, hid_a = a_store()
    sid_b, owner_b, _, hid_b = a_store()
    completed(sid_a, hid_a, 9999, payment="cod")
    assert partner(owner_b).get("/api/partner/earnings").json()["months"][0]["gross"] == 0


def test_an_empty_month_still_appears_so_the_partner_can_see_it_is_empty():
    sid, owner, staff, hid = a_store()
    e = partner(owner).get("/api/partner/earnings?months=4").json()["months"]
    assert len(e) == 4 and all(m["gross"] == 0 for m in e)
    assert e[0]["feePct"] == 8          # the rate still shows, so they know what it will be


def test_the_csv_carries_what_was_settled():
    """Finance reconciles in a spreadsheet; a CSV that omits the reference is a CSV they cannot reconcile."""
    sid, owner, staff, hid = a_store()
    completed(sid, hid, 2000, payment="upi-paid")
    adm = admin()
    adm.post(f"/api/admin/settlements/{THIS_MONTH}/{sid}", json={"ref": "UTR777"})
    csv = adm.get(f"/api/admin/settlements.csv?month={THIS_MONTH}").text
    head, *body = [l for l in csv.strip().split("\n") if l]
    assert head.endswith("settled,settled_net_inr,settled_ref,settled_by")
    line = next(l for l in body if sid in l)
    assert "UTR777" in line and ",True," in line


def test_an_unsettled_row_leaves_the_settled_columns_empty_rather_than_writing_none():
    sid, owner, staff, hid = a_store()
    completed(sid, hid, 1000, payment="cod")
    csv = admin().get(f"/api/admin/settlements.csv?month={THIS_MONTH}").text
    line = next(l for l in csv.strip().split("\n") if sid in l)
    assert line.endswith("False,,,") and "None" not in line

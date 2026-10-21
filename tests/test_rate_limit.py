"""Rate limiting that holds across containers.

The limiter was a dict inside each process. That was right while the service ran pinned to one instance and
wrong the moment it did not: eight sign-in attempts per container is eight times eight across eight
containers. It is also why the service is still pinned.

These tests reach past the request layer and exercise the shared counter directly, because the thing under
test is precisely the part that is NOT in this process's memory.

Run: python -m pytest -q tests/test_rate_limit.py
"""
import os
import time
import uuid

os.environ.setdefault("OTP_DEMO", "1")
os.environ.setdefault("PWNED_CHECK", "0")
os.environ["DATABASE_URL"] = "sqlite:///./data/test_ratelimit.db"

import pytest  # noqa: E402
from fastapi import HTTPException  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import server  # noqa: E402
from api import auth  # noqa: E402
from api.db import Base, engine, session  # noqa: E402
from api.models import Admin, RateHit  # noqa: E402
from api.security import hash_pw  # noqa: E402

H = {"x-tht": "1"}
PW = "Zq!8vB#2mLp@9xT"
Base.metadata.create_all(engine)


class Req:
    """Just enough of a Request for the limiter: an address it can key on."""

    def __init__(self, ip):
        self.headers = {"x-forwarded-for": ip}
        self.client = None


def fresh_ip():
    return f"203.0.113.{uuid.uuid4().int % 250 + 1}.{uuid.uuid4().int % 9000}"


def another_container():
    """A second process would start with an empty dict and reach the same database."""
    auth._HITS.clear()


# ---------------------------------------------------------------- the counter is shared
def test_the_budget_is_not_multiplied_by_the_number_of_containers():
    ip, r = fresh_ip(), None
    r = Req(ip)
    for i in range(3):
        auth.limit(r, "t-share", 3, 60)
    another_container()                      # the next request lands on a different instance
    with pytest.raises(HTTPException) as e:
        auth.limit(r, "t-share", 3, 60)
    assert e.value.status_code == 429


def test_two_addresses_do_not_share_a_budget():
    a, b = Req(fresh_ip()), Req(fresh_ip())
    for _ in range(3):
        auth.limit(a, "t-two", 3, 60)
    auth.limit(b, "t-two", 3, 60)            # the other address is untouched
    with pytest.raises(HTTPException):
        auth.limit(a, "t-two", 3, 60)


def test_two_buckets_do_not_share_a_budget():
    r = Req(fresh_ip())
    for _ in range(3):
        auth.limit(r, "t-bucket-a", 3, 60)
    auth.limit(r, "t-bucket-b", 3, 60)


def test_the_window_slides_rather_than_resetting_on_a_boundary():
    """A fixed window lets a burst through at twice the rate as it rolls over, which on a sign-in endpoint is
    the exact thing being guarded against."""
    ip = fresh_ip()
    k = f"t-slide:{ip}"
    t = int(time.time())
    with session() as db:
        db.add(RateHit(k=k, hits=[t - 59, t - 58, t - 57], seen=t))
    another_container()
    with pytest.raises(HTTPException):
        auth.limit(Req(ip), "t-slide", 3, 60)
    # those three fall out of a 60s window as it moves on; a fixed window would have reset all three at once
    with session() as db:
        db.get(RateHit, k).hits = [t - 61, t - 62, t - 63]
    another_container()
    auth.limit(Req(ip), "t-slide", 3, 60)


def test_the_limiter_falls_open_when_the_database_cannot_be_reached():
    """A limiter that raises 500 on a database blip takes sign-in down with it. The in-process layer still
    holds, so this degrades to the old behaviour rather than to nothing."""
    r = Req(fresh_ip())
    boom = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("no database"))
    real = auth._shared
    auth._shared = boom
    try:
        with pytest.raises(RuntimeError):
            auth._shared()
        auth._shared = real
        import api.db as dbmod
        real_session = dbmod.session
        dbmod.session = boom
        try:
            for _ in range(3):
                auth.limit(r, "t-open", 3, 60)   # local layer only; no exception from the database
            with pytest.raises(HTTPException):
                auth.limit(r, "t-open", 3, 60)   # and it still stops at three
        finally:
            dbmod.session = real_session
    finally:
        auth._shared = real


def test_a_spent_bucket_leaves_no_entry_behind_in_memory():
    """One empty deque per attacking address, never removed, is a slow leak with an attacker holding the tap."""
    ip = fresh_ip()
    r = Req(ip)
    auth.limit(r, "t-leak", 3, 1)
    assert f"t-leak:{ip}" in auth._HITS
    time.sleep(1.1)
    auth.limit(r, "t-leak", 3, 1)
    # the stale entry was dropped and replaced, not accumulated
    assert len(auth._HITS[f"t-leak:{ip}"]) == 1


# ---------------------------------------------------------------- sign-in counts failures, not attempts
def an_admin():
    email = f"a{uuid.uuid4().hex[:8]}@tht.test"
    with session() as db:
        db.add(Admin(email=email, pw_hash=hash_pw(PW), role="owner"))
    return email


def client(ip):
    c = TestClient(server.app)
    c.__enter__()
    c.headers["x-forwarded-for"] = ip
    return c


def test_signing_in_correctly_over_and_over_is_not_an_attack():
    email, ip = an_admin(), fresh_ip()
    c = client(ip)
    for _ in range(12):
        assert c.post("/api/admin/login", headers=H, json={"email": email, "password": PW}).status_code == 200


def test_eight_wrong_passwords_closes_the_door():
    email, ip = an_admin(), fresh_ip()
    c = client(ip)
    for _ in range(8):
        assert c.post("/api/admin/login", headers=H, json={"email": email, "password": "nope"}).status_code == 401
    # even the right password now waits
    assert c.post("/api/admin/login", headers=H, json={"email": email, "password": PW}).status_code == 429


def test_the_closed_door_follows_the_address_to_another_container():
    email, ip = an_admin(), fresh_ip()
    c = client(ip)
    for _ in range(8):
        c.post("/api/admin/login", headers=H, json={"email": email, "password": "nope"})
    another_container()
    assert client(ip).post("/api/admin/login", headers=H, json={"email": email, "password": PW}).status_code == 429


def test_getting_in_forgets_the_near_misses():
    """A fat-fingered morning should not lock out the afternoon."""
    email, ip = an_admin(), fresh_ip()
    c = client(ip)
    for _ in range(7):
        c.post("/api/admin/login", headers=H, json={"email": email, "password": "nope"})
    assert c.post("/api/admin/login", headers=H, json={"email": email, "password": PW}).status_code == 200
    for _ in range(7):
        assert c.post("/api/admin/login", headers=H, json={"email": email, "password": "nope"}).status_code == 401


def test_one_address_failing_does_not_lock_out_another():
    email = an_admin()
    bad, good = client(fresh_ip()), client(fresh_ip())
    for _ in range(8):
        bad.post("/api/admin/login", headers=H, json={"email": email, "password": "nope"})
    assert good.post("/api/admin/login", headers=H, json={"email": email, "password": PW}).status_code == 200


def test_the_partner_portal_is_guarded_the_same_way():
    from api.models import PartnerUser, Store

    tag = uuid.uuid4().hex[:8]
    with session() as db:
        s = Store(kind="lab", name=f"L{tag}", city="Hyderabad", lat=17.44, lng=78.35, active=True)
        db.add(s)
        db.flush()
        db.add(PartnerUser(store_id=s.id, email=f"p{tag}@lab.test", role="owner",
                           pw_hash=hash_pw(PW), active=True, must_change=False))
    ip = fresh_ip()
    c = client(ip)
    for _ in range(8):
        assert c.post("/api/partner/login", headers=H, json={"email": f"p{tag}@lab.test", "password": "nope"}).status_code == 401
    another_container()
    assert client(ip).post("/api/partner/login", headers=H,
                           json={"email": f"p{tag}@lab.test", "password": PW}).status_code == 429

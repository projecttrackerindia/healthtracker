import os
import glob as _glob

# Every test writes sqlite:///./data/test_<name>.db, and /data/ is git-ignored — so it does not exist in a
# fresh clone and SQLite cannot create a file inside a directory that is not there. The suite passed for
# everyone who had run the app locally and failed for everyone who had not, which is the worst way for a test
# suite to behave: green on the machine that wrote it, red on CI and on a new contributor's first morning.
os.makedirs("./data", exist_ok=True)

for _old in _glob.glob("./data/test_*.db*"):  # every run starts from an empty store (fixed UTRs, stock counts and the like must not carry over)
    try:
        os.remove(_old)
    except OSError:
        pass
os.environ.setdefault("APP_ENV", "test")   # demo one-time codes are refused in production

import pytest


@pytest.fixture(autouse=True)
def _reset_rate_limits():
    """Both layers of the limiter, between every test.

    The in-process deque is not the whole story any more: the counter is also kept in the database so that it
    holds across containers, and that half survives everything the test harness does to memory. Left alone, a
    full suite run spends the signup budget somewhere around the ninth test that signs anybody up, and every
    test after that gets a 429 from a limiter that is working exactly as intended."""
    from api import auth
    auth._HITS.clear()
    _clear_shared()
    yield
    auth._HITS.clear()
    _clear_shared()


def _clear_shared():
    try:
        from api.db import session
        from api.models import RateHit
        with session() as db:
            db.query(RateHit).delete()
    except Exception:
        pass        # the table does not exist yet on the very first test to touch the database


# Home visits and deliveries now need a full address with a map pin. Older tests send only a text address,
# so give those requests a complete address at the store's own location (they are not testing the address rules).
import pytest as _pt


@_pt.fixture(autouse=True)
def _full_address(monkeypatch):
    from fastapi.testclient import TestClient as _TC
    orig = _TC.post

    def post(self, url, *a, **k):
        j = k.get("json")
        if isinstance(j, dict) and str(url).startswith("/api/v1/orders") and url.rstrip("/") == "/api/v1/orders" and "addr" not in j and j.get("address") != "x":
            from api.db import SessionLocal
            from api.models import Store
            with SessionLocal() as db:
                s = db.get(Store, j.get("store"))
                if s is not None:
                    pin = ((s.profile or {}).get("pins") or [None])[0] or "500081"
                    j = {**j, "addr": {"line1": "Flat 1", "line2": j.get("address") or "Main road", "landmark": "Near the park", "pin": pin,
                                       "lat": s.lat or 17.44, "lng": s.lng or 78.38}}
                    k["json"] = j
        import re as _re
        m = _re.match(r"/api/(?:partner/orders/([^/]+)/status|tech/jobs/([^/]+)/collected)$", str(url))
        if m and isinstance(j, dict) and "code" not in j and (j.get("status") in ("collected", "delivered") or m.group(2)):
            from api.db import SessionLocal
            from api.models import Order
            with SessionLocal() as db:
                o = db.get(Order, m.group(1) or m.group(2))
                if o is not None and o.door_code:
                    k["json"] = {**j, "code": o.door_code}
        return orig(self, url, *a, **k)

    monkeypatch.setattr(_TC, "post", post)


# Partner sign-ins are created with a one-time set-up link now; nobody is handed a password. Older tests were
# written against the temporary-password flow and are testing other things (rosters, prescriptions, consults), so
# this completes the link exactly as the person would (open it, choose a password) and hands the test that
# password under the old key. Doctors and pharmacists created here are also treated as already approved by two
# admins; the approval rules themselves are tested on their own in test_enterprise_admin.py.
_SETUP_ROUTES = r"/api/(admin/stores/[^/]+/users(/[^/]+/reset)?|partner/techs(/[^/]+/reset)?)$"


@_pt.fixture(autouse=True)
def _complete_setup_links(monkeypatch):
    import json as _json
    import re as _re
    import secrets as _sec
    from fastapi.testclient import TestClient as _TC
    orig = _TC.post

    def post(self, url, *a, **k):
        r = orig(self, url, *a, **k)
        if r.status_code == 200 and _re.match(_SETUP_ROUTES, str(url)):
            try:
                j = r.json()
            except Exception:
                return r
            link = j.get("demoLink") or ""
            if link:
                while True:   # a random password that passes the same rules a person's would
                    pw = "Tmp#" + _sec.token_hex(6) + "Aa1"
                    from api.passwords import check as _pwcheck
                    if not _pwcheck(pw):   # the server's own rules, so this never trips over a rule added later
                        break
                import server
                c = _TC(server.app)
                c.__enter__()
                jr = orig(c, "/api/partner/join", json={"token": link.rsplit("/", 1)[1], "password": pw}, headers={"x-tht": "1"})
                assert jr.status_code == 200, jr.text
                from api.db import SessionLocal
                from api.models import PartnerUser
                with SessionLocal() as db:
                    u = db.get(PartnerUser, j.get("id"))
                    if u is not None:
                        u.must_change = True
                        if u.role in ("doctor", "pharmacist", "owner"):
                            u.reg_doc, u.reg_expiry = "test", "2099-12-31"   # certificate on file
                        if u.role in ("pharmacist", "owner"):
                            u.verified, u.verify_by = True, "tests"           # doctors go through two-admin approval in the tests
                        db.commit()
                        if not j.get("email") or str(j.get("email")).endswith(".invalid"):
                            j.setdefault("email", u.email)
                j["tempPassword"] = pw
                r._content = _json.dumps(j).encode()
        return r

    monkeypatch.setattr(_TC, "post", post)

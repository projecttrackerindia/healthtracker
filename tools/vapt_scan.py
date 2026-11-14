"""Automated VAPT pass over every route the server exposes.

    python tools/vapt_scan.py            # prints findings, exits 1 if any

1. Unauthenticated: every /api route is called with no session. Anything that answers 2xx and is not on the
   PUBLIC list below is a finding (missing auth).
2. Cross-account (IDOR): user A creates a family member and a record; user B, signed in, calls every route that
   takes an id with A's ids. Any 2xx is a finding.
3. CSRF: state-changing calls without the X-THT header must be refused.
4. Headers and cookies: security headers on pages and the API, session cookie flags.
"""
from __future__ import annotations

import os
import re
import sys
import uuid

os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("OTP_DEMO", "1")
os.environ.setdefault("DATABASE_URL", "sqlite:///./data/vapt_scan.db")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.makedirs("./data", exist_ok=True)
try:
    os.remove("./data/vapt_scan.db")
except OSError:
    pass

from fastapi.routing import APIRoute  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import server  # noqa: E402

# Intentionally public: the site, sign-in itself, lookups that reveal nothing personal, and webhooks that carry
# their own signature checks. Patterns are matched against the route path.
PUBLIC = [
    r"^/api/v1/auth/(config|signup/start|signup/verify|otp/start|otp/verify|password/login|password/reset|step/verify|"
    r"passkey/.*|google|rsms/.*|logout|contact/start|contact/verify)$",
    r"^/api/v1/config$", r"^/api/v1/plans$", r"^/api/v1/app/(android|ios)$", r"^/api/health$", r"^/healthz$",
    r"^/api/v2/services$", r"^/api/v1/digilocker/status$", r"^/api/v1/partner/apply$", r"^/api/partner/join",
    r"^/api/v2/household/invite/", r"^/api/v1/family/invite/", r"^/api/v1/errors?$", r"^/api/v1/client-error",
    r"^/api/v1/i18n", r"^/api/v1/places/", r"^/api/v1/public", r"/webhook", r"^/api/v1/payments/razorpay/webhook",
    r"^/api/v1/whatsapp/hook", r"^/api/v1/sms/", r"^/api/v1/csp-report", r"^/api/v1/geo", r"^/api/v1/network",
    r"^/api/v2/doctor-shares/[^/]+/qr\.svg$", r"^/api/v1/abdm/callback", r"^/api/v1/digilocker/callback",
    r"^/api/v1/oauth/", r"^/api/v1/wearables/.*/callback", r"^/api/v1/fitbit/callback",
    # reviewed Nov 2026: catalogues and reference data with nothing personal in them
    r"^/api/v1/(stores|visit-tags|labs/tests|seasonal|videos|hospitals|returns/policy|shop/products|push/key|settings|"
    r"abha/status|fitbit/status|wear/status|sos/channels)$", r"^/api/v2/(catalog/packages|privacy/contact|serviceable|schemes|"
    r"schemes/check|schemes/doctors|client-error)$", r"^/api/v1/auth/me$", r"^/api/(admin|partner)/logout$",
    # reviewed Nov 2026: the classic app's household-key routes answer an empty list without a valid key
    r"^/api/v1/(orders|inbox|inbox/read|appointments|messages/threads|medical-id|pay/upi|donor|blood/requests)$",
]

findings: list[str] = []


def fill(path: str, ids: dict | None = None) -> str:
    ids = ids or {}
    def rep(m):
        k = m.group(1).split(":")[0]
        return str(ids.get(k, ids.get("*", "x" + uuid.uuid4().hex[:10])))
    return re.sub(r"\{([^}]+)\}", rep, path)


def _flat(rs, prefix=""):
    for r in rs:
        if isinstance(r, APIRoute):
            yield prefix + r.path, r
        elif hasattr(r, "original_router"):   # FastAPI 0.16x keeps included routers as a node
            yield from _flat(r.original_router.routes, prefix + (r.include_context.prefix or ""))
        elif hasattr(r, "routes"):
            yield from _flat(r.routes, prefix + getattr(r, "path", ""))


def routes():
    seen = set()
    for path, r in _flat(server.app.routes):
        if path.startswith("/api"):
            for m in sorted(r.methods - {"HEAD", "OPTIONS"}):
                if (m, path) not in seen:
                    seen.add((m, path))
                    yield m, path


def signup(c: TestClient, tag: str) -> dict:
    u = uuid.uuid4().hex[:6]
    phone = "9" + str(uuid.uuid4().int)[-9:].zfill(9)
    r = c.post("/api/v1/auth/signup/start", json={"name": f"Vapt {tag}", "email": f"v{tag}{u}@ex.com", "phone": phone,
                                                    "password": "Zq!8vB#2mLp@9xT", "terms": True})
    assert r.status_code == 200, r.text
    d = r.json()
    r = c.post("/api/v1/auth/signup/verify", json={"flow": d["flow"], "code": d["demo"]})
    assert r.status_code == 200, r.text
    return r.json()


def main() -> int:
    with TestClient(server.app, base_url="https://urbanhealth.in") as anon:
        # ---- 1. unauthenticated -------------------------------------------------------------------------------
        open_routes = []
        for m, p in routes():
            if any(re.search(x, p) for x in PUBLIC):
                continue
            r = anon.request(m, fill(p), headers={"x-tht": "1"}, json={} if m != "GET" else None)
            if 200 <= r.status_code < 300:
                open_routes.append(f"{m} {p} -> {r.status_code}")
        for o in open_routes:
            findings.append("NO-AUTH " + o)

        # ---- 3. CSRF ------------------------------------------------------------------------------------------
        a = TestClient(server.app, base_url="https://urbanhealth.in")
        a.headers.update({"x-tht": "1"})
        signup(a, "a")
        r = a.post("/api/v2/people", json={"name": "Child A", "dependent": True, "same_ok": True, "profile": {"dob": "2019-01-01", "sex": "female"}},
                   headers={"x-tht": ""})
        if r.status_code < 400:
            findings.append(f"CSRF POST /api/v2/people without X-THT -> {r.status_code}")

        # ---- 2. cross-account ---------------------------------------------------------------------------------
        r = a.post("/api/v2/people", json={"name": "Child A", "dependent": True, "same_ok": True, "profile": {"dob": "2019-01-01", "sex": "female"}})
        pid = (r.json() or {}).get("id") if r.status_code == 200 else None
        rid = None
        if pid:
            r = a.post(f"/api/v2/people/{pid}/records", json={"kind": "med", "data": {"name": "Secretmed A", "dose": "1"}})
            if r.status_code == 200:
                rid = r.json().get("id")
            else:
                print("record create failed:", r.status_code, r.text[:200])
        me_a = a.get("/api/v1/auth/me").json().get("user") or {}
        b = TestClient(server.app, base_url="https://urbanhealth.in")
        b.headers.update({"x-tht": "1"})
        signup(b, "b")
        ids = {"pid": pid, "person_id": pid, "rid": rid, "record_id": rid, "id": rid or pid, "uid": me_a.get("id"),
               "user_id": me_a.get("id"), "*": pid}
        leaks = []
        for m, p in routes():
            if "{" not in p or p.startswith("/api/admin") or any(re.search(x, p) for x in PUBLIC):
                continue
            if m == "DELETE":
                continue  # destructive probes are done by hand
            r = b.request(m, fill(p, ids), json={} if m != "GET" else None)
            if 200 <= r.status_code < 300 and ("Secretmed" in r.text or "Child A" in r.text or m != "GET"):
                leaks.append(f"{m} {p} -> {r.status_code} {r.text[:80]!r}")
        for l in leaks:
            findings.append("IDOR " + l)
        print(f"cross-account ids: person={pid} record={rid}")

        # ---- 4. headers and cookies ---------------------------------------------------------------------------
        need = {"content-security-policy", "strict-transport-security", "x-content-type-options", "referrer-policy",
                "permissions-policy"}
        for path in ("/", "/app", "/partner", "/api/v1/config", "/s/authfx.js", "/no-such-page"):
            h = {k.lower() for k in anon.get(path).headers}
            miss = need - h
            if path.startswith("/api") or path.endswith(".js"):
                miss -= {"content-security-policy", "permissions-policy"}
            if miss:
                findings.append(f"HEADERS {path} missing {sorted(miss)}")
        c2 = TestClient(server.app, base_url="https://urbanhealth.in")
        c2.headers.update({"x-tht": "1"})
        u = uuid.uuid4().hex[:6]
        r = c2.post("/api/v1/auth/signup/start", json={"name": "Cookie T", "email": f"ck{u}@ex.com", "phone": "9" + str(uuid.uuid4().int)[-9:].zfill(9), "password": "Zq!8vB#2mLp@9xT", "terms": True})
        r = c2.post("/api/v1/auth/signup/verify", json={"flow": r.json()["flow"], "code": r.json()["demo"]})
        for sc in r.headers.get_list("set-cookie"):
            low = sc.lower()
            name = sc.split("=", 1)[0]
            for flag in ("httponly", "secure", "samesite"):
                if flag not in low:
                    findings.append(f"COOKIE {name} missing {flag}")

        # ---- 5. a few classic probes --------------------------------------------------------------------------
        for p in ("/.env", "/.git/config", "/server.py", "/api/../server.py", "/s/../server.py", "/data/app.db",
                  "/api/v1/openapi.json", "/docs", "/redoc"):
            r = anon.get(p)
            if r.status_code == 200 and ("DATABASE" in r.text or "[core]" in r.text or "import " in r.text or '"paths"' in r.text):
                findings.append(f"EXPOSED {p} -> {r.status_code}")
        r = a.post("/api/v1/auth/password/login", json={"id": "nobody@ex.com", "password": "x" * 20})
        hits = [a.post("/api/v1/auth/password/login", json={"id": "nobody@ex.com", "password": "x" * 20}).status_code for _ in range(40)]
        if 429 not in hits:
            findings.append("RATE-LIMIT password login: 40 tries in a row never answered 429")

    print(f"{len(findings)} finding(s)")
    for f in findings:
        print(" -", f)
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())

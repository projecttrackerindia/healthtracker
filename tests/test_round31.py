"""Round 31: the shop comes first — Book a test, Order medicines, and the three engines end in a basket.
Also: ten documents a day for the AI. Run: python -m pytest -q tests/test_round31.py"""
import os
import uuid
from pathlib import Path

os.environ.setdefault("OTP_DEMO", "1")
os.environ.setdefault("PWNED_CHECK", "0")
os.environ["DATABASE_URL"] = "sqlite:///./data/test_round31.db"

from fastapi.testclient import TestClient  # noqa: E402

import server  # noqa: E402
from api import routes  # noqa: E402
from api.db import SessionLocal  # noqa: E402
from api.models import AiJob, Household, now  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
H = {"x-tht": "1"}


def client():
    c = TestClient(server.app)
    c.__enter__()
    c.headers["X-DoKKo-Key"] = uuid.uuid4().hex
    c.post("/api/v1/hello", headers=H, json={"name": "Raghavan", "members": 3})
    return c


def household_of(key):
    from sqlalchemy import select
    s = SessionLocal()
    return s, s.scalar(select(Household).where(Household.key == key))


# ---------------------------------------------------------------- ten documents a day
def test_ten_documents_a_day_counted_per_family_and_only_for_documents():
    assert routes.AI_DAY_DOCS == 10
    c = client()
    s, h = household_of(c.headers["X-DoKKo-Key"])
    assert routes.docs_today(s, h) == 0
    for kind in ("report", "prescription", "card", "policy"):
        s.add(AiJob(household_id=h.id, kind=kind, engine="claude", ms=1))
    s.add(AiJob(household_id=h.id, kind="ask", engine="claude", ms=1))          # questions have their own limit
    s.add(AiJob(household_id=h.id, kind="insight", engine="claude", ms=1))
    s.add(AiJob(household_id=h.id, kind="report", engine="local", ms=1))        # the basic reader is not rationed
    s.add(AiJob(household_id=h.id, kind="report", engine="claude", ms=1, t=now() - 2 * 86400))   # yesterday does not count
    s.commit()
    assert routes.docs_today(s, h) == 4
    for _ in range(6):
        s.add(AiJob(household_id=h.id, kind="report", engine="claude", ms=1))
    s.commit()
    assert routes.docs_today(s, h) == 10
    s.close()
    # the app is told where it stands
    j = c.post("/api/v1/hello", headers=H, json={"name": "Raghavan", "members": 3}).json()
    assert j["ai"]["dayCap"] == 10 and j["ai"]["today"] == 10


def test_the_eleventh_document_falls_back_to_the_basic_reader_with_a_plain_message(monkeypatch):
    from api import ai as AI
    monkeypatch.setattr(AI, "available", lambda: True)
    c = client()
    s, h = household_of(c.headers["X-DoKKo-Key"])
    for _ in range(routes.AI_DAY_DOCS):
        s.add(AiJob(household_id=h.id, kind="report", engine="claude", ms=1))
    s.commit()
    s.close()
    r = c.post("/api/v1/ai/analyze", headers=H, data={"kind": "report", "consent": "1", "text": "Haemoglobin 11.2 g/dL"})
    assert r.status_code == 200
    j = r.json()
    assert j["engine"] != "claude"                       # read locally, nothing lost
    assert any("10 documents read today" in w for w in j.get("warnings", []))
    assert "upgrade" not in " ".join(j.get("warnings", [])).lower()     # there is nothing to upgrade to
    assert j["quota"]["dayCap"] == 10 and j["quota"]["today"] >= 10


# ---------------------------------------------------------------- the shop in front
def test_the_page_puts_the_shop_first_and_wires_the_three_engines():
    html = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
    assert "/*live-p31*/" in html
    # the tab order
    assert "rec.tabs=['labshop','tests','vault','insights']" in html
    assert "med.tabs=['finder','rx','orders']" in html
    # the booking page exists and the engines reach it
    assert "SX.reg('labshop'" in html and "function dueRows" in html and "PACKS=" in html
    assert "SX.suggestions=suggestions;" in html and "SX.medCatalog=()=>C;" in html and "SX.placesHTML=placesHTML;" in html
    assert "SX.labOpen=(codes,sel)=>SX.act.labs(" in html
    # the three dead ends are gone
    assert "SX.act.labgo=([id])=>" in html                       # a partner lab opens the price sheet, not the results page
    assert "SX.act.refill=([id])=>{const m=SX.me()" in html      # reorder fills the basket, not a search box
    # honest prices: a typical price, never an invented floor
    assert "typical(codes)*.75" not in html and "P('about')" in html


def test_signing_out_lands_on_the_sign_in_screen_not_the_marketing_page():
    html = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
    assert "SX.act.signout=async()=>{try{await loadAuthJs();await THT.api('/logout',{})}catch(e){}location.href='/signin'};" in html
    assert "location.href='/'}" not in html          # nothing in the app drops a signed-out family on the website
    # /signin is served by the site and opens the sign-in sheet, which carries "Create an account"
    site = (ROOT / "site" / "index.html").read_text(encoding="utf-8")
    assert "'/signin':'signin'" in site and "Create an account" in site


def test_the_morning_nudge_sends_people_to_the_booking_page():
    src = (ROOT / "api" / "proactive.py").read_text(encoding="utf-8")
    assert "/app#page=labshop" in src and "#page=nearlabs" not in src


def test_the_lab_catalogue_backs_the_packages():
    c = client()
    tests = {t["code"]: t for t in c.get("/api/v1/labs/tests", headers=H).json()["tests"]}
    for code in ("cbc", "lipid", "hba1c", "tsh", "thy", "vitd", "kft", "lft", "urine", "pap", "psa", "ecg", "echo", "iron", "b12", "ogtt", "usg", "glu_f", "glu_pp", "ferr"):
        assert code in tests or code in ("ferr",), code       # every code the packages and the due-map use
        if code in tests:
            assert tests[code]["name"] and tests[code]["typical"] > 0

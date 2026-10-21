"""Round 30: the launch period — every feature free until 31 March 2027, nothing to buy, one switch to end it.

Run: python -m pytest -q tests/test_round30.py
"""
import os
import uuid
from datetime import date
from pathlib import Path

import pytest

os.environ.setdefault("OTP_DEMO", "1")
os.environ.setdefault("PWNED_CHECK", "0")
os.environ["DATABASE_URL"] = "sqlite:///./data/test_round30.db"

from fastapi.testclient import TestClient  # noqa: E402

import server  # noqa: E402
from api import launch, routes  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
H = {"x-tht": "1"}


def client():
    c = TestClient(server.app)
    c.__enter__()
    c.headers["X-DoKKo-Key"] = uuid.uuid4().hex
    c.post("/api/v1/hello", headers=H, json={"name": "Raghavan", "members": 3})
    return c


def test_the_launch_period_is_on_by_default_and_ends_on_31_march_2027():
    assert launch.until() == date(2027, 3, 31)
    assert launch.free_now() is True and launch.label() == "31 March 2027"
    assert launch.state() == {"free": True, "until": launch.until_ts(), "label": "31 March 2027"}
    # every family reads as the top plan while it runs, whatever is stored against them
    stored_free = type("H", (), {"plan": "free"})()
    assert launch.plan_of(stored_free) == "plus"


def test_one_environment_variable_ends_it_and_the_stored_plans_come_back(monkeypatch):
    monkeypatch.setenv("FREE_UNTIL", "")
    assert launch.free_now() is False and launch.until_ts() is None and launch.label() == ""
    assert launch.plan_of(type("H", (), {"plan": "free"})()) == "free"
    assert launch.plan_of(type("H", (), {"plan": "family"})()) == "family"
    # a date in the past ends it too, and a malformed one is ignored rather than crashing the app
    monkeypatch.setenv("FREE_UNTIL", "2020-01-01")
    assert launch.free_now() is False
    monkeypatch.setenv("FREE_UNTIL", "whenever")
    assert launch.until() is None and launch.free_now() is False


def test_the_app_is_told_everything_is_free_and_no_plan_is_priced():
    c = client()
    cfg = c.get("/api/v1/config", headers=H).json()
    assert cfg["launch"]["free"] is True and cfg["launch"]["label"] == "31 March 2027"
    hello = c.post("/api/v1/hello", headers=H, json={"name": "Raghavan", "members": 3}).json()
    assert hello["plan"] == "plus" and hello["planUntil"] is None and hello["launch"]["free"] is True
    assert hello["ai"]["cap"] == routes.AI_CAP["plus"]        # no monthly limit a family would ever meet
    plans = c.get("/api/v1/plans", headers=H).json()
    assert plans["launch"]["free"] is True and plans["current"] == "plus" and plans["until"] is None
    assert [p["month"] for p in plans["plans"]] == [0] * len(plans["plans"])
    assert [p["year"] for p in plans["plans"]] == [0] * len(plans["plans"])
    assert any(p["listMonth"] > 0 for p in plans["plans"])    # the future prices are still on file, just not charged


def test_nothing_can_be_sold_while_everything_is_free():
    c = client()
    r = c.post("/api/v1/subscribe", headers=H, json={"plan": "plus", "period": "year"})
    assert r.status_code == 400 and "31 March 2027" in r.json()["detail"]
    r = c.post("/api/v1/pay/upi/start", headers=H, json={"kind": "plan", "plan": "family", "period": "month"})
    assert r.status_code in (400, 503)
    if r.status_code == 400:
        assert "31 March 2027" in r.json()["detail"]
    # the family is still on the free-for-all plan afterwards, with no invoice and no end date
    j = c.get("/api/v1/plans", headers=H).json()
    assert j["current"] == "plus" and j["until"] is None and j["history"] == []


def test_a_paid_plan_still_works_the_day_the_launch_period_ends(monkeypatch):
    monkeypatch.setenv("FREE_UNTIL", "")
    monkeypatch.setenv("APP_ENV", "dev")
    c = client()
    plans = c.get("/api/v1/plans", headers=H).json()
    assert plans["launch"]["free"] is False
    paid = next(p for p in plans["plans"] if p["month"] > 0)
    assert paid["month"] == paid["listMonth"]
    r = c.post("/api/v1/subscribe", headers=H, json={"plan": paid["code"], "period": "month"})
    assert r.status_code == 200 and r.json()["invoice"].startswith("THT-")
    assert c.get("/api/v1/plans", headers=H).json()["current"] == paid["code"]


def test_no_plan_lapses_or_renews_while_nothing_is_sold(monkeypatch):
    from sqlalchemy import select

    from api import proactive
    from api.db import SessionLocal
    from api.models import Household, Notice, now

    c = client()
    key = c.headers["X-DoKKo-Key"]
    s = SessionLocal()
    h = s.scalar(select(Household).where(Household.key == key))
    h.plan, h.plan_until = "family", now() - 86400          # a plan that ended yesterday
    s.commit()
    hid = h.id
    proactive.housekeeping(s, date.today())
    s.commit()
    assert s.get(Household, hid).plan == "family"           # left alone: nobody is paying, so nobody is downgraded
    assert not s.scalars(select(Notice).where(Notice.household_id == hid, Notice.kind == "plan")).all()
    s.close()


def test_the_page_and_the_site_say_it_in_plain_words():
    html = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
    assert "/*live-p30*/" in html and "lv30-free" in html
    assert "Everything is free until" in html and "A small share from the labs and pharmacies you order through" in html
    assert "Paid plans add AI analysis" not in html        # the old plan-page subtitle is gone
    site = (ROOT / "site" / "index.html").read_text(encoding="utf-8")
    assert "Free for every family until 31 March 2027." in site and "free-band" in site
    assert "₹39" not in site and "₹99" not in site and "Upgrade for AI" not in site
    assert "Is it really free? What happens in April 2027?" in site


@pytest.mark.parametrize("path", ["api/routes.py", "api/upipay.py", "api/proactive.py"])
def test_every_gate_reads_the_one_switch(path):
    src = (ROOT / path).read_text(encoding="utf-8")
    assert "launch import" in src

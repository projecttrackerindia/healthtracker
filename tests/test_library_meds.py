"""Library · Medicines: the plain words families read, the links into the app, cold chain, and CSV import.

Run: python -m pytest -q tests/test_library_meds.py
"""
import os
import uuid

os.environ.setdefault("OTP_DEMO", "1")
os.environ.setdefault("PWNED_CHECK", "0")
os.environ["DATABASE_URL"] = "sqlite:///./data/test_library_meds.db"

from fastapi.testclient import TestClient  # noqa: E402

import server  # noqa: E402
from api.db import Base, engine, session  # noqa: E402
from api.models import Admin  # noqa: E402
from api.security import hash_pw  # noqa: E402

H = {"x-tht": "1"}
PW = "Zq!8vB#2mLp@9xT"
Base.metadata.create_all(engine)


def admin():
    tag = uuid.uuid4().hex[:8]
    with session() as db:
        db.add(Admin(email=f"a{tag}@tht.test", pw_hash=hash_pw(PW), role="owner"))
    c = TestClient(server.app)
    c.headers.update({**H, "x-forwarded-for": f"10.9.{int(tag[:2], 16)}.{int(tag[2:4], 16)}"})
    assert c.post("/api/admin/login", json={"email": f"a{tag}@tht.test", "password": PW}).status_code == 200
    return c


def test_the_plain_words_reach_the_family_search_cut_at_a_word():
    adm = admin()
    m = adm.get("/api/admin/catalog/meds").json()["rows"][0]
    about = "Brings down fever and eases pain. Take with water after food, no more than four times a day, and call the doctor if the fever lasts beyond three days."
    r = adm.put(f"/api/admin/catalog/meds/{m['sku']}", json={**m, "about": about, "organ": "Blood", "test": "cbc", "refillDays": 30})
    assert r.status_code == 200
    j = r.json()
    assert j["about"] == about and j["organ"] == "blood" and j["test"] == "cbc" and j["refillDays"] == 30
    rows = TestClient(server.app).get("/api/v2/catalog/suggest", params={"q": m["name"][:5]}).json()["rows"]
    hit = next(x for x in rows if x["src"] == "catalog" and x["name"].startswith(m["name"]))
    assert hit["sub"].endswith("…") and len(hit["sub"]) <= 111 and not hit["sub"][:-1].endswith(" ")
    assert about.startswith(hit["sub"][:-1])


def test_an_edit_from_the_form_keeps_the_family_words():
    adm = admin()
    m = adm.get("/api/admin/catalog/meds").json()["rows"][1]
    adm.put(f"/api/admin/catalog/meds/{m['sku']}", json={**m, "about": "Keeps blood pressure steady."})
    again = adm.get("/api/admin/catalog/meds").json()["rows"][1]
    assert again["about"] == "Keeps blood pressure steady."


def test_refill_days_are_bounded():
    adm = admin()
    m = adm.get("/api/admin/catalog/meds").json()["rows"][0]
    assert adm.put(f"/api/admin/catalog/meds/{m['sku']}", json={**m, "refillDays": 900}).status_code == 400


def test_cold_chain_and_schedule_filters():
    adm = admin()
    m = adm.get("/api/admin/catalog/meds").json()["rows"][2]
    adm.put(f"/api/admin/catalog/meds/{m['sku']}", json={**m, "cold": True})
    d = adm.get("/api/admin/catalog/meds?tab=cold").json()
    assert d["counts"]["cold"] >= 1 and all(r["cold"] for r in d["rows"]) and any(r["sku"] == m["sku"] for r in d["rows"])
    s = adm.get("/api/admin/catalog/meds?tab=sch").json()
    assert all(r["schedule"] for r in s["rows"])


def test_csv_import_adds_updates_and_reports_bad_lines():
    adm = admin()
    tag = uuid.uuid4().hex[:6]
    csv = ("sku,name,salt,form,mrp,schedule,about,cold,refill_days\n"
           f"glyc{tag},Glycomet 500,Metformin,500 mg tablets · strip of 15,32,H,Lowers blood sugar. Take with food.,no,30\n"
           f"lant{tag},Lantus SoloStar,Insulin glargine,100 IU/mL · 1 pen,712,H,,yes,\n"
           "BAD SKU,Nope,,,,,,,\n"
           f"x{tag},Dear,,,abc,,,,\n"
           f"y{tag},Wrong schedule,,,10,Q,,,\n")
    r = adm.post("/api/admin/catalog/meds/import", files={"file": ("m.csv", csv.encode(), "text/csv")})
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["added"] == 2 and j["updated"] == 0 and j["skippedN"] == 3
    assert [b["line"] for b in j["skipped"]] == [4, 5, 6]
    rows = {x["sku"]: x for x in adm.get("/api/admin/catalog/meds").json()["rows"]}
    g, lan = rows[f"glyc{tag}"], rows[f"lant{tag}"]
    assert g["rx"] and g["schedule"] == "H" and g["mrp"] == 32 and g["refillDays"] == 30 and not g["cold"]
    assert lan["cold"] and lan["rx"]
    again = adm.post("/api/admin/catalog/meds/import", files={"file": ("m.csv", f"sku,name,mrp\nglyc{tag},Glycomet 500,30\n".encode(), "text/csv")}).json()
    assert again["updated"] == 1 and again["added"] == 0
    assert adm.get("/api/admin/catalog/meds").json()["rows"] and \
        next(x for x in adm.get("/api/admin/catalog/meds").json()["rows"] if x["sku"] == f"glyc{tag}")["about"] == "Lowers blood sugar. Take with food."


def test_csv_without_a_header_is_refused():
    r = admin().post("/api/admin/catalog/meds/import", files={"file": ("m.csv", b"glyc,Glycomet\n", "text/csv")})
    assert r.status_code == 400

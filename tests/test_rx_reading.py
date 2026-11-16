"""The admin prescription check shows what report reading found on the shared prescription, line by line against the order."""
import os
import uuid

os.environ.setdefault("DATABASE_URL", "sqlite://")
from api import db as DB  # noqa: E402
from api.family import encrypt  # noqa: E402
from api.models import Base, HealthRecord, Order  # noqa: E402
from api.ops2 import rx_reading  # noqa: E402

Base.metadata.create_all(DB.engine)


def test_reading_matches_lines_to_the_order():
    fid = "f" + uuid.uuid4().hex[:12]
    with DB.session() as db:
        db.add(HealthRecord(person_id="p" + uuid.uuid4().hex[:8], kind="report", day="2026-11-12", file_id=fid,
                            blob=encrypt({"doc": "prescription", "doctor": "Dr S. Ramesh", "medicines": [
                                {"name": "Tab. Metformin", "strength": "500 mg", "dose": "1-0-1", "duration": "30 days", "sure": False},
                                {"name": "Atorvastatin", "strength": "10 mg", "dose": "0-0-1"},
                                {"name": "Telmisartan", "strength": "40 mg"}]})))
        db.flush()
        o = Order(kind="medicine", items=[{"name": "Metformin 500 mg", "rx": True}, {"name": "Atorvastatin 10 mg", "rx": True},
                                          {"name": "Pantoprazole 40 mg", "rx": True}], rx_shared=True, rx_files=[fid])
        r = rx_reading(db, o)
    assert r["read"] is True
    by = {l["name"]: l for l in r["lines"]}
    assert by["Tab. Metformin"]["ordered"] and not by["Tab. Metformin"]["sure"]
    assert by["Atorvastatin"]["ordered"] and by["Atorvastatin"]["sure"]
    assert not by["Telmisartan"]["ordered"]
    assert r["notOnRx"] == ["Pantoprazole 40 mg"]


def test_nothing_read_without_a_shared_prescription():
    with DB.session() as db:
        r = rx_reading(db, Order(kind="medicine", items=[{"name": "Metformin", "rx": True}], rx_shared=False, rx_files=[]))
    assert r == {"read": False, "lines": [], "notOnRx": []}

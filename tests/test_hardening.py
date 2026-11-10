"""Uploads are judged by their bytes, sign-up consent is recorded, and only one worker runs the background loops."""
import os, uuid
os.environ.setdefault("OTP_DEMO", "1")
os.environ.setdefault("APP_ENV", "development")
import pytest
from fastapi import HTTPException
from api import storage, tasks


def test_sniff_accepts_documents_and_photos_only():
    assert storage.sniff(b"%PDF-1.7 ...") == "application/pdf"
    assert storage.sniff(b"\xff\xd8\xff\xe0....") == "image/jpeg"
    assert storage.sniff(b"\x89PNG\r\n\x1a\n....") == "image/png"
    assert storage.sniff(b"MZ\x90\x00 windows exe") is None
    assert storage.sniff(b"<html><script>alert(1)</script>") is None


def test_uploads_reject_disguised_file():
    with pytest.raises(HTTPException) as e:
        storage.checked(b"<svg onload=alert(1)>", "x.pdf")
    assert e.value.status_code == 415


def test_one_worker_runs_loops(tmp_path, monkeypatch):
    monkeypatch.setenv("LOOP_LOCK", str(tmp_path / "l.lock"))
    tasks._LEADER.clear()
    assert tasks.in_process_loops() is True
    # a second process is simulated by trying the same lock from a fresh handle
    import fcntl
    f = open(tmp_path / "l.lock", "w")
    with pytest.raises(OSError):
        fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
    tasks._LEADER.clear()


def test_signup_records_consent():
    from fastapi.testclient import TestClient
    import server
    from api.db import Base, engine
    Base.metadata.create_all(engine)
    client = TestClient(server.app)
    client.headers.update({"x-tht": "1"})
    from api.db import session
    from api.models import ConsentLog, User
    u = uuid.uuid4().hex[:6]
    r = client.post("/api/v1/auth/signup/start", json={"name": "Consent Test", "email": f"c{u}@ex.com", "phone": "9" + str(uuid.uuid4().int)[-9:].zfill(9), "password": "Zq!8vB#2mLp@9xT", "terms": True})
    assert r.status_code == 200, r.text
    d = r.json()
    r = client.post("/api/v1/auth/signup/verify", json={"flow": d["flow"], "code": d["demo"]})
    assert r.status_code == 200, r.text
    with session() as db:
        uid = db.query(User).filter(User.email == f"c{u}@ex.com").one().id
        kinds = sorted(c.kind for c in db.query(ConsentLog).filter(ConsentLog.user_id == uid))
    assert kinds == ["health_data", "privacy", "terms"]

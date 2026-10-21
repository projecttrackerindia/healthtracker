"""Phase 0: the scheduled work moves out of the web process, so more than one container can run.
Run: python -m pytest -q tests/test_phase0_tasks.py"""
import os
import time

os.environ.setdefault("OTP_DEMO", "1")
os.environ.setdefault("PWNED_CHECK", "0")
os.environ["DATABASE_URL"] = "sqlite:///./data/test_phase0.db"
os.environ["TASKS_TOKEN"] = "test-token-aaaaaaaaaaaaaaaaaaaaaaaa"

from fastapi.testclient import TestClient  # noqa: E402

import server  # noqa: E402
from api import tasks  # noqa: E402

H = {"X-Task-Token": os.environ["TASKS_TOKEN"]}


def setup_function():
    """Another test module may have imported the app first; the token is read per call, so just make sure the
    environment this file relies on is in place for each test."""
    os.environ["TASKS_TOKEN"] = "test-token-aaaaaaaaaaaaaaaaaaaaaaaa"


def client():
    c = TestClient(server.app)
    c.__enter__()
    return c


# ---------------------------------------------------------------- the endpoints are not open to the world
def test_no_token_is_rejected():
    c = client()
    assert c.post("/api/v1/tasks/reminders").status_code == 401
    assert c.post("/api/v1/tasks/proactive", headers={"X-Task-Token": "wrong"}).status_code == 401


def test_an_unconfigured_deployment_fails_closed(monkeypatch):
    """An unauthenticated task endpoint would let anyone on the internet trigger a push run."""
    monkeypatch.delenv("TASKS_TOKEN", raising=False)
    c = client()
    assert c.post("/api/v1/tasks/reminders", headers=H).status_code == 503


# ---------------------------------------------------------------- only one container runs a tick
def test_the_lease_admits_one_holder():
    name = "t_" + str(int(time.time() * 1000))
    assert tasks.lease(name, 60) is True
    mine, tasks.WHO = tasks.WHO, "someone-else"
    try:
        assert tasks.lease(name, 60) is False, "a second container ran the same tick"
    finally:
        tasks.WHO = mine


def test_the_lease_is_released_so_the_next_minute_is_not_blocked():
    name = "r_" + str(int(time.time() * 1000))
    assert tasks.lease(name, 600) is True
    tasks.release(name)
    mine, tasks.WHO = tasks.WHO, "someone-else"
    try:
        assert tasks.lease(name, 60) is True
    finally:
        tasks.WHO = mine


def test_an_expired_lease_is_taken_over():
    """A container that dies mid-tick must not block the task forever."""
    name = "x_" + str(int(time.time() * 1000))
    assert tasks.lease(name, 0) is True        # expires immediately
    time.sleep(1.1)
    mine, tasks.WHO = tasks.WHO, "someone-else"
    try:
        assert tasks.lease(name, 60) is True
    finally:
        tasks.WHO = mine


# ---------------------------------------------------------------- the work still happens
def test_tasks_run_and_report():
    c = client()
    r = c.post("/api/v1/tasks/proactive", headers=H)
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["ok"] is True
    assert j.get("task") == "proactive" or "skipped" in j


def test_health_shows_when_each_task_last_ran():
    c = client()
    c.post("/api/v1/tasks/proactive", headers=H)
    j = c.get("/api/v1/tasks/health", headers=H).json()
    assert "tasks" in j and "inProcessLoops" in j
    names = {t["name"] for t in j["tasks"]}
    assert "proactive" in names
    for t in j["tasks"]:
        assert t["agoS"] >= 0


# ---------------------------------------------------------------- the switch-over is safe in both directions
def test_the_in_process_loops_can_be_switched_off(monkeypatch):
    """Both on would double every reminder; both off would send none. The flag has to be honoured by all three."""
    monkeypatch.setenv("IN_PROCESS_LOOPS", "0")
    assert tasks.in_process_loops() is False
    monkeypatch.setenv("IN_PROCESS_LOOPS", "1")
    assert tasks.in_process_loops() is True


def test_each_loop_checks_the_flag():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    for mod in ("reminders.py", "proactive.py", "i18n.py"):
        src = (root / "api" / mod).read_text(encoding="utf-8")
        assert "in_process_loops" in src, f"{mod} would keep running beside Cloud Scheduler"


def test_proactive_has_a_callable_tick():
    from api import proactive

    assert callable(getattr(proactive, "tick", None)), "the endpoint has nothing to call"


# ---------------------------------------------------------------- the other reason we were pinned to one container
def test_signalling_presence_lives_in_the_database():
    """A WebSocket belongs to one process, so two peers on a call can land on two containers. Presence in one
    process's memory is what made --max-instances 1 load-bearing for video calls."""
    from api import consult

    aid = "a_" + str(int(time.time() * 1000))
    assert consult._rtc_present(aid, "doctor") is False
    consult._rtc_seen(aid, "doctor")
    assert consult._rtc_present(aid, "doctor") is True
    consult._rtc_gone(aid, "doctor")
    assert consult._rtc_present(aid, "doctor") is False


def test_a_message_reaches_a_peer_on_another_container():
    from api import consult

    aid = "b_" + str(int(time.time() * 1000))
    consult._rtc_post(aid, "family", {"type": "offer", "sdp": "v=0...", "from": "doctor"})
    after, bodies = consult._rtc_take(aid, "family", 0)
    assert len(bodies) == 1 and "offer" in bodies[0]
    # delivered once, not again
    _, again = consult._rtc_take(aid, "family", after)
    assert again == []


def test_a_stale_peer_is_not_treated_as_present():
    """A container that vanished must not leave a call looking connected forever."""
    from api import consult
    from api.db import session
    from api.models import RtcPeer

    aid = "c_" + str(int(time.time() * 1000))
    consult._rtc_seen(aid, "family")
    with session() as db:
        db.get(RtcPeer, (aid, "family")).seen = int(time.time()) - consult.PEER_TTL - 5
    assert consult._rtc_present(aid, "family") is False


def test_messages_are_addressed_to_one_role():
    from api import consult

    aid = "d_" + str(int(time.time() * 1000))
    consult._rtc_post(aid, "family", {"type": "ice"})
    _, forDoctor = consult._rtc_take(aid, "doctor", 0)
    assert forDoctor == [], "a peer read the other side's signalling"

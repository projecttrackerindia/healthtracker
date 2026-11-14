"""The standby runs reminders when nothing else has, and stays out of the way when the scheduler is working."""
import os
import time

os.environ.setdefault("DATABASE_URL", "sqlite:///./data/test_standby.db")
from fastapi.testclient import TestClient  # noqa: E402

import server  # noqa: E402
from api import tasks  # noqa: E402
from api.db import session  # noqa: E402
from api.models import TaskLock  # noqa: E402


def test_overdue_is_seen_and_a_fresh_run_is_left_alone():
    TestClient(server.app).__enter__()
    with session() as db:
        for n in ("reminders", "proactive"):
            row = db.get(TaskLock, n)
            if row:
                db.delete(row)
    assert tasks._last_ran("reminders") == 0                     # never ran: overdue
    out = tasks._run("reminders", 55, lambda: {"sent": 0})
    assert out["ok"] and not out.get("skipped")
    assert time.time() - tasks._last_ran("reminders") < 5        # recorded, so the standby now waits
    assert tasks._run("reminders", 55, lambda: 1)["ok"]          # lease released after a run: next minute is free


def test_the_in_process_loops_go_through_the_lease():
    src = open("api/reminders.py").read() + open("api/proactive.py").read()
    assert '_run("reminders", 55, tick)' in src and '_run("proactive", 300, tick)' in src
    assert "standby_start()" in open("server.py").read()

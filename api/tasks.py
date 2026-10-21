"""Scheduled work, moved out of the web process.

Three loops used to run as daemon threads inside the API container: medicine reminders every 60 seconds,
proactive nudges every 10 minutes, and the translation worker. That is why the service runs with
`--no-cpu-throttling --min-instances 1 --max-instances 1`: CPU throttling freezes a thread between requests, so
reminders would simply stop, and a second container would send every reminder twice.

Both constraints go away if the schedule lives outside the process. Cloud Scheduler calls the endpoints below;
a lease in the database makes sure that only one container runs a given tick even when several are up. The
threads stay available behind IN_PROCESS_LOOPS so a deployment can be switched over and switched back.

Cloud Scheduler setup (once, per environment):

    gcloud scheduler jobs create http tht-reminders --location=asia-south1 \
      --schedule="* * * * *" --uri="$URL/api/v1/tasks/reminders" --http-method=POST \
      --headers="X-Task-Token=$TASKS_TOKEN" --attempt-deadline=120s

    ... the same for tasks/proactive at "*/10 * * * *" and tasks/i18n at "*/15 * * * *".
"""
from __future__ import annotations

import hmac
import os
import socket
import time
import uuid

from fastapi import APIRouter, Header, HTTPException
from sqlalchemy import update

from api.db import session
from api.models import TaskLock

r = APIRouter(prefix="/api/v1")

# Read per call, not at import: the value a container was started with is the one that counts, and reading it
# lazily also keeps the endpoints honest under test, where import order is not ours to control.
def _token() -> str:
    return os.getenv("TASKS_TOKEN", "")


# Each container identifies itself so a stuck lease can be traced to the instance that took it.
WHO = f"{socket.gethostname()[:40]}:{uuid.uuid4().hex[:8]}"


def in_process_loops() -> bool:
    """True while the old daemon threads should still run. Set IN_PROCESS_LOOPS=0 once Cloud Scheduler is
    calling these endpoints; leaving both on would double every reminder."""
    return os.getenv("IN_PROCESS_LOOPS", "1") == "1"


def _auth(token: str | None) -> None:
    want = _token()
    if not want:
        # Fail closed. An unauthenticated task endpoint lets anyone on the internet trigger a push run.
        raise HTTPException(503, "TASKS_TOKEN is not configured")
    if not token or not hmac.compare_digest(token, want):
        raise HTTPException(401, "bad task token")


def lease(name: str, seconds: int) -> bool:
    """Take the lease for `name`, or return False because somebody else holds it.

    One conditional UPDATE does the whole job: the row is only taken when its lease has expired, and the
    database decides the winner. Cloud Scheduler can retry and several containers can be up; exactly one of
    them proceeds."""
    t = int(time.time())
    with session() as db:
        row = db.get(TaskLock, name)
        if row is None:
            db.add(TaskLock(name=name, holder=WHO, until=t + seconds, ran_at=t))
            try:
                db.flush()
                return True
            except Exception:           # another container inserted it in the same instant
                db.rollback()
                return False
        n = db.execute(
            update(TaskLock)
            .where(TaskLock.name == name, TaskLock.until < t)
            .values(holder=WHO, until=t + seconds, ran_at=t)
        ).rowcount
        return bool(n)


def release(name: str) -> None:
    """Give the lease back early, so a minute-by-minute task is not blocked by its own safety margin."""
    with session() as db:
        db.execute(update(TaskLock).where(TaskLock.name == name, TaskLock.holder == WHO).values(until=0))


def _run(name: str, seconds: int, fn) -> dict:
    if not lease(name, seconds):
        return {"ok": True, "skipped": "another instance holds the lease"}
    t0 = time.perf_counter()
    try:
        out = fn()
    except Exception as e:
        print(f"[tasks] {name} failed:", type(e).__name__, str(e)[:200], flush=True)
        release(name)
        raise HTTPException(500, f"{name} failed")
    release(name)
    return {"ok": True, "task": name, "ms": round((time.perf_counter() - t0) * 1000), "result": out}


@r.post("/tasks/reminders", include_in_schema=False)
def task_reminders(x_task_token: str | None = Header(None)):
    """Every minute. The slot windows are 45 minutes wide, so a missed minute costs nothing."""
    _auth(x_task_token)
    from api import reminders

    return _run("reminders", 55, lambda: {"sent": reminders.tick()})


@r.post("/tasks/proactive", include_in_schema=False)
def task_proactive(x_task_token: str | None = Header(None)):
    """Every ten minutes. Housekeeping always; the morning pass only inside its hour, guarded by its own
    ReminderSent key so it cannot run twice in a day however often this is called."""
    _auth(x_task_token)
    from api import proactive

    return _run("proactive", 570, proactive.tick)


@r.post("/tasks/i18n", include_in_schema=False)
def task_i18n(x_task_token: str | None = Header(None)):
    """Every quarter of an hour. Translating is slow and entirely background work; it held a database
    connection for up to forty minutes when it ran as a thread."""
    _auth(x_task_token)
    from api import i18n
    from api.db import SessionLocal

    def go():
        s = SessionLocal()
        try:
            return {"translated": i18n.translate_pending(s)}
        finally:
            s.close()

    return _run("i18n", 840, go)


@r.get("/tasks/health", include_in_schema=False)
def task_health(x_task_token: str | None = Header(None)):
    """When each task last ran, so a silent scheduler is visible instead of being discovered by a family who
    stopped getting their reminders."""
    _auth(x_task_token)
    t = int(time.time())
    with session() as db:
        rows = db.query(TaskLock).all()
        return {"now": t, "inProcessLoops": in_process_loops(),
                "tasks": [{"name": x.name, "ranAt": x.ran_at, "agoS": t - x.ran_at, "heldBy": x.holder,
                           "leaseEndsIn": max(0, x.until - t)} for x in rows]}

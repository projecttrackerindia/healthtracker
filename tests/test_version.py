"""/api/health should answer "is the thing I just merged live?" without a shell.

It reported "dev" for every deploy since the move off Railway, because it read a variable only Railway sets.
Several deploys this week were therefore verified by reading a service-worker cache name out of a terminal.

Run: python -m pytest -q tests/test_version.py
"""
import os
import re
import subprocess
from pathlib import Path

os.environ.setdefault("OTP_DEMO", "1")
os.environ.setdefault("PWNED_CHECK", "0")
os.environ["DATABASE_URL"] = "sqlite:///./data/test_version.db"

from fastapi.testclient import TestClient  # noqa: E402

import server  # noqa: E402
from api.db import Base, engine  # noqa: E402

Base.metadata.create_all(engine)


def client():
    c = TestClient(server.app)
    c.__enter__()
    return c


def test_health_is_public_and_says_what_is_running():
    h = client().get("/api/health").json()
    assert h["ok"] is True
    assert set(h) >= {"version", "uptime_s", "built", "sw"}


def test_the_service_worker_version_is_read_from_the_file_we_actually_ship():
    """The cache name is what decides whether a family's phone picks up new front-end code, so it is the
    honest answer to "did the app update?" — and it is read from the file, not written twice."""
    shipped = re.search(r"const V='([^']+)'", Path("web/sw.js").read_text(encoding="utf-8")).group(1)
    assert client().get("/api/health").json()["sw"] == shipped


def test_the_commit_comes_from_the_environment_the_deploy_sets():
    import importlib

    os.environ["APP_VERSION"] = "abc1234567"
    os.environ["APP_BUILT"] = "2026-10-21T20:00:00Z"
    try:
        importlib.reload(server)
        h = TestClient(server.app).get("/api/health").json()
        assert h["version"] == "abc1234567" and h["built"] == "2026-10-21T20:00:00Z"
    finally:
        del os.environ["APP_VERSION"], os.environ["APP_BUILT"]
        importlib.reload(server)


def test_the_deploy_script_stamps_the_commit_before_it_builds():
    """Stamping after the build would name whatever HEAD had become by then."""
    sh = Path("deploy/gcp/deploy.sh").read_text(encoding="utf-8")
    assert sh.index("stamp-env.sh") < sh.index("gcloud builds submit")
    assert "rev-parse" in sh
    assert subprocess.run(["bash", "-n", "deploy/gcp/deploy.sh"]).returncode == 0


def test_both_deploy_paths_stamp_the_commit():
    """Cloud Run and the VM must set APP_VERSION the same way.

    The VM release shipped without stamping at all: /api/health reported "dev", so release.sh compared the
    commit against the literal string "dev" and could only ever pass. A verification step that cannot fail
    is worse than none, because it is believed. One shared script, and this test asserting both callers
    use it, is what stops the two drifting apart again."""
    stamp = Path("deploy/gcp/stamp-env.sh")
    assert stamp.exists(), "the shared stamping script is gone"
    assert "APP_VERSION" in stamp.read_text(encoding="utf-8")
    assert subprocess.run(["bash", "-n", str(stamp)]).returncode == 0

    assert "stamp-env.sh" in Path("deploy/gcp/deploy.sh").read_text(encoding="utf-8")

    wf = Path(".github/workflows/gcp-deploy.yml").read_text(encoding="utf-8")
    vm = wf.index("Release to the VM")
    assert "stamp-env.sh" in wf[vm:], "the VM release does not stamp the commit"
    assert wf.index("stamp-env.sh", vm) < wf.index("compute scp", vm), \
        "env.yaml is copied to the VM before it is stamped, so the stamp never arrives"

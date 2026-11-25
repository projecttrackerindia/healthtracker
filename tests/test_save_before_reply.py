"""25 Nov: a request whose save failed still answered 200, because the save ran after the reply was sent.
Every endpoint now saves before it replies."""
import subprocess
from pathlib import Path

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]


def test_no_endpoint_saves_after_replying():
    out = subprocess.run(["grep", "-rn", "Depends(get_db)", "--include=*.py", "api", "server.py"], cwd=ROOT, capture_output=True, text=True).stdout
    assert out == "", "use Depends(get_db, scope=\"function\"):\n" + out


def test_a_failed_save_is_an_error_not_a_200():
    def dep():
        yield 1
        raise RuntimeError("commit failed")

    app = FastAPI()

    @app.get("/x")
    def x(d=Depends(dep, scope="function")):
        return {"ok": True}

    assert TestClient(app, raise_server_exceptions=False).get("/x").status_code == 500

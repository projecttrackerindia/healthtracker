"""Admin Ask: a question is answered from the same numbers Today shows; without an AI key it gives a plain summary."""
import os

os.environ.setdefault("OTP_DEMO", "1")
os.environ.setdefault("PWNED_CHECK", "0")
os.environ["DATABASE_URL"] = "sqlite:///./data/test_console_ask.db"
os.environ.pop("GEMINI_API_KEY", None)
os.environ.pop("ANTHROPIC_API_KEY", None)

import sys  # noqa: E402
sys.path.insert(0, os.path.dirname(__file__))
import test_round7 as R  # noqa: E402


def test_ask_answers_from_today_without_ai():
    R.TestClient(R.server.app).__enter__()   # tables are created on startup
    a = R.admin()
    r = a.post("/api/admin/console/ask", json={"q": "which orders are late?"})
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["ai"] is False and j["answer"].startswith("Right now:")
    assert isinstance(j["go"], list)
    assert a.post("/api/admin/console/ask", json={"q": "x"}).status_code == 422


def test_ask_needs_an_admin():
    from fastapi.testclient import TestClient
    import server
    assert TestClient(server.app).post("/api/admin/console/ask", json={"q": "late orders?"}).status_code in (401, 403)

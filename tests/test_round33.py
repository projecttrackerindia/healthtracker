"""Round 33: the app stops being slow and fragile under load.
Run: python -m pytest -q tests/test_round33.py"""
import gzip
import os
from pathlib import Path

os.environ.setdefault("OTP_DEMO", "1")
os.environ.setdefault("PWNED_CHECK", "0")
os.environ["DATABASE_URL"] = "sqlite:///./data/test_round33.db"

from fastapi.testclient import TestClient  # noqa: E402

import server  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def client():
    c = TestClient(server.app)
    c.__enter__()
    return c


# ---------------------------------------------------------------- the event loop stays free
def test_model_call_runs_off_the_event_loop():
    """/ai/analyze is async; calling the provider SDK inline froze every other request in the container."""
    src = (ROOT / "api" / "routes.py").read_text(encoding="utf-8")
    assert "run_in_threadpool" in src
    body = src[src.index('@r.post("/ai/analyze")'):]
    body = body[: body.index("class AskIn")]
    assert "await run_in_threadpool(_read)" in body
    for call in ("AI.analyze(", "AI.analyze_policy(", "AI.analyze_card("):
        i = body.index(call)
        assert "def _read()" in body[:i], f"{call} is outside the threadpool helper"


def test_provider_call_has_a_timeout():
    """Without one the SDK waits 600 seconds, which on a single instance is a ten-minute outage."""
    src = (ROOT / "api" / "ai.py").read_text(encoding="utf-8")
    assert "AI_TIMEOUT" in src
    assert "anthropic.Anthropic(timeout=AI_TIMEOUT" in src


def test_s3_client_is_cached_and_bounded():
    src = (ROOT / "api" / "storage.py").read_text(encoding="utf-8")
    assert "_CLIENT" in src, "a new boto3 client was built on every call"
    assert "connect_timeout" in src and "read_timeout" in src


# ---------------------------------------------------------------- the pool is sized
def test_connection_pool_is_configured():
    """SQLAlchemy defaults to 5+10; the threadpool is 40 wide, so 25 requests queued and then failed."""
    from api.db import IS_SQLITE, _POOL

    if IS_SQLITE:
        assert _POOL == {}
        return
    assert _POOL["pool_size"] >= 20
    assert _POOL["max_overflow"] >= 10
    assert _POOL["pool_timeout"] <= 15, "a long timeout holds the worker instead of failing fast"
    assert _POOL["pool_recycle"] > 0, "the Cloud SQL proxy drops idle connections"


# ---------------------------------------------------------------- bytes on the wire
def test_every_compressible_file_has_both_variants():
    """A .br with no .gz means every browser without brotli downloads the raw file — 1.57 MB for the shell."""
    missing = []
    for d in (ROOT / "web", ROOT / "site"):
        for br in d.rglob("*.br"):
            src = br.with_name(br.name[:-3])
            if src.is_file() and not src.with_name(src.name + ".gz").exists():
                missing.append(str(src.relative_to(ROOT)))
    assert not missing, f"no .gz twin for: {missing}"


def test_app_shell_gzip_is_much_smaller():
    raw = (ROOT / "web" / "index.html").stat().st_size
    gz = (ROOT / "web" / "index.html.gz").stat().st_size
    assert gz < raw * 0.45, f"{gz} is not meaningfully smaller than {raw}"
    assert gzip.decompress((ROOT / "web" / "index.html.gz").read_bytes()) == (ROOT / "web" / "index.html").read_bytes()


def test_api_responses_are_compressed():
    c = client()
    big = c.get("/api/v1/i18n", headers={"accept-encoding": "gzip"})
    assert big.status_code == 200
    assert len(big.content) > 2000, "sanity: this response should be large enough to matter"
    raw = len(c.get("/api/v1/i18n", headers={"accept-encoding": "identity"}).content)
    assert raw > len(big.content) or big.headers.get("content-encoding") == "gzip"


def test_gzip_middleware_is_installed():
    assert any("GZip" in type(m.cls).__name__ or "GZip" in str(m.cls) for m in server.app.user_middleware)


def test_repeat_open_is_a_304():
    """The shell is `no-cache`, i.e. revalidate. Without If-None-Match handling that was a full resend."""
    c = client()
    r1 = c.get("/app")
    assert r1.status_code == 200
    tag = r1.headers.get("etag")
    assert tag, "no ETag, so the browser can never revalidate"
    r2 = c.get("/app", headers={"if-none-match": tag})
    assert r2.status_code == 304
    assert not r2.content


# ---------------------------------------------------------------- queries
def test_listing_files_does_not_load_their_bytes():
    """StoredFile.blob is a LargeBinary; selecting whole rows pulled every document into a 1 GiB container."""
    src = (ROOT / "api" / "more.py").read_text(encoding="utf-8")
    body = src[src.index('@r.get("/files")'):]
    body = body[: body.index("\n@r.")]
    assert "select(StoredFile)" not in body, "still selecting whole rows"
    assert "StoredFile.file_id" in body and "StoredFile.size" in body


def test_hello_counts_orders_instead_of_loading_them():
    src = (ROOT / "api" / "routes.py").read_text(encoding="utf-8")
    assert "len(h.orders)" not in src
    assert "func.count(Order.id)" in src


def test_orders_list_joins_the_store():
    src = (ROOT / "api" / "routes.py").read_text(encoding="utf-8")
    assert "joinedload(Order.store)" in src, "one query per row to name the store"


def test_hot_indexes_exist_and_are_created_on_existing_databases():
    from api import models
    from api.db import ensure_indexes

    assert models.ReminderSent.__table__.c.t.index, "range-deleted every tick without an index"
    assert any(i.name == "ix_phrases_pending" for i in models.Phrase.__table__.indexes)
    # create_all() never adds an index to a table that already exists, so there must be a boot-time path
    src = (ROOT / "api" / "db.py").read_text(encoding="utf-8")
    assert "CREATE INDEX IF NOT EXISTS" in src
    ensure_indexes()   # idempotent
    ensure_indexes()


# ---------------------------------------------------------------- the global mutex
def test_rate_limiter_does_not_sleep_holding_the_lock():
    """Sleeping under a process-wide mutex serialised every caller and parked them in the threadpool."""
    src = (ROOT / "api" / "places.py").read_text(encoding="utf-8")
    blk = src[src.index("def _get("):]
    blk = blk[: blk.index("req = urllib.request.Request")]
    lock = blk.index("with _LOCK:")
    sleep = blk.index("time.sleep")
    assert sleep > lock
    body = blk[lock:sleep]
    assert body.count("\n    if wait > 0:") == 1 or "\n    if wait" in blk[lock:sleep], "sleep is still inside the lock"

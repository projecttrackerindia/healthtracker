"""Database setup.

* DATABASE_URL set (Railway Postgres plugin)  -> PostgreSQL via psycopg 3
* otherwise                                   -> SQLite file next to the app (fine for demos; not shared between
                                                 Railway replicas and wiped on redeploy, so use Postgres in production)
"""
from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

ROOT = Path(__file__).resolve().parent.parent


def _url() -> str:
    u = os.getenv("DATABASE_URL", "").strip()
    if u:
        if u.startswith("postgres://"):
            u = "postgresql+psycopg://" + u[len("postgres://"):]
        elif u.startswith("postgresql://"):
            u = "postgresql+psycopg://" + u[len("postgresql://"):]
        return u
    for d in (ROOT / "data", Path("/tmp/dokko")):
        try:
            d.mkdir(parents=True, exist_ok=True)
            (d / ".w").write_text("ok")
            return f"sqlite:///{d / 'dokko.db'}"
        except OSError:
            continue
    return "sqlite:///:memory:"


DB_URL = _url()
IS_SQLITE = DB_URL.startswith("sqlite")
print(f"[db] backend={'sqlite (ephemeral!)' if IS_SQLITE else 'postgres'}", flush=True)
# Pool sizing matters more than it looks. FastAPI runs every `def` endpoint in AnyIO's threadpool, which is 40
# threads wide; SQLAlchemy's default pool is 5 + 10 overflow. The 25 requests that don't get a connection block
# inside SessionLocal() for pool_timeout (default 30s) and then raise. 35 connections covers the threadpool and
# the three daemon threads and still sits well under db-g1-small's max_connections. pool_timeout is short on
# purpose: failing in 10s frees the thread, where waiting 30s holds it and spreads the stall.
_POOL = {} if IS_SQLITE else {
    "pool_size": int(os.getenv("DB_POOL_SIZE", "20")),
    "max_overflow": int(os.getenv("DB_POOL_OVERFLOW", "15")),
    "pool_timeout": int(os.getenv("DB_POOL_TIMEOUT", "10")),
    "pool_recycle": int(os.getenv("DB_POOL_RECYCLE", "1800")),   # the Cloud SQL proxy drops idle connections
}
engine = create_engine(
    DB_URL,
    pool_pre_ping=not IS_SQLITE,
    connect_args={"check_same_thread": False} if IS_SQLITE else {},
    future=True,
    **_POOL,
)
if IS_SQLITE:

    @event.listens_for(engine, "connect")
    def _pragmas(dbapi_conn, _):
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA journal_mode=WAL")
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()


SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, class_=Session)


class Base(DeclarativeBase):
    pass


@contextmanager
def session():
    s = SessionLocal()
    try:
        yield s
        s.commit()
    except Exception:
        s.rollback()
        raise
    finally:
        s.close()


def get_db():
    s = SessionLocal()
    try:
        yield s
        s.commit()
    except Exception:
        s.rollback()
        raise
    finally:
        s.close()


def ensure_columns() -> None:
    """create_all() only creates missing tables. New columns on old tables are added here, idempotently."""
    from sqlalchemy import inspect, text

    wanted = {"users": [("member_id", "VARCHAR(32)"), ("name_changed", "INTEGER"), ("role", "VARCHAR(12) DEFAULT 'member'"), ("aadhaar_verified", "INTEGER"), ("aadhaar_last4", "VARCHAR(4) DEFAULT ''"), ("aadhaar_dob", "VARCHAR(10) DEFAULT ''"), ("ref_code", "VARCHAR(12) DEFAULT ''"), ("referred_by", "VARCHAR(32) DEFAULT ''"), ("ref_rewarded", "INTEGER DEFAULT 0")], "ai_jobs": [("tin", "INTEGER DEFAULT 0"), ("tout", "INTEGER DEFAULT 0")], "stores": [("gstin", "VARCHAR(20) DEFAULT ''"), ("gst_pct", "INTEGER DEFAULT 0")], "orders": [("member_id", "VARCHAR(32)"), ("rx_files", "JSON"), ("addr", "JSON")],
              "invites": [("role", "VARCHAR(12) DEFAULT 'member'")],
              "partner_users": [("reg_no", "VARCHAR(40) DEFAULT ''"), ("specialty", "VARCHAR(60) DEFAULT ''"), ("verified", "BOOLEAN DEFAULT FALSE")],
              "appointments": [("transcript", "JSON"), ("rx", "JSON"), ("summary", "TEXT DEFAULT ''"), ("call_started", "INTEGER"), ("call_ended", "INTEGER")],
              "households": [("backup_at", "INTEGER"), ("backup_to", "VARCHAR(200) DEFAULT ''")]}
    insp = inspect(engine)
    with engine.begin() as conn:
        for table, cols in wanted.items():
            if table not in insp.get_table_names():
                continue
            have = {c["name"] for c in insp.get_columns(table)}
            for name, typ in cols:
                if name not in have:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {typ}"))
                    print(f"[db] added column {table}.{name}", flush=True)


def ensure_indexes() -> None:
    """create_all() adds indexes only with the table. An index declared on a model that already exists in the
    database is never created, so new ones are issued here, idempotently. Safe to run on every boot."""
    from sqlalchemy import text

    want = [
        ("ix_reminders_sent_t", "reminders_sent", "(t)"),
        ("ix_phrases_pending", "phrases", "(done, tries, created)"),
        ("ix_task_locks_until", "task_locks", "(until)"),
        ("ix_rtc_relay_pick", "rtc_relay", "(aid, to_role, id)"),
        ("ix_track_pings_pick", "track_pings", "(order_id, id)"),
        ("ix_orders_agent_state", "orders", "(agent_id, status)"),
    ]
    with engine.begin() as c:
        for name, table, cols in want:
            try:
                c.execute(text(f"CREATE INDEX IF NOT EXISTS {name} ON {table} {cols}"))
            except Exception as e:   # a missing table on a fresh install, or a backend without IF NOT EXISTS
                print(f"[db] index {name}: {type(e).__name__}: {str(e)[:120]}", flush=True)

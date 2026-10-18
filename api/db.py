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
engine = create_engine(
    DB_URL,
    pool_pre_ping=not IS_SQLITE,
    connect_args={"check_same_thread": False} if IS_SQLITE else {},
    future=True,
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

    wanted = {"users": [("member_id", "VARCHAR(32)"), ("name_changed", "INTEGER")], "orders": [("member_id", "VARCHAR(32)"), ("rx_files", "JSON")]}
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

"""SQLite database setup for the FarmTrust API."""

from __future__ import annotations

import os
from pathlib import Path

from sqlmodel import SQLModel, Session, create_engine


DATABASE_URL = os.environ.get("FARMTRUST_DATABASE_URL", "sqlite:///data/farmtrust.sqlite3")

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)


def init_db() -> None:
    from api import models  # noqa: F401  # ensure SQLModel table metadata is registered

    if DATABASE_URL.startswith("sqlite:///"):
        db_path = Path(DATABASE_URL.removeprefix("sqlite:///"))
        db_path.parent.mkdir(parents=True, exist_ok=True)
    SQLModel.metadata.create_all(engine)
    _migrate_db()


def _migrate_db() -> None:
    """Apply additive column migrations for SQLite (ALTER TABLE ADD COLUMN).

    SQLite does not support IF NOT EXISTS for ALTER TABLE, so we catch
    OperationalError on duplicate columns and continue.
    """
    if not DATABASE_URL.startswith("sqlite:"):
        return

    import sqlite3

    db_path = DATABASE_URL.removeprefix("sqlite:///")
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()
        migrations = [
            "ALTER TABLE job ADD COLUMN cancel_requested INTEGER NOT NULL DEFAULT 0",
            "ALTER TABLE job ADD COLUMN scene_total INTEGER",
            "ALTER TABLE job ADD COLUMN scene_done INTEGER",
            "ALTER TABLE land ADD COLUMN lookback_days INTEGER NOT NULL DEFAULT 730",
        ]
        for sql in migrations:
            try:
                cursor.execute(sql)
            except sqlite3.OperationalError:
                pass  # column already exists
        conn.commit()
    finally:
        conn.close()


def get_session():
    with Session(engine) as session:
        yield session

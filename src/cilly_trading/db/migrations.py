"""Lightweight versioned migration runner for the SQLite schema.

Each migration is a plain SQL string with a unique integer version.
The applied version is tracked in a `schema_migrations` table inside the DB.

Usage::

    from cilly_trading.db.migrations import run_migrations
    run_migrations(db_path)   # idempotent; only unapplied migrations are run
"""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path
from typing import Optional

from cilly_trading.db.init_db import DEFAULT_DB_PATH

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Migration registry — append new entries; never modify existing ones.
# Each tuple: (version: int, description: str, sql: str)
# ---------------------------------------------------------------------------
_MIGRATIONS: list[tuple[int, str, str]] = [
    (
        1,
        "Add signal_id, analysis_run_id, ingestion_run_id, reasons_json, stop_loss to signals",
        """
        ALTER TABLE signals ADD COLUMN signal_id TEXT;
        ALTER TABLE signals ADD COLUMN analysis_run_id TEXT;
        ALTER TABLE signals ADD COLUMN ingestion_run_id TEXT;
        ALTER TABLE signals ADD COLUMN reasons_json TEXT;
        ALTER TABLE signals ADD COLUMN stop_loss REAL;
        """,
    ),
    (
        2,
        "Add unique index on signals (ingestion_run_id, signal_id)",
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_signals_ingestion_run_signal_id_unique
          ON signals(ingestion_run_id, signal_id)
          WHERE ingestion_run_id IS NOT NULL AND signal_id IS NOT NULL;
        """,
    ),
    (
        3,
        "Add signal_id to trades table",
        """
        ALTER TABLE trades ADD COLUMN signal_id TEXT;
        """,
    ),
]


def _ensure_migrations_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version     INTEGER PRIMARY KEY,
            description TEXT    NOT NULL,
            applied_at  TEXT    NOT NULL DEFAULT (datetime('now'))
        );
        """
    )
    conn.commit()


def _applied_versions(conn: sqlite3.Connection) -> set[int]:
    cur = conn.execute("SELECT version FROM schema_migrations;")
    return {row[0] for row in cur.fetchall()}


def run_migrations(db_path: Optional[Path] = None) -> int:
    """Apply all pending migrations and return the number of migrations run.

    Safe to call multiple times — already-applied migrations are skipped.

    Args:
        db_path: Path to the SQLite database file. Defaults to DEFAULT_DB_PATH.

    Returns:
        Number of migrations applied in this call.
    """
    if db_path is None:
        db_path = DEFAULT_DB_PATH

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    try:
        _ensure_migrations_table(conn)
        applied = _applied_versions(conn)
        pending = [(v, d, s) for v, d, s in _MIGRATIONS if v not in applied]

        if not pending:
            logger.debug("DB schema up to date: db=%s", db_path)
            return 0

        count = 0
        for version, description, sql in sorted(pending, key=lambda m: m[0]):
            logger.info(
                "Applying migration %d: %s db=%s", version, description, db_path
            )
            try:
                # Each migration may contain multiple statements separated by ';'
                for statement in sql.split(";"):
                    stmt = statement.strip()
                    if stmt:
                        conn.execute(stmt)
                conn.execute(
                    "INSERT INTO schema_migrations (version, description) VALUES (?, ?);",
                    (version, description),
                )
                conn.commit()
                count += 1
            except sqlite3.OperationalError as exc:
                # Column-already-exists errors are safe to ignore (idempotent ADD COLUMN)
                if "duplicate column name" in str(exc).lower():
                    logger.debug(
                        "Migration %d already partially applied (column exists), recording: %s",
                        version,
                        exc,
                    )
                    conn.execute(
                        "INSERT OR IGNORE INTO schema_migrations (version, description) VALUES (?, ?);",
                        (version, description),
                    )
                    conn.commit()
                    count += 1
                else:
                    conn.rollback()
                    logger.error(
                        "Migration %d failed, rolling back: %s", version, exc
                    )
                    raise

        logger.info("Applied %d migration(s): db=%s", count, db_path)
        return count
    finally:
        conn.close()

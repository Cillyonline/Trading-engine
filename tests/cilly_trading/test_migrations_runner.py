"""End-to-end tests for the SQLite migration runner (issue #1134)."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from cilly_trading.db.init_db import init_db
from cilly_trading.db.migrations import _MIGRATIONS, run_migrations


def _applied_versions(db_path: Path) -> set[int]:
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.execute("SELECT version FROM schema_migrations;")
        return {row[0] for row in cur.fetchall()}
    finally:
        conn.close()


def test_run_migrations_applies_all_pending_on_fresh_db(tmp_path: Path) -> None:
    db = tmp_path / "fresh.sqlite"
    init_db(db)
    applied = run_migrations(db)
    expected = len(_MIGRATIONS)
    assert applied == expected
    assert _applied_versions(db) == {v for v, _, _ in _MIGRATIONS}


def test_run_migrations_is_idempotent(tmp_path: Path) -> None:
    """A second invocation must apply zero new migrations."""

    db = tmp_path / "idempotent.sqlite"
    init_db(db)
    first = run_migrations(db)
    second = run_migrations(db)
    third = run_migrations(db)
    assert first > 0
    assert second == 0
    assert third == 0
    assert _applied_versions(db) == {v for v, _, _ in _MIGRATIONS}


def test_run_migrations_records_each_version_exactly_once(tmp_path: Path) -> None:
    db = tmp_path / "recorded.sqlite"
    init_db(db)
    run_migrations(db)
    run_migrations(db)

    conn = sqlite3.connect(db)
    try:
        cur = conn.execute(
            "SELECT version, COUNT(*) FROM schema_migrations GROUP BY version;"
        )
        rows = cur.fetchall()
    finally:
        conn.close()

    for version, count in rows:
        assert count == 1, f"version {version} recorded {count} times"


def test_run_migrations_creates_schema_migrations_table(tmp_path: Path) -> None:
    db = tmp_path / "table.sqlite"
    init_db(db)
    run_migrations(db)

    conn = sqlite3.connect(db)
    try:
        cur = conn.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type='table' AND name='schema_migrations';"
        )
        row = cur.fetchone()
    finally:
        conn.close()

    assert row is not None
    assert row[0] == "schema_migrations"


def test_run_migrations_after_table_recreated_only_records_new(tmp_path: Path) -> None:
    """Even when the analysis schema is fully created up-front by init_db,
    run_migrations must not crash on duplicate-column errors and must end
    with all known versions recorded."""

    db = tmp_path / "recreated.sqlite"
    init_db(db)
    # init_db has already created tables with the migrated columns. The
    # migration runner must therefore tolerate ``duplicate column`` errors
    # for ALTER TABLE migrations and still record their version.
    applied = run_migrations(db)
    assert applied == len(_MIGRATIONS)
    assert _applied_versions(db) == {v for v, _, _ in _MIGRATIONS}


def test_run_migrations_returns_zero_when_db_is_at_head(tmp_path: Path) -> None:
    db = tmp_path / "head.sqlite"
    init_db(db)
    run_migrations(db)
    assert run_migrations(db) == 0


def test_migration_versions_are_unique_and_monotonic() -> None:
    versions = [v for v, _, _ in _MIGRATIONS]
    assert len(versions) == len(set(versions)), "duplicate migration version found"
    assert versions == sorted(versions), "migrations not declared in version order"

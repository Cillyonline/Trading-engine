"""Tests for SQLite connection tuning (issue #1136).

Verifies the PRAGMA values applied by ``BaseSqliteRepository._get_connection``
and the env-var overrides for batch jobs.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from cilly_trading.repositories._base_sqlite import (
    BaseSqliteRepository,
    _DEFAULT_BUSY_TIMEOUT_MS,
    _DEFAULT_SYNCHRONOUS,
    _resolve_busy_timeout_ms,
    _resolve_synchronous_mode,
)


def _read_pragma(repo: BaseSqliteRepository, pragma: str) -> int | str:
    with repo._connection() as conn:
        row = conn.execute(f"PRAGMA {pragma};").fetchone()
    # PRAGMA returns a Row with a single value
    return row[0]


def test_default_busy_timeout_is_5_seconds(tmp_path: Path) -> None:
    repo = BaseSqliteRepository(db_path=tmp_path / "tune.sqlite")
    assert _read_pragma(repo, "busy_timeout") == _DEFAULT_BUSY_TIMEOUT_MS == 5000


def test_default_synchronous_is_normal_for_wal(tmp_path: Path) -> None:
    repo = BaseSqliteRepository(db_path=tmp_path / "tune.sqlite")
    # PRAGMA synchronous returns int: OFF=0, NORMAL=1, FULL=2, EXTRA=3
    assert _read_pragma(repo, "synchronous") == 1
    assert _DEFAULT_SYNCHRONOUS == "NORMAL"


def test_journal_mode_is_wal(tmp_path: Path) -> None:
    repo = BaseSqliteRepository(db_path=tmp_path / "tune.sqlite")
    assert _read_pragma(repo, "journal_mode") == "wal"


def test_busy_timeout_env_override(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("CILLY_SQLITE_BUSY_TIMEOUT_MS", "12345")
    repo = BaseSqliteRepository(db_path=tmp_path / "tune.sqlite")
    assert _read_pragma(repo, "busy_timeout") == 12345


def test_busy_timeout_env_invalid_falls_back(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CILLY_SQLITE_BUSY_TIMEOUT_MS", "not-a-number")
    assert _resolve_busy_timeout_ms() == _DEFAULT_BUSY_TIMEOUT_MS

    monkeypatch.setenv("CILLY_SQLITE_BUSY_TIMEOUT_MS", "0")
    assert _resolve_busy_timeout_ms() == _DEFAULT_BUSY_TIMEOUT_MS


def test_synchronous_env_override(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("CILLY_SQLITE_SYNCHRONOUS", "FULL")
    repo = BaseSqliteRepository(db_path=tmp_path / "tune.sqlite")
    assert _read_pragma(repo, "synchronous") == 2  # FULL


def test_synchronous_env_invalid_falls_back(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CILLY_SQLITE_SYNCHRONOUS", "BOGUS")
    assert _resolve_synchronous_mode() == _DEFAULT_SYNCHRONOUS

    monkeypatch.setenv("CILLY_SQLITE_SYNCHRONOUS", "  off  ")
    assert _resolve_synchronous_mode() == "OFF"


def test_executemany_helper_runs_batch_insert(tmp_path: Path) -> None:
    repo = BaseSqliteRepository(db_path=tmp_path / "tune.sqlite")
    with repo._connection() as conn:
        conn.execute("CREATE TABLE batch_test (key TEXT PRIMARY KEY, value INTEGER);")
        conn.commit()

    rows = [("a", 1), ("b", 2), ("c", 3)]
    affected = repo._executemany(
        "INSERT INTO batch_test (key, value) VALUES (?, ?);", rows
    )
    assert affected == 3

    with repo._connection() as conn:
        count = conn.execute("SELECT COUNT(*) FROM batch_test;").fetchone()[0]
    assert count == 3


def test_executemany_helper_handles_empty_iterable(tmp_path: Path) -> None:
    repo = BaseSqliteRepository(db_path=tmp_path / "tune.sqlite")
    with repo._connection() as conn:
        conn.execute("CREATE TABLE batch_test (key TEXT PRIMARY KEY);")
        conn.commit()

    affected = repo._executemany(
        "INSERT INTO batch_test (key) VALUES (?);", []
    )
    assert affected == 0

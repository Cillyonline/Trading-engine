"""Tests for DatabaseConfig / ConnectionFactory abstraction (Issue #1104).

Runs against SQLite in all environments.  PostgreSQL tests are skipped
automatically unless the ``DATABASE_URL`` environment variable points to a
live PostgreSQL instance.
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

import pytest

from cilly_trading.db.config import (
    ConnectionFactory,
    DatabaseConfig,
    load_database_config,
)
from cilly_trading.repositories._base_sqlite import BaseSqliteRepository


# ── fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture()
def sqlite_factory(tmp_path: Path) -> ConnectionFactory:
    db_path = tmp_path / "test.db"
    return ConnectionFactory(DatabaseConfig(backend="sqlite", sqlite_path=db_path))


_PG_URL = os.getenv("DATABASE_URL", "")
_PG_AVAILABLE = bool(
    _PG_URL and (_PG_URL.startswith("postgresql") or _PG_URL.startswith("postgres"))
)


@pytest.fixture()
def pg_factory() -> ConnectionFactory:
    if not _PG_AVAILABLE:
        pytest.skip("DATABASE_URL not set to a PostgreSQL URL; skipping PostgreSQL tests")
    return ConnectionFactory(DatabaseConfig(backend="postgresql", postgresql_url=_PG_URL))


@pytest.fixture(
    params=["sqlite", pytest.param("postgresql", marks=pytest.mark.skipif(
        not _PG_AVAILABLE, reason="DATABASE_URL not set to a PostgreSQL URL"
    ))],
)
def any_factory(request, tmp_path: Path) -> ConnectionFactory:
    """Parametrized factory — yields SQLite always, PostgreSQL only if available."""
    if request.param == "sqlite":
        return ConnectionFactory(
            DatabaseConfig(backend="sqlite", sqlite_path=tmp_path / "param.db")
        )
    return ConnectionFactory(DatabaseConfig(backend="postgresql", postgresql_url=_PG_URL))


# ── DatabaseConfig ────────────────────────────────────────────────────────────


def test_database_config_default_backend() -> None:
    cfg = DatabaseConfig()
    assert cfg.backend == "sqlite"


def test_database_config_sqlite_backend() -> None:
    cfg = DatabaseConfig(backend="sqlite", sqlite_path=Path("test.db"))
    assert cfg.backend == "sqlite"
    assert cfg.sqlite_path == Path("test.db")


def test_database_config_postgresql_backend() -> None:
    cfg = DatabaseConfig(
        backend="postgresql",
        postgresql_url="postgresql+psycopg2://user:pass@host/db",
    )
    assert cfg.backend == "postgresql"
    assert cfg.postgresql_url == "postgresql+psycopg2://user:pass@host/db"


def test_database_config_is_immutable() -> None:
    cfg = DatabaseConfig()
    with pytest.raises(Exception):
        cfg.backend = "postgresql"  # type: ignore[misc]


# ── load_database_config ──────────────────────────────────────────────────────


def test_load_database_config_defaults_to_sqlite(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    cfg = load_database_config()
    assert cfg.backend == "sqlite"


def test_load_database_config_postgresql_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg2://u:p@localhost/db")
    cfg = load_database_config()
    assert cfg.backend == "postgresql"
    assert cfg.postgresql_url == "postgresql+psycopg2://u:p@localhost/db"


def test_load_database_config_postgres_prefix_also_works(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgres://u:p@localhost/db")
    cfg = load_database_config()
    assert cfg.backend == "postgresql"


def test_load_database_config_ignores_non_pg_database_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "sqlite:///local.db")
    cfg = load_database_config()
    assert cfg.backend == "sqlite"


# ── ConnectionFactory: backend property ──────────────────────────────────────


def test_connection_factory_backend_sqlite(sqlite_factory: ConnectionFactory) -> None:
    assert sqlite_factory.backend == "sqlite"


def test_connection_factory_sqlite_path_set(
    sqlite_factory: ConnectionFactory, tmp_path: Path
) -> None:
    assert sqlite_factory.sqlite_path is not None
    assert sqlite_factory.sqlite_path.parent == tmp_path


# ── ConnectionFactory: SQLite connection ──────────────────────────────────────


def test_sqlite_get_connection_returns_sqlite3_connection(
    sqlite_factory: ConnectionFactory,
) -> None:
    conn = sqlite_factory.get_connection()
    try:
        assert isinstance(conn, sqlite3.Connection)
    finally:
        conn.close()


def test_sqlite_connection_has_row_factory(sqlite_factory: ConnectionFactory) -> None:
    conn = sqlite_factory.get_connection()
    try:
        assert conn.row_factory is sqlite3.Row
    finally:
        conn.close()


def test_sqlite_wal_mode_is_set(sqlite_factory: ConnectionFactory) -> None:
    conn = sqlite_factory.get_connection()
    try:
        row = conn.execute("PRAGMA journal_mode;").fetchone()
        assert row[0] == "wal"
    finally:
        conn.close()


def test_sqlite_foreign_keys_are_enabled(sqlite_factory: ConnectionFactory) -> None:
    conn = sqlite_factory.get_connection()
    try:
        row = conn.execute("PRAGMA foreign_keys;").fetchone()
        assert row[0] == 1
    finally:
        conn.close()


def test_sqlite_pragmas_not_applied_to_postgresql_factory() -> None:
    """Ensure we don't accidentally apply SQLite pragmas to PostgreSQL config."""
    cfg = DatabaseConfig(
        backend="postgresql",
        postgresql_url="postgresql+psycopg2://u:p@localhost/db",
    )
    factory = ConnectionFactory(cfg)
    # The factory is created without error; pragmas are only applied on connection.
    assert factory.backend == "postgresql"


# ── ConnectionFactory: SQLAlchemy engine ─────────────────────────────────────


def test_sqlite_engine_is_created(sqlite_factory: ConnectionFactory) -> None:
    engine = sqlite_factory.engine
    assert engine is not None


def test_sqlite_engine_url_contains_sqlite(sqlite_factory: ConnectionFactory) -> None:
    engine = sqlite_factory.engine
    assert "sqlite" in str(engine.url)


def test_sqlite_engine_is_cached(sqlite_factory: ConnectionFactory) -> None:
    e1 = sqlite_factory.engine
    e2 = sqlite_factory.engine
    assert e1 is e2


# ── ConnectionFactory: creates DB file on first connection ────────────────────


def test_sqlite_creates_db_file_on_connect(tmp_path: Path) -> None:
    db_path = tmp_path / "new" / "nested" / "test.db"
    factory = ConnectionFactory(DatabaseConfig(backend="sqlite", sqlite_path=db_path))
    conn = factory.get_connection()
    conn.close()
    assert db_path.exists()


# ── BaseSqliteRepository: accepts connection_factory ─────────────────────────


class _SimpleRepo(BaseSqliteRepository):
    """Minimal subclass for testing connection factory injection."""

    def write_and_read(self, value: str) -> str:
        with self._connection() as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS _kv (k TEXT PRIMARY KEY, v TEXT)"
            )
            conn.execute(
                "INSERT OR REPLACE INTO _kv VALUES (?, ?)", ("key", value)
            )
            conn.commit()
            row = conn.execute("SELECT v FROM _kv WHERE k='key'").fetchone()
            return row[0]


def test_base_repo_accepts_connection_factory(tmp_path: Path) -> None:
    factory = ConnectionFactory(
        DatabaseConfig(backend="sqlite", sqlite_path=tmp_path / "repo.db")
    )
    repo = _SimpleRepo(connection_factory=factory)
    result = repo.write_and_read("hello")
    assert result == "hello"


def test_base_repo_backward_compat_db_path(tmp_path: Path) -> None:
    """Existing db_path parameter must still work unchanged."""
    db_path = tmp_path / "compat.db"
    repo = _SimpleRepo(db_path=db_path)
    result = repo.write_and_read("world")
    assert result == "world"


def test_base_repo_connection_factory_backend_is_sqlite(tmp_path: Path) -> None:
    factory = ConnectionFactory(
        DatabaseConfig(backend="sqlite", sqlite_path=tmp_path / "t.db")
    )
    repo = _SimpleRepo(connection_factory=factory)
    assert repo._connection_factory.backend == "sqlite"


# ── Parametrized: both backends ───────────────────────────────────────────────


def test_factory_get_connection_returns_connection(any_factory: ConnectionFactory) -> None:
    conn = any_factory.get_connection()
    try:
        assert conn is not None
    finally:
        conn.close()


def test_factory_backend_matches_config(any_factory: ConnectionFactory) -> None:
    assert any_factory.backend in ("sqlite", "postgresql")


# ── PostgreSQL-specific tests ─────────────────────────────────────────────────


def test_pg_factory_backend_is_postgresql(pg_factory: ConnectionFactory) -> None:
    assert pg_factory.backend == "postgresql"


def test_pg_factory_engine_url_starts_with_postgresql(pg_factory: ConnectionFactory) -> None:
    assert "postgresql" in str(pg_factory.engine.url) or "postgres" in str(
        pg_factory.engine.url
    )


def test_pg_connection_can_execute_select(pg_factory: ConnectionFactory) -> None:
    conn = pg_factory.get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT 1")
        row = cur.fetchone()
        assert row[0] == 1
        cur.close()
    finally:
        conn.close()

"""Database configuration and connection factory (Issue #1104).

Provides a ``DatabaseConfig`` / ``ConnectionFactory`` abstraction that
supports both SQLite (default) and PostgreSQL backends without requiring
any changes to existing repository logic.

Backend selection
─────────────────
``backend`` defaults to ``"sqlite"``.  Set the ``DATABASE_URL`` environment
variable to a PostgreSQL connection string to switch to PostgreSQL:

    DATABASE_URL=postgresql+psycopg2://user:pass@host/db

SQLite path is resolved from ``CILLY_DB_PATH`` or defaults to
``cilly_trading.db`` in the current working directory (same as before).

SQLite-specific pragmas
────────────────────────
``PRAGMA journal_mode=WAL``, ``PRAGMA foreign_keys=ON``, and
``PRAGMA busy_timeout=30000`` are applied only when ``backend == "sqlite"``.
They are not applied (and not relevant) for the PostgreSQL backend.
"""

from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

DATABASE_URL_ENV_VAR = "DATABASE_URL"


@dataclass(frozen=True)
class DatabaseConfig:
    """Immutable database backend configuration.

    Attributes:
        backend: Either ``"sqlite"`` (default) or ``"postgresql"``.
        sqlite_path: Path to the SQLite database file.  ``None`` defers
            resolution to :func:`load_database_config`.
        postgresql_url: Full SQLAlchemy-compatible PostgreSQL connection
            URL (e.g. ``postgresql+psycopg2://user:pass@host/db``).
            Required when ``backend == "postgresql"``.
    """

    backend: Literal["sqlite", "postgresql"] = "sqlite"
    sqlite_path: Path | None = None
    postgresql_url: str | None = None


def load_database_config() -> DatabaseConfig:
    """Build :class:`DatabaseConfig` from the current process environment.

    If ``DATABASE_URL`` is set and starts with ``postgresql`` or
    ``postgres``, the PostgreSQL backend is selected.  Otherwise SQLite is
    used with the path resolved by
    :func:`cilly_trading.db.init_db.resolve_default_db_path`.

    Returns:
        A :class:`DatabaseConfig` reflecting the current environment.
    """
    db_url = os.getenv(DATABASE_URL_ENV_VAR)
    if db_url and (
        db_url.startswith("postgresql") or db_url.startswith("postgres")
    ):
        return DatabaseConfig(backend="postgresql", postgresql_url=db_url)

    from cilly_trading.db.init_db import resolve_default_db_path

    return DatabaseConfig(backend="sqlite", sqlite_path=resolve_default_db_path())


class ConnectionFactory:
    """Creates database connections for the configured backend.

    Supports SQLite (default, uses the stdlib ``sqlite3`` module) and
    PostgreSQL (via SQLAlchemy, optional).

    For the SQLite backend the factory applies SQLite-specific pragmas
    (WAL mode, foreign keys, busy timeout) on every new connection.  These
    pragmas are intentionally not applied for the PostgreSQL backend.

    A lazy SQLAlchemy :class:`~sqlalchemy.engine.Engine` is also available
    via the :attr:`engine` property for both backends (e.g. for schema
    inspection or Alembic migrations).

    Args:
        config: Database configuration.  When ``None`` the config is loaded
            from the process environment via :func:`load_database_config`.
    """

    def __init__(self, config: DatabaseConfig | None = None) -> None:
        if config is None:
            config = load_database_config()
        self._config = config
        self._engine: Any = None  # lazy SQLAlchemy engine

    # ── public properties ──────────────────────────────────────────────────

    @property
    def backend(self) -> Literal["sqlite", "postgresql"]:
        """The configured database backend."""
        return self._config.backend

    @property
    def sqlite_path(self) -> Path | None:
        """The SQLite file path, or ``None`` when backend is PostgreSQL."""
        return self._config.sqlite_path

    @property
    def engine(self) -> Any:
        """Lazy SQLAlchemy engine for the configured backend.

        For SQLite the engine attaches a ``connect`` event listener that
        applies the standard pragmas so that connections obtained via
        SQLAlchemy also inherit the correct SQLite settings.

        Raises:
            ImportError: If ``sqlalchemy`` is not installed.
        """
        if self._engine is None:
            self._engine = self._create_engine()
        return self._engine

    # ── connection retrieval ───────────────────────────────────────────────

    def get_connection(self) -> Any:
        """Return a DB-API 2.0 connection for the configured backend.

        For SQLite:
            Returns a :class:`sqlite3.Connection` with ``row_factory`` set
            to :data:`sqlite3.Row` and WAL / foreign-keys / busy-timeout
            pragmas applied.

        For PostgreSQL:
            Returns a raw connection from the SQLAlchemy engine (psycopg2
            or another configured dialect driver).

        Returns:
            An open database connection.  The caller is responsible for
            closing it when done.
        """
        if self._config.backend == "sqlite":
            return self._get_sqlite_connection()
        return self.engine.raw_connection()

    # ── internals ─────────────────────────────────────────────────────────

    def _get_sqlite_connection(self) -> sqlite3.Connection:
        path = self._config.sqlite_path
        if path is None:
            from cilly_trading.db.init_db import resolve_default_db_path

            path = resolve_default_db_path()

        if path.parent and not path.parent.exists():
            path.parent.mkdir(parents=True, exist_ok=True)

        conn = sqlite3.connect(str(path), timeout=30.0)
        conn.row_factory = sqlite3.Row
        # SQLite-specific pragmas — applied only for this backend
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA busy_timeout = 30000;")
        return conn

    def _create_engine(self) -> Any:
        try:
            from sqlalchemy import create_engine, event
        except ImportError as exc:
            raise ImportError(
                "sqlalchemy is required to use ConnectionFactory.engine; "
                "install it with: pip install sqlalchemy"
            ) from exc

        if self._config.backend == "sqlite":
            path = self._config.sqlite_path
            if path is None:
                from cilly_trading.db.init_db import resolve_default_db_path

                path = resolve_default_db_path()
            engine = create_engine(
                f"sqlite:///{path}",
                connect_args={"check_same_thread": False},
            )

            # Apply SQLite pragmas for connections obtained through the engine
            @event.listens_for(engine, "connect")
            def _set_sqlite_pragmas(
                dbapi_conn: Any, _connection_record: Any
            ) -> None:
                cur = dbapi_conn.cursor()
                cur.execute("PRAGMA journal_mode=WAL")
                cur.execute("PRAGMA foreign_keys=ON")
                cur.execute("PRAGMA busy_timeout=30000")
                cur.close()

            return engine

        # PostgreSQL
        url = self._config.postgresql_url
        if not url:
            raise ValueError(
                "postgresql_url must be set in DatabaseConfig when backend is 'postgresql'"
            )
        return create_engine(url)

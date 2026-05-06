from __future__ import annotations

import asyncio
import functools
import logging
import os
import random
import sqlite3
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from pathlib import Path
from typing import Any, Callable, Iterable, Optional, Sequence, TypeVar

from cilly_trading.db import DEFAULT_DB_PATH, init_db

logger = logging.getLogger(__name__)

_MAX_RETRIES = 4
_BASE_DELAY_S = 0.1

# Default SQLite busy_timeout for interactive (API) requests, in
# milliseconds. Keeping this short (5s) prevents an API request from
# parking on a single Connection for the previous 30s default and
# starving the request thread pool. Batch jobs that need a longer wait
# can override via :func:`BaseSqliteRepository._set_busy_timeout` or by
# setting ``CILLY_SQLITE_BUSY_TIMEOUT_MS``.
_DEFAULT_BUSY_TIMEOUT_MS = 5_000

# ``synchronous = NORMAL`` is the recommended setting for WAL mode: it
# preserves crash-safety for committed transactions while removing the
# extra fsync per write that ``FULL`` enforces. SQLite docs:
# https://www.sqlite.org/pragma.html#pragma_synchronous
_DEFAULT_SYNCHRONOUS = "NORMAL"

# Dedicated thread pool for SQLite I/O — keeps blocking DB calls off the
# event loop when repositories are called from async handlers.
_SQLITE_EXECUTOR: ThreadPoolExecutor = ThreadPoolExecutor(
    max_workers=4, thread_name_prefix="sqlite"
)

_T = TypeVar("_T")


def _resolve_busy_timeout_ms() -> int:
    raw = os.getenv("CILLY_SQLITE_BUSY_TIMEOUT_MS")
    if raw is None:
        return _DEFAULT_BUSY_TIMEOUT_MS
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return _DEFAULT_BUSY_TIMEOUT_MS
    if value <= 0:
        return _DEFAULT_BUSY_TIMEOUT_MS
    return value


def _resolve_synchronous_mode() -> str:
    raw = os.getenv("CILLY_SQLITE_SYNCHRONOUS")
    if raw is None:
        return _DEFAULT_SYNCHRONOUS
    normalized = raw.strip().upper()
    if normalized not in {"OFF", "NORMAL", "FULL", "EXTRA"}:
        return _DEFAULT_SYNCHRONOUS
    return normalized


class BaseSqliteRepository:
    def __init__(self, db_path: Optional[Path] = None) -> None:
        self._db_path = Path(db_path if db_path is not None else DEFAULT_DB_PATH)
        init_db(self._db_path)

    def _get_connection(self) -> sqlite3.Connection:
        last_exc: sqlite3.OperationalError | None = None
        busy_timeout_ms = _resolve_busy_timeout_ms()
        synchronous = _resolve_synchronous_mode()
        for attempt in range(_MAX_RETRIES):
            try:
                conn = sqlite3.connect(self._db_path, timeout=30.0)
                conn.row_factory = sqlite3.Row
                conn.execute("PRAGMA journal_mode=WAL;")
                conn.execute("PRAGMA foreign_keys = ON;")
                # Issue #1136:
                #   * shorter busy_timeout for interactive requests
                #   * synchronous=NORMAL for better write throughput in WAL
                conn.execute(f"PRAGMA busy_timeout = {busy_timeout_ms};")
                conn.execute(f"PRAGMA synchronous = {synchronous};")
                return conn
            except sqlite3.OperationalError as exc:
                last_exc = exc
                if attempt < _MAX_RETRIES - 1:
                    delay = _BASE_DELAY_S * (2**attempt) + random.uniform(0, 0.05)
                    logger.warning(
                        "sqlite_connection_failed",
                        extra={
                            "attempt": attempt + 1,
                            "max_retries": _MAX_RETRIES,
                            "retry_delay_s": round(delay, 4),
                            "db_path": str(self._db_path),
                            "error": str(exc),
                        },
                    )
                    time.sleep(delay)
        raise last_exc  # type: ignore[misc]

    def _connection(self):
        return closing(self._get_connection())

    def _executemany(
        self,
        sql: str,
        rows: Sequence[Sequence[Any]] | Iterable[Sequence[Any]],
    ) -> int:
        """Run a single ``executemany`` for batch inserts/updates.

        Returns the number of rows affected. A single transaction is used,
        which is dramatically cheaper than committing per row when many
        signals or trades are persisted in one request (issue #1136).
        """

        materialised: list[Sequence[Any]] = list(rows)
        if not materialised:
            return 0
        with self._connection() as conn:
            cur = conn.cursor()
            cur.executemany(sql, materialised)
            conn.commit()
            return cur.rowcount if cur.rowcount is not None else 0

    # ------------------------------------------------------------------
    # Read-query construction helpers (issue #1137).
    #
    # These helpers exist to remove duplicated optional-filter / pagination
    # construction across read methods in repositories such as
    # ``SqliteSignalRepository`` and ``SqliteOrderEventRepository``.
    #
    # They are intentionally narrow:
    #   * They only build equality filters and append them to a caller-supplied
    #     ``where_clauses`` / ``params`` pair.
    #   * They never interpolate user-controlled values into SQL — only column
    #     names from the calling repository (which are static identifiers).
    #   * They do not introduce a new public repository API: all helpers are
    #     marked private with a leading underscore.
    # ------------------------------------------------------------------

    @staticmethod
    def _append_equality_filter(
        where_clauses: list[str],
        params: list[Any],
        column: str,
        value: Any,
    ) -> None:
        """Append ``column = ?`` to *where_clauses* and bind ``value``.

        ``value`` is appended only if it is not ``None``. ``column`` MUST be a
        static identifier provided by the caller (never user-controlled).
        """

        if value is None:
            return
        where_clauses.append(f"{column} = ?")
        params.append(value)

    @staticmethod
    def _append_equality_filters(
        where_clauses: list[str],
        params: list[Any],
        filters: Iterable[tuple[str, Any]],
    ) -> None:
        """Convenience wrapper for adding several optional equality filters."""

        for column, value in filters:
            BaseSqliteRepository._append_equality_filter(
                where_clauses, params, column, value
            )

    @staticmethod
    def _compose_where_clause(where_clauses: Sequence[str]) -> str:
        """Return ``"WHERE a AND b"`` or ``""`` for an empty clause list."""

        if not where_clauses:
            return ""
        return "WHERE " + " AND ".join(where_clauses)

    @staticmethod
    def _pagination_params(limit: int, offset: int) -> list[int]:
        """Return ``[limit, offset]`` as a list ready to extend bind params."""

        return [int(limit), int(offset)]

    async def run_in_thread(
        self, fn: Callable[..., _T], /, *args: Any, **kwargs: Any
    ) -> _T:
        """Run a blocking repository method in the SQLite thread pool.

        Prevents I/O-bound SQLite calls from blocking the asyncio event loop
        when this repository is used from async handlers or tasks.
        """
        loop = asyncio.get_event_loop()
        wrapped = functools.partial(fn, *args, **kwargs) if kwargs else fn
        call_args = () if kwargs else args
        return await loop.run_in_executor(_SQLITE_EXECUTOR, wrapped, *call_args)

from __future__ import annotations

import asyncio
import functools
import logging
import random
import sqlite3
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from pathlib import Path
from typing import Any, Callable, Optional, TypeVar

from cilly_trading.db import DEFAULT_DB_PATH, init_db

logger = logging.getLogger(__name__)

_MAX_RETRIES = 4
_BASE_DELAY_S = 0.1

# Dedicated thread pool for SQLite I/O — keeps blocking DB calls off the
# event loop when repositories are called from async handlers.
_SQLITE_EXECUTOR: ThreadPoolExecutor = ThreadPoolExecutor(
    max_workers=4, thread_name_prefix="sqlite"
)

_T = TypeVar("_T")


class BaseSqliteRepository:
    def __init__(self, db_path: Optional[Path] = None) -> None:
        self._db_path = Path(db_path if db_path is not None else DEFAULT_DB_PATH)
        init_db(self._db_path)

    def _get_connection(self) -> sqlite3.Connection:
        last_exc: sqlite3.OperationalError | None = None
        for attempt in range(_MAX_RETRIES):
            try:
                conn = sqlite3.connect(self._db_path, timeout=30.0)
                conn.row_factory = sqlite3.Row
                conn.execute("PRAGMA journal_mode=WAL;")
                conn.execute("PRAGMA foreign_keys = ON;")
                conn.execute("PRAGMA busy_timeout = 30000;")
                return conn
            except sqlite3.OperationalError as exc:
                last_exc = exc
                if attempt < _MAX_RETRIES - 1:
                    delay = _BASE_DELAY_S * (2**attempt) + random.uniform(0, 0.05)
                    logger.warning(
                        "SQLite connection failed (attempt %d/%d), retrying in %.2fs: %s",
                        attempt + 1,
                        _MAX_RETRIES,
                        delay,
                        exc,
                    )
                    time.sleep(delay)
        raise last_exc  # type: ignore[misc]

    def _connection(self):
        return closing(self._get_connection())

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

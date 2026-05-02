from __future__ import annotations

import logging
import random
import sqlite3
import time
from contextlib import closing
from pathlib import Path
from typing import Optional

from cilly_trading.db import DEFAULT_DB_PATH, init_db

logger = logging.getLogger(__name__)

_MAX_RETRIES = 4
_BASE_DELAY_S = 0.1


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

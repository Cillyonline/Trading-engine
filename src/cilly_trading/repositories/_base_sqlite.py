from __future__ import annotations

import logging
import random
import sqlite3
import time
from contextlib import closing
from pathlib import Path
from typing import Optional

from cilly_trading.db import DEFAULT_DB_PATH, init_db
from cilly_trading.db.config import ConnectionFactory, DatabaseConfig

logger = logging.getLogger(__name__)

_MAX_RETRIES = 4
_BASE_DELAY_S = 0.1


class BaseSqliteRepository:
    def __init__(
        self,
        db_path: Optional[Path] = None,
        *,
        connection_factory: Optional[ConnectionFactory] = None,
    ) -> None:
        if connection_factory is not None:
            self._connection_factory = connection_factory
            self._db_path = connection_factory.sqlite_path
            # Only initialise the schema for SQLite — PostgreSQL schema management
            # is out of scope for this layer.
            if (
                connection_factory.backend == "sqlite"
                and connection_factory.sqlite_path is not None
            ):
                init_db(connection_factory.sqlite_path)
        else:
            path = Path(db_path if db_path is not None else DEFAULT_DB_PATH)
            self._db_path = path
            self._connection_factory = ConnectionFactory(
                DatabaseConfig(backend="sqlite", sqlite_path=path)
            )
            init_db(path)

    def _get_connection(self):
        last_exc: Exception | None = None
        for attempt in range(_MAX_RETRIES):
            try:
                return self._connection_factory.get_connection()
            except (sqlite3.OperationalError, Exception) as exc:
                last_exc = exc
                if attempt < _MAX_RETRIES - 1:
                    delay = _BASE_DELAY_S * (2**attempt) + random.uniform(0, 0.05)
                    logger.warning(
                        "DB connection failed (attempt %d/%d), retrying in %.2fs: %s",
                        attempt + 1,
                        _MAX_RETRIES,
                        delay,
                        exc,
                    )
                    time.sleep(delay)
        raise last_exc  # type: ignore[misc]

    def _connection(self):
        return closing(self._get_connection())

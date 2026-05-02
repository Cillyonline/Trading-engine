from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Optional

from cilly_trading.db import DEFAULT_DB_PATH, init_db


class BaseSqliteRepository:
    def __init__(self, db_path: Optional[Path] = None) -> None:
        self._db_path = Path(db_path if db_path is not None else DEFAULT_DB_PATH)
        init_db(self._db_path)

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path, timeout=5.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA busy_timeout = 5000;")
        return conn

    def _connection(self):
        return closing(self._get_connection())

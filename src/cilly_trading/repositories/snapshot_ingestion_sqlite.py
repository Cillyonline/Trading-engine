from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from cilly_trading.db import DEFAULT_DB_PATH, init_db


@dataclass(frozen=True)
class SnapshotIngestionRunRecord:
    ingestion_run_id: str
    created_at: str
    source: str
    symbols: tuple[str, ...]
    timeframe: str
    fingerprint_hash: str


@dataclass(frozen=True)
class OhlcvSnapshotRowRecord:
    ingestion_run_id: str
    symbol: str
    timeframe: str
    ts: int
    open: float
    high: float
    low: float
    close: float
    volume: float


class SqliteSnapshotIngestionRepository:
    """Persist bounded snapshot ingestion runs into the canonical SQLite schema."""

    def __init__(self, db_path: Optional[Path] = None) -> None:
        if db_path is None:
            db_path = DEFAULT_DB_PATH
        self._db_path = Path(db_path)
        init_db(self._db_path)

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path, timeout=5.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA busy_timeout = 5000;")
        return conn

    def save_snapshot_run(
        self,
        *,
        run: SnapshotIngestionRunRecord,
        rows: tuple[OhlcvSnapshotRowRecord, ...],
    ) -> None:
        if not rows:
            raise ValueError("snapshot rows must not be empty")

        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO ingestion_runs (
                    ingestion_run_id,
                    created_at,
                    source,
                    symbols_json,
                    timeframe,
                    fingerprint_hash
                )
                VALUES (?, ?, ?, ?, ?, ?);
                """,
                (
                    run.ingestion_run_id,
                    run.created_at,
                    run.source,
                    json.dumps(list(run.symbols), separators=(",", ":"), ensure_ascii=True),
                    run.timeframe,
                    run.fingerprint_hash,
                ),
            )
            cur.executemany(
                """
                INSERT INTO ohlcv_snapshots (
                    ingestion_run_id,
                    symbol,
                    timeframe,
                    ts,
                    open,
                    high,
                    low,
                    close,
                    volume
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                [
                    (
                        row.ingestion_run_id,
                        row.symbol,
                        row.timeframe,
                        row.ts,
                        row.open,
                        row.high,
                        row.low,
                        row.close,
                        row.volume,
                    )
                    for row in rows
                ],
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

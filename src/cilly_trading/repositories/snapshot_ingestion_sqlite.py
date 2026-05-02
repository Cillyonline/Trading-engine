from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from cilly_trading.repositories._base_sqlite import BaseSqliteRepository


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


class SqliteSnapshotIngestionRepository(BaseSqliteRepository):
    """Persist bounded snapshot ingestion runs into the canonical SQLite schema."""

    def save_snapshot_run(
        self,
        *,
        run: SnapshotIngestionRunRecord,
        rows: tuple[OhlcvSnapshotRowRecord, ...],
    ) -> None:
        if not rows:
            raise ValueError("snapshot rows must not be empty")

        with self._connection() as conn:
            cur = conn.cursor()
            try:
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

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import pytest

from cilly_trading.db.init_db import get_connection, init_db


def _insert_ingestion_run(conn: sqlite3.Connection, ingestion_run_id: str) -> None:
    conn.execute(
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
            ingestion_run_id,
            datetime.now(timezone.utc).isoformat(),
            "test",
            json.dumps(["AAPL"]),
            "D1",
            None,
        ),
    )


def _insert_snapshot_row(conn: sqlite3.Connection, ingestion_run_id: str) -> None:
    conn.execute(
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
        (
            ingestion_run_id,
            "AAPL",
            "D1",
            1735689600000,
            101.0,
            102.0,
            100.0,
            101.0,
            1000.0,
        ),
    )


def _snapshot_row_count(conn: sqlite3.Connection, ingestion_run_id: str) -> int:
    cur = conn.execute(
        """
        SELECT COUNT(*) AS total
        FROM ohlcv_snapshots
        WHERE ingestion_run_id = ?;
        """,
        (ingestion_run_id,),
    )
    row = cur.fetchone()
    return int(row[0]) if row else 0


def test_snapshot_rows_are_immutable(tmp_path: Path) -> None:
    db_path = tmp_path / "analysis.db"
    init_db(db_path)
    conn = get_connection(db_path)
    try:
        ingestion_run_id = "00000000-0000-4000-8000-000000000000"
        _insert_ingestion_run(conn, ingestion_run_id)
        _insert_snapshot_row(conn, ingestion_run_id)
        conn.commit()

        with pytest.raises(sqlite3.IntegrityError) as update_error:
            conn.execute(
                """
                UPDATE ohlcv_snapshots
                SET close = 999.0
                WHERE ingestion_run_id = ?;
                """,
                (ingestion_run_id,),
            )
        assert "snapshot_immutable" in str(update_error.value)

        with pytest.raises(sqlite3.IntegrityError) as delete_error:
            conn.execute(
                """
                DELETE FROM ohlcv_snapshots
                WHERE ingestion_run_id = ?;
                """,
                (ingestion_run_id,),
            )
        assert "snapshot_immutable" in str(delete_error.value)

        assert _snapshot_row_count(conn, ingestion_run_id) == 1
    finally:
        conn.close()

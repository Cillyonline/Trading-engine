from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import pandas as pd

from cilly_trading.db import DEFAULT_DB_PATH, init_db
from cilly_trading.db.init_db import get_connection
from data_layer.ingestion_validation import SnapshotValidationError, validate_snapshot_ingestion


def _load_existing_source(
    conn, ingestion_run_id: str
) -> Optional[str]:
    cur = conn.cursor()
    cur.execute(
        """
        SELECT source
        FROM ingestion_runs
        WHERE ingestion_run_id = ?
        LIMIT 1;
        """,
        (ingestion_run_id,),
    )
    row = cur.fetchone()
    if row is None:
        return None
    return row[0]


def _insert_ingestion_run(
    conn,
    *,
    ingestion_run_id: str,
    source: str,
    symbols: list[str],
    timeframe: str,
) -> None:
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
            ingestion_run_id,
            datetime.now(timezone.utc).isoformat(),
            source,
            json.dumps(symbols),
            timeframe,
            None,
        ),
    )


def _resolve_timestamp_column(df: pd.DataFrame) -> str:
    if "ts" in df.columns:
        return "ts"
    return "timestamp"


def _coerce_timestamp(value: object) -> int:
    if isinstance(value, pd.Timestamp):
        return int(value.value // 1_000_000)
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return int(value.timestamp() * 1000)
    if isinstance(value, str):
        parsed = pd.to_datetime(value, utc=True)
        return int(parsed.timestamp() * 1000)
    return int(value)


def _persist_ohlcv_rows(
    conn,
    df: pd.DataFrame,
    *,
    ingestion_run_id: str,
    timeframe: str,
) -> None:
    if df is None or df.empty:
        return

    timestamp_column = _resolve_timestamp_column(df)
    rows = []
    for _, row in df.iterrows():
        rows.append(
            (
                ingestion_run_id,
                row["symbol"],
                row.get("timeframe", timeframe),
                _coerce_timestamp(row[timestamp_column]),
                row["open"],
                row["high"],
                row["low"],
                row["close"],
                row["volume"],
            )
        )

    cur = conn.cursor()
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
        rows,
    )


def ingest_snapshot(
    df: pd.DataFrame,
    *,
    ingestion_run_id: str,
    source: str,
    symbols: list[str],
    timeframe: str,
    db_path: Optional[Path] = None,
) -> None:
    if db_path is None:
        db_path = DEFAULT_DB_PATH

    init_db(db_path)
    conn = get_connection(db_path)
    try:
        existing_source = _load_existing_source(conn, ingestion_run_id)
        validate_snapshot_ingestion(
            df,
            source=source,
            ingestion_run_id=ingestion_run_id,
            existing_source=existing_source,
            symbols=symbols,
            timeframe=timeframe,
        )
        if existing_source is None:
            _insert_ingestion_run(
                conn,
                ingestion_run_id=ingestion_run_id,
                source=source,
                symbols=symbols,
                timeframe=timeframe,
            )
        _persist_ohlcv_rows(
            conn,
            df,
            ingestion_run_id=ingestion_run_id,
            timeframe=timeframe,
        )
        conn.commit()
    except SnapshotValidationError:
        conn.rollback()
        raise
    finally:
        conn.close()

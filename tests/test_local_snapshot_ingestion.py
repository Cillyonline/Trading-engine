from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from cilly_trading.engine.data import (
    SnapshotIngestionError,
    ingest_local_snapshot,
    load_snapshot_metadata,
)


def _count_rows(db_path: Path, table: str) -> int:
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(f"SELECT COUNT(*) FROM {table};")
    count = cur.fetchone()[0]
    conn.close()
    return count


def _fetch_snapshot_ids(db_path: Path) -> list[str]:
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT fingerprint_hash FROM ingestion_runs ORDER BY created_at;")
    rows = [row[0] for row in cur.fetchall()]
    conn.close()
    return rows


def test_local_csv_ingestion_success(tmp_path: Path) -> None:
    db_path = tmp_path / "analysis.db"
    fixture = Path("tests/schema/fixtures/local_snapshot.csv")
    result = ingest_local_snapshot(
        input_path=fixture,
        symbol="AAPL",
        timeframe="D1",
        source="local-test",
        db_path=db_path,
    )

    assert result.snapshot_id
    assert _count_rows(db_path, "ingestion_runs") == 1
    assert _count_rows(db_path, "ohlcv_snapshots") == 2
    assert _fetch_snapshot_ids(db_path)[0] == result.snapshot_id


def test_local_json_ingestion_success(tmp_path: Path) -> None:
    db_path = tmp_path / "analysis.db"
    fixture = Path("tests/schema/fixtures/local_snapshot.json")
    result = ingest_local_snapshot(
        input_path=fixture,
        symbol="AAPL",
        timeframe="D1",
        source="local-test",
        db_path=db_path,
    )

    assert result.snapshot_id
    assert _count_rows(db_path, "ingestion_runs") == 1
    assert _count_rows(db_path, "ohlcv_snapshots") == 2
    assert _fetch_snapshot_ids(db_path)[0] == result.snapshot_id


def test_local_snapshot_idempotent(tmp_path: Path) -> None:
    db_path = tmp_path / "analysis.db"
    fixture = Path("tests/schema/fixtures/local_snapshot.csv")
    first = ingest_local_snapshot(
        input_path=fixture,
        symbol="AAPL",
        timeframe="D1",
        source="local-test",
        db_path=db_path,
    )
    second = ingest_local_snapshot(
        input_path=fixture,
        symbol="AAPL",
        timeframe="D1",
        source="local-test",
        db_path=db_path,
    )

    assert first.snapshot_id == second.snapshot_id
    assert _count_rows(db_path, "ingestion_runs") == 2
    assert _count_rows(db_path, "ohlcv_snapshots") == 2


def test_local_snapshot_invalid_input(tmp_path: Path) -> None:
    db_path = tmp_path / "analysis.db"
    fixture = Path("tests/schema/fixtures/local_snapshot_invalid.csv")

    with pytest.raises(SnapshotIngestionError, match="snapshot_missing_columns"):
        ingest_local_snapshot(
            input_path=fixture,
            symbol="AAPL",
            timeframe="D1",
            source="local-test",
            db_path=db_path,
        )

    assert _count_rows(db_path, "ingestion_runs") == 0
    assert _count_rows(db_path, "ohlcv_snapshots") == 0


def test_local_snapshot_metadata_uses_fingerprint(tmp_path: Path) -> None:
    db_path = tmp_path / "analysis.db"
    fixture = Path("tests/schema/fixtures/local_snapshot.csv")
    result = ingest_local_snapshot(
        input_path=fixture,
        symbol="AAPL",
        timeframe="D1",
        source="local-test",
        db_path=db_path,
    )

    metadata = load_snapshot_metadata(
        ingestion_run_id=result.ingestion_run_id,
        db_path=db_path,
    )

    assert metadata["snapshot_id"] == result.snapshot_id
    if "payload_checksum" in metadata:
        assert metadata["payload_checksum"] == result.snapshot_id
    if "deterministic_snapshot_id" in metadata:
        assert metadata["deterministic_snapshot_id"] == result.snapshot_id

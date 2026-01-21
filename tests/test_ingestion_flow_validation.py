from __future__ import annotations

import json
import sqlite3
import uuid
from pathlib import Path

import pandas as pd
import pytest

from cilly_trading.db import init_db
from cilly_trading.ingestion import ingest_snapshot
from data_layer.ingestion_validation import SnapshotValidationError


def _base_df() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "symbol": "AAPL",
                "timeframe": "D1",
                "timestamp": "2024-01-01T00:00:00Z",
                "open": 1,
                "high": 2,
                "low": 1,
                "close": 2,
                "volume": 10,
            },
            {
                "symbol": "AAPL",
                "timeframe": "D1",
                "timestamp": "2024-01-02T00:00:00Z",
                "open": 2,
                "high": 3,
                "low": 2,
                "close": 3,
                "volume": 11,
            },
        ]
    )


def _count_rows(db_path: Path, table: str) -> int:
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(f"SELECT COUNT(*) FROM {table};")
    count = cur.fetchone()[0]
    conn.close()
    return count


def test_ingest_snapshot_blocks_invalid_rows(monkeypatch, tmp_path: Path) -> None:
    db_path = tmp_path / "analysis.db"
    df = _base_df()
    df["source"] = ["yahoo", "binance"]
    called = {"insert": False, "persist": False}

    def _spy_insert(*args, **kwargs) -> None:
        called["insert"] = True

    def _spy_persist(*args, **kwargs) -> None:
        called["persist"] = True

    monkeypatch.setattr("cilly_trading.ingestion._insert_ingestion_run", _spy_insert)
    monkeypatch.setattr("cilly_trading.ingestion._persist_ohlcv_rows", _spy_persist)

    with pytest.raises(SnapshotValidationError, match="snapshot_mixed_sources"):
        ingest_snapshot(
            df,
            ingestion_run_id=str(uuid.uuid4()),
            source="yahoo",
            symbols=["AAPL"],
            timeframe="D1",
            db_path=db_path,
        )

    assert called["insert"] is False
    assert called["persist"] is False
    assert _count_rows(db_path, "ingestion_runs") == 0
    assert _count_rows(db_path, "ohlcv_snapshots") == 0


def test_ingest_snapshot_rejects_source_change(monkeypatch, tmp_path: Path) -> None:
    db_path = tmp_path / "analysis.db"
    init_db(db_path)
    ingestion_run_id = str(uuid.uuid4())
    conn = sqlite3.connect(db_path)
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
            "2024-01-01T00:00:00+00:00",
            "yahoo",
            json.dumps(["AAPL"]),
            "D1",
            None,
        ),
    )
    conn.commit()
    conn.close()

    df = _base_df()
    df["source"] = ["binance", "binance"]
    called = {"persist": False}

    def _spy_persist(*args, **kwargs) -> None:
        called["persist"] = True

    monkeypatch.setattr("cilly_trading.ingestion._persist_ohlcv_rows", _spy_persist)

    with pytest.raises(SnapshotValidationError, match="snapshot_source_immutable"):
        ingest_snapshot(
            df,
            ingestion_run_id=ingestion_run_id,
            source="binance",
            symbols=["AAPL"],
            timeframe="D1",
            db_path=db_path,
        )

    assert called["persist"] is False
    assert _count_rows(db_path, "ohlcv_snapshots") == 0

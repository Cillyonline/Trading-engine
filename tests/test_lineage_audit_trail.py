from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
import pytest

from cilly_trading.db import init_db
from cilly_trading.engine.core import EngineConfig, run_watchlist_analysis
from cilly_trading.engine.lineage import LineageMissingError
from cilly_trading.repositories.lineage_repository import SqliteLineageRepository
from cilly_trading.repositories.signals_sqlite import SqliteSignalRepository


class _TestStrategy:
    name = "TEST"

    def generate_signals(self, df: Any, config: Dict[str, Any]) -> List[dict]:
        return [{"score": 42.0, "stage": "setup"}]


class _InconsistentLineageStrategy:
    name = "TEST"

    def generate_signals(self, df: Any, config: Dict[str, Any]) -> List[dict]:
        return [{"score": 42.0, "stage": "setup", "ingestion_run_id": "other-run"}]


def _insert_ingestion_run(db_path: Path, ingestion_run_id: str, snapshot_id: str) -> None:
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
            "2025-01-01T00:00:00+00:00",
            "internal",
            '["AAPL"]',
            "D1",
            snapshot_id,
        ),
    )
    conn.commit()
    conn.close()


def _insert_snapshot_row(db_path: Path, ingestion_run_id: str) -> None:
    conn = sqlite3.connect(db_path)
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
            100.0,
            110.0,
            90.0,
            105.0,
            1000.0,
        ),
    )
    conn.commit()
    conn.close()


def _minimal_df() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "timestamp": "2025-01-01T00:00:00Z",
                "open": 1.0,
                "high": 1.0,
                "low": 1.0,
                "close": 1.0,
                "volume": 100.0,
            }
        ]
    )


def test_lineage_persisted_on_successful_analysis(tmp_path: Path) -> None:
    db_path = tmp_path / "analysis.db"
    init_db(db_path)
    ingestion_run_id = "11111111-1111-4111-8111-111111111111"
    snapshot_id = "snapshot-0001"
    _insert_ingestion_run(db_path, ingestion_run_id, snapshot_id)
    _insert_snapshot_row(db_path, ingestion_run_id)

    signal_repo = SqliteSignalRepository(db_path=db_path)
    signals = run_watchlist_analysis(
        symbols=["AAPL"],
        strategies=[_TestStrategy()],
        engine_config=EngineConfig(),
        strategy_configs={},
        signal_repo=signal_repo,
        ingestion_run_id=ingestion_run_id,
        snapshot_id=snapshot_id,
        db_path=db_path,
        snapshot_only=True,
    )

    lineage_repo = SqliteLineageRepository(db_path=db_path)
    records = lineage_repo.list_by_snapshot_id(snapshot_id)

    assert len(records) == 1
    record = records[0]
    assert record.snapshot_id == snapshot_id
    assert record.ingestion_run_id == ingestion_run_id
    assert record.analysis_run_id

    assert signals
    for signal in signals:
        assert signal.get("analysis_run_id")
        assert signal.get("snapshot_id")
        assert signal.get("ingestion_run_id")
        assert signal["analysis_run_id"] == record.analysis_run_id
        assert signal["snapshot_id"] == record.snapshot_id
        assert signal["ingestion_run_id"] == record.ingestion_run_id


def test_analysis_fails_without_lineage(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("cilly_trading.engine.core.load_ohlcv", lambda **_: _minimal_df())
    with pytest.raises(LineageMissingError, match="ingestion_run_id is required"):
        run_watchlist_analysis(
            symbols=["AAPL"],
            strategies=[_TestStrategy()],
            engine_config=EngineConfig(external_data_enabled=True),
            strategy_configs={},
            signal_repo=SqliteSignalRepository(db_path=tmp_path / "signals.db"),
            ingestion_run_id="",
            snapshot_id="snapshot-missing",
        )


def test_analysis_fails_when_lineage_inconsistent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("cilly_trading.engine.core.load_ohlcv", lambda **_: _minimal_df())
    with pytest.raises(LineageMissingError, match="ingestion_run_id mismatch"):
        run_watchlist_analysis(
            symbols=["AAPL"],
            strategies=[_InconsistentLineageStrategy()],
            engine_config=EngineConfig(external_data_enabled=True),
            strategy_configs={},
            signal_repo=SqliteSignalRepository(db_path=tmp_path / "signals.db"),
            ingestion_run_id="ingest-consistency-001",
            snapshot_id="snapshot-consistency-001",
        )


def test_analysis_run_id_is_deterministic_for_same_inputs(tmp_path: Path) -> None:
    ingestion_run_id = "11111111-1111-4111-8111-111111111111"
    snapshot_id = "snapshot-0001"

    db_path_a = tmp_path / "analysis_a.db"
    init_db(db_path_a)
    _insert_ingestion_run(db_path_a, ingestion_run_id, snapshot_id)
    _insert_snapshot_row(db_path_a, ingestion_run_id)
    signal_repo_a = SqliteSignalRepository(db_path=db_path_a)
    signals_a = run_watchlist_analysis(
        symbols=["AAPL"],
        strategies=[_TestStrategy()],
        engine_config=EngineConfig(),
        strategy_configs={},
        signal_repo=signal_repo_a,
        ingestion_run_id=ingestion_run_id,
        snapshot_id=snapshot_id,
        db_path=db_path_a,
        snapshot_only=True,
    )

    db_path_b = tmp_path / "analysis_b.db"
    init_db(db_path_b)
    _insert_ingestion_run(db_path_b, ingestion_run_id, snapshot_id)
    _insert_snapshot_row(db_path_b, ingestion_run_id)
    signal_repo_b = SqliteSignalRepository(db_path=db_path_b)
    signals_b = run_watchlist_analysis(
        symbols=["AAPL"],
        strategies=[_TestStrategy()],
        engine_config=EngineConfig(),
        strategy_configs={},
        signal_repo=signal_repo_b,
        ingestion_run_id=ingestion_run_id,
        snapshot_id=snapshot_id,
        db_path=db_path_b,
        snapshot_only=True,
    )

    assert signals_a
    assert signals_b
    assert signals_a[0]["analysis_run_id"] == signals_b[0]["analysis_run_id"]

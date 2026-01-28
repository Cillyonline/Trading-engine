from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path

import pytest

from cilly_trading.db import init_db
from cilly_trading.engine.core import EngineConfig, run_watchlist_analysis
from cilly_trading.repositories.signals_sqlite import SqliteSignalRepository


class _NoopStrategy:
    name = "NOOP"

    def generate_signals(self, df, config):
        return []


def _insert_ingestion_run(db_path: Path, ingestion_run_id: str) -> None:
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
            json.dumps(["AAPL"]),
            "D1",
            "checksum-123",
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


def _prepare_snapshot_db(db_path: Path, ingestion_run_id: str) -> None:
    init_db(db_path)
    _insert_ingestion_run(db_path, ingestion_run_id)
    _insert_snapshot_row(db_path, ingestion_run_id)


def test_phase6_snapshot_requires_ingestion_run_id(tmp_path: Path) -> None:
    signal_repo = SqliteSignalRepository(db_path=tmp_path / "signals.db")
    with pytest.raises(ValueError, match="snapshot_only requires ingestion_run_id"):
        run_watchlist_analysis(
            symbols=["AAPL"],
            strategies=[_NoopStrategy()],
            engine_config=EngineConfig(),
            strategy_configs={},
            signal_repo=signal_repo,
            snapshot_only=True,
        )


def test_phase6_audit_persisted_for_snapshot_run(tmp_path: Path) -> None:
    db_path = tmp_path / "analysis.db"
    ingestion_run_id = "11111111-1111-4111-8111-111111111111"
    _prepare_snapshot_db(db_path, ingestion_run_id)

    signal_repo = SqliteSignalRepository(db_path=tmp_path / "signals.db")
    run_id = "run-0001"
    audit_dir = tmp_path / "audits"

    run_watchlist_analysis(
        symbols=["AAPL"],
        strategies=[_NoopStrategy()],
        engine_config=EngineConfig(),
        strategy_configs={},
        signal_repo=signal_repo,
        ingestion_run_id=ingestion_run_id,
        db_path=db_path,
        run_id=run_id,
        audit_dir=audit_dir,
        snapshot_only=True,
    )

    audit_path = audit_dir / run_id / "audit.json"
    audit_payload = json.loads(audit_path.read_text(encoding="utf-8"))

    assert audit_payload["run_id"] == run_id
    assert audit_payload["snapshot_id"] == ingestion_run_id
    assert audit_payload["snapshot_metadata"]["snapshot_id"] == ingestion_run_id


def test_phase6_replay_produces_identical_audit_bytes(tmp_path: Path) -> None:
    db_path = tmp_path / "analysis.db"
    ingestion_run_id = "11111111-1111-4111-8111-111111111111"
    _prepare_snapshot_db(db_path, ingestion_run_id)

    signal_repo = SqliteSignalRepository(db_path=tmp_path / "signals.db")
    run_id = "run-0002"
    audit_dir = tmp_path / "audits"

    run_watchlist_analysis(
        symbols=["AAPL"],
        strategies=[_NoopStrategy()],
        engine_config=EngineConfig(),
        strategy_configs={},
        signal_repo=signal_repo,
        ingestion_run_id=ingestion_run_id,
        db_path=db_path,
        run_id=run_id,
        audit_dir=audit_dir,
        snapshot_only=True,
    )
    first_bytes = (audit_dir / run_id / "audit.json").read_bytes()

    run_watchlist_analysis(
        symbols=["AAPL"],
        strategies=[_NoopStrategy()],
        engine_config=EngineConfig(),
        strategy_configs={},
        signal_repo=signal_repo,
        ingestion_run_id=ingestion_run_id,
        db_path=db_path,
        run_id=run_id,
        audit_dir=audit_dir,
        snapshot_only=True,
    )
    second_bytes = (audit_dir / run_id / "audit.json").read_bytes()

    assert first_bytes == second_bytes
    assert hashlib.sha256(first_bytes).hexdigest() == hashlib.sha256(second_bytes).hexdigest()

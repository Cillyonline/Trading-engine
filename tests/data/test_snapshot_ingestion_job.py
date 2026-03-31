from __future__ import annotations

import importlib.util
import json
import sqlite3
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
import sys

import pytest

from cilly_trading.engine.logging import (
    InMemoryEngineLogSink,
    configure_engine_log_emitter,
    reset_engine_logging_for_tests,
)
from cilly_trading.repositories.snapshot_ingestion_sqlite import (
    SqliteSnapshotIngestionRepository,
)


def _load_module(module_name: str, relative_path: str):
    root = Path(__file__).resolve().parents[2]
    module_path = root / relative_path
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load module: {relative_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


_provider_module = _load_module(
    "snapshot_ingestion_job_provider_contract",
    "src/cilly_trading/engine/data/market_data_provider.py",
)
_job_module = _load_module(
    "snapshot_ingestion_job_module",
    "src/cilly_trading/engine/data/snapshot_ingestion_job.py",
)

Candle = _provider_module.Candle
MarketDataProviderRegistry = _provider_module.MarketDataProviderRegistry
SnapshotIngestionJob = _job_module.SnapshotIngestionJob
SnapshotIngestionJobError = _job_module.SnapshotIngestionJobError
SnapshotIngestionJobRequest = _job_module.SnapshotIngestionJobRequest


class _StaticProvider:
    def __init__(self, candles: tuple[Candle, ...]) -> None:
        self._candles = candles

    def iter_candles(self, request):
        return iter(
            candle
            for candle in self._candles
            if candle.symbol == request.symbol and candle.timeframe == request.timeframe
        )


class _OverflowProvider:
    def iter_candles(self, request):
        candles = [
            Candle(
                timestamp=datetime(2025, 1, index + 1, tzinfo=timezone.utc),
                symbol=request.symbol,
                timeframe=request.timeframe,
                open=Decimal("100.0"),
                high=Decimal("101.0"),
                low=Decimal("99.0"),
                close=Decimal("100.5"),
                volume=Decimal("1000.0"),
            )
            for index in range(request.limit + 1)
        ]
        return iter(tuple(candles))


def _build_registry(*, name: str, provider) -> MarketDataProviderRegistry:
    registry = MarketDataProviderRegistry()
    registry.register(name=name, provider=provider, priority=10)
    return registry


def _count_rows(db_path: Path, table: str) -> int:
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(f"SELECT COUNT(*) FROM {table};")
    count = cur.fetchone()[0]
    conn.close()
    return count


def _fetch_run(db_path: Path) -> sqlite3.Row:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(
        """
        SELECT ingestion_run_id, source, symbols_json, timeframe, fingerprint_hash
        FROM ingestion_runs
        LIMIT 1;
        """
    )
    row = cur.fetchone()
    conn.close()
    if row is None:
        raise AssertionError("expected ingestion_runs row")
    return row


@pytest.fixture(autouse=True)
def _reset_structured_logging() -> None:
    reset_engine_logging_for_tests()
    configure_engine_log_emitter(None)


def test_snapshot_ingestion_job_persists_repository_compatible_rows(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "analysis.db"
    candles = (
        Candle(
            timestamp=datetime(2025, 1, 1, tzinfo=timezone.utc),
            symbol="AAPL",
            timeframe="D1",
            open=Decimal("100.0"),
            high=Decimal("101.0"),
            low=Decimal("99.5"),
            close=Decimal("100.5"),
            volume=Decimal("1000.0"),
        ),
        Candle(
            timestamp=datetime(2025, 1, 2, tzinfo=timezone.utc),
            symbol="AAPL",
            timeframe="D1",
            open=Decimal("101.0"),
            high=Decimal("102.0"),
            low=Decimal("100.0"),
            close=Decimal("101.5"),
            volume=Decimal("1100.0"),
        ),
    )
    job = SnapshotIngestionJob(
        repository=SqliteSnapshotIngestionRepository(db_path=db_path),
        provider_registry=_build_registry(name="test-provider", provider=_StaticProvider(candles)),
    )

    result = job.run(
        SnapshotIngestionJobRequest(
            symbols=("AAPL",),
            timeframe="D1",
            limit=2,
            provider_name="test-provider",
        )
    )

    assert result.ingestion_run_id
    assert result.provider_name == "test-provider"
    assert result.inserted_rows == 2
    assert len(result.datasets) == 1
    assert _count_rows(db_path, "ingestion_runs") == 1
    assert _count_rows(db_path, "ohlcv_snapshots") == 2

    run_row = _fetch_run(db_path)
    assert run_row["ingestion_run_id"] == result.ingestion_run_id
    assert run_row["source"] == "test-provider"
    assert json.loads(run_row["symbols_json"]) == ["AAPL"]
    assert run_row["timeframe"] == "D1"
    assert run_row["fingerprint_hash"] == result.fingerprint_hash


def test_snapshot_ingestion_job_fails_explicitly_for_invalid_provider_data(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "analysis.db"
    duplicate_timestamp_candles = (
        Candle(
            timestamp=datetime(2025, 1, 1, tzinfo=timezone.utc),
            symbol="AAPL",
            timeframe="D1",
            open=Decimal("100.0"),
            high=Decimal("101.0"),
            low=Decimal("99.5"),
            close=Decimal("100.5"),
            volume=Decimal("1000.0"),
        ),
        Candle(
            timestamp=datetime(2025, 1, 1, tzinfo=timezone.utc),
            symbol="AAPL",
            timeframe="D1",
            open=Decimal("101.0"),
            high=Decimal("102.0"),
            low=Decimal("100.0"),
            close=Decimal("101.5"),
            volume=Decimal("1100.0"),
        ),
    )
    job = SnapshotIngestionJob(
        repository=SqliteSnapshotIngestionRepository(db_path=db_path),
        provider_registry=_build_registry(
            name="invalid-provider",
            provider=_StaticProvider(duplicate_timestamp_candles),
        ),
    )

    with pytest.raises(
        SnapshotIngestionJobError,
        match="snapshot_provider_invalid_data",
    ):
        job.run(
            SnapshotIngestionJobRequest(
                symbols=("AAPL",),
                timeframe="D1",
                limit=2,
                provider_name="invalid-provider",
            )
        )

    assert _count_rows(db_path, "ingestion_runs") == 0
    assert _count_rows(db_path, "ohlcv_snapshots") == 0


def test_snapshot_ingestion_job_logs_reviewable_server_events(tmp_path: Path) -> None:
    db_path = tmp_path / "analysis.db"
    sink = InMemoryEngineLogSink()
    configure_engine_log_emitter(sink.write)
    candles = (
        Candle(
            timestamp=datetime(2025, 1, 1, tzinfo=timezone.utc),
            symbol="MSFT",
            timeframe="D1",
            open=Decimal("200.0"),
            high=Decimal("201.0"),
            low=Decimal("199.0"),
            close=Decimal("200.5"),
            volume=Decimal("1200.0"),
        ),
    )
    job = SnapshotIngestionJob(
        repository=SqliteSnapshotIngestionRepository(db_path=db_path),
        provider_registry=_build_registry(name="test-provider", provider=_StaticProvider(candles)),
    )

    result = job.run(
        SnapshotIngestionJobRequest(
            symbols=("MSFT",),
            timeframe="D1",
            limit=1,
            provider_name="test-provider",
        )
    )

    events = [json.loads(line) for line in sink.lines]
    assert [event["event"] for event in events] == [
        "snapshot_ingestion.started",
        "snapshot_ingestion.completed",
    ]
    assert events[0]["payload"]["provider_name"] == "test-provider"
    assert events[1]["payload"]["ingestion_run_id"] == result.ingestion_run_id
    assert events[1]["payload"]["inserted_rows"] == 1


def test_snapshot_ingestion_job_rejects_provider_overflow_bounded(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "analysis.db"
    job = SnapshotIngestionJob(
        repository=SqliteSnapshotIngestionRepository(db_path=db_path),
        provider_registry=_build_registry(name="overflow-provider", provider=_OverflowProvider()),
    )

    with pytest.raises(
        SnapshotIngestionJobError,
        match="snapshot_provider_limit_exceeded",
    ):
        job.run(
            SnapshotIngestionJobRequest(
                symbols=("AAPL",),
                timeframe="D1",
                limit=2,
                provider_name="overflow-provider",
            )
        )

    assert _count_rows(db_path, "ingestion_runs") == 0
    assert _count_rows(db_path, "ohlcv_snapshots") == 0

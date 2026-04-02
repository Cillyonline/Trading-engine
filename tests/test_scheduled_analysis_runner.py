from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from api.services import analysis_service
from api.services.scheduled_analysis_runner import ScheduledAnalysisRunner, parse_scheduled_tasks
from cilly_trading.repositories.analysis_runs_sqlite import SqliteAnalysisRunRepository
from cilly_trading.repositories.signals_sqlite import SqliteSignalRepository
from cilly_trading.repositories.watchlists_sqlite import SqliteWatchlistRepository


class _RuntimeStateStub:
    def __init__(self, state: str) -> None:
        self.state = state


class _NamedStrategy:
    def __init__(self, name: str) -> None:
        self.name = name


def _insert_ingestion_run(
    db_path: Path,
    ingestion_run_id: str,
    *,
    symbols: list[str],
    created_at: str,
    timeframe: str = "D1",
) -> None:
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
            created_at,
            "test",
            json.dumps(symbols),
            timeframe,
            None,
        ),
    )
    conn.commit()
    conn.close()


def _insert_snapshot_rows(
    db_path: Path,
    ingestion_run_id: str,
    symbol: str,
    timeframe: str,
    rows: list[tuple[Any, float, float, float, float, float]],
) -> None:
    conn = sqlite3.connect(db_path)
    conn.executemany(
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
                ingestion_run_id,
                symbol,
                timeframe,
                ts,
                open_,
                high,
                low,
                close,
                volume,
            )
            for ts, open_, high, low, close, volume in rows
        ],
    )
    conn.commit()
    conn.close()


def _build_dependencies(
    *,
    tmp_path: Path,
    analysis_repo: SqliteAnalysisRunRepository,
    signal_repo: SqliteSignalRepository,
    watchlist_repo: SqliteWatchlistRepository,
    run_snapshot_analysis,
):
    return analysis_service.AnalysisServiceDependencies(
        analysis_run_repo=analysis_repo,
        signal_repo=signal_repo,
        watchlist_repo=watchlist_repo,
        default_strategy_configs={"RSI2": {}, "TURTLE": {}},
        require_ingestion_run=lambda ingestion_run_id: analysis_service.require_ingestion_run(
            ingestion_run_id=ingestion_run_id,
            analysis_run_repo=analysis_repo,
        ),
        require_snapshot_ready=lambda ingestion_run_id, *, symbols, timeframe="D1": analysis_service.require_snapshot_ready(
            ingestion_run_id=ingestion_run_id,
            analysis_run_repo=analysis_repo,
            symbols=symbols,
            timeframe=timeframe,
        ),
        run_snapshot_analysis=run_snapshot_analysis,
        resolve_analysis_db_path=lambda: str(tmp_path / "analysis.db"),
        create_strategy=lambda name: _NamedStrategy(name),
        create_registered_strategies=lambda: [_NamedStrategy("RSI2"), _NamedStrategy("TURTLE")],
        trigger_operator_analysis_run=lambda **kwargs: kwargs["execute"](**kwargs["execute_kwargs"]),
    )


def test_parse_scheduled_tasks_derives_stable_ids_and_validates_shape() -> None:
    tasks = parse_scheduled_tasks(
        json.dumps(
            [
                {
                    "kind": "analysis",
                    "symbol": "AAPL",
                    "strategy": "RSI2",
                    "market_type": "stock",
                    "lookback_days": 200,
                },
                {
                    "kind": "watchlist",
                    "watchlist_id": "tech",
                    "market_type": "stock",
                    "lookback_days": 200,
                    "min_score": 30.0,
                },
            ]
        )
    )

    assert len(tasks) == 2
    assert tasks[0].stable_task_id
    assert tasks[1].stable_task_id
    assert tasks[0].stable_task_id != tasks[1].stable_task_id


def test_scheduled_runner_selects_newest_valid_snapshot_for_analysis_and_persists_result(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("CILLY_ANALYSIS_EVIDENCE_DIR", str(tmp_path / "evidence"))
    analysis_repo = SqliteAnalysisRunRepository(db_path=tmp_path / "analysis.db")
    signal_repo = SqliteSignalRepository(db_path=tmp_path / "signals.db")
    watchlist_repo = SqliteWatchlistRepository(db_path=tmp_path / "watchlists.db")

    older_run_id = str(uuid.uuid4())
    newer_invalid_run_id = str(uuid.uuid4())
    _insert_ingestion_run(
        tmp_path / "analysis.db",
        older_run_id,
        symbols=["AAPL"],
        created_at="2026-03-30T10:00:00+00:00",
    )
    _insert_ingestion_run(
        tmp_path / "analysis.db",
        newer_invalid_run_id,
        symbols=["AAPL"],
        created_at="2026-03-31T10:00:00+00:00",
    )
    _insert_snapshot_rows(
        tmp_path / "analysis.db",
        older_run_id,
        "AAPL",
        "D1",
        [
            (1735689600000, 101.0, 102.0, 100.0, 101.0, 1000.0),
            (1735776000000, 100.0, 101.0, 90.0, 91.0, 1000.0),
        ],
    )
    _insert_snapshot_rows(
        tmp_path / "analysis.db",
        newer_invalid_run_id,
        "AAPL",
        "D1",
        [("bad-ts", 101.0, 102.0, 100.0, 101.0, 1000.0)],
    )

    run_calls: list[str] = []

    def _run_snapshot_analysis(**kwargs):
        run_calls.append(kwargs["ingestion_run_id"])
        return [
            {
                "symbol": "AAPL",
                "strategy": "RSI2",
                "stage": "setup",
                "score": 42.0,
                "timestamp": "2026-03-30T00:00:00+00:00",
                "timeframe": "D1",
                "market_type": "stock",
                "data_source": "yahoo",
                "direction": "long",
            }
        ]

    deps = _build_dependencies(
        tmp_path=tmp_path,
        analysis_repo=analysis_repo,
        signal_repo=signal_repo,
        watchlist_repo=watchlist_repo,
        run_snapshot_analysis=_run_snapshot_analysis,
    )

    runner = ScheduledAnalysisRunner(
        enabled=True,
        poll_interval_seconds=60,
        snapshot_scan_limit=10,
        raw_tasks_json=json.dumps(
            [
                {
                    "kind": "analysis",
                    "symbol": "AAPL",
                    "strategy": "RSI2",
                    "market_type": "stock",
                    "lookback_days": 200,
                }
            ]
        ),
        build_analysis_service_dependencies=lambda: deps,
        get_runtime_controller=lambda: _RuntimeStateStub("running"),
        resolve_analysis_db_path=lambda: str(tmp_path / "analysis.db"),
    )

    outcomes_first = runner.run_once()
    outcomes_second = runner.run_once()

    assert run_calls == [older_run_id]
    assert outcomes_first[0]["status"] == "completed"
    assert outcomes_first[0]["ingestion_run_id"] == older_run_id
    assert outcomes_second[0]["status"] == "already_completed_for_snapshot"

    persisted = analysis_repo.get_run(outcomes_first[0]["analysis_run_id"])
    assert persisted is not None
    assert persisted["ingestion_run_id"] == older_run_id
    assert persisted["result"]["symbol"] == "AAPL"
    assert persisted["evidence"]["review_week"] == "2026-W14"
    assert Path(persisted["evidence"]["evidence_file"]).exists()
    assert Path(persisted["evidence"]["operator_review_file"]).exists()


def test_scheduled_runner_executes_watchlist_against_newest_partially_valid_snapshot_and_persists_failures(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("CILLY_ANALYSIS_EVIDENCE_DIR", str(tmp_path / "evidence"))
    analysis_repo = SqliteAnalysisRunRepository(db_path=tmp_path / "analysis.db")
    signal_repo = SqliteSignalRepository(db_path=tmp_path / "signals.db")
    watchlist_repo = SqliteWatchlistRepository(db_path=tmp_path / "watchlists.db")
    watchlist_repo.create_watchlist(
        watchlist_id="core-tech",
        name="Core Tech",
        symbols=["MSFT", "AAPL"],
    )

    older_run_id = str(uuid.uuid4())
    newer_run_id = str(uuid.uuid4())
    _insert_ingestion_run(
        tmp_path / "analysis.db",
        older_run_id,
        symbols=["AAPL", "MSFT"],
        created_at="2026-03-30T10:00:00+00:00",
    )
    _insert_ingestion_run(
        tmp_path / "analysis.db",
        newer_run_id,
        symbols=["AAPL", "MSFT"],
        created_at="2026-03-31T10:00:00+00:00",
    )
    _insert_snapshot_rows(
        tmp_path / "analysis.db",
        older_run_id,
        "AAPL",
        "D1",
        [(1735689600000, 101.0, 102.0, 100.0, 101.0, 1000.0)],
    )
    _insert_snapshot_rows(
        tmp_path / "analysis.db",
        older_run_id,
        "MSFT",
        "D1",
        [(1735689600000, 201.0, 202.0, 200.0, 201.0, 1000.0)],
    )
    _insert_snapshot_rows(
        tmp_path / "analysis.db",
        newer_run_id,
        "AAPL",
        "D1",
        [(1735776000000, 111.0, 112.0, 110.0, 111.0, 1200.0)],
    )

    def _run_snapshot_analysis(**kwargs):
        kwargs["symbol_failures"].append(
            {
                "symbol": "MSFT",
                "code": "snapshot_data_invalid",
                "detail": "snapshot data unavailable or invalid for symbol",
            }
        )
        return [
            {
                "symbol": "AAPL",
                "strategy": "RSI2",
                "stage": "setup",
                "score": 88.0,
                "signal_strength": 0.9,
                "timestamp": "2026-03-31T00:00:00+00:00",
                "timeframe": "D1",
                "market_type": "stock",
                "data_source": "yahoo",
                "direction": "long",
            }
        ]

    deps = _build_dependencies(
        tmp_path=tmp_path,
        analysis_repo=analysis_repo,
        signal_repo=signal_repo,
        watchlist_repo=watchlist_repo,
        run_snapshot_analysis=_run_snapshot_analysis,
    )

    runner = ScheduledAnalysisRunner(
        enabled=True,
        poll_interval_seconds=60,
        snapshot_scan_limit=10,
        raw_tasks_json=json.dumps(
            [
                {
                    "kind": "watchlist",
                    "watchlist_id": "core-tech",
                    "market_type": "stock",
                    "lookback_days": 200,
                    "min_score": 30.0,
                }
            ]
        ),
        build_analysis_service_dependencies=lambda: deps,
        get_runtime_controller=lambda: _RuntimeStateStub("running"),
        resolve_analysis_db_path=lambda: str(tmp_path / "analysis.db"),
    )

    outcomes = runner.run_once()

    assert outcomes[0]["status"] == "completed"
    assert outcomes[0]["ingestion_run_id"] == newer_run_id

    persisted = analysis_repo.get_run(outcomes[0]["analysis_run_id"])
    assert persisted is not None
    assert persisted["result"]["ingestion_run_id"] == newer_run_id
    assert persisted["result"]["watchlist_id"] == "core-tech"
    assert persisted["result"]["failures"] == [
        {
            "symbol": "MSFT",
            "code": "snapshot_data_invalid",
            "detail": "snapshot data unavailable or invalid for symbol",
        }
    ]
    evidence_payload = json.loads(
        Path(persisted["evidence"]["evidence_file"]).read_text(encoding="utf-8")
    )
    assert evidence_payload["workflow"]["kind"] == "watchlist_execution"
    assert evidence_payload["workflow"]["outcome_classification"] == "isolated_symbol_failure"


def test_scheduled_runner_skips_when_another_execution_is_active(tmp_path: Path) -> None:
    analysis_repo = SqliteAnalysisRunRepository(db_path=tmp_path / "analysis.db")
    signal_repo = SqliteSignalRepository(db_path=tmp_path / "signals.db")
    watchlist_repo = SqliteWatchlistRepository(db_path=tmp_path / "watchlists.db")
    deps = _build_dependencies(
        tmp_path=tmp_path,
        analysis_repo=analysis_repo,
        signal_repo=signal_repo,
        watchlist_repo=watchlist_repo,
        run_snapshot_analysis=lambda **_kwargs: [],
    )

    runner = ScheduledAnalysisRunner(
        enabled=True,
        poll_interval_seconds=60,
        snapshot_scan_limit=10,
        raw_tasks_json=json.dumps(
            [
                {
                    "kind": "analysis",
                    "symbol": "AAPL",
                    "strategy": "RSI2",
                }
            ]
        ),
        build_analysis_service_dependencies=lambda: deps,
        get_runtime_controller=lambda: _RuntimeStateStub("running"),
        resolve_analysis_db_path=lambda: str(tmp_path / "analysis.db"),
    )

    runner._run_lock.acquire()
    try:
        assert runner.run_once() == []
    finally:
        runner._run_lock.release()

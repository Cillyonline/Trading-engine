from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi.testclient import TestClient

import api.main as api_main
from cilly_trading.engine.runtime_controller import _reset_runtime_controller_for_tests
from cilly_trading.repositories.analysis_runs_sqlite import SqliteAnalysisRunRepository
from cilly_trading.repositories.signals_sqlite import SqliteSignalRepository

OWNER_HEADERS = {api_main.ROLE_HEADER_NAME: "owner"}
OPERATOR_HEADERS = {api_main.ROLE_HEADER_NAME: "operator"}
READ_ONLY_HEADERS = {api_main.ROLE_HEADER_NAME: "read_only"}


class _RuntimeStateStub:
    def __init__(self, state: str) -> None:
        self.state = state


def setup_function() -> None:
    _reset_runtime_controller_for_tests()


def teardown_function() -> None:
    _reset_runtime_controller_for_tests()


def _insert_ingestion_run(
    db_path: Path,
    ingestion_run_id: str,
    *,
    symbols: list[str],
    timeframe: str = "D1",
    source: str = "test",
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
            datetime.now(timezone.utc).isoformat(),
            source,
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
    rows: list[tuple[int, float, float, float, float, float]],
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


def _setup_analysis_dependencies(tmp_path: Path, monkeypatch) -> str:
    signal_repo = SqliteSignalRepository(db_path=tmp_path / "signals.db")
    analysis_repo = SqliteAnalysisRunRepository(db_path=tmp_path / "analysis.db")

    monkeypatch.setattr(api_main, "signal_repo", signal_repo)
    monkeypatch.setattr(api_main, "analysis_run_repo", analysis_repo)

    ingestion_run_id = str(uuid.uuid4())
    _insert_ingestion_run(
        tmp_path / "analysis.db",
        ingestion_run_id,
        symbols=["AAPL", "MSFT"],
        timeframe="D1",
    )

    rows = [
        (1735689600000, 101.0, 102.0, 100.0, 101.0, 1000.0),
        (1735776000000, 100.0, 101.0, 90.0, 91.0, 1000.0),
        (1735862400000, 90.0, 91.0, 80.0, 81.0, 1000.0),
    ]
    _insert_snapshot_rows(tmp_path / "analysis.db", ingestion_run_id, "AAPL", "D1", rows)
    _insert_snapshot_rows(tmp_path / "analysis.db", ingestion_run_id, "MSFT", "D1", rows)

    return ingestion_run_id


def test_runtime_is_started_on_api_startup(monkeypatch) -> None:
    calls: list[str] = []

    def _start() -> str:
        calls.append("start")
        return "running"

    monkeypatch.setattr(api_main, "start_engine_runtime", _start)

    with TestClient(api_main.app):
        assert calls == ["start"]


def test_runtime_is_shutdown_on_api_shutdown(monkeypatch) -> None:
    calls: list[str] = []

    def _start() -> str:
        return "running"

    def _shutdown() -> str:
        calls.append("shutdown")
        return "stopped"

    monkeypatch.setattr(api_main, "start_engine_runtime", _start)
    monkeypatch.setattr(api_main, "shutdown_engine_runtime", _shutdown)

    with TestClient(api_main.app):
        pass

    assert calls == ["shutdown"]


def test_engine_requests_are_blocked_when_runtime_not_running(tmp_path: Path, monkeypatch) -> None:
    ingestion_run_id = _setup_analysis_dependencies(tmp_path, monkeypatch)

    def _start() -> str:
        return "ready"

    def _runtime() -> _RuntimeStateStub:
        return _RuntimeStateStub("ready")

    def _fail_run_watchlist_analysis(*args, **kwargs):
        raise AssertionError("run_watchlist_analysis should not be called")

    monkeypatch.setattr(api_main, "start_engine_runtime", _start)
    monkeypatch.setattr(api_main, "get_runtime_controller", _runtime)
    monkeypatch.setattr(api_main, "run_watchlist_analysis", _fail_run_watchlist_analysis)

    with TestClient(api_main.app) as client:
        for path, payload in [
            (
                "/strategy/analyze",
                {
                    "ingestion_run_id": ingestion_run_id,
                    "symbol": "AAPL",
                    "strategy": "RSI2",
                    "market_type": "stock",
                    "lookback_days": 200,
                },
            ),
            (
                "/analysis/run",
                {
                    "ingestion_run_id": ingestion_run_id,
                    "symbol": "AAPL",
                    "strategy": "RSI2",
                    "market_type": "stock",
                    "lookback_days": 200,
                },
            ),
            (
                "/screener/basic",
                {
                    "ingestion_run_id": ingestion_run_id,
                    "symbols": ["AAPL", "MSFT"],
                    "market_type": "stock",
                    "lookback_days": 200,
                    "min_score": 30.0,
                },
            ),
        ]:
            headers = OPERATOR_HEADERS
            response = client.post(path, headers=headers, json=payload)
            assert response.status_code == 503
            assert response.json() == {
                "detail": {
                    "code": "engine_runtime_not_running",
                    "state": "ready",
                }
            }


def test_engine_requests_work_normally_when_runtime_running(monkeypatch) -> None:
    def _start() -> str:
        return "running"

    def _runtime() -> _RuntimeStateStub:
        return _RuntimeStateStub("running")

    monkeypatch.setattr(api_main, "start_engine_runtime", _start)
    monkeypatch.setattr(api_main, "get_runtime_controller", _runtime)

    with TestClient(api_main.app) as client:
        response = client.post(
            "/strategy/analyze",
            headers=OPERATOR_HEADERS,
            json={
                "ingestion_run_id": "not-a-uuid",
                "symbol": "AAPL",
                "strategy": "RSI2",
                "market_type": "stock",
                "lookback_days": 200,
            },
        )

    assert response.status_code == 422
    assert response.json() == {"detail": "invalid_ingestion_run_id"}


def test_engine_requests_are_blocked_when_runtime_paused(tmp_path: Path, monkeypatch) -> None:
    ingestion_run_id = _setup_analysis_dependencies(tmp_path, monkeypatch)

    def _start() -> str:
        return "paused"

    def _runtime() -> _RuntimeStateStub:
        return _RuntimeStateStub("paused")

    def _fail_run_watchlist_analysis(*args, **kwargs):
        raise AssertionError("run_watchlist_analysis should not be called")

    monkeypatch.setattr(api_main, "start_engine_runtime", _start)
    monkeypatch.setattr(api_main, "get_runtime_controller", _runtime)
    monkeypatch.setattr(api_main, "run_watchlist_analysis", _fail_run_watchlist_analysis)

    with TestClient(api_main.app) as client:
        response = client.post(
            "/strategy/analyze",
            headers=OPERATOR_HEADERS,
            json={
                "ingestion_run_id": ingestion_run_id,
                "symbol": "AAPL",
                "strategy": "RSI2",
                "market_type": "stock",
                "lookback_days": 200,
            },
        )

    assert response.status_code == 503
    assert response.json() == {
        "detail": {
            "code": "engine_runtime_not_running",
            "state": "paused",
        }
    }


def test_pause_during_in_progress_analysis_does_not_interrupt_execution(monkeypatch) -> None:
    class _Strategy:
        name = "RSI2"

    class _InMemoryAnalysisRunRepo:
        def __init__(self) -> None:
            self._runs: dict[str, dict[str, object]] = {}

        def get_run(self, analysis_run_id: str) -> dict[str, object] | None:
            return self._runs.get(analysis_run_id)

        def save_run(
            self,
            *,
            analysis_run_id: str,
            ingestion_run_id: str,
            request_payload: dict[str, object],
            result_payload: dict[str, object],
        ) -> None:
            self._runs[analysis_run_id] = {
                "analysis_run_id": analysis_run_id,
                "ingestion_run_id": ingestion_run_id,
                "request": request_payload,
                "result": result_payload,
            }

    calls = {"run": 0}

    _reset_runtime_controller_for_tests()
    monkeypatch.setattr(api_main, "_require_ingestion_run", lambda *_: None)
    monkeypatch.setattr(api_main, "_require_snapshot_ready", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(api_main, "create_strategy", lambda *_: _Strategy())
    monkeypatch.setattr(api_main, "analysis_run_repo", _InMemoryAnalysisRunRepo())
    monkeypatch.setattr(api_main, "_resolve_analysis_db_path", lambda: "analysis.db")

    def _run_snapshot_analysis(**kwargs):
        calls["run"] += 1
        pause_response = client.post("/execution/pause", headers=OWNER_HEADERS)
        assert pause_response.status_code == 200
        assert pause_response.json() == {"state": "paused"}
        return [
            {
                "symbol": kwargs["symbols"][0],
                "strategy": "RSI2",
                "stage": "setup",
            }
        ]

    monkeypatch.setattr(api_main, "_run_snapshot_analysis", _run_snapshot_analysis)

    with TestClient(api_main.app) as client:
        response = client.post(
            "/analysis/run",
            headers=OPERATOR_HEADERS,
            json={
                "ingestion_run_id": str(uuid.uuid4()),
                "symbol": "AAPL",
                "strategy": "RSI2",
                "market_type": "stock",
                "lookback_days": 200,
            },
        )
        introspection = client.get("/runtime/introspection", headers=READ_ONLY_HEADERS)

    assert calls["run"] == 1
    assert response.status_code == 200
    assert response.json()["signals"][0]["symbol"] == "AAPL"
    assert introspection.status_code == 200
    assert introspection.json()["mode"] == "paused"


def test_execution_start_endpoint_transitions_ready_runtime_to_running() -> None:
    _reset_runtime_controller_for_tests()

    with TestClient(api_main.app) as client:
        _reset_runtime_controller_for_tests()
        runtime = api_main.get_runtime_controller()
        runtime.init()

        response = client.post("/execution/start", headers=OWNER_HEADERS)
        introspection = client.get("/runtime/introspection", headers=READ_ONLY_HEADERS)

    assert response.status_code == 200
    assert response.json() == {"state": "running"}
    assert introspection.status_code == 200
    assert introspection.json()["mode"] == "running"


def test_execution_start_endpoint_returns_conflict_for_paused_runtime() -> None:
    with TestClient(api_main.app) as client:
        client.post("/execution/pause", headers=OWNER_HEADERS)
        response = client.post("/execution/start", headers=OWNER_HEADERS)
        introspection = client.get("/runtime/introspection", headers=READ_ONLY_HEADERS)

    assert response.status_code == 409
    assert response.json() == {
        "detail": "Cannot ensure running runtime from state 'paused'."
    }
    assert introspection.status_code == 200
    assert introspection.json()["mode"] == "paused"


def test_execution_stop_endpoint_stops_running_runtime() -> None:
    with TestClient(api_main.app) as client:
        response = client.post("/execution/stop", headers=OWNER_HEADERS)
        introspection = client.get("/runtime/introspection", headers=READ_ONLY_HEADERS)

    assert response.status_code == 200
    assert response.json() == {"state": "stopped"}
    assert introspection.status_code == 200
    assert introspection.json()["mode"] == "stopped"


def test_execution_stop_endpoint_returns_ready_when_runtime_not_started(monkeypatch) -> None:
    def _start() -> str:
        return "ready"

    monkeypatch.setattr(api_main, "start_engine_runtime", _start)

    with TestClient(api_main.app) as client:
        _reset_runtime_controller_for_tests()
        runtime = api_main.get_runtime_controller()
        runtime.init()

        response = client.post("/execution/stop", headers=OWNER_HEADERS)
        introspection = client.get("/runtime/introspection", headers=READ_ONLY_HEADERS)

    assert response.status_code == 200
    assert response.json() == {"state": "ready"}
    assert introspection.status_code == 200
    assert introspection.json()["mode"] == "ready"

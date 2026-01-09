from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

import api.main as api_main
from cilly_trading.repositories.analysis_runs_sqlite import SqliteAnalysisRunRepository
from cilly_trading.repositories.signals_sqlite import SqliteSignalRepository


def _make_signal_repo(tmp_path: Path) -> SqliteSignalRepository:
    return SqliteSignalRepository(db_path=tmp_path / "signals.db")


def _make_analysis_repo(tmp_path: Path) -> SqliteAnalysisRunRepository:
    return SqliteAnalysisRunRepository(db_path=tmp_path / "analysis.db")


def test_manual_analysis_idempotent(tmp_path: Path, monkeypatch) -> None:
    signal_repo = _make_signal_repo(tmp_path)
    analysis_repo = _make_analysis_repo(tmp_path)

    monkeypatch.setattr(api_main, "signal_repo", signal_repo)
    monkeypatch.setattr(api_main, "analysis_run_repo", analysis_repo)

    def _fail_run_watchlist_analysis(*args, **kwargs):
        raise AssertionError("run_watchlist_analysis should not be called")

    monkeypatch.setattr(api_main, "run_watchlist_analysis", _fail_run_watchlist_analysis)

    response_payload = {
        "analysis_run_id": "run-1",
        "ingestion_run_id": "snapshot-1",
        "symbol": "AAPL",
        "strategy": "RSI2",
        "signals": [
            {
                "symbol": "AAPL",
                "strategy": "RSI2",
                "direction": "long",
                "score": 42.0,
                "timestamp": "2025-01-03T00:00:00+00:00",
                "stage": "setup",
                "timeframe": "D1",
                "market_type": "stock",
                "data_source": "yahoo",
            }
        ],
    }
    analysis_repo.save_run(
        analysis_run_id="run-1",
        ingestion_run_id="snapshot-1",
        request_payload={"analysis_run_id": "run-1", "ingestion_run_id": "snapshot-1"},
        result_payload=response_payload,
    )

    client = TestClient(api_main.app)
    payload = {
        "analysis_run_id": "run-1",
        "ingestion_run_id": "snapshot-1",
        "symbol": "AAPL",
        "strategy": "RSI2",
        "market_type": "stock",
        "lookback_days": 200,
    }

    response_first = client.post("/analysis/run", json=payload)
    assert response_first.status_code == 200
    first_body = response_first.json()
    assert first_body["analysis_run_id"] == "run-1"
    assert first_body == response_payload

    response_second = client.post("/analysis/run", json=payload)
    assert response_second.status_code == 200
    second_body = response_second.json()
    assert second_body == first_body


def test_manual_analysis_rejects_new_run(tmp_path: Path, monkeypatch) -> None:
    signal_repo = _make_signal_repo(tmp_path)
    analysis_repo = _make_analysis_repo(tmp_path)

    monkeypatch.setattr(api_main, "signal_repo", signal_repo)
    monkeypatch.setattr(api_main, "analysis_run_repo", analysis_repo)

    def _fail_run_watchlist_analysis(*args, **kwargs):
        raise AssertionError("run_watchlist_analysis should not be called")

    monkeypatch.setattr(api_main, "run_watchlist_analysis", _fail_run_watchlist_analysis)

    client = TestClient(api_main.app)
    response = client.post(
        "/analysis/run",
        json={
            "analysis_run_id": "run-missing",
            "ingestion_run_id": "missing-snapshot",
            "symbol": "AAPL",
            "strategy": "RSI2",
            "market_type": "stock",
            "lookback_days": 200,
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "snapshot_not_supported"
    assert analysis_repo.get_run("run-missing") is None

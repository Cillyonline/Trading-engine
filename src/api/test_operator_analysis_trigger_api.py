from __future__ import annotations

import logging
from typing import Any

from fastapi.testclient import TestClient

import api.main as api_main

OPERATOR_HEADERS = {api_main.ROLE_HEADER_NAME: "operator"}
READ_ONLY_HEADERS = {api_main.ROLE_HEADER_NAME: "read_only"}


class _InMemoryAnalysisRunRepo:
    def __init__(self) -> None:
        self._runs: dict[str, dict[str, Any]] = {}

    def get_run(self, analysis_run_id: str) -> dict[str, Any] | None:
        return self._runs.get(analysis_run_id)

    def save_run(
        self,
        *,
        analysis_run_id: str,
        ingestion_run_id: str,
        request_payload: dict[str, Any],
        result_payload: dict[str, Any],
    ) -> None:
        self._runs[analysis_run_id] = {
            "analysis_run_id": analysis_run_id,
            "ingestion_run_id": ingestion_run_id,
            "request": request_payload,
            "result": result_payload,
        }


def test_operator_can_trigger_analysis_run_and_execution_is_logged(monkeypatch, caplog) -> None:
    call_count = {"value": 0}

    class _Strategy:
        name = "RSI2"

    def _start() -> str:
        return "running"

    def _run_snapshot_analysis(**kwargs):
        call_count["value"] += 1
        return [
            {
                "symbol": kwargs["symbols"][0],
                "strategy": "RSI2",
                "stage": "setup",
            }
        ]

    monkeypatch.setattr(api_main, "start_engine_runtime", _start)
    monkeypatch.setattr(api_main, "_require_ingestion_run", lambda *_: None)
    monkeypatch.setattr(api_main, "_require_snapshot_ready", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(api_main, "create_strategy", lambda *_: _Strategy())
    monkeypatch.setattr(api_main, "_run_snapshot_analysis", _run_snapshot_analysis)
    monkeypatch.setattr(api_main, "analysis_run_repo", _InMemoryAnalysisRunRepo())

    caplog.set_level(logging.INFO)

    with TestClient(api_main.app) as client:
        response = client.post(
            "/analysis/run",
            headers=OPERATOR_HEADERS,
            json={
                "ingestion_run_id": "dbfb3ea6-cef8-49f3-acdb-df0de7115d6f",
                "symbol": "AAPL",
                "strategy": "RSI2",
                "market_type": "stock",
                "lookback_days": 200,
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["symbol"] == "AAPL"
    assert payload["strategy"] == "RSI2"
    assert payload["signals"]
    assert call_count["value"] == 1
    assert "Operator analysis run requested" in caplog.text
    assert "Operator analysis run completed" in caplog.text


def test_analysis_run_endpoint_validates_request(monkeypatch) -> None:
    def _start() -> str:
        return "running"

    monkeypatch.setattr(api_main, "start_engine_runtime", _start)

    with TestClient(api_main.app) as client:
        response = client.post(
            "/analysis/run",
            headers=OPERATOR_HEADERS,
            json={
                "ingestion_run_id": "dbfb3ea6-cef8-49f3-acdb-df0de7115d6f",
                "strategy": "RSI2",
                "market_type": "stock",
                "lookback_days": 200,
            },
        )

    assert response.status_code == 422


def test_analysis_run_endpoint_requires_authenticated_role(monkeypatch) -> None:
    monkeypatch.setattr(api_main, "start_engine_runtime", lambda: "running")

    with TestClient(api_main.app) as client:
        response = client.post(
            "/analysis/run",
            json={
                "ingestion_run_id": "dbfb3ea6-cef8-49f3-acdb-df0de7115d6f",
                "symbol": "AAPL",
                "strategy": "RSI2",
                "market_type": "stock",
                "lookback_days": 200,
            },
        )

    assert response.status_code == 401
    assert response.json() == {"detail": "unauthorized"}


def test_analysis_run_endpoint_forbids_read_only_role_without_execution(monkeypatch) -> None:
    call_count = {"value": 0}

    def _start() -> str:
        return "running"

    def _run_snapshot_analysis(**_kwargs):
        call_count["value"] += 1
        return []

    monkeypatch.setattr(api_main, "start_engine_runtime", _start)
    monkeypatch.setattr(api_main, "_run_snapshot_analysis", _run_snapshot_analysis)

    with TestClient(api_main.app) as client:
        response = client.post(
            "/analysis/run",
            headers=READ_ONLY_HEADERS,
            json={
                "ingestion_run_id": "dbfb3ea6-cef8-49f3-acdb-df0de7115d6f",
                "symbol": "AAPL",
                "strategy": "RSI2",
                "market_type": "stock",
                "lookback_days": 200,
            },
        )

    assert response.status_code == 403
    assert response.json() == {"detail": "forbidden"}
    assert call_count["value"] == 0

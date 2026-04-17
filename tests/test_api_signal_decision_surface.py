from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

import api.main as api_main
from cilly_trading.repositories.signals_sqlite import SqliteSignalRepository

READ_ONLY_HEADERS = {api_main.ROLE_HEADER_NAME: "read_only"}


def _make_repo(tmp_path: Path) -> SqliteSignalRepository:
    db_path = tmp_path / "signal_decision_surface.db"
    return SqliteSignalRepository(db_path=db_path)


def _base_signal(**overrides):
    base = {
        "ingestion_run_id": "test-run-001",
        "symbol": "AAPL",
        "strategy": "RSI2",
        "direction": "long",
        "score": 55.0,
        "timestamp": "2026-01-01T00:00:00+00:00",
        "stage": "setup",
        "timeframe": "D1",
        "market_type": "stock",
        "data_source": "yahoo",
    }
    base.update(overrides)
    return base


def test_signal_decision_surface_returns_bounded_technical_states(tmp_path: Path, monkeypatch) -> None:
    repo = _make_repo(tmp_path)
    repo.save_signals(
        [
            _base_signal(symbol="BLOCK", score=20.0, stage="setup", timestamp="2026-01-03T00:00:00+00:00"),
            _base_signal(symbol="WATCH", score=60.0, stage="setup", timestamp="2026-01-02T00:00:00+00:00"),
            _base_signal(
                symbol="CANDIDATE",
                score=88.0,
                stage="entry_confirmed",
                timestamp="2026-01-01T00:00:00+00:00",
            ),
        ]
    )
    monkeypatch.setattr(api_main, "signal_repo", repo)
    client = TestClient(api_main.app)

    response = client.get("/signals/decision-surface", headers=READ_ONLY_HEADERS)
    assert response.status_code == 200
    payload = response.json()

    assert payload["workflow_id"] == "ui_signal_decision_surface_v1"
    assert payload["boundary"]["mode"] == "non_live_signal_decision_surface"
    assert payload["boundary"]["strategy_readiness_evidence"]["inferred_readiness_claim"] == "prohibited"
    assert payload["total"] == 3
    assert [item["decision_state"] for item in payload["items"]] == [
        "blocked",
        "watch",
        "paper_candidate",
    ]
    assert payload["items"][0]["blocking_conditions"]
    assert payload["items"][1]["missing_criteria"]
    assert payload["items"][2]["missing_criteria"] == []
    assert "score" in payload["items"][2]["score_contribution"].lower()
    assert "stage" in payload["items"][1]["stage_assessment"].lower()


def test_signal_decision_surface_openapi_contract_is_explicit(monkeypatch, tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    monkeypatch.setattr(api_main, "signal_repo", repo)
    client = TestClient(api_main.app)

    response = client.get("/openapi.json")
    assert response.status_code == 200
    openapi = response.json()

    assert "/signals/decision-surface" in openapi["paths"]
    get_spec = openapi["paths"]["/signals/decision-surface"]["get"]
    assert "bounded non-live technical decision states" in get_spec["description"]
    assert "does not imply trader validation or operational readiness" in get_spec["description"]


def test_signal_decision_surface_requires_read_only_role(monkeypatch, tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    monkeypatch.setattr(api_main, "signal_repo", repo)
    client = TestClient(api_main.app)

    response = client.get("/signals/decision-surface")
    assert response.status_code == 401
    assert response.json() == {"detail": "unauthorized"}


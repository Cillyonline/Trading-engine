"""Integration tests for health probe and health sub-system endpoints.

Covers:
- /health/live   — liveness probe (no auth, always 200)
- /health/ready  — readiness probe (no auth, 200 or 503)
- /health        — aggregate health (read_only auth required)
- /health/engine — engine subsystem health (read_only auth required)
- /health/data   — data subsystem health (read_only auth required)
- /health/guards — compliance guards health (read_only auth required)
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import api.main as api_main
from cilly_trading.engine.runtime_controller import _reset_runtime_controller_for_tests

READ_ONLY_HEADERS = {api_main.ROLE_HEADER_NAME: "read_only"}
OWNER_HEADERS = {api_main.ROLE_HEADER_NAME: "owner"}


def setup_function() -> None:
    _reset_runtime_controller_for_tests()


def teardown_function() -> None:
    _reset_runtime_controller_for_tests()


# ---------------------------------------------------------------------------
# /health/live
# ---------------------------------------------------------------------------


def test_health_live_returns_200_without_authentication() -> None:
    with TestClient(api_main.app) as client:
        response = client.get("/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "alive"}


def test_health_live_returns_200_with_owner_role() -> None:
    with TestClient(api_main.app) as client:
        response = client.get("/health/live", headers=OWNER_HEADERS)

    assert response.status_code == 200
    assert response.json() == {"status": "alive"}


def test_health_live_is_always_200_regardless_of_runtime_state(monkeypatch) -> None:
    monkeypatch.setattr(api_main, "start_engine_runtime", lambda: "stopped")

    with TestClient(api_main.app) as client:
        response = client.get("/health/live")

    assert response.status_code == 200


# ---------------------------------------------------------------------------
# /health/ready
# ---------------------------------------------------------------------------


def test_health_ready_returns_200_when_runtime_is_running() -> None:
    with TestClient(api_main.app) as client:
        response = client.get("/health/ready")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"
    assert body["runtime"] in ("running", "paused", "ready")


def test_health_ready_returns_503_when_runtime_is_stopped() -> None:
    _reset_runtime_controller_for_tests()

    with TestClient(api_main.app) as client:
        client.post("/execution/stop", headers=OWNER_HEADERS)
        response = client.get("/health/ready")

    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "not_ready"


def test_health_ready_returns_200_without_authentication() -> None:
    with TestClient(api_main.app) as client:
        response = client.get("/health/ready")

    assert response.status_code in (200, 503)


def test_health_ready_returns_200_after_runtime_pause() -> None:
    with TestClient(api_main.app) as client:
        client.post("/execution/pause", headers=OWNER_HEADERS)
        response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json()["runtime"] == "paused"


# ---------------------------------------------------------------------------
# /health (aggregate)
# ---------------------------------------------------------------------------


def test_health_aggregate_requires_authenticated_role() -> None:
    with TestClient(api_main.app) as client:
        response = client.get("/health")

    assert response.status_code == 401
    assert response.json() == {"detail": "unauthorized"}


def test_health_aggregate_returns_200_with_read_only_role() -> None:
    with TestClient(api_main.app) as client:
        response = client.get("/health", headers=READ_ONLY_HEADERS)

    assert response.status_code == 200
    body = response.json()
    assert "status" in body
    assert "mode" in body
    assert "ready" in body


def test_health_aggregate_returns_200_with_owner_role() -> None:
    with TestClient(api_main.app) as client:
        response = client.get("/health", headers=OWNER_HEADERS)

    assert response.status_code == 200


def test_health_aggregate_rejects_unknown_role() -> None:
    with TestClient(api_main.app) as client:
        response = client.get("/health", headers={api_main.ROLE_HEADER_NAME: "auditor"})

    assert response.status_code == 401


# ---------------------------------------------------------------------------
# /health/engine
# ---------------------------------------------------------------------------


def test_health_engine_requires_authenticated_role() -> None:
    with TestClient(api_main.app) as client:
        response = client.get("/health/engine")

    assert response.status_code == 401


def test_health_engine_returns_200_with_read_only_role() -> None:
    with TestClient(api_main.app) as client:
        response = client.get("/health/engine", headers=READ_ONLY_HEADERS)

    assert response.status_code == 200
    body = response.json()
    assert body["subsystem"] == "engine"
    assert "status" in body
    assert "ready" in body
    assert "mode" in body


# ---------------------------------------------------------------------------
# /health/data
# ---------------------------------------------------------------------------


def test_health_data_requires_authenticated_role() -> None:
    with TestClient(api_main.app) as client:
        response = client.get("/health/data")

    assert response.status_code == 401


def test_health_data_returns_200_with_read_only_role(tmp_path: Path, monkeypatch) -> None:
    db_path = tmp_path / "test.db"
    db_path.touch()
    monkeypatch.setattr(api_main, "_resolve_analysis_db_path", lambda: str(db_path))

    with TestClient(api_main.app) as client:
        response = client.get("/health/data", headers=READ_ONLY_HEADERS)

    assert response.status_code == 200
    body = response.json()
    assert body["subsystem"] == "data"
    assert body["status"] == "healthy"
    assert body["ready"] is True


def test_health_data_reports_unavailable_when_db_missing(tmp_path: Path, monkeypatch) -> None:
    missing_path = tmp_path / "nonexistent.db"
    monkeypatch.setattr(api_main, "_resolve_analysis_db_path", lambda: str(missing_path))

    with TestClient(api_main.app) as client:
        response = client.get("/health/data", headers=READ_ONLY_HEADERS)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "unavailable"
    assert body["ready"] is False


# ---------------------------------------------------------------------------
# /health/guards
# ---------------------------------------------------------------------------


def test_health_guards_requires_authenticated_role() -> None:
    with TestClient(api_main.app) as client:
        response = client.get("/health/guards")

    assert response.status_code == 401


def test_health_guards_returns_200_with_read_only_role() -> None:
    with TestClient(api_main.app) as client:
        response = client.get("/health/guards", headers=READ_ONLY_HEADERS)

    assert response.status_code == 200
    body = response.json()
    assert body["subsystem"] == "guards"
    assert "status" in body
    assert "ready" in body
    assert "blocking" in body
    assert "guards" in body


def test_health_guards_reports_degraded_when_kill_switch_active(monkeypatch) -> None:
    monkeypatch.setenv("CILLY_EXECUTION_KILL_SWITCH_ACTIVE", "true")

    with TestClient(api_main.app) as client:
        response = client.get("/health/guards", headers=READ_ONLY_HEADERS)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "degraded"
    assert body["blocking"] is True
    assert body["ready"] is False
    assert body["guards"]["kill_switch"]["blocking"] is True


def test_health_guards_reports_healthy_when_no_guards_active() -> None:
    with TestClient(api_main.app) as client:
        response = client.get("/health/guards", headers=READ_ONLY_HEADERS)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "healthy"
    assert body["blocking"] is False
    assert body["ready"] is True

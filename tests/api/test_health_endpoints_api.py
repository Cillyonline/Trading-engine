from __future__ import annotations

from datetime import datetime, timezone

from fastapi.testclient import TestClient

import api.main as api_main

READ_ONLY_HEADERS = {api_main.ROLE_HEADER_NAME: "read_only"}


def _runtime_payload(mode: str = "running") -> dict[str, object]:
    return {
        "schema_version": "v1",
        "runtime_id": "engine-runtime-123",
        "mode": mode,
        "timestamps": {
            "started_at": "2026-01-01T12:00:00+00:00",
            "updated_at": "2026-01-01T12:00:00+00:00",
        },
        "ownership": {"owner_tag": "engine"},
    }


def test_health_engine_reports_runtime_readiness(monkeypatch) -> None:
    fixed_now = datetime(2026, 1, 1, 12, 0, 30, tzinfo=timezone.utc)

    monkeypatch.setattr(api_main, "start_engine_runtime", lambda: "running")
    monkeypatch.setattr(api_main, "get_runtime_introspection_payload", lambda: _runtime_payload("running"))
    monkeypatch.setattr(api_main, "_health_now", lambda: fixed_now)

    with TestClient(api_main.app) as client:
        response = client.get("/health/engine", headers=READ_ONLY_HEADERS)

    assert response.status_code == 200
    assert response.json() == {
        "subsystem": "engine",
        "status": "healthy",
        "ready": True,
        "mode": "running",
        "reason": "bounded_runtime_ready",
        "runtime_status": "healthy",
        "runtime_reason": "runtime_running_fresh",
        "checked_at": fixed_now.isoformat(),
    }


def test_health_data_reports_unavailable_when_data_source_is_missing(monkeypatch, tmp_path) -> None:
    fixed_now = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    missing_db_path = tmp_path / "missing-analysis.db"

    monkeypatch.setattr(api_main, "start_engine_runtime", lambda: "running")
    monkeypatch.setattr(api_main, "ANALYSIS_DB_PATH", str(missing_db_path))
    monkeypatch.setattr(api_main, "_health_now", lambda: fixed_now)

    with TestClient(api_main.app) as client:
        response = client.get("/health/data", headers=READ_ONLY_HEADERS)

    assert response.status_code == 200
    assert response.json() == {
        "subsystem": "data",
        "status": "unavailable",
        "ready": False,
        "reason": "data_source_unavailable",
        "checked_at": fixed_now.isoformat(),
    }


def test_health_guards_reports_blocking_state(monkeypatch) -> None:
    fixed_now = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

    monkeypatch.setattr(api_main, "start_engine_runtime", lambda: "running")
    monkeypatch.setattr(api_main, "_health_now", lambda: fixed_now)
    monkeypatch.setenv("CILLY_EXECUTION_KILL_SWITCH_ACTIVE", "true")

    with TestClient(api_main.app) as client:
        response = client.get("/health/guards", headers=READ_ONLY_HEADERS)

    assert response.status_code == 200
    assert response.json() == {
        "subsystem": "guards",
        "status": "degraded",
        "ready": False,
        "decision": "blocking",
        "blocking": True,
        "guards": {
            "drawdown_guard": {"enabled": False, "blocking": False},
            "daily_loss_guard": {"enabled": False, "blocking": False},
            "kill_switch": {"active": True, "blocking": True},
        },
        "checked_at": fixed_now.isoformat(),
    }


def test_health_guards_requires_valid_authenticated_role(monkeypatch) -> None:
    monkeypatch.setattr(api_main, "start_engine_runtime", lambda: "running")

    with TestClient(api_main.app) as client:
        missing = client.get("/health/guards")
        invalid = client.get("/health/guards", headers={api_main.ROLE_HEADER_NAME: "auditor"})

    assert missing.status_code == 401
    assert missing.json() == {"detail": "unauthorized"}
    assert invalid.status_code == 401
    assert invalid.json() == {"detail": "unauthorized"}


def test_health_guards_uses_internal_guard_helper_not_route_handler(monkeypatch) -> None:
    fixed_now = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

    monkeypatch.setattr(api_main, "start_engine_runtime", lambda: "running")
    monkeypatch.setattr(api_main, "_health_now", lambda: fixed_now)
    monkeypatch.setattr(
        api_main,
        "read_compliance_guard_status",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("route handler reused")),
    )

    with TestClient(api_main.app) as client:
        response = client.get("/health/guards", headers=READ_ONLY_HEADERS)

    assert response.status_code == 200
    assert response.json()["subsystem"] == "guards"


def test_health_endpoints_are_deterministic_for_identical_state(monkeypatch, tmp_path) -> None:
    fixed_now = datetime(2026, 1, 1, 12, 0, 30, tzinfo=timezone.utc)
    existing_db_path = tmp_path / "analysis.db"
    existing_db_path.write_text("", encoding="utf-8")

    monkeypatch.setattr(api_main, "start_engine_runtime", lambda: "running")
    monkeypatch.setattr(api_main, "get_runtime_introspection_payload", lambda: _runtime_payload("running"))
    monkeypatch.setattr(api_main, "ANALYSIS_DB_PATH", str(existing_db_path))
    monkeypatch.setattr(api_main, "_health_now", lambda: fixed_now)
    monkeypatch.setenv("CILLY_EXECUTION_KILL_SWITCH_ACTIVE", "false")

    with TestClient(api_main.app) as client:
        for path in ("/health", "/health/engine", "/health/data", "/health/guards"):
            first = client.get(path, headers=READ_ONLY_HEADERS).json()
            second = client.get(path, headers=READ_ONLY_HEADERS).json()
            assert first == second

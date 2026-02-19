from __future__ import annotations

from datetime import datetime, timezone

from fastapi.testclient import TestClient

import api.main as api_main


class _SideEffectProbe:
    def __init__(self) -> None:
        self.transition_calls = 0
        self.write_calls = 0


def test_health_endpoint_reports_runtime_health_from_simulated_snapshot(monkeypatch) -> None:
    fixed_now = datetime(2026, 1, 1, 12, 0, 30, tzinfo=timezone.utc)

    def _start() -> str:
        return "running"

    def _health_now() -> datetime:
        return fixed_now

    def _introspection_payload() -> dict[str, object]:
        return {
            "schema_version": "v1",
            "runtime_id": "engine-runtime-123",
            "mode": "running",
            "timestamps": {
                "started_at": "2026-01-01T12:00:00+00:00",
                "updated_at": "2026-01-01T12:00:10+00:00",
            },
            "ownership": {"owner_tag": "engine"},
        }

    monkeypatch.setattr(api_main, "start_engine_runtime", _start)
    monkeypatch.setattr(api_main, "get_runtime_introspection_payload", _introspection_payload)
    monkeypatch.setattr(api_main, "_health_now", _health_now)

    with TestClient(api_main.app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "mode": "running",
        "reason": "runtime_running_fresh",
        "checked_at": fixed_now.isoformat(),
    }


def test_health_endpoint_is_read_only_without_runtime_transitions_or_writes(monkeypatch) -> None:
    probe = _SideEffectProbe()

    def _start() -> str:
        return "running"

    def _shutdown() -> str:
        return "stopped"

    def _health_now() -> datetime:
        return datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

    def _introspection_payload() -> dict[str, object]:
        return {
            "schema_version": "v1",
            "runtime_id": "engine-runtime-123",
            "mode": "ready",
            "timestamps": {
                "started_at": "2026-01-01T12:00:00+00:00",
                "updated_at": "2026-01-01T12:00:00+00:00",
            },
            "ownership": {"owner_tag": "engine"},
        }

    def _unexpected_transition(*args, **kwargs):
        probe.transition_calls += 1
        raise AssertionError("runtime transitions must not be called by /health")

    def _unexpected_write(*args, **kwargs):
        probe.write_calls += 1
        raise AssertionError("persistence writes must not be called by /health")

    monkeypatch.setattr(api_main, "start_engine_runtime", _start)
    monkeypatch.setattr(api_main, "shutdown_engine_runtime", _shutdown)
    monkeypatch.setattr(api_main, "get_runtime_introspection_payload", _introspection_payload)
    monkeypatch.setattr(api_main, "_health_now", _health_now)
    monkeypatch.setattr(api_main, "get_runtime_controller", _unexpected_transition)
    monkeypatch.setattr(api_main.signal_repo, "save_signals", _unexpected_write)
    monkeypatch.setattr(api_main.analysis_run_repo, "save_run", _unexpected_write)

    with TestClient(api_main.app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "degraded"
    assert response.json()["reason"] == "runtime_not_started"
    assert probe.transition_calls == 0
    assert probe.write_calls == 0


def test_health_endpoint_reports_unavailable_boundary(monkeypatch) -> None:
    fixed_now = datetime(2026, 1, 1, 12, 2, 1, tzinfo=timezone.utc)

    def _start() -> str:
        return "running"

    def _health_now() -> datetime:
        return fixed_now

    def _introspection_payload() -> dict[str, object]:
        return {
            "schema_version": "v1",
            "runtime_id": "engine-runtime-123",
            "mode": "running",
            "timestamps": {
                "started_at": "2026-01-01T12:00:00+00:00",
                "updated_at": "2026-01-01T12:00:00+00:00",
            },
            "ownership": {"owner_tag": "engine"},
        }

    monkeypatch.setattr(api_main, "start_engine_runtime", _start)
    monkeypatch.setattr(api_main, "get_runtime_introspection_payload", _introspection_payload)
    monkeypatch.setattr(api_main, "_health_now", _health_now)

    with TestClient(api_main.app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "unavailable"
    assert response.json()["reason"] == "runtime_running_timeout"


def test_ui_endpoint_serves_html(monkeypatch) -> None:
    def _start() -> str:
        return "running"

    monkeypatch.setattr(api_main, "start_engine_runtime", _start)

    with TestClient(api_main.app) as client:
        response = client.get("/ui")

    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")
    assert "Owner Dashboard" in response.text

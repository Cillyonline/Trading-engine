from __future__ import annotations

from datetime import datetime, timezone

from fastapi.testclient import TestClient
import api.main as api_main
from cilly_trading.engine.observability_extensions import RuntimeObservabilityRegistry
import cilly_trading.engine.runtime_introspection as runtime_introspection

READ_ONLY_HEADERS = {api_main.ROLE_HEADER_NAME: "read_only"}


class _RuntimeStateStub:
    def __init__(self, state: str) -> None:
        self.state = state


def _build_registry_for_tests() -> RuntimeObservabilityRegistry:
    registry = RuntimeObservabilityRegistry()
    registry.register("status", name="core.status", extension=lambda _context: {}, source="core")
    registry.register("health", name="ext.disabled", extension=lambda _context: {}, enabled=False)
    registry.register("introspection", name="ext.enabled", extension=lambda _context: {}, enabled=True)
    return registry


def test_runtime_introspection_contract_is_explicit_and_stable(monkeypatch) -> None:
    runtime = _RuntimeStateStub("running")
    fixed_updated_at = datetime(2026, 1, 1, 12, 0, 5, tzinfo=timezone.utc)

    def _start() -> str:
        return "running"

    def _runtime() -> _RuntimeStateStub:
        return runtime

    monkeypatch.setattr(api_main, "start_engine_runtime", _start)
    monkeypatch.setattr(api_main, "get_runtime_controller", _runtime)
    monkeypatch.setattr(runtime_introspection, "get_runtime_controller", _runtime)
    monkeypatch.setattr(runtime_introspection, "_RUNTIME_OBSERVABILITY_REGISTRY", _build_registry_for_tests())
    monkeypatch.setattr(runtime_introspection, "_runtime_updated_at", lambda: fixed_updated_at)

    with TestClient(api_main.app) as client:
        first = client.get("/runtime/introspection", headers=READ_ONLY_HEADERS)
        second = client.get("/runtime/introspection", headers=READ_ONLY_HEADERS)

    assert first.status_code == 200
    assert second.status_code == 200

    first_payload = first.json()
    second_payload = second.json()

    assert first_payload == second_payload
    assert first_payload == {
        "schema_version": "v1",
        "runtime_id": first_payload["runtime_id"],
        "mode": "running",
        "timestamps": {
            "started_at": first_payload["timestamps"]["started_at"],
            "updated_at": "2026-01-01T12:00:05+00:00",
        },
        "ownership": {"owner_tag": "engine"},
        "extensions": [
            {
                "name": "ext.disabled",
                "point": "health",
                "enabled": False,
                "source": "extension",
            },
            {
                "name": "ext.enabled",
                "point": "introspection",
                "enabled": True,
                "source": "extension",
            },
            {
                "name": "core.status",
                "point": "status",
                "enabled": True,
                "source": "core",
            },
        ],
    }
    assert runtime.state == "running"


def test_runtime_introspection_triggers_no_persistence_writes(monkeypatch) -> None:
    runtime = _RuntimeStateStub("running")
    fixed_updated_at = datetime(2026, 1, 1, 12, 0, 5, tzinfo=timezone.utc)

    def _start() -> str:
        return "running"

    def _runtime() -> _RuntimeStateStub:
        return runtime

    def _unexpected_save_run(*args, **kwargs):
        raise AssertionError("analysis_run_repo.save_run must not be called")

    def _unexpected_save_signals(*args, **kwargs):
        raise AssertionError("signal_repo.save_signals must not be called")

    monkeypatch.setattr(api_main, "start_engine_runtime", _start)
    monkeypatch.setattr(api_main, "get_runtime_controller", _runtime)
    monkeypatch.setattr(runtime_introspection, "get_runtime_controller", _runtime)
    monkeypatch.setattr(api_main.analysis_run_repo, "save_run", _unexpected_save_run)
    monkeypatch.setattr(api_main.signal_repo, "save_signals", _unexpected_save_signals)
    monkeypatch.setattr(runtime_introspection, "_RUNTIME_OBSERVABILITY_REGISTRY", _build_registry_for_tests())
    monkeypatch.setattr(runtime_introspection, "_runtime_updated_at", lambda: fixed_updated_at)

    with TestClient(api_main.app) as client:
        response = client.get("/runtime/introspection", headers=READ_ONLY_HEADERS)

    assert response.status_code == 200


def test_runtime_introspection_rejects_missing_and_invalid_roles(monkeypatch) -> None:
    runtime = _RuntimeStateStub("running")
    fixed_updated_at = datetime(2026, 1, 1, 12, 0, 5, tzinfo=timezone.utc)

    monkeypatch.setattr(api_main, "start_engine_runtime", lambda: "running")
    monkeypatch.setattr(api_main, "get_runtime_controller", lambda: runtime)
    monkeypatch.setattr(runtime_introspection, "get_runtime_controller", lambda: runtime)
    monkeypatch.setattr(runtime_introspection, "_RUNTIME_OBSERVABILITY_REGISTRY", _build_registry_for_tests())
    monkeypatch.setattr(runtime_introspection, "_runtime_updated_at", lambda: fixed_updated_at)

    with TestClient(api_main.app) as client:
        missing = client.get("/runtime/introspection")
        invalid = client.get(
            "/runtime/introspection",
            headers={api_main.ROLE_HEADER_NAME: "auditor"},
        )

    assert missing.status_code == 401
    assert missing.json() == {"detail": "unauthorized"}
    assert invalid.status_code == 401
    assert invalid.json() == {"detail": "unauthorized"}


def test_system_state_uses_internal_helper_not_runtime_route_handler(monkeypatch) -> None:
    payload = {
        "schema_version": "v1",
        "status": "running",
        "runtime": {
            "schema_version": "v1",
            "runtime_id": "runtime-test",
            "mode": "running",
            "timestamps": {
                "started_at": "2025-01-01T00:00:00+00:00",
                "updated_at": "2025-01-01T00:00:00+00:00",
            },
            "ownership": {"owner_tag": "engine"},
            "extensions": [],
        },
        "metadata": {
            "read_only": True,
            "source": "engine_control_plane",
        },
    }

    monkeypatch.setattr(api_main, "start_engine_runtime", lambda: "running")
    monkeypatch.setattr(api_main, "get_system_state_payload", lambda: payload)
    monkeypatch.setattr(
        api_main,
        "runtime_introspection",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("route handler reused")),
    )

    with TestClient(api_main.app) as client:
        response = client.get("/system/state", headers=READ_ONLY_HEADERS)

    assert response.status_code == 200
    assert response.json() == payload


def test_runtime_introspection_is_deterministic_across_repeated_calls(monkeypatch) -> None:
    runtime = _RuntimeStateStub("running")
    fixed_updated_at = datetime(2026, 1, 1, 12, 0, 5, tzinfo=timezone.utc)

    monkeypatch.setattr(api_main, "start_engine_runtime", lambda: "running")
    monkeypatch.setattr(api_main, "get_runtime_controller", lambda: runtime)
    monkeypatch.setattr(runtime_introspection, "get_runtime_controller", lambda: runtime)
    monkeypatch.setattr(runtime_introspection, "_RUNTIME_OBSERVABILITY_REGISTRY", _build_registry_for_tests())
    monkeypatch.setattr(runtime_introspection, "_runtime_updated_at", lambda: fixed_updated_at)

    with TestClient(api_main.app) as client:
        payloads = [client.get("/runtime/introspection", headers=READ_ONLY_HEADERS).json() for _ in range(5)]

    assert payloads[0] == payloads[1] == payloads[2] == payloads[3] == payloads[4]


def test_runtime_introspection_advances_updated_at_across_calls(monkeypatch) -> None:
    runtime = _RuntimeStateStub("running")
    updated_values = iter(
        [
            datetime(2026, 1, 1, 12, 0, 1, tzinfo=timezone.utc),
            datetime(2026, 1, 1, 12, 0, 2, tzinfo=timezone.utc),
        ]
    )

    monkeypatch.setattr(api_main, "start_engine_runtime", lambda: "running")
    monkeypatch.setattr(api_main, "get_runtime_controller", lambda: runtime)
    monkeypatch.setattr(runtime_introspection, "get_runtime_controller", lambda: runtime)
    monkeypatch.setattr(runtime_introspection, "_RUNTIME_OBSERVABILITY_REGISTRY", _build_registry_for_tests())
    monkeypatch.setattr(runtime_introspection, "_runtime_updated_at", lambda: next(updated_values))

    with TestClient(api_main.app) as client:
        first = client.get("/runtime/introspection", headers=READ_ONLY_HEADERS).json()
        second = client.get("/runtime/introspection", headers=READ_ONLY_HEADERS).json()

    assert first["timestamps"]["started_at"] == second["timestamps"]["started_at"]
    assert first["timestamps"]["updated_at"] == "2026-01-01T12:00:01+00:00"
    assert second["timestamps"]["updated_at"] == "2026-01-01T12:00:02+00:00"

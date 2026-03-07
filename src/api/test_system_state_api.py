from __future__ import annotations

from fastapi.testclient import TestClient

import api.main as api_main
from tests.utils.json_schema_validator import validate_json_schema


def _build_system_state_payload() -> dict[str, object]:
    return {
        "schema_version": "v1",
        "status": "running",
        "runtime": {
            "schema_version": "v1",
            "runtime_id": "engine-runtime-123",
            "mode": "running",
            "timestamps": {
                "started_at": "2026-01-01T12:00:00+00:00",
                "updated_at": "2026-01-01T12:00:00+00:00",
            },
            "ownership": {"owner_tag": "engine"},
            "extensions": [
                {
                    "name": "core.health",
                    "point": "health",
                    "enabled": True,
                    "source": "core",
                }
            ],
        },
        "metadata": {
            "read_only": True,
            "source": "engine_control_plane",
        },
    }


def test_system_state_endpoint_responds_successfully_with_deterministic_structure(
    monkeypatch,
) -> None:
    expected = _build_system_state_payload()

    monkeypatch.setattr(api_main, "start_engine_runtime", lambda: "running")
    monkeypatch.setattr(api_main, "get_system_state_payload", lambda: expected)

    with TestClient(api_main.app) as client:
        first = client.get("/system/state")
        second = client.get("/system/state")

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json() == expected
    assert second.json() == expected


def test_system_state_endpoint_payload_matches_response_schema(monkeypatch) -> None:
    monkeypatch.setattr(api_main, "start_engine_runtime", lambda: "running")
    monkeypatch.setattr(api_main, "get_system_state_payload", _build_system_state_payload)

    with TestClient(api_main.app) as client:
        payload = client.get("/system/state").json()

    schema = api_main.SystemStateResponse.model_json_schema()
    errors = validate_json_schema(payload, schema)

    assert errors == []


def test_system_state_endpoint_is_documented(monkeypatch) -> None:
    monkeypatch.setattr(api_main, "start_engine_runtime", lambda: "running")

    with TestClient(api_main.app) as client:
        openapi = client.get("/openapi.json").json()

    get_spec = openapi["paths"]["/system/state"]["get"]
    assert get_spec["summary"] == "System State"
    assert "Read-only system runtime state for operator inspection." in get_spec["description"]


def test_system_state_reflects_paused_runtime_mode(monkeypatch) -> None:
    payload = _build_system_state_payload()
    payload["status"] = "paused"
    payload["runtime"]["mode"] = "paused"

    monkeypatch.setattr(api_main, "start_engine_runtime", lambda: "running")
    monkeypatch.setattr(api_main, "get_system_state_payload", lambda: payload)

    with TestClient(api_main.app) as client:
        response = client.get("/system/state")

    assert response.status_code == 200
    assert response.json()["status"] == "paused"
    assert response.json()["runtime"]["mode"] == "paused"

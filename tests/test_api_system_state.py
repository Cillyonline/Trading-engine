from __future__ import annotations

from fastapi.testclient import TestClient

import api.main as api_main

READ_ONLY_HEADERS = {api_main.ROLE_HEADER_NAME: "read_only"}


def _runtime_payload() -> dict:
    return {
        "schema_version": "v1",
        "runtime_id": "runtime-test",
        "mode": "running",
        "timestamps": {
            "started_at": "2025-01-01T00:00:00+00:00",
            "updated_at": "2025-01-01T00:00:00+00:00",
        },
        "ownership": {"owner_tag": "engine"},
        "extensions": [],
    }


def test_system_state_requires_read_only_role(monkeypatch) -> None:
    monkeypatch.setattr(api_main, "start_engine_runtime", lambda: "running")
    with TestClient(api_main.app) as client:
        response = client.get("/system/state")

    assert response.status_code == 401
    assert response.json()["detail"] == "unauthorized"


def test_system_state_returns_read_only_runtime_payload(monkeypatch) -> None:
    monkeypatch.setattr(api_main, "start_engine_runtime", lambda: "running")
    monkeypatch.setattr(api_main, "get_system_state_payload", lambda: {
        "schema_version": "v1",
        "status": "running",
        "runtime": _runtime_payload(),
        "metadata": {
            "read_only": True,
            "source": "engine_control_plane",
        },
    })

    with TestClient(api_main.app) as client:
        response = client.get("/system/state", headers=READ_ONLY_HEADERS)

    assert response.status_code == 200
    payload = response.json()
    assert payload == {
        "schema_version": "v1",
        "status": "running",
        "runtime": _runtime_payload(),
        "metadata": {
            "read_only": True,
            "source": "engine_control_plane",
        },
    }

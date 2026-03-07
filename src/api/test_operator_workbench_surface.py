from __future__ import annotations

from fastapi.testclient import TestClient

import api.main as api_main


def test_operator_workbench_ui_surface_is_reachable(monkeypatch) -> None:
    def _start() -> str:
        return "running"

    monkeypatch.setattr(api_main, "start_engine_runtime", _start)

    with TestClient(api_main.app) as client:
        response = client.get("/ui")

    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")


def test_operator_workbench_ui_surface_has_base_navigation(monkeypatch) -> None:
    def _start() -> str:
        return "running"

    monkeypatch.setattr(api_main, "start_engine_runtime", _start)

    with TestClient(api_main.app) as client:
        response = client.get("/ui")

    assert response.status_code == 200
    assert "Operator Workbench" in response.text
    assert "Workbench navigation" in response.text
    assert "Overview" in response.text
    assert "Runtime Status" in response.text
    assert "Analysis Runs" in response.text
    assert "Strategies" in response.text
    assert "Strategy List Panel" in response.text
    assert "Signals Panel" in response.text
    assert "id=\"strategy-list\"" in response.text
    assert "id=\"signal-list\"" in response.text
    assert "/strategies" in response.text
    assert "/signals?limit=20&sort=created_at_desc" in response.text
    assert "Journal Artifacts Panel" in response.text
    assert "Decision Trace Panel" in response.text
    assert "id=\"journal-artifact-list\"" in response.text
    assert "id=\"decision-trace-list\"" in response.text
    assert "/journal/artifacts" in response.text
    assert "/journal/decision-trace" in response.text
    assert "Audit Trail" in response.text


def test_operator_workbench_strategy_metadata_read_api(monkeypatch) -> None:
    def _start() -> str:
        return "running"

    monkeypatch.setattr(api_main, "start_engine_runtime", _start)

    with TestClient(api_main.app) as client:
        response = client.get("/strategies")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] >= 1
    assert isinstance(payload["items"], list)
    first = payload["items"][0]
    assert "strategy" in first
    assert "display_name" in first
    assert "default_config_keys" in first
    assert "has_default_config" in first

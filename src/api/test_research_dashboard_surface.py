from __future__ import annotations

from fastapi.testclient import TestClient

import api.main as api_main


def test_legacy_research_dashboard_route_is_not_a_runtime_entrypoint(monkeypatch) -> None:
    monkeypatch.setattr(api_main, "start_engine_runtime", lambda: "running")

    with TestClient(api_main.app) as client:
        response = client.get("/research-dashboard")

    assert response.status_code == 404


def test_ui_surface_is_canonical_website_facing_workflow_shell(monkeypatch) -> None:
    monkeypatch.setattr(api_main, "start_engine_runtime", lambda: "running")

    with TestClient(api_main.app) as client:
        response = client.get("/ui")

    assert response.status_code == 200
    assert "Bounded Website-Facing Workflow Shell" in response.text
    assert "single canonical website-facing workflow entrypoint" in response.text
    assert 'id="ui-primary-navigation-contract"' in response.text
    assert 'id="ui-workflow-boundary-marker"' in response.text
    assert "No live trading" in response.text
    assert "No Phase 39 or Phase 40 features" in response.text

from __future__ import annotations

from fastapi.testclient import TestClient

import api.main as api_main


def test_research_dashboard_surface_is_reachable(monkeypatch) -> None:
    monkeypatch.setattr(api_main, "start_engine_runtime", lambda: "running")

    with TestClient(api_main.app) as client:
        response = client.get("/research-dashboard")

    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")


def test_research_dashboard_surface_is_identifiable_and_separate_from_operator_shell(monkeypatch) -> None:
    monkeypatch.setattr(api_main, "start_engine_runtime", lambda: "running")

    with TestClient(api_main.app) as client:
        response = client.get("/research-dashboard")

    assert response.status_code == 200
    assert "Research Dashboard" in response.text
    assert 'id="phase23-research-dashboard-surface"' in response.text
    assert "Phase 23 research-only surface" in response.text
    assert "/research-dashboard" in response.text
    assert "/ui" in response.text
    assert "separate from the shared operator shell" in response.text
    assert "trader readiness" in response.text
    assert "production readiness" in response.text
    assert "#914" in response.text
    assert "Operator Workbench" not in response.text

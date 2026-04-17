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
    assert 'id="ui-signal-review-workflow-contract"' in response.text
    assert "Signal Review Workflow Step 1: Run Analysis" in response.text
    assert "Signal Review Workflow Step 3: Evaluate Ranked Signals" in response.text
    assert "Signal Decision Surface" in response.text
    assert "/signals/decision-surface" in response.text
    assert "blocked" in response.text
    assert "watch" in response.text
    assert "paper_candidate" in response.text
    assert "one bounded non-live signal review and trade-evaluation workflow" in response.text
    assert "No live trading" in response.text
    assert "Bounded Phase 39 visual-analysis/charting markers coexist" in response.text
    assert 'id="runtime-chart-panel"' in response.text
    assert "phase39-visual-analysis" in response.text

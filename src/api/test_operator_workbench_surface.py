from __future__ import annotations

from fastapi.testclient import TestClient

import api.main as api_main

READ_ONLY_HEADERS = {api_main.ROLE_HEADER_NAME: "read_only"}


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
    assert "Canonical /ui Workflow Shell" in response.text
    assert "Bounded Website-Facing Workflow Shell" in response.text
    assert "Signal Review Workflow Step 1: Run Analysis" in response.text
    assert "Signal Review Workflow Step 2: Configure Watchlist Scope" in response.text
    assert "Signal Review Workflow Step 3: Evaluate Ranked Signals" in response.text
    assert "Signal Review Workflow Step 4: Inspect Backtest Artifacts" in response.text
    assert "Signal Review Workflow Step 5: Inspect Runtime Data" in response.text
    assert "Signal Review Workflow Step 6: Review Run Evidence" in response.text
    assert "single canonical website-facing workflow entrypoint" in response.text
    assert "No live trading" in response.text
    assert "broker execution controls" in response.text
    assert "Technical signal visibility is explicitly separate from trader validation and operational readiness decisions." in response.text
    assert "Watchlist Management Panel" in response.text
    assert "Watchlist Execution Panel" in response.text
    assert "Watchlist Ranked Results Panel" in response.text
    assert "id=\"watchlist-form\"" in response.text
    assert "id=\"watchlist-select\"" in response.text
    assert "id=\"watchlist-ranked-result-list\"" in response.text
    assert "id=\"watchlist-failure-list\"" in response.text
    assert "/watchlists" in response.text
    assert "/watchlists/{watchlist_id}" in response.text
    assert "/watchlists/{watchlist_id}/execute" in response.text
    assert "Backtest Entry/Read Panel" in response.text
    assert "id=\"backtest-entry-read-form\"" in response.text
    assert "id=\"backtest-artifact-list\"" in response.text
    assert "/backtest/artifacts" in response.text
    assert "/backtest/artifacts/{run_id}/{artifact_name}" in response.text
    assert "Technical availability of bounded backtest artifacts is not trader validation." in response.text
    assert "does not establish operational readiness or live execution readiness." in response.text
    assert "strategy_readiness_evidence" in response.text
    assert "inferred_readiness_claim" in response.text
    assert "Inferred readiness claim:" in response.text
    assert "Bounded Phase 39 visual-analysis/charting markers coexist" in response.text
    assert "/alerts/history" in response.text
    assert 'id="alert-status"' in response.text
    assert 'id="alert-list"' in response.text
    assert 'id="runtime-chart-panel"' in response.text
    assert "phase39-visual-analysis" in response.text
    assert "Strategies" in response.text
    assert "Strategy List Panel" in response.text
    assert "Signals Panel" in response.text
    assert "Signal Decision Surface" in response.text
    assert "id=\"strategy-list\"" in response.text
    assert "id=\"signal-list\"" in response.text
    assert "/strategies" in response.text
    assert "/signals/decision-surface?limit=20&sort=created_at_desc" in response.text
    assert "blocked" in response.text
    assert "watch" in response.text
    assert "paper_candidate" in response.text
    assert "Trade Lifecycle Panel" in response.text
    assert "id=\"lifecycle-order-list\"" in response.text
    assert "id=\"lifecycle-event-timeline\"" in response.text
    assert "/execution/orders?limit=200&offset=0" in response.text
    assert "Journal Artifacts Panel" in response.text
    assert "Decision Trace Panel" in response.text
    assert "id=\"journal-artifact-list\"" in response.text
    assert "id=\"decision-trace-list\"" in response.text
    assert "/journal/artifacts" in response.text
    assert "/journal/decision-trace" in response.text
    assert "Audit Trail" in response.text
    assert "Paper Runtime Evidence Series" in response.text
    assert "/paper/runtime/evidence-series" in response.text
    assert 'id="paper-runtime-evidence"' in response.text
    assert "does not trigger paper-runtime runs" in response.text


def test_operator_workbench_strategy_metadata_read_api(monkeypatch) -> None:
    def _start() -> str:
        return "running"

    monkeypatch.setattr(api_main, "start_engine_runtime", _start)

    with TestClient(api_main.app) as client:
        response = client.get("/strategies", headers=READ_ONLY_HEADERS)

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] >= 1
    assert isinstance(payload["items"], list)
    first = payload["items"][0]
    assert "strategy" in first
    assert "display_name" in first
    assert "default_config_keys" in first
    assert "has_default_config" in first

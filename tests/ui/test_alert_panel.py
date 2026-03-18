from __future__ import annotations

from fastapi.testclient import TestClient

import api.main as api_main


READ_ONLY_HEADERS = {api_main.ROLE_HEADER_NAME: "read_only"}


def test_ui_alert_panel_markup_and_deterministic_empty_state(monkeypatch) -> None:
    monkeypatch.setattr(api_main, "start_engine_runtime", lambda: "running")
    api_main.app.state.alert_history_store = []

    with TestClient(api_main.app) as client:
        response = client.get("/ui")

    assert response.status_code == 200
    assert "Recent Alerts" in response.text
    assert "/alerts/history" in response.text
    assert 'id="alert-history-status"' in response.text
    assert 'id="alert-history-list"' in response.text
    assert 'id="alert-history-empty"' in response.text
    assert "No recent alerts available for this dashboard session." in response.text


def test_ui_alert_panel_uses_read_only_alert_history_endpoint(monkeypatch) -> None:
    monkeypatch.setattr(api_main, "start_engine_runtime", lambda: "running")
    api_main.app.state.alert_history_store = [
        {
            "event_id": "evt-latest",
            "alert_id": "runtime-critical",
            "name": "Runtime Halted",
            "severity": "critical",
            "source": "runtime",
            "triggered_at": "2026-03-16T09:00:00Z",
            "summary": "Runtime entered a blocked state.",
            "symbol": None,
            "strategy": None,
        },
        {
            "event_id": "evt-older",
            "alert_id": "drawdown-warning",
            "name": "Drawdown Warning",
            "severity": "warning",
            "source": "risk",
            "triggered_at": "2026-03-16T08:00:00Z",
            "summary": "Drawdown crossed the warning threshold.",
            "symbol": "BTCUSDT",
            "strategy": "RSI2",
        },
    ]

    with TestClient(api_main.app) as client:
        history_response = client.get("/alerts/history", headers=READ_ONLY_HEADERS)

    assert history_response.status_code == 200
    payload = history_response.json()
    assert [item["event_id"] for item in payload["items"]] == ["evt-latest", "evt-older"]
    assert payload["items"][0]["triggered_at"] == "2026-03-16T09:00:00Z"
    assert payload["items"][1]["triggered_at"] == "2026-03-16T08:00:00Z"

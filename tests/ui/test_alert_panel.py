from __future__ import annotations

from fastapi.testclient import TestClient

import api.main as api_main

OPERATOR_HEADERS = {api_main.ROLE_HEADER_NAME: "operator"}
READ_ONLY_HEADERS = {api_main.ROLE_HEADER_NAME: "read_only"}


def test_alert_panel_ui_and_history_endpoint(monkeypatch) -> None:
    monkeypatch.setattr(api_main, "start_engine_runtime", lambda: "running")
    api_main.app.state.alert_history_store = [
        {
            "schema_version": "1.0",
            "event_id": "alert_1",
            "event_type": "signal.generated",
            "source_type": "signal",
            "source_id": "sig_1",
            "severity": "warning",
            "occurred_at": "2025-01-02T00:00:00+00:00",
            "symbol": "AAPL",
            "strategy": "RSI2",
            "correlation_id": None,
            "payload": {},
        },
        {
            "schema_version": "1.0",
            "event_id": "alert_2",
            "event_type": "signal.generated",
            "source_type": "signal",
            "source_id": "sig_2",
            "severity": "info",
            "occurred_at": "2025-01-01T00:00:00+00:00",
            "symbol": "MSFT",
            "strategy": "RSI2",
            "correlation_id": None,
            "payload": {},
        },
    ]

    with TestClient(api_main.app) as client:
        alerts_response = client.get("/alerts/history", headers=READ_ONLY_HEADERS)
        assert alerts_response.status_code == 200
        alerts_payload = alerts_response.json()
        assert alerts_payload["total"] == 2
        assert [event["event_id"] for event in alerts_payload["items"]] == ["alert_1", "alert_2"]

        ui_response = client.get("/ui")
        assert ui_response.status_code == 200
        assert "/alerts/history" in ui_response.text
        assert 'id="alert-status"' in ui_response.text
        assert 'id="alert-list"' in ui_response.text

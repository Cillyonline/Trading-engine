from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.alerts_api import build_alerts_router
from cilly_trading.alerts.alert_delivery_service import AlertDeliveryService
from cilly_trading.alerts.alert_persistence_sqlite import (
    SqliteAlertConfigurationRepository,
    SqliteAlertDeliveryHistoryRepository,
)

OPERATOR_HEADERS = {"X-Cilly-Role": "operator"}
READ_ONLY_HEADERS = {"X-Cilly-Role": "read_only"}


def _require_role(minimum_role: str):
    def _dependency() -> str:
        return minimum_role

    return _dependency


def _build_test_app(db_path) -> FastAPI:
    app = FastAPI()
    app.state.alert_configuration_store = SqliteAlertConfigurationRepository(db_path=db_path)
    app.state.alert_history_store = SqliteAlertDeliveryHistoryRepository(db_path=db_path)
    app.state.alert_delivery_service = AlertDeliveryService(history_store=app.state.alert_history_store)
    app.include_router(build_alerts_router(_require_role))
    return app


def test_alert_event_dispatch_lifecycle_is_deterministic_and_restart_safe(tmp_path) -> None:
    db_path = tmp_path / "alerts-lifecycle.db"
    app = _build_test_app(db_path)

    with TestClient(app) as client:
        create_config_response = client.post(
            "/alerts/configurations",
            json={
                "alert_id": "drawdown-life",
                "name": "Drawdown Lifecycle",
                "description": "Lifecycle verification",
                "source": "risk",
                "metric": "drawdown_pct",
                "operator": "gte",
                "threshold": 4.2,
                "severity": "warning",
                "enabled": True,
                "tags": ["risk"],
            },
            headers=OPERATOR_HEADERS,
        )
        assert create_config_response.status_code == 201

        dispatch_response = client.post(
            "/alerts/dispatches",
            json={
                "event": {
                    "schema_version": "1.0",
                    "event_id": "alert_static_lifecycle_event",
                    "event_type": "runtime.guard_triggered",
                    "source_type": "runtime",
                    "source_id": "guard-lifecycle",
                    "severity": "warning",
                    "occurred_at": "2026-04-12T12:00:00Z",
                    "symbol": "AAPL",
                    "strategy": "RSI2",
                    "correlation_id": None,
                    "payload": {"guard": "drawdown", "value": 4.2},
                }
            },
            headers=OPERATOR_HEADERS,
        )
        assert dispatch_response.status_code == 200
        assert dispatch_response.json() == {
            "event_id": "alert_static_lifecycle_event",
            "deliveries": [
                {"channel_name": "bounded_non_live", "delivered": True, "error": None}
            ],
            "delivery_mode": "bounded_non_live",
            "live_routing": False,
        }

        history_response = client.get("/alerts/history", headers=READ_ONLY_HEADERS)
        assert history_response.status_code == 200
        history_payload = history_response.json()
        assert history_payload["total"] == 1
        assert history_payload["items"][0]["event_id"] == "alert_static_lifecycle_event"

        delivery_results_response = client.get(
            "/alerts/delivery-results",
            headers=READ_ONLY_HEADERS,
        )
        assert delivery_results_response.status_code == 200
        delivery_results_payload = delivery_results_response.json()
        assert delivery_results_payload["total"] == 1
        assert delivery_results_payload["items"] == [
            {
                "event_id": "alert_static_lifecycle_event",
                "channel_name": "bounded_non_live",
                "delivered": True,
                "error": None,
                "occurred_at": "2026-04-12T12:00:00Z",
                "recorded_at": delivery_results_payload["items"][0]["recorded_at"],
                "delivery_mode": "bounded_non_live",
            }
        ]

    restarted_app = _build_test_app(db_path)
    with TestClient(restarted_app) as restarted_client:
        configurations_response = restarted_client.get(
            "/alerts/configurations",
            headers=READ_ONLY_HEADERS,
        )
        assert configurations_response.status_code == 200
        assert configurations_response.json()["total"] == 1
        assert configurations_response.json()["items"][0]["alert_id"] == "drawdown-life"

        history_response = restarted_client.get("/alerts/history", headers=READ_ONLY_HEADERS)
        assert history_response.status_code == 200
        assert history_response.json()["total"] == 1
        assert history_response.json()["items"][0]["event_id"] == "alert_static_lifecycle_event"

        restarted_delivery_results_response = restarted_client.get(
            "/alerts/delivery-results",
            headers=READ_ONLY_HEADERS,
        )
        assert restarted_delivery_results_response.status_code == 200
        restarted_delivery_payload = restarted_delivery_results_response.json()
        assert restarted_delivery_payload["total"] == 1
        assert restarted_delivery_payload["items"] == [
            {
                "event_id": "alert_static_lifecycle_event",
                "channel_name": "bounded_non_live",
                "delivered": True,
                "error": None,
                "occurred_at": "2026-04-12T12:00:00Z",
                "recorded_at": restarted_delivery_payload["items"][0]["recorded_at"],
                "delivery_mode": "bounded_non_live",
            }
        ]

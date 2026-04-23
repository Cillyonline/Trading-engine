from __future__ import annotations

import json
from pathlib import Path

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


def _build_app(*, db_path: Path, file_sink_path: Path | None) -> FastAPI:
    app = FastAPI()
    app.state.alert_configuration_store = SqliteAlertConfigurationRepository(db_path=db_path)
    app.state.alert_history_store = SqliteAlertDeliveryHistoryRepository(db_path=db_path)
    app.state.alert_delivery_service = AlertDeliveryService(
        history_store=app.state.alert_history_store,
        file_sink_path=file_sink_path,
    )
    app.include_router(build_alerts_router(_require_role))
    return app


def _dispatch_payload(event_id: str = "alert_static_file_sink_event") -> dict:
    return {
        "event": {
            "schema_version": "1.0",
            "event_id": event_id,
            "event_type": "runtime.guard_triggered",
            "source_type": "runtime",
            "source_id": "guard-file-sink",
            "severity": "warning",
            "occurred_at": "2026-04-12T12:00:00Z",
            "symbol": "AAPL",
            "strategy": "RSI2",
            "correlation_id": None,
            "payload": {"guard": "drawdown", "value": 4.2},
        }
    }


def test_dispatch_via_file_sink_channel_writes_jsonl_and_persists_results(tmp_path: Path) -> None:
    db_path = tmp_path / "alerts.db"
    sink_path = tmp_path / "sink" / "alerts.jsonl"
    app = _build_app(db_path=db_path, file_sink_path=sink_path)

    with TestClient(app) as client:
        dispatch_response = client.post(
            "/alerts/dispatches",
            json=_dispatch_payload(),
            headers=OPERATOR_HEADERS,
        )
        assert dispatch_response.status_code == 200
        body = dispatch_response.json()
        assert body["event_id"] == "alert_static_file_sink_event"
        assert body["delivery_mode"] == "bounded_non_live"
        assert body["live_routing"] is False
        assert {delivery["channel_name"] for delivery in body["deliveries"]} == {
            "bounded_non_live",
            "file_sink",
        }
        for delivery in body["deliveries"]:
            assert delivery["delivered"] is True
            assert delivery["error"] is None

        delivery_results = client.get(
            "/alerts/delivery-results",
            headers=READ_ONLY_HEADERS,
        ).json()
        assert delivery_results["total"] == 2
        channel_names = sorted(item["channel_name"] for item in delivery_results["items"])
        assert channel_names == ["bounded_non_live", "file_sink"]

    on_disk = sink_path.read_text(encoding="utf-8").splitlines()
    assert len(on_disk) == 1
    assert json.loads(on_disk[0])["event_id"] == "alert_static_file_sink_event"


def test_dispatch_records_explicit_failure_when_file_sink_unavailable(tmp_path: Path) -> None:
    db_path = tmp_path / "alerts.db"
    blocking_file = tmp_path / "blocked"
    blocking_file.write_text("not-a-directory")
    sink_path = blocking_file / "alerts.jsonl"

    app = _build_app(db_path=db_path, file_sink_path=sink_path)

    with TestClient(app) as client:
        dispatch_response = client.post(
            "/alerts/dispatches",
            json=_dispatch_payload(event_id="alert_static_file_sink_failure"),
            headers=OPERATOR_HEADERS,
        )
        assert dispatch_response.status_code == 200
        body = dispatch_response.json()
        deliveries = {entry["channel_name"]: entry for entry in body["deliveries"]}
        assert deliveries["bounded_non_live"]["delivered"] is True
        assert deliveries["file_sink"]["delivered"] is False
        assert deliveries["file_sink"]["error"]
        assert body["live_routing"] is False
        assert body["delivery_mode"] == "bounded_non_live"

        delivery_results = client.get(
            "/alerts/delivery-results",
            headers=READ_ONLY_HEADERS,
        ).json()
        assert delivery_results["total"] == 2
        failed_rows = [item for item in delivery_results["items"] if not item["delivered"]]
        assert len(failed_rows) == 1
        assert failed_rows[0]["channel_name"] == "file_sink"
        assert failed_rows[0]["error"]

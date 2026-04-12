from __future__ import annotations

import pytest
from pydantic import ValidationError

from api.alerts_api import AlertConfigurationCreateRequest
from cilly_trading.alerts.alert_delivery_service import AlertDeliveryService
from cilly_trading.alerts.alert_models import create_alert_event
from cilly_trading.alerts.alert_persistence_sqlite import (
    BOUNDED_DELIVERY_MODE,
    SqliteAlertConfigurationRepository,
    SqliteAlertDeliveryHistoryRepository,
)


def _config_payload(alert_id: str = "drawdown-bounded") -> dict[str, object]:
    return {
        "alert_id": alert_id,
        "name": "Drawdown Guard",
        "description": "Bounded drawdown threshold alert",
        "source": "risk",
        "metric": "drawdown_pct",
        "operator": "gte",
        "threshold": 3.5,
        "severity": "warning",
        "enabled": True,
        "tags": ["risk", "bounded"],
    }


def _event_payload() -> dict[str, object]:
    return {
        "event_type": "runtime.guard_triggered",
        "source_type": "runtime",
        "source_id": "guard-risk-1",
        "severity": "warning",
        "occurred_at": "2026-04-12T10:00:00Z",
        "payload": {"guard": "drawdown", "value": 3.8},
    }


def test_bounded_dispatch_persists_delivery_result(tmp_path) -> None:
    db_path = tmp_path / "alerts-mvp.db"
    history_store = SqliteAlertDeliveryHistoryRepository(db_path=db_path)
    service = AlertDeliveryService(history_store=history_store)
    event = create_alert_event(**_event_payload())

    result = service.dispatch_event(event)
    stored_rows, total = history_store.list_delivery_results(limit=10, offset=0)

    assert result.event_id == event.event_id
    assert result.delivered_channels == ("bounded_non_live",)
    assert result.failed_channels == ()
    assert total == 1
    assert stored_rows == [
        {
            "event_id": event.event_id,
            "channel_name": "bounded_non_live",
            "delivered": True,
            "error": None,
            "occurred_at": "2026-04-12T10:00:00Z",
            "recorded_at": stored_rows[0]["recorded_at"],
            "delivery_mode": BOUNDED_DELIVERY_MODE,
        }
    ]


def test_restart_preserves_configuration_and_history(tmp_path) -> None:
    db_path = tmp_path / "alerts-restart.db"
    config_store = SqliteAlertConfigurationRepository(db_path=db_path)
    history_store = SqliteAlertDeliveryHistoryRepository(db_path=db_path)
    delivery_service = AlertDeliveryService(history_store=history_store)

    config_store.create(_config_payload())
    event = create_alert_event(**_event_payload())
    delivery_service.dispatch_event(event)

    restarted_config_store = SqliteAlertConfigurationRepository(db_path=db_path)
    restarted_history_store = SqliteAlertDeliveryHistoryRepository(db_path=db_path)

    config_item = restarted_config_store.get("drawdown-bounded")
    events, total_events = restarted_history_store.list_events(limit=20, offset=0)

    assert config_item is not None
    assert config_item["name"] == "Drawdown Guard"
    assert total_events == 1
    assert events[0]["event_id"] == event.event_id


def test_invalid_alert_configuration_is_rejected() -> None:
    with pytest.raises(ValidationError):
        AlertConfigurationCreateRequest.model_validate(
            {
                "alert_id": "invalid-operator",
                "name": "Invalid Operator",
                "description": None,
                "source": "risk",
                "metric": "drawdown_pct",
                "operator": "invalid",
                "threshold": 2.0,
                "severity": "warning",
                "enabled": True,
                "tags": ["risk"],
            }
        )

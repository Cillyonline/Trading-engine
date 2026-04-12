from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request

from cilly_trading.alerts.alert_delivery_service import AlertDeliveryService
from cilly_trading.alerts.alert_persistence_sqlite import (
    SqliteAlertConfigurationRepository,
    SqliteAlertDeliveryHistoryRepository,
)

ALERT_CONFIGURATION_STORE_ATTR = "alert_configuration_store"
ALERT_HISTORY_STORE_ATTR = "alert_history_store"
ALERT_DELIVERY_SERVICE_ATTR = "alert_delivery_service"


def initialize_alert_state(app: FastAPI) -> None:
    app.state.alert_configuration_store = SqliteAlertConfigurationRepository()
    app.state.alert_history_store = SqliteAlertDeliveryHistoryRepository()
    app.state.alert_delivery_service = AlertDeliveryService(
        history_store=app.state.alert_history_store
    )


def get_alert_configuration_store(
    request: Request,
) -> dict[str, dict[str, Any]] | SqliteAlertConfigurationRepository:
    store = getattr(request.app.state, ALERT_CONFIGURATION_STORE_ATTR, None)
    if store is None:
        store = SqliteAlertConfigurationRepository()
        setattr(request.app.state, ALERT_CONFIGURATION_STORE_ATTR, store)
    return store


def get_alert_history_store(
    request: Request,
) -> list[dict[str, Any]] | SqliteAlertDeliveryHistoryRepository:
    store = getattr(request.app.state, ALERT_HISTORY_STORE_ATTR, None)
    if store is None:
        store = SqliteAlertDeliveryHistoryRepository()
        setattr(request.app.state, ALERT_HISTORY_STORE_ATTR, store)
    return store


def get_alert_delivery_service(request: Request) -> AlertDeliveryService:
    service = getattr(request.app.state, ALERT_DELIVERY_SERVICE_ATTR, None)
    if service is None:
        history_store = get_alert_history_store(request)
        if isinstance(history_store, list):
            # This branch is used by legacy tests that inject in-memory state directly.
            history_store = SqliteAlertDeliveryHistoryRepository()
            setattr(request.app.state, ALERT_HISTORY_STORE_ATTR, history_store)
        service = AlertDeliveryService(history_store=history_store)
        setattr(request.app.state, ALERT_DELIVERY_SERVICE_ATTR, service)
    return service

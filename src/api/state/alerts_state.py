from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request


ALERT_CONFIGURATION_STORE_ATTR = "alert_configuration_store"
ALERT_HISTORY_STORE_ATTR = "alert_history_store"


def initialize_alert_state(app: FastAPI) -> None:
    app.state.alert_configuration_store = {}
    app.state.alert_history_store = []


def get_alert_configuration_store(request: Request) -> dict[str, dict[str, Any]]:
    store = getattr(request.app.state, ALERT_CONFIGURATION_STORE_ATTR, None)
    if store is None:
        store = {}
        setattr(request.app.state, ALERT_CONFIGURATION_STORE_ATTR, store)
    return store


def get_alert_history_store(request: Request) -> list[dict[str, Any]]:
    store = getattr(request.app.state, ALERT_HISTORY_STORE_ATTR, None)
    if store is None:
        store = []
        setattr(request.app.state, ALERT_HISTORY_STORE_ATTR, store)
    return store

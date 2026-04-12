from __future__ import annotations

from typing import Any, Callable, Dict, List, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, ConfigDict, Field, model_validator

from cilly_trading.alerts.alert_models import AlertEvent
from cilly_trading.alerts.alert_persistence_sqlite import BOUNDED_DELIVERY_MODE

from .state import (
    get_alert_configuration_store,
    get_alert_delivery_service,
    get_alert_history_store,
)


class AlertConfigurationPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=1, max_length=128)
    description: str | None = Field(default=None, max_length=512)
    source: str = Field(..., min_length=1, max_length=64)
    metric: str = Field(..., min_length=1, max_length=64)
    operator: Literal["gt", "gte", "lt", "lte", "eq"]
    threshold: float = Field(..., allow_inf_nan=False)
    severity: Literal["info", "warning", "critical"]
    enabled: bool = True
    tags: List[str] = Field(default_factory=list, max_length=10)

    @model_validator(mode="after")
    def _validate_tags(self) -> "AlertConfigurationPayload":
        normalized_tags = [tag.strip() for tag in self.tags]
        if any(not tag for tag in normalized_tags):
            raise ValueError("tags must not contain blank values")
        if len(set(normalized_tags)) != len(normalized_tags):
            raise ValueError("tags must be unique")
        self.tags = normalized_tags
        return self


class AlertConfigurationCreateRequest(AlertConfigurationPayload):
    alert_id: str = Field(..., min_length=1, max_length=64)


class AlertConfigurationUpdateRequest(AlertConfigurationPayload):
    pass


class AlertConfigurationResponse(AlertConfigurationPayload):
    alert_id: str


class AlertConfigurationListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: List[AlertConfigurationResponse]
    total: int


class AlertListItemResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    alert_id: str
    name: str
    severity: Literal["info", "warning", "critical"]
    enabled: bool
    source: str
    metric: str
    operator: Literal["gt", "gte", "lt", "lte", "eq"]
    threshold: float


class AlertListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: List[AlertListItemResponse]
    total: int


class AlertHistoryListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: List[AlertEvent]
    total: int


class AlertDeliveryResultItemResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_id: str
    channel_name: str
    delivered: bool
    error: str | None
    occurred_at: str
    recorded_at: str
    delivery_mode: str


class AlertDeliveryResultListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: List[AlertDeliveryResultItemResponse]
    total: int


class AlertConfigurationDeleteResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    alert_id: str
    deleted: Literal[True]


class AlertDispatchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event: AlertEvent


class ChannelDeliveryResultResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    channel_name: str
    delivered: bool
    error: str | None = None


class AlertDispatchResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_id: str
    deliveries: List[ChannelDeliveryResultResponse]
    delivery_mode: Literal["bounded_non_live"]
    live_routing: Literal[False] = False


def _get_store(request: Request) -> Any:
    return get_alert_configuration_store(request)


def _get_alert_history_store(request: Request) -> Any:
    return get_alert_history_store(request)


def _sorted_items(store: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [store[alert_id] for alert_id in sorted(store)]


def _create_config_item(store: Any, payload: dict[str, Any]) -> dict[str, Any]:
    if isinstance(store, dict):
        if payload["alert_id"] in store:
            raise ValueError("alert_configuration_exists")
        store[payload["alert_id"]] = payload
        return payload
    return store.create(payload)


def _list_config_items(store: Any) -> list[dict[str, Any]]:
    if isinstance(store, dict):
        return _sorted_items(store)
    return store.list()


def _get_config_item(store: Any, alert_id: str) -> dict[str, Any] | None:
    if isinstance(store, dict):
        return store.get(alert_id)
    return store.get(alert_id)


def _update_config_item(store: Any, alert_id: str, payload: dict[str, Any]) -> dict[str, Any] | None:
    if isinstance(store, dict):
        if alert_id not in store:
            return None
        store[alert_id] = payload
        return payload
    return store.update(alert_id, payload)


def _delete_config_item(store: Any, alert_id: str) -> bool:
    if isinstance(store, dict):
        if alert_id not in store:
            return False
        del store[alert_id]
        return True
    return bool(store.delete(alert_id))


def _list_history_events(store: Any, *, limit: int, offset: int) -> tuple[list[dict[str, Any]], int]:
    if isinstance(store, list):
        sorted_events = sorted(
            store,
            key=lambda event: (
                event.get("occurred_at", ""),
                event.get("event_id", ""),
            ),
            reverse=True,
        )
        return sorted_events[offset : offset + limit], len(store)
    return store.list_events(limit=limit, offset=offset)


def _list_delivery_results(store: Any, *, limit: int, offset: int) -> tuple[list[dict[str, Any]], int]:
    if isinstance(store, list):
        sorted_events = sorted(
            store,
            key=lambda event: (
                event.get("occurred_at", ""),
                event.get("event_id", ""),
            ),
            reverse=True,
        )
        items = [
            {
                "event_id": event.get("event_id", ""),
                "channel_name": "bounded_non_live",
                "delivered": True,
                "error": None,
                "occurred_at": event.get("occurred_at", ""),
                "recorded_at": event.get("occurred_at", ""),
                "delivery_mode": BOUNDED_DELIVERY_MODE,
            }
            for event in sorted_events[offset : offset + limit]
        ]
        return items, len(store)
    return store.list_delivery_results(limit=limit, offset=offset)


def build_alerts_router(require_role: Callable[[str], Any]) -> APIRouter:
    router = APIRouter(tags=["alerts"])

    @router.post(
        "/alerts/configurations",
        response_model=AlertConfigurationResponse,
        status_code=status.HTTP_201_CREATED,
    )
    def create_alert_configuration(
        req: AlertConfigurationCreateRequest,
        request: Request,
        _: str = Depends(require_role("operator")),
    ) -> AlertConfigurationResponse:
        store = _get_store(request)
        payload = req.model_dump()
        try:
            created = _create_config_item(store, payload)
        except ValueError as exc:
            if str(exc) == "alert_configuration_exists":
                raise HTTPException(status_code=409, detail="alert_configuration_exists") from exc
            raise
        return AlertConfigurationResponse(**created)

    @router.get("/alerts/configurations", response_model=AlertConfigurationListResponse)
    def read_alert_configurations(
        request: Request,
        _: str = Depends(require_role("read_only")),
    ) -> AlertConfigurationListResponse:
        store = _get_store(request)
        items = [AlertConfigurationResponse(**item) for item in _list_config_items(store)]
        return AlertConfigurationListResponse(items=items, total=len(items))

    @router.get(
        "/alerts/configurations/{alert_id}",
        response_model=AlertConfigurationResponse,
    )
    def read_alert_configuration(
        alert_id: str,
        request: Request,
        _: str = Depends(require_role("read_only")),
    ) -> AlertConfigurationResponse:
        store = _get_store(request)
        item = _get_config_item(store, alert_id)
        if item is None:
            raise HTTPException(status_code=404, detail="alert_configuration_not_found")
        return AlertConfigurationResponse(**item)

    @router.put(
        "/alerts/configurations/{alert_id}",
        response_model=AlertConfigurationResponse,
    )
    def update_alert_configuration(
        alert_id: str,
        req: AlertConfigurationUpdateRequest,
        request: Request,
        _: str = Depends(require_role("operator")),
    ) -> AlertConfigurationResponse:
        store = _get_store(request)
        payload = {"alert_id": alert_id, **req.model_dump()}
        item = _update_config_item(store, alert_id, payload)
        if item is None:
            raise HTTPException(status_code=404, detail="alert_configuration_not_found")
        return AlertConfigurationResponse(**item)

    @router.delete(
        "/alerts/configurations/{alert_id}",
        response_model=AlertConfigurationDeleteResponse,
    )
    def delete_alert_configuration(
        alert_id: str,
        request: Request,
        _: str = Depends(require_role("operator")),
    ) -> AlertConfigurationDeleteResponse:
        store = _get_store(request)
        deleted = _delete_config_item(store, alert_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="alert_configuration_not_found")
        return AlertConfigurationDeleteResponse(alert_id=alert_id, deleted=True)

    @router.get("/alerts", response_model=AlertListResponse)
    def list_alerts(
        request: Request,
        _: str = Depends(require_role("read_only")),
    ) -> AlertListResponse:
        store = _get_store(request)
        items = [
            AlertListItemResponse(
                alert_id=item["alert_id"],
                name=item["name"],
                severity=item["severity"],
                enabled=item["enabled"],
                source=item["source"],
                metric=item["metric"],
                operator=item["operator"],
                threshold=item["threshold"],
            )
            for item in _list_config_items(store)
        ]
        return AlertListResponse(items=items, total=len(items))

    @router.post("/alerts/dispatches", response_model=AlertDispatchResponse)
    def dispatch_alert_event(
        req: AlertDispatchRequest,
        request: Request,
        _: str = Depends(require_role("operator")),
    ) -> AlertDispatchResponse:
        delivery_service = get_alert_delivery_service(request)
        result = delivery_service.dispatch_event(req.event)
        return AlertDispatchResponse(
            event_id=result.event_id,
            deliveries=[
                ChannelDeliveryResultResponse(
                    channel_name=delivery.channel_name,
                    delivered=delivery.delivered,
                    error=delivery.error,
                )
                for delivery in result.deliveries
            ],
            delivery_mode=BOUNDED_DELIVERY_MODE,
            live_routing=False,
        )

    @router.get("/alerts/history", response_model=AlertHistoryListResponse)
    def read_alert_history(
        request: Request,
        limit: int = Query(default=20, ge=1, le=200),
        offset: int = Query(default=0, ge=0),
        _: str = Depends(require_role("read_only")),
    ) -> AlertHistoryListResponse:
        store = _get_alert_history_store(request)
        events, total = _list_history_events(store, limit=limit, offset=offset)
        items = [AlertEvent(**event) for event in events]
        return AlertHistoryListResponse(items=items, total=total)

    @router.get("/alerts/delivery-results", response_model=AlertDeliveryResultListResponse)
    def read_alert_delivery_results(
        request: Request,
        limit: int = Query(default=20, ge=1, le=200),
        offset: int = Query(default=0, ge=0),
        _: str = Depends(require_role("read_only")),
    ) -> AlertDeliveryResultListResponse:
        store = _get_alert_history_store(request)
        rows, total = _list_delivery_results(store, limit=limit, offset=offset)
        items = [AlertDeliveryResultItemResponse(**row) for row in rows]
        return AlertDeliveryResultListResponse(items=items, total=total)

    return router

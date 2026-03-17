from __future__ import annotations

from typing import Any, Callable, Dict, List, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, ConfigDict, Field, model_validator

from cilly_trading.alerts.alert_models import AlertEvent


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


class AlertConfigurationDeleteResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    alert_id: str
    deleted: Literal[True]


def _get_store(request: Request) -> Dict[str, Dict[str, Any]]:
    store = getattr(request.app.state, "alert_configuration_store", None)
    if store is None:
        store = {}
        request.app.state.alert_configuration_store = store
    return store


def _get_alert_history_store(request: Request) -> List[Dict[str, Any]]:
    store = getattr(request.app.state, "alert_history_store", None)
    if store is None:
        store = []
        request.app.state.alert_history_store = store
    return store


def _sorted_items(store: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [store[alert_id] for alert_id in sorted(store)]


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
        if req.alert_id in store:
            raise HTTPException(status_code=409, detail="alert_configuration_exists")

        payload = req.model_dump()
        store[req.alert_id] = payload
        return AlertConfigurationResponse(**payload)

    @router.get("/alerts/configurations", response_model=AlertConfigurationListResponse)
    def read_alert_configurations(
        request: Request,
        _: str = Depends(require_role("read_only")),
    ) -> AlertConfigurationListResponse:
        store = _get_store(request)
        items = [AlertConfigurationResponse(**item) for item in _sorted_items(store)]
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
        item = store.get(alert_id)
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
        if alert_id not in store:
            raise HTTPException(status_code=404, detail="alert_configuration_not_found")

        payload = {"alert_id": alert_id, **req.model_dump()}
        store[alert_id] = payload
        return AlertConfigurationResponse(**payload)

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
        if alert_id not in store:
            raise HTTPException(status_code=404, detail="alert_configuration_not_found")

        del store[alert_id]
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
            for item in _sorted_items(store)
        ]
        return AlertListResponse(items=items, total=len(items))

    @router.get("/alerts/history", response_model=AlertHistoryListResponse)
    def read_alert_history(
        request: Request,
        limit: int = Query(default=20, ge=1, le=200),
        offset: int = Query(default=0, ge=0),
        _: str = Depends(require_role("read_only")),
    ) -> AlertHistoryListResponse:
        store = _get_alert_history_store(request)
        sorted_events = sorted(
            store,
            key=lambda event: (
                event.get("occurred_at", ""),
                event.get("event_id", ""),
            ),
            reverse=True,
        )
        items = [AlertEvent(**event) for event in sorted_events[offset : offset + limit]]
        return AlertHistoryListResponse(items=items, total=len(store))

    return router

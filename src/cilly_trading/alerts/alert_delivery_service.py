"""Bounded alert delivery orchestrator."""

from __future__ import annotations

from .alert_dispatcher import AlertDispatchResult, AlertDispatcher
from .alert_models import AlertEvent
from .alert_persistence_sqlite import (
    BOUNDED_DELIVERY_MODE,
    SqliteAlertDeliveryHistoryRepository,
)
from .channels.bounded_non_live_channel import BoundedNonLiveChannel


class AlertDeliveryService:
    """Dispatch alert events through one bounded channel and persist results."""

    def __init__(
        self,
        *,
        history_store: SqliteAlertDeliveryHistoryRepository,
        dispatcher: AlertDispatcher | None = None,
    ) -> None:
        self._history_store = history_store
        self._dispatcher = dispatcher or AlertDispatcher(channels=[BoundedNonLiveChannel()])

    @property
    def channel_names(self) -> tuple[str, ...]:
        return self._dispatcher.channel_names

    def dispatch_event(self, event: AlertEvent) -> AlertDispatchResult:
        dispatch_result = self._dispatcher.dispatch(event)
        self._history_store.record_dispatch(
            event=event,
            dispatch_result=dispatch_result,
            delivery_mode=BOUNDED_DELIVERY_MODE,
        )
        return dispatch_result


__all__ = ["AlertDeliveryService"]

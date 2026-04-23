"""Bounded alert delivery orchestrator."""

from __future__ import annotations

from pathlib import Path

from .alert_dispatcher import AlertDispatchResult, AlertDispatcher
from .alert_models import AlertEvent
from .alert_persistence_sqlite import (
    BOUNDED_DELIVERY_MODE,
    SqliteAlertDeliveryHistoryRepository,
)
from .channels.bounded_non_live_channel import BoundedNonLiveChannel
from .channels.file_sink_channel import FileSinkChannel


class AlertDeliveryService:
    """Dispatch alert events through bounded channels and persist results.

    By default, the service registers a single bounded, non-live, no-op channel
    so existing behaviour is preserved. When ``file_sink_path`` is provided the
    service also registers a deterministic, append-only JSONL ``FileSinkChannel``
    as a bounded external delivery destination. The file sink performs no
    network I/O, no broker integration, and no live trading routing.
    """

    def __init__(
        self,
        *,
        history_store: SqliteAlertDeliveryHistoryRepository,
        dispatcher: AlertDispatcher | None = None,
        file_sink_path: str | Path | None = None,
    ) -> None:
        self._history_store = history_store
        if dispatcher is not None:
            self._dispatcher = dispatcher
        else:
            channels: list = [BoundedNonLiveChannel()]
            if file_sink_path is not None:
                channels.append(FileSinkChannel(file_sink_path))
            self._dispatcher = AlertDispatcher(channels=channels)

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

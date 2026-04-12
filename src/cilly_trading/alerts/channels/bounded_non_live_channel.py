"""Single bounded, deterministic, explicitly non-live alert channel."""

from __future__ import annotations

from cilly_trading.alerts.alert_models import AlertEvent


class BoundedNonLiveChannel:
    """No-op channel that marks delivery as successful without external routing."""

    channel_name = "bounded_non_live"

    def deliver(self, event: AlertEvent) -> None:
        # Explicitly bounded behavior: validate that event identity exists, then no-op.
        if not event.event_id:
            raise ValueError("alert event_id is required")


__all__ = ["BoundedNonLiveChannel"]

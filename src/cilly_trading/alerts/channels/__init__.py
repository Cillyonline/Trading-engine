"""Notification channel contracts for alert delivery."""

from __future__ import annotations

from typing import Protocol

from cilly_trading.alerts.alert_models import AlertEvent


class NotificationChannel(Protocol):
    """Minimal delivery contract implemented by notification channels."""

    channel_name: str

    def deliver(self, event: AlertEvent) -> None:
        """Deliver an alert event to an external notification destination."""


__all__ = ["NotificationChannel"]

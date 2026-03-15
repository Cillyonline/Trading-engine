"""Alert notification dispatcher with graceful failure handling."""

from __future__ import annotations

from dataclasses import dataclass

from .alert_models import AlertEvent
from .channels import NotificationChannel


@dataclass(frozen=True)
class ChannelDeliveryResult:
    """Outcome for a single channel delivery attempt."""

    channel_name: str
    delivered: bool
    error: str | None = None


@dataclass(frozen=True)
class AlertDispatchResult:
    """Aggregate result for a dispatcher fan-out operation."""

    event_id: str
    deliveries: tuple[ChannelDeliveryResult, ...]

    @property
    def delivered_channels(self) -> tuple[str, ...]:
        return tuple(result.channel_name for result in self.deliveries if result.delivered)

    @property
    def failed_channels(self) -> tuple[str, ...]:
        return tuple(result.channel_name for result in self.deliveries if not result.delivered)

    @property
    def has_failures(self) -> bool:
        return any(not result.delivered for result in self.deliveries)


class AlertDispatcher:
    """Delivers alert events to registered channels without failing the caller."""

    def __init__(
        self,
        channels: list[NotificationChannel] | tuple[NotificationChannel, ...] | None = None,
    ) -> None:
        self._channels: dict[str, NotificationChannel] = {}

        for channel in channels or ():
            self.register_channel(channel)

    def register_channel(self, channel: NotificationChannel) -> None:
        channel_name = _get_channel_name(channel)
        if channel_name in self._channels:
            raise ValueError(f"channel already registered: {channel_name}")
        self._channels[channel_name] = channel

    @property
    def channel_names(self) -> tuple[str, ...]:
        return tuple(sorted(self._channels))

    def dispatch(self, event: AlertEvent) -> AlertDispatchResult:
        deliveries = tuple(
            self._deliver_to_channel(channel_name=channel_name, event=event)
            for channel_name in self.channel_names
        )
        return AlertDispatchResult(event_id=event.event_id, deliveries=deliveries)

    def _deliver_to_channel(
        self,
        *,
        channel_name: str,
        event: AlertEvent,
    ) -> ChannelDeliveryResult:
        try:
            self._channels[channel_name].deliver(event)
        except Exception as error:
            return ChannelDeliveryResult(
                channel_name=channel_name,
                delivered=False,
                error=_format_exception(error),
            )
        return ChannelDeliveryResult(channel_name=channel_name, delivered=True)


def _get_channel_name(channel: NotificationChannel) -> str:
    channel_name = getattr(channel, "channel_name", None)
    if not isinstance(channel_name, str) or not channel_name:
        raise ValueError("registered notification channels must define a non-empty channel_name")
    return channel_name


def _format_exception(error: Exception) -> str:
    message = str(error)
    if message:
        return f"{type(error).__name__}: {message}"
    return type(error).__name__


__all__ = [
    "AlertDispatcher",
    "AlertDispatchResult",
    "ChannelDeliveryResult",
]

"""Deterministic alert routing primitives.

The router dispatches validated ``AlertEvent`` instances to registered channels
without depending on any concrete notification integration.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Protocol

from .alert_models import AlertEvent


class AlertChannel(Protocol):
    """Minimal channel contract for router dispatch."""

    channel_name: str

    def dispatch(self, event: AlertEvent) -> None:
        """Handle a routed alert event."""


class AlertRouter:
    """Routes alert events to registered channels in a deterministic order."""

    def __init__(self, channels: Iterable[AlertChannel] | None = None) -> None:
        self._channels: dict[str, AlertChannel] = {}
        for channel in channels or ():
            self.register_channel(channel)

    def register_channel(self, channel: AlertChannel) -> None:
        channel_name = _get_channel_name(channel)
        if channel_name in self._channels:
            raise ValueError(f"channel already registered: {channel_name}")
        self._channels[channel_name] = channel

    @property
    def channel_names(self) -> tuple[str, ...]:
        return tuple(sorted(self._channels))

    def route(self, event: AlertEvent) -> tuple[str, ...]:
        dispatched_channels: list[str] = []
        for channel_name in self.channel_names:
            self._channels[channel_name].dispatch(event)
            dispatched_channels.append(channel_name)
        return tuple(dispatched_channels)


def _get_channel_name(channel: AlertChannel) -> str:
    channel_name = getattr(channel, "channel_name", None)
    if not isinstance(channel_name, str) or not channel_name:
        raise ValueError("registered alert channels must define a non-empty channel_name")
    return channel_name


__all__ = ["AlertChannel", "AlertRouter"]

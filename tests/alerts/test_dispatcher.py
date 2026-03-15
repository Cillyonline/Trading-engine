from __future__ import annotations

from dataclasses import dataclass, field
from threading import Event

import pytest

from cilly_trading.alerts.alert_dispatcher import AlertDispatcher
from cilly_trading.alerts.alert_models import AlertEvent, create_alert_event


@dataclass
class RecordingNotificationChannel:
    channel_name: str
    received_events: list[AlertEvent] = field(default_factory=list)
    delivered: Event = field(default_factory=Event)

    def deliver(self, event: AlertEvent) -> None:
        self.received_events.append(event)
        self.delivered.set()


@dataclass
class FailingNotificationChannel:
    channel_name: str
    error_message: str = "delivery failed"

    def deliver(self, event: AlertEvent) -> None:
        raise RuntimeError(self.error_message)


def _event_fixture() -> AlertEvent:
    return create_alert_event(
        event_type="runtime.guard_triggered",
        source_type="runtime",
        source_id="guard-17",
        severity="warning",
        occurred_at="2024-01-01T10:30:00Z",
        payload={"guard": "position_limit", "triggered": True},
    )


def test_dispatcher_registers_channels_by_name() -> None:
    email = RecordingNotificationChannel(channel_name="email")
    slack = RecordingNotificationChannel(channel_name="slack")

    dispatcher = AlertDispatcher()
    dispatcher.register_channel(slack)
    dispatcher.register_channel(email)

    assert dispatcher.channel_names == ("email", "slack")


def test_dispatcher_rejects_duplicate_channel_registration() -> None:
    dispatcher = AlertDispatcher()
    dispatcher.register_channel(RecordingNotificationChannel(channel_name="email"))

    with pytest.raises(ValueError, match="already registered"):
        dispatcher.register_channel(RecordingNotificationChannel(channel_name="email"))


def test_dispatcher_delivers_alerts_to_registered_channels() -> None:
    email = RecordingNotificationChannel(channel_name="email")
    slack = RecordingNotificationChannel(channel_name="slack")
    dispatcher = AlertDispatcher(channels=[slack, email])
    event = _event_fixture()

    result = dispatcher.dispatch(event)

    assert result.delivered_channels == ("email", "slack")
    assert result.failed_channels == ()
    assert result.has_failures is False
    assert email.received_events == [event]
    assert slack.received_events == [event]


def test_dispatcher_records_failures_without_stopping_other_deliveries() -> None:
    email = RecordingNotificationChannel(channel_name="email")
    pagerduty = FailingNotificationChannel(channel_name="pagerduty", error_message="api unavailable")
    slack = RecordingNotificationChannel(channel_name="slack")
    dispatcher = AlertDispatcher(channels=[pagerduty, slack, email])

    result = dispatcher.dispatch(_event_fixture())

    assert result.delivered_channels == ("email", "slack")
    assert result.failed_channels == ("pagerduty",)
    assert result.has_failures is True
    assert [delivery.error for delivery in result.deliveries] == [
        None,
        "RuntimeError: api unavailable",
        None,
    ]
    assert email.delivered.is_set()
    assert slack.delivered.is_set()


def test_dispatcher_continues_after_failed_channel_in_deterministic_order() -> None:
    email = RecordingNotificationChannel(channel_name="email")
    pagerduty = FailingNotificationChannel(channel_name="pagerduty", error_message="api unavailable")
    slack = RecordingNotificationChannel(channel_name="slack")

    result = AlertDispatcher(channels=[slack, pagerduty, email]).dispatch(_event_fixture())

    assert [delivery.channel_name for delivery in result.deliveries] == [
        "email",
        "pagerduty",
        "slack",
    ]
    assert result.delivered_channels == ("email", "slack")
    assert result.failed_channels == ("pagerduty",)
    assert email.received_events
    assert slack.received_events


def test_dispatcher_returns_empty_result_when_no_channels_registered() -> None:
    result = AlertDispatcher().dispatch(_event_fixture())

    assert result.deliveries == ()
    assert result.delivered_channels == ()
    assert result.failed_channels == ()

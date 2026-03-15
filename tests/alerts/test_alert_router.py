from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from cilly_trading.alerts import AlertEvent, AlertRouter, create_alert_event


@dataclass
class RecordingChannel:
    channel_name: str
    received_events: list[AlertEvent] = field(default_factory=list)

    def dispatch(self, event: AlertEvent) -> None:
        self.received_events.append(event)


def _event_fixture() -> AlertEvent:
    return create_alert_event(
        event_type="runtime.guard_triggered",
        source_type="runtime",
        source_id="guard-17",
        severity="warning",
        occurred_at="2024-01-01T10:30:00Z",
        payload={"guard": "position_limit", "triggered": True},
    )


def test_alert_router_registers_channels_by_name() -> None:
    email = RecordingChannel(channel_name="email")
    slack = RecordingChannel(channel_name="slack")

    router = AlertRouter()
    router.register_channel(slack)
    router.register_channel(email)

    assert router.channel_names == ("email", "slack")


def test_alert_router_rejects_duplicate_channel_registration() -> None:
    router = AlertRouter()
    router.register_channel(RecordingChannel(channel_name="email"))

    with pytest.raises(ValueError, match="already registered"):
        router.register_channel(RecordingChannel(channel_name="email"))


def test_alert_router_dispatches_event_to_registered_channels() -> None:
    email = RecordingChannel(channel_name="email")
    slack = RecordingChannel(channel_name="slack")
    router = AlertRouter(channels=[slack, email])
    event = _event_fixture()

    dispatched = router.route(event)

    assert dispatched == ("email", "slack")
    assert email.received_events == [event]
    assert slack.received_events == [event]


def test_alert_router_routing_order_is_deterministic_across_registration_order() -> None:
    event = _event_fixture()
    first_router = AlertRouter(
        channels=[
            RecordingChannel(channel_name="pagerduty"),
            RecordingChannel(channel_name="email"),
            RecordingChannel(channel_name="slack"),
        ]
    )
    second_router = AlertRouter(
        channels=[
            RecordingChannel(channel_name="slack"),
            RecordingChannel(channel_name="pagerduty"),
            RecordingChannel(channel_name="email"),
        ]
    )

    first_dispatch = first_router.route(event)
    second_dispatch = second_router.route(event)

    assert first_dispatch == ("email", "pagerduty", "slack")
    assert second_dispatch == first_dispatch


def test_alert_router_returns_empty_dispatch_when_no_channels_registered() -> None:
    router = AlertRouter()

    assert router.route(_event_fixture()) == ()

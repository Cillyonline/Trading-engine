"""Tests for engine runtime lifecycle controller."""

import pytest

from cilly_trading.engine.runtime_controller import (
    EngineRuntimeController,
    LifecycleTransitionError,
)


def test_valid_lifecycle_transitions_succeed() -> None:
    controller = EngineRuntimeController()

    assert controller.state == "init"
    assert controller.init() == "ready"
    assert controller.start() == "running"
    assert controller.shutdown() == "stopped"
    assert controller.state == "stopped"


def test_invalid_transitions_are_rejected() -> None:
    controller = EngineRuntimeController()

    with pytest.raises(LifecycleTransitionError):
        controller.start()

    assert controller.init() == "ready"

    with pytest.raises(LifecycleTransitionError):
        controller.init()

    assert controller.start() == "running"

    with pytest.raises(LifecycleTransitionError):
        controller.start()


def test_shutdown_is_idempotent_and_deterministic() -> None:
    controller = EngineRuntimeController()

    controller.init()
    controller.start()

    assert controller.shutdown() == "stopped"
    assert controller.shutdown() == "stopped"
    assert controller.state == "stopped"


def test_shutdown_before_running_is_rejected() -> None:
    controller = EngineRuntimeController()

    with pytest.raises(LifecycleTransitionError):
        controller.shutdown()

    controller.init()

    with pytest.raises(LifecycleTransitionError):
        controller.shutdown()

"""Deterministic tests for runtime lifecycle invariants."""

import pytest

import cilly_trading.engine.runtime_controller as runtime_controller_module
from cilly_trading.engine.invariants import (
    assert_can_init,
    assert_can_shutdown,
    assert_can_start,
    assert_postcondition_running,
)
from cilly_trading.engine.runtime_controller import LifecycleTransitionError


def test_illegal_start_transition_raises() -> None:
    with pytest.raises(
        LifecycleTransitionError,
        match=r"Cannot start\(\) while in state 'init'\. Expected 'ready'\.",
    ):
        assert_can_start("init")


def test_illegal_shutdown_transition_raises() -> None:
    with pytest.raises(
        LifecycleTransitionError,
        match=r"Cannot shutdown\(\) while in state 'ready'\. Expected 'running', 'stopping', or 'stopped'\.",
    ):
        assert_can_shutdown("ready")


def test_invalid_init_transition_raises() -> None:
    with pytest.raises(
        LifecycleTransitionError,
        match=r"Cannot init\(\) while in state 'running'\. Expected 'init'\.",
    ):
        assert_can_init("running")


def test_postcondition_failure_raises() -> None:
    with pytest.raises(
        LifecycleTransitionError,
        match=r"Cannot ensure running runtime from state 'stopped'\.",
    ):
        assert_postcondition_running("stopped")


def test_shutdown_from_stopping_calls_invariant_and_transitions() -> None:
    controller = runtime_controller_module.EngineRuntimeController()
    controller._state = "stopping"

    calls: list[str] = []

    def _spy_assert_can_shutdown(state: str) -> None:
        calls.append(state)
        assert state == "stopping"
        assert controller.state == "stopping"

    original_assert = runtime_controller_module.assert_can_shutdown
    runtime_controller_module.assert_can_shutdown = _spy_assert_can_shutdown
    try:
        assert controller.shutdown() == "stopped"
    finally:
        runtime_controller_module.assert_can_shutdown = original_assert

    assert calls == ["stopping"]
    assert controller.state == "stopped"

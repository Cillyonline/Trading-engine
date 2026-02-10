"""Tests for engine runtime lifecycle controller."""

import pytest

from cilly_trading.engine.runtime_controller import (
    EngineRuntimeController,
    LifecycleTransitionError,
    _reset_runtime_controller_for_tests,
    get_runtime_controller,
    shutdown_engine_runtime,
    start_engine_runtime,
)


@pytest.fixture(autouse=True)
def _reset_runtime_singleton() -> None:
    _reset_runtime_controller_for_tests()


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


def test_process_runtime_is_singleton_and_started_once() -> None:
    runtime_a = get_runtime_controller()
    runtime_b = get_runtime_controller()

    assert runtime_a is runtime_b
    assert runtime_a.state == "init"

    assert start_engine_runtime() == "running"
    assert start_engine_runtime() == "running"
    assert runtime_a.state == "running"


def test_process_runtime_shutdown_is_best_effort() -> None:
    runtime = get_runtime_controller()

    assert shutdown_engine_runtime() == "init"
    assert runtime.state == "init"

    start_engine_runtime()
    assert shutdown_engine_runtime() == "stopped"
    assert shutdown_engine_runtime() == "stopped"
    assert runtime.state == "stopped"

"""Lifecycle invariant assertions for engine runtime state transitions."""

from __future__ import annotations


def _lifecycle_transition_error(message: str) -> RuntimeError:
    try:
        from cilly_trading.engine.runtime_controller import LifecycleTransitionError

        return LifecycleTransitionError(message)
    except (ImportError, AttributeError):
        return RuntimeError(message)


def assert_can_init(state: str) -> None:
    """Assert that runtime can transition through ``init()``."""

    if state != "init":
        raise _lifecycle_transition_error(
            f"Cannot init() while in state '{state}'. Expected 'init'."
        )


def assert_can_start(state: str) -> None:
    """Assert that runtime can transition through ``start()``."""

    if state != "ready":
        raise _lifecycle_transition_error(
            f"Cannot start() while in state '{state}'. Expected 'ready'."
        )


def assert_can_shutdown(state: str) -> None:
    """Assert that runtime can transition through ``shutdown()``."""

    if state not in {"running", "stopping", "stopped"}:
        raise _lifecycle_transition_error(
            f"Cannot shutdown() while in state '{state}'. Expected 'running', 'stopping', or 'stopped'."
        )


def assert_postcondition_running(state: str) -> None:
    """Assert process runtime has reached the required ``running`` state."""

    if state != "running":
        raise _lifecycle_transition_error(
            f"Cannot ensure running runtime from state '{state}'."
        )

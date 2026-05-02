"""Runtime lifecycle controller for the engine domain."""

from __future__ import annotations

from dataclasses import dataclass, field
from threading import Lock
from typing import Final

from cilly_trading.engine.invariants import (
    assert_can_init,
    assert_can_shutdown,
    assert_can_start,
    assert_postcondition_running,
)


class LifecycleTransitionError(RuntimeError):
    """Raised when a runtime lifecycle transition is not allowed."""


@dataclass
class EngineRuntimeController:
    """Controls lifecycle transitions for a single engine runtime instance.

    The lifecycle follows the contract order:
    ``init -> ready -> running <-> paused -> stopping -> stopped``.
    """

    _state: str = field(default="init", init=False)

    _STATE_ORDER: Final[tuple[str, ...]] = (
        "init",
        "ready",
        "running",
        "paused",
        "stopping",
        "stopped",
    )

    @property
    def state(self) -> str:
        """Return the current lifecycle state.

        Returns:
            str: Current lifecycle state.
        """

        return self._state

    def init(self) -> str:
        """Transition the runtime to the ``ready`` state.

        Returns:
            str: The resulting lifecycle state.

        Raises:
            LifecycleTransitionError: If called when not in ``init`` state.
        """

        assert_can_init(self._state)
        self._state = "ready"
        return self._state

    def start(self) -> str:
        """Transition the runtime to the ``running`` state.

        Returns:
            str: The resulting lifecycle state.

        Raises:
            LifecycleTransitionError: If called when not in ``ready`` state.
        """

        assert_can_start(self._state)
        self._state = "running"
        return self._state

    def shutdown(self) -> str:
        """Stop runtime execution safely and idempotently.

        When in ``running`` state this method deterministically performs:
        ``running -> stopping -> stopped``.

        Returns:
            str: The resulting lifecycle state.

        Raises:
            LifecycleTransitionError: If called before runtime reaches ``running``.
        """

        if self._state == "paused":
            self._state = "stopped"
            return self._state

        assert_can_shutdown(self._state)

        if self._state == "stopped":
            return self._state

        if self._state == "stopping":
            self._state = "stopped"
            return self._state

        self._state = "stopping"
        self._state = "stopped"
        return self._state

    def pause_execution(self) -> str:
        """Pause execution while keeping runtime initialized."""

        if self._state == "paused":
            return self._state

        if self._state != "running":
            raise LifecycleTransitionError(
                f"Cannot pause_execution() while in state '{self._state}'. Expected 'running' or 'paused'."
            )

        self._state = "paused"
        return self._state

    def resume_execution(self) -> str:
        """Resume execution after an operator pause."""

        if self._state == "running":
            return self._state

        if self._state != "paused":
            raise LifecycleTransitionError(
                f"Cannot resume_execution() while in state '{self._state}'. Expected 'paused' or 'running'."
            )

        self._state = "running"
        return self._state


class RuntimeControllerRegistry:
    """Thread-safe registry for an EngineRuntimeController instance.

    Use this class directly when you need an isolated controller (e.g. in
    tests or multi-tenant scenarios) without relying on the process-wide
    singleton functions below.

    Example::

        registry = RuntimeControllerRegistry()
        registry.start()
        state = registry.get_controller().state
        registry.shutdown()
    """

    def __init__(self) -> None:
        self._lock: Lock = Lock()
        self._controller: EngineRuntimeController | None = None

    def _get_or_create(self) -> EngineRuntimeController:
        if self._controller is None:
            self._controller = EngineRuntimeController()
        return self._controller

    def get_controller(self) -> EngineRuntimeController:
        with self._lock:
            return self._get_or_create()

    def start(self) -> str:
        with self._lock:
            runtime = self._get_or_create()
            if runtime.state == "init":
                runtime.init()
            if runtime.state == "ready":
                runtime.start()
            assert_postcondition_running(runtime.state)
            return runtime.state

    def shutdown(self) -> str:
        with self._lock:
            runtime = self._get_or_create()
            if runtime.state in {"init", "ready"}:
                return runtime.state
            return runtime.shutdown()

    def pause(self) -> str:
        with self._lock:
            return self._get_or_create().pause_execution()

    def resume(self) -> str:
        with self._lock:
            return self._get_or_create().resume_execution()

    def reset(self) -> None:
        """Reset the controller to a fresh ``init`` state."""
        with self._lock:
            self._controller = None


# ---------------------------------------------------------------------------
# Process-wide singleton — kept for backward compatibility.
# Prefer injecting a RuntimeControllerRegistry instance instead.
# ---------------------------------------------------------------------------

_REGISTRY: Final[RuntimeControllerRegistry] = RuntimeControllerRegistry()


def get_runtime_controller() -> EngineRuntimeController:
    """Return the single process-wide runtime controller owned by the engine."""
    return _REGISTRY.get_controller()


def start_engine_runtime() -> str:
    """Initialize and start the process-wide engine runtime."""
    return _REGISTRY.start()


def shutdown_engine_runtime() -> str:
    """Best-effort shutdown for the process-wide engine runtime."""
    return _REGISTRY.shutdown()


def pause_engine_runtime() -> str:
    """Pause execution for the process-wide runtime."""
    return _REGISTRY.pause()


def resume_engine_runtime() -> str:
    """Resume execution for the process-wide runtime."""
    return _REGISTRY.resume()


def _reset_runtime_controller_for_tests() -> None:
    """Reset process-wide runtime controller singleton for test isolation."""
    _REGISTRY.reset()

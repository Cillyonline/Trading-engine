"""Runtime lifecycle controller for the engine domain."""

from __future__ import annotations

from dataclasses import dataclass, field
from threading import Lock
from typing import Final


class LifecycleTransitionError(RuntimeError):
    """Raised when a runtime lifecycle transition is not allowed."""


@dataclass
class EngineRuntimeController:
    """Controls lifecycle transitions for a single engine runtime instance.

    The lifecycle follows the contract order:
    ``init -> ready -> running -> stopping -> stopped``.
    """

    _state: str = field(default="init", init=False)

    _STATE_ORDER: Final[tuple[str, ...]] = (
        "init",
        "ready",
        "running",
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

        self._assert_state("init", action="init")
        self._state = "ready"
        return self._state

    def start(self) -> str:
        """Transition the runtime to the ``running`` state.

        Returns:
            str: The resulting lifecycle state.

        Raises:
            LifecycleTransitionError: If called when not in ``ready`` state.
        """

        self._assert_state("ready", action="start")
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

        if self._state == "stopped":
            return self._state

        if self._state == "stopping":
            self._state = "stopped"
            return self._state

        if self._state != "running":
            raise LifecycleTransitionError(
                f"Cannot shutdown() while in state '{self._state}'. Expected 'running', 'stopping', or 'stopped'."
            )

        self._state = "stopping"
        self._state = "stopped"
        return self._state

    def _assert_state(self, expected: str, *, action: str) -> None:
        """Validate current state for transition actions.

        Args:
            expected: Required current state.
            action: Action being executed.

        Raises:
            LifecycleTransitionError: If current state does not match expected.
        """

        if self._state != expected:
            raise LifecycleTransitionError(
                f"Cannot {action}() while in state '{self._state}'. Expected '{expected}'."
            )


_RUNTIME_LOCK: Final[Lock] = Lock()
_RUNTIME_CONTROLLER: EngineRuntimeController | None = None


def _get_or_create_runtime_controller() -> EngineRuntimeController:
    global _RUNTIME_CONTROLLER

    if _RUNTIME_CONTROLLER is None:
        _RUNTIME_CONTROLLER = EngineRuntimeController()

    return _RUNTIME_CONTROLLER


def get_runtime_controller() -> EngineRuntimeController:
    """Return the single process-wide runtime controller owned by the engine."""

    with _RUNTIME_LOCK:
        return _get_or_create_runtime_controller()


def start_engine_runtime() -> str:
    """Initialize and start the process-wide engine runtime."""

    with _RUNTIME_LOCK:
        runtime = _get_or_create_runtime_controller()

        if runtime.state == "init":
            runtime.init()

        if runtime.state == "ready":
            runtime.start()

        if runtime.state != "running":
            raise LifecycleTransitionError(
                f"Cannot ensure running runtime from state '{runtime.state}'."
            )

        return runtime.state


def shutdown_engine_runtime() -> str:
    """Best-effort shutdown for the process-wide engine runtime."""

    with _RUNTIME_LOCK:
        runtime = _get_or_create_runtime_controller()

        if runtime.state in {"init", "ready"}:
            return runtime.state

        return runtime.shutdown()


def _reset_runtime_controller_for_tests() -> None:
    """Reset process-wide runtime controller singleton for test isolation."""

    global _RUNTIME_CONTROLLER

    with _RUNTIME_LOCK:
        _RUNTIME_CONTROLLER = None

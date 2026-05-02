"""Thread-safe circuit breaker for external data sources.

States:
  closed   → normal operation, calls pass through
  open     → too many recent failures, calls are rejected immediately
  half-open → cooldown expired, next call is a probe; success closes, failure re-opens
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Callable, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


class CircuitOpenError(RuntimeError):
    """Raised when a circuit is open and the call is rejected."""


@dataclass
class CircuitBreaker:
    """Circuit breaker with configurable failure threshold and cooldown.

    Args:
        name: Human-readable label used in log messages.
        max_failures: Consecutive failures before the circuit opens.
        cooldown_s: Seconds to wait in open state before allowing a probe.
        call_timeout_s: Per-call wall-clock timeout enforced via a thread.
    """

    name: str
    max_failures: int = 3
    cooldown_s: float = 60.0
    call_timeout_s: float = 30.0

    _failures: int = field(default=0, init=False, repr=False)
    _opened_at: float | None = field(default=None, init=False, repr=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False, repr=False)

    @property
    def state(self) -> str:
        with self._lock:
            return self._state_unlocked()

    def _state_unlocked(self) -> str:
        if self._opened_at is None:
            return "closed"
        if time.monotonic() - self._opened_at >= self.cooldown_s:
            return "half-open"
        return "open"

    def call(self, fn: Callable[..., T], *args: object, **kwargs: object) -> T:
        """Execute *fn* with circuit-breaker protection and timeout.

        Raises:
            CircuitOpenError: When the circuit is open (too many recent failures).
            TimeoutError: When the call exceeds *call_timeout_s*.
            Any exception raised by *fn* itself.
        """
        with self._lock:
            state = self._state_unlocked()
            if state == "open":
                raise CircuitOpenError(
                    f"Circuit '{self.name}' is open after {self._failures} failures; "
                    f"retry in {self.cooldown_s - (time.monotonic() - self._opened_at):.0f}s"
                )
            if state == "half-open":
                logger.info("Circuit '%s' probing after cooldown.", self.name)
                self._opened_at = None

        result: list[T] = []
        exc: list[BaseException] = []

        def _run() -> None:
            try:
                result.append(fn(*args, **kwargs))
            except BaseException as e:
                exc.append(e)

        thread = threading.Thread(target=_run, daemon=True)
        thread.start()
        thread.join(timeout=self.call_timeout_s)

        if thread.is_alive():
            self._record_failure()
            raise TimeoutError(
                f"Circuit '{self.name}': call timed out after {self.call_timeout_s}s"
            )

        if exc:
            self._record_failure()
            raise exc[0]

        self._record_success()
        return result[0]

    def _record_success(self) -> None:
        with self._lock:
            if self._failures > 0:
                logger.info("Circuit '%s' recovered after success.", self.name)
            self._failures = 0
            self._opened_at = None

    def _record_failure(self) -> None:
        with self._lock:
            self._failures += 1
            if self._failures >= self.max_failures and self._opened_at is None:
                self._opened_at = time.monotonic()
                logger.warning(
                    "Circuit '%s' opened after %d consecutive failures.",
                    self.name,
                    self._failures,
                )

    def reset(self) -> None:
        """Reset circuit to closed state (for tests or manual recovery)."""
        with self._lock:
            self._failures = 0
            self._opened_at = None

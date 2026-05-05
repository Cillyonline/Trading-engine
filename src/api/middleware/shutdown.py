"""In-flight request tracking + graceful shutdown drain (issue #1133).

When a process receives ``SIGTERM`` (Kubernetes rolling update,
``docker stop``, etc.), Uvicorn invokes the FastAPI lifespan shutdown
hook before tearing down the worker. Without coordination, in-flight
requests are abandoned mid-flight, which can corrupt SQLite writes or
truncate analysis runs.

This module provides two pieces:

* :class:`InFlightRequestTracker` — a small async-safe counter with an
  ``await drain(timeout)`` helper that waits until no requests remain.
* :class:`GracefulShutdownMiddleware` — increments the tracker around
  every HTTP request and, once shutdown has begun, refuses *new*
  requests with a deterministic ``503 service_shutting_down`` response
  so that load balancers stop routing traffic instead of failing
  unpredictably.

The shutdown flag is decoupled from the tracker (see
``signal_shutdown_started``) so that test harnesses constructing a fresh
``TestClient`` without entering the lifespan never inherit a stale
"shutting_down" state from a previous test that did exit it.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Callable, Optional

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from .request_id import REQUEST_ID_HEADER, current_request_id


logger = logging.getLogger(__name__)

DEFAULT_SHUTDOWN_DRAIN_TIMEOUT_S = 30.0


class InFlightRequestTracker:
    """Async-safe in-flight request counter with a drain primitive."""

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._idle_event = asyncio.Event()
        self._idle_event.set()
        self._in_flight = 0

    @property
    def in_flight(self) -> int:
        return self._in_flight

    def reset(self) -> None:
        """Reset state for a fresh lifespan (idempotent)."""

        self._in_flight = 0
        self._idle_event.set()

    async def acquire(self) -> None:
        async with self._lock:
            self._in_flight += 1
            self._idle_event.clear()

    async def release(self) -> None:
        async with self._lock:
            self._in_flight = max(0, self._in_flight - 1)
            if self._in_flight == 0:
                self._idle_event.set()

    async def drain(self, timeout_s: float = DEFAULT_SHUTDOWN_DRAIN_TIMEOUT_S) -> bool:
        """Wait until in-flight requests reach zero or ``timeout_s`` elapses.

        Returns ``True`` if the queue drained, ``False`` on timeout. Safe
        to call multiple times.
        """

        if self._in_flight == 0:
            return True
        try:
            await asyncio.wait_for(self._idle_event.wait(), timeout=timeout_s)
            return True
        except asyncio.TimeoutError:
            logger.warning(
                "graceful_shutdown_drain_timeout",
                extra={
                    "in_flight": self._in_flight,
                    "timeout_s": timeout_s,
                },
            )
            return False


class GracefulShutdownMiddleware:
    """Tracks in-flight requests and rejects new traffic after SIGTERM."""

    def __init__(
        self,
        app: ASGIApp,
        *,
        tracker: Optional[InFlightRequestTracker] = None,
        is_shutting_down: Optional[Callable[[], bool]] = None,
    ) -> None:
        self.app = app
        self.tracker = tracker if tracker is not None else InFlightRequestTracker()
        # By default the middleware is never in shutdown mode unless an
        # explicit predicate (typically wired by the runtime lifecycle)
        # signals that drain has started.
        self._is_shutting_down: Callable[[], bool] = (
            is_shutting_down if is_shutting_down is not None else (lambda: False)
        )

    @property
    def shutting_down(self) -> bool:
        return self._is_shutting_down()

    def signal_shutdown_started(self) -> None:
        """Force the middleware into reject-new-traffic mode (test helper)."""

        self._is_shutting_down = lambda: True

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "") or ""

        # Continue serving liveness probes during drain so orchestrators can
        # observe the in-progress shutdown rather than mark the pod as dead.
        if self._is_shutting_down() and path != "/health/live":
            request_id = current_request_id() or ""
            payload = {
                "detail": "service_shutting_down",
                "request_id": request_id,
            }
            response = JSONResponse(status_code=503, content=payload)
            response.headers["Connection"] = "close"
            response.headers["Retry-After"] = "5"
            if request_id:
                response.headers[REQUEST_ID_HEADER] = request_id
            await response(scope, receive, send)
            return

        await self.tracker.acquire()
        try:
            await self.app(scope, receive, send)
        finally:
            await self.tracker.release()

"""Per-request timeout middleware.

Caps the wall-clock duration of any single HTTP request to protect the
server against slow-client attacks, hung downstream calls and runaway
analysis jobs. Long-running endpoints such as ``/analysis/run`` are given
a higher budget than fast read-only endpoints; ``/health/*`` calls fail
fast so that orchestrators can rotate unhealthy pods quickly.

When a request exceeds its budget, the middleware returns a deterministic
``504 Gateway Timeout`` JSON response with the same envelope shape used by
the rest of the API (``{"detail", "request_id"}``) and an
``X-Request-Timeout`` header carrying the configured limit in seconds.

The middleware is conservative by design:

* The only non-request-scoped state is the per-instance route table.
* Timeouts are applied via :func:`asyncio.wait_for`, which cancels the
  pending task; downstream handlers must therefore be cancellation-safe.
* Health-probe paths are always honoured, even when the operator
  configures longer global defaults, because Kubernetes liveness probes
  must not be allowed to wait the full default budget.
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Iterable

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from .request_id import REQUEST_ID_HEADER, current_request_id


logger = logging.getLogger(__name__)


# Default per-prefix timeouts, in seconds.
# Order matters: the *first* prefix matching the request path is used.
# Tuned per issue #1130.
DEFAULT_PATH_TIMEOUTS: tuple[tuple[str, float], ...] = (
    ("/health", 5.0),
    ("/analysis/run", 60.0),
    ("/strategy/analyze", 60.0),
    ("/screener", 30.0),
    ("/watchlists", 30.0),
)

# Fallback for any path not matched above.
DEFAULT_REQUEST_TIMEOUT_S = 30.0


def _read_float_env(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return default
    if value <= 0:
        return default
    return value


def resolve_default_timeout() -> float:
    """Resolve the catch-all timeout, honouring ``CILLY_REQUEST_TIMEOUT_S``."""

    return _read_float_env("CILLY_REQUEST_TIMEOUT_S", DEFAULT_REQUEST_TIMEOUT_S)


class RequestTimeoutMiddleware:
    """ASGI middleware enforcing a wall-clock budget per HTTP request."""

    def __init__(
        self,
        app: ASGIApp,
        *,
        default_timeout_s: float | None = None,
        path_timeouts: Iterable[tuple[str, float]] | None = None,
    ) -> None:
        self.app = app
        self._default_timeout_s = (
            default_timeout_s if default_timeout_s is not None else resolve_default_timeout()
        )
        # Sort by descending prefix length so that more specific prefixes
        # (e.g. ``/analysis/run``) win over shorter ones (e.g. ``/``).
        configured = (
            tuple(path_timeouts) if path_timeouts is not None else DEFAULT_PATH_TIMEOUTS
        )
        self._path_timeouts: tuple[tuple[str, float], ...] = tuple(
            sorted(configured, key=lambda item: len(item[0]), reverse=True)
        )

    def _resolve_timeout(self, path: str) -> float:
        for prefix, budget in self._path_timeouts:
            if path.startswith(prefix):
                return budget
        return self._default_timeout_s

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "") or ""
        timeout_s = self._resolve_timeout(path)

        response_started = False

        async def _send(message: Message) -> None:
            nonlocal response_started
            if message["type"] == "http.response.start":
                response_started = True
            await send(message)

        try:
            await asyncio.wait_for(
                self.app(scope, receive, _send),
                timeout=timeout_s,
            )
        except asyncio.TimeoutError:
            if response_started:
                # The handler already flushed headers; we cannot replace the
                # response body, so we simply log and let the connection
                # close. Returning normally keeps the ASGI contract intact.
                logger.warning(
                    "request_timeout_after_response_started",
                    extra={
                        "path": path,
                        "timeout_s": timeout_s,
                        "request_id": current_request_id() or "-",
                    },
                )
                return
            request_id = current_request_id() or ""
            payload = {"detail": "request_timeout", "request_id": request_id}
            response = JSONResponse(status_code=504, content=payload)
            response.headers["X-Request-Timeout"] = f"{timeout_s:.3f}"
            if request_id:
                response.headers[REQUEST_ID_HEADER] = request_id
            logger.warning(
                "request_timeout",
                extra={
                    "path": path,
                    "timeout_s": timeout_s,
                    "request_id": request_id or "-",
                },
            )
            await response(scope, receive, send)

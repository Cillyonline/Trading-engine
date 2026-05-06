"""Request-ID middleware and structured-logging integration.

Each incoming request either carries an ``X-Request-ID`` header or is
assigned a freshly generated UUID4 by :class:`RequestIdMiddleware`. The
resulting identifier is:

* exposed to downstream code via :data:`request_id_var` (a
  :class:`contextvars.ContextVar`), so that any log records emitted while
  handling the request automatically include it via :class:`RequestIdLogFilter`;
* echoed back to the client in the ``X-Request-ID`` response header; and
* injected into the JSON body of structured error responses produced by the
  global exception handlers in :mod:`api.main`.
"""

from __future__ import annotations

import logging
import uuid
from contextvars import ContextVar
from typing import Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp


REQUEST_ID_HEADER = "X-Request-ID"

# ContextVar holding the request id for the duration of an in-flight
# request. ``None`` outside any request scope (e.g. background startup).
request_id_var: ContextVar[Optional[str]] = ContextVar("cilly_request_id", default=None)


def current_request_id() -> Optional[str]:
    """Return the request id bound to the current async/task context, if any."""

    return request_id_var.get()


def _looks_like_valid_request_id(value: str) -> bool:
    """Lightweight validation for incoming ``X-Request-ID`` headers."""

    stripped = value.strip()
    if not stripped or len(stripped) > 200:
        return False
    # Allow a permissive but safe charset: alphanumerics, dashes,
    # underscores, dots and colons. This rejects whitespace, control
    # characters, and header-injection attempts via CR/LF.
    return all(ch.isalnum() or ch in "-_.:" for ch in stripped)


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Bind a request id to each request and echo it on the response."""

    def __init__(self, app: ASGIApp, header_name: str = REQUEST_ID_HEADER) -> None:
        super().__init__(app)
        self.header_name = header_name

    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        incoming = request.headers.get(self.header_name)
        if incoming and _looks_like_valid_request_id(incoming):
            request_id = incoming.strip()
        else:
            request_id = str(uuid.uuid4())

        token = request_id_var.set(request_id)
        # Make the id available on ``request.state`` for downstream handlers
        # that prefer not to import the contextvar directly.
        request.state.request_id = request_id
        try:
            response: Response = await call_next(request)
        finally:
            request_id_var.reset(token)

        response.headers[self.header_name] = request_id
        return response


class RequestIdLogFilter(logging.Filter):
    """Logging filter that attaches ``request_id`` to every log record."""

    def filter(self, record: logging.LogRecord) -> bool:  # noqa: D401 - logging API
        record.request_id = current_request_id() or "-"
        return True


def install_request_id_log_filter(logger: Optional[logging.Logger] = None) -> RequestIdLogFilter:
    """Install :class:`RequestIdLogFilter` on the given logger (root by default).

    Returns the installed filter instance. Safe to call repeatedly: only one
    filter of this type is installed per logger.
    """

    target = logger if logger is not None else logging.getLogger()
    for existing in target.filters:
        if isinstance(existing, RequestIdLogFilter):
            return existing
    log_filter = RequestIdLogFilter()
    target.addFilter(log_filter)
    # Also install on every existing handler so that handler-level
    # formatters can reference ``%(request_id)s`` reliably.
    for handler in target.handlers:
        if not any(isinstance(f, RequestIdLogFilter) for f in handler.filters):
            handler.addFilter(log_filter)
    return log_filter

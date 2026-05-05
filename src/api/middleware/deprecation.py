"""Deprecation header middleware for legacy un-versioned API paths.

Issue #1135 introduces a ``/v1`` mount alongside the existing root-level
URLs. Clients hitting the legacy path receive a ``Deprecation: true``
response header plus a ``Sunset`` hint, so monitoring/log-tail tooling
can flag stragglers without breaking them.
"""

from __future__ import annotations

from typing import Iterable

from starlette.types import ASGIApp, Message, Receive, Scope, Send


# RFC 8594 / RFC 9745 hint. Choose a far-enough date so we don't have to
# bump it for every release; the header is informational only.
DEFAULT_SUNSET_DATE = "Sun, 01 Jan 2028 00:00:00 GMT"

# Path prefixes that are *not* part of the versioned API surface. Hits to
# these paths must NOT carry the deprecation header.
_NON_API_PREFIXES: tuple[str, ...] = (
    "/ui",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/favicon.ico",
    "/static",
)


class LegacyApiDeprecationMiddleware:
    """Tag responses on legacy un-versioned API paths with deprecation hints."""

    def __init__(
        self,
        app: ASGIApp,
        *,
        version_prefix: str = "/v1",
        sunset_date: str = DEFAULT_SUNSET_DATE,
        non_api_prefixes: Iterable[str] = _NON_API_PREFIXES,
    ) -> None:
        self.app = app
        self._version_prefix = version_prefix.rstrip("/")
        self._sunset_date = sunset_date
        self._non_api_prefixes = tuple(non_api_prefixes)

    def _should_tag(self, path: str) -> bool:
        if not path or path == "/":
            return False
        if path.startswith(self._version_prefix + "/") or path == self._version_prefix:
            return False
        for prefix in self._non_api_prefixes:
            if path.startswith(prefix):
                return False
        return True

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "") or ""
        if not self._should_tag(path):
            await self.app(scope, receive, send)
            return

        link_target = f"<{self._version_prefix}{path}>; rel=\"successor-version\""
        sunset = self._sunset_date

        async def _send(message: Message) -> None:
            if message["type"] == "http.response.start":
                # Headers are a list of (bytes, bytes) tuples in ASGI.
                headers = list(message.get("headers", []))
                headers.append((b"deprecation", b"true"))
                headers.append((b"sunset", sunset.encode("latin-1")))
                headers.append((b"link", link_target.encode("latin-1")))
                message = {**message, "headers": headers}
            await send(message)

        await self.app(scope, receive, _send)

"""Domain-specific exception hierarchy for the Cilly Trading Engine.

These exceptions are mapped to HTTP responses by global FastAPI exception
handlers registered in ``api.main``:

* :class:`NotFoundError`   -> HTTP 404
* :class:`ConflictError`   -> HTTP 409
* :class:`ValidationError` -> HTTP 422

All concrete subclasses inherit from :class:`CillyError`, which carries a
human-readable ``detail`` string used as the response payload's ``detail``
field. The accompanying ``request_id`` field on the JSON response is added
by the FastAPI exception handler, sourced from the per-request context
variable populated by the request-id middleware.
"""

from __future__ import annotations


class CillyError(Exception):
    """Base class for all domain-level errors raised by the API layer."""

    #: HTTP status code used by the global exception handler when a more
    #: specific subclass is not matched.
    http_status_code: int = 500

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


class NotFoundError(CillyError):
    """Raised when a requested resource does not exist (HTTP 404)."""

    http_status_code = 404


class ValidationError(CillyError):
    """Raised when a request payload or referenced state is invalid (HTTP 422)."""

    http_status_code = 422


class ConflictError(CillyError):
    """Raised when a request conflicts with the current resource state (HTTP 409)."""

    http_status_code = 409


__all__ = [
    "CillyError",
    "NotFoundError",
    "ValidationError",
    "ConflictError",
]

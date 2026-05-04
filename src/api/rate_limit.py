"""Shared rate-limiter instance for the API.

Import this module to access the singleton Limiter and the exception handler
to register on the FastAPI app.  Using a single module-level instance ensures
all routers share the same in-process counter store.
"""

from __future__ import annotations

from slowapi import Limiter, _rate_limit_exceeded_handler  # noqa: F401  (re-exported)
from slowapi.errors import RateLimitExceeded  # noqa: F401  (re-exported)
from slowapi.util import get_remote_address

limiter: Limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[],
)

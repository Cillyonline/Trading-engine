from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _disable_rate_limit():
    """Disable slowapi rate limiting for all tests.

    The in-memory counter persists across the test session, so rate-limited
    endpoints (5/min) would return 429 after the fifth call — breaking any
    test suite that exercises those endpoints more than the limit allows.
    """
    try:
        from api.rate_limit import limiter
        limiter.enabled = False
        yield
        limiter.enabled = True
        limiter.reset()
    except Exception:
        yield

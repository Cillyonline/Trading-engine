"""Tests for graceful shutdown / in-flight drain (issue #1133)."""

from __future__ import annotations

import asyncio

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.middleware import (
    GracefulShutdownMiddleware,
    InFlightRequestTracker,
    RequestIdMiddleware,
)


# ---------------------------------------------------------------------------
# InFlightRequestTracker unit tests
# ---------------------------------------------------------------------------


def test_tracker_starts_idle() -> None:
    tracker = InFlightRequestTracker()
    assert tracker.in_flight == 0


def test_tracker_acquire_release_balances_counter() -> None:
    tracker = InFlightRequestTracker()

    async def _flow() -> None:
        await tracker.acquire()
        await tracker.acquire()
        assert tracker.in_flight == 2
        await tracker.release()
        await tracker.release()
        assert tracker.in_flight == 0

    asyncio.run(_flow())


def test_drain_returns_immediately_when_idle() -> None:
    tracker = InFlightRequestTracker()

    async def _flow() -> bool:
        return await tracker.drain(timeout_s=0.5)

    assert asyncio.run(_flow()) is True


def test_drain_waits_for_inflight_to_finish() -> None:
    tracker = InFlightRequestTracker()

    async def _flow() -> bool:
        await tracker.acquire()

        async def _release_after_delay() -> None:
            await asyncio.sleep(0.05)
            await tracker.release()

        asyncio.create_task(_release_after_delay())
        return await tracker.drain(timeout_s=2.0)

    assert asyncio.run(_flow()) is True
    assert tracker.in_flight == 0


def test_drain_times_out_when_requests_never_finish() -> None:
    tracker = InFlightRequestTracker()

    async def _flow() -> bool:
        await tracker.acquire()
        return await tracker.drain(timeout_s=0.05)

    assert asyncio.run(_flow()) is False


# ---------------------------------------------------------------------------
# Middleware integration tests
# ---------------------------------------------------------------------------


def _build_app(tracker: InFlightRequestTracker, *, shutting_down: bool = False) -> FastAPI:
    app = FastAPI()

    @app.get("/echo")
    async def echo() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/health/live")
    async def live() -> dict[str, str]:
        return {"status": "alive"}

    app.add_middleware(
        GracefulShutdownMiddleware,
        tracker=tracker,
        is_shutting_down=lambda: shutting_down,
    )
    app.add_middleware(RequestIdMiddleware)
    return app


def test_middleware_passes_through_when_not_shutting_down() -> None:
    tracker = InFlightRequestTracker()
    app = _build_app(tracker)
    with TestClient(app) as client:
        response = client.get("/echo")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    # After the request completes, the counter must return to zero.
    assert tracker.in_flight == 0


def test_middleware_rejects_new_traffic_after_shutdown_begins() -> None:
    tracker = InFlightRequestTracker()
    app = _build_app(tracker, shutting_down=True)
    with TestClient(app) as client:
        response = client.get("/echo")
    assert response.status_code == 503
    body = response.json()
    assert body["detail"] == "service_shutting_down"
    assert response.headers["Connection"] == "close"
    assert response.headers["Retry-After"] == "5"


def test_middleware_keeps_serving_health_live_during_shutdown() -> None:
    """Liveness probes must still return 200 so orchestrators don't kill -9."""

    tracker = InFlightRequestTracker()
    app = _build_app(tracker, shutting_down=True)
    with TestClient(app) as client:
        response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "alive"}


def test_drain_timeout_resolution_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    from api.composition.runtime_lifecycle import _resolve_drain_timeout

    monkeypatch.delenv("CILLY_SHUTDOWN_DRAIN_TIMEOUT_S", raising=False)
    assert _resolve_drain_timeout() == 30.0

    monkeypatch.setenv("CILLY_SHUTDOWN_DRAIN_TIMEOUT_S", "5.5")
    assert _resolve_drain_timeout() == 5.5

    monkeypatch.setenv("CILLY_SHUTDOWN_DRAIN_TIMEOUT_S", "garbage")
    assert _resolve_drain_timeout() == 30.0

    monkeypatch.setenv("CILLY_SHUTDOWN_DRAIN_TIMEOUT_S", "0")
    assert _resolve_drain_timeout() == 30.0


def test_app_state_exposes_inflight_tracker() -> None:
    """``api.main`` wires the tracker so the lifespan can drain it."""

    import api.main as api_main

    tracker = api_main.app.state.inflight_tracker
    assert isinstance(tracker, InFlightRequestTracker)

"""Tests for the per-request timeout middleware (issue #1130)."""

from __future__ import annotations

import asyncio

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.middleware import (
    REQUEST_ID_HEADER,
    RequestIdMiddleware,
    RequestTimeoutMiddleware,
)


def _build_app(*, default_timeout_s: float, path_timeouts=None) -> FastAPI:
    app = FastAPI()

    @app.get("/fast")
    async def fast() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/slow")
    async def slow() -> dict[str, str]:
        await asyncio.sleep(2.0)
        return {"status": "ok"}

    @app.get("/health/ready")
    async def health_ready() -> dict[str, str]:
        await asyncio.sleep(0.5)
        return {"status": "ok"}

    # Timeout must be installed BEFORE RequestIdMiddleware so that the
    # request id is bound when the timeout response is built.
    app.add_middleware(
        RequestTimeoutMiddleware,
        default_timeout_s=default_timeout_s,
        path_timeouts=path_timeouts,
    )
    app.add_middleware(RequestIdMiddleware)
    return app


def test_fast_request_completes_normally() -> None:
    app = _build_app(default_timeout_s=1.0)
    with TestClient(app) as client:
        response = client.get("/fast")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_slow_request_returns_504_with_envelope() -> None:
    app = _build_app(default_timeout_s=0.1)
    with TestClient(app) as client:
        response = client.get("/fast")
        assert response.status_code == 200  # baseline still works

        slow_response = client.get("/slow")

    assert slow_response.status_code == 504
    body = slow_response.json()
    assert body["detail"] == "request_timeout"
    assert "request_id" in body
    assert slow_response.headers["X-Request-Timeout"] == "0.100"
    # Request id must be propagated to the timeout response.
    assert slow_response.headers.get(REQUEST_ID_HEADER) == body["request_id"]
    assert body["request_id"]


def test_per_path_timeout_overrides_default() -> None:
    # Default 0.05 (everything times out), but /slow gets 5s budget.
    app = _build_app(
        default_timeout_s=0.05,
        path_timeouts=[("/slow", 5.0)],
    )
    with TestClient(app) as client:
        response = client.get("/slow")
    assert response.status_code == 200


def test_health_path_uses_short_default_budget() -> None:
    # Default 5s, but health/ready handler sleeps 0.5s — should pass.
    app = _build_app(default_timeout_s=10.0, path_timeouts=[("/health", 5.0)])
    with TestClient(app) as client:
        response = client.get("/health/ready")
    assert response.status_code == 200


def test_health_path_short_budget_times_out_when_handler_too_slow() -> None:
    app = _build_app(default_timeout_s=10.0, path_timeouts=[("/health", 0.05)])
    with TestClient(app) as client:
        response = client.get("/health/ready")
    assert response.status_code == 504
    assert response.json()["detail"] == "request_timeout"


def test_request_id_echoed_back_for_normal_responses() -> None:
    app = _build_app(default_timeout_s=5.0)
    with TestClient(app) as client:
        response = client.get(
            "/fast",
            headers={REQUEST_ID_HEADER: "abc-123"},
        )
    assert response.status_code == 200
    assert response.headers[REQUEST_ID_HEADER] == "abc-123"


@pytest.mark.parametrize(
    "path,expected_budget",
    [
        ("/health/live", 5.0),
        ("/health/ready", 5.0),
        ("/analysis/run", 60.0),
        ("/screener/basic", 30.0),
        ("/strategy/analyze", 60.0),
        ("/watchlists/foo", 30.0),
        ("/unknown", 30.0),  # default
    ],
)
def test_default_path_budgets(path: str, expected_budget: float) -> None:
    middleware = RequestTimeoutMiddleware(lambda *_: None)
    assert middleware._resolve_timeout(path) == expected_budget


def test_resolve_default_timeout_honours_env(monkeypatch: pytest.MonkeyPatch) -> None:
    from api.middleware.timeout import resolve_default_timeout

    monkeypatch.setenv("CILLY_REQUEST_TIMEOUT_S", "12.5")
    assert resolve_default_timeout() == 12.5

    monkeypatch.setenv("CILLY_REQUEST_TIMEOUT_S", "not-a-number")
    assert resolve_default_timeout() == 30.0

    monkeypatch.setenv("CILLY_REQUEST_TIMEOUT_S", "-1")
    assert resolve_default_timeout() == 30.0

    monkeypatch.delenv("CILLY_REQUEST_TIMEOUT_S")
    assert resolve_default_timeout() == 30.0

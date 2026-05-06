"""Tests for /v1 API versioning and legacy deprecation header (issue #1135)."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import api.main as api_main
from api.middleware import (
    DEFAULT_SUNSET_DATE,
    LegacyApiDeprecationMiddleware,
)
from cilly_trading.engine.runtime_controller import _reset_runtime_controller_for_tests


def setup_function() -> None:
    _reset_runtime_controller_for_tests()


def teardown_function() -> None:
    _reset_runtime_controller_for_tests()


# ---------------------------------------------------------------------------
# /v1 mount: identical responses to legacy paths
# ---------------------------------------------------------------------------


def test_v1_health_live_mirrors_legacy() -> None:
    with TestClient(api_main.app) as client:
        legacy = client.get("/health/live")
        v1 = client.get("/v1/health/live")
    assert legacy.status_code == 200
    assert v1.status_code == 200
    assert legacy.json() == v1.json() == {"status": "alive"}


def test_v1_health_ready_mirrors_legacy() -> None:
    with TestClient(api_main.app) as client:
        legacy = client.get("/health/ready")
        v1 = client.get("/v1/health/ready")
    assert legacy.status_code == v1.status_code
    # The two payloads must agree on the runtime status.
    assert legacy.json()["status"] == v1.json()["status"]


# ---------------------------------------------------------------------------
# Legacy deprecation header
# ---------------------------------------------------------------------------


def test_legacy_path_carries_deprecation_headers() -> None:
    with TestClient(api_main.app) as client:
        response = client.get("/health/live")
    assert response.headers.get("Deprecation") == "true"
    assert response.headers.get("Sunset") == DEFAULT_SUNSET_DATE
    link = response.headers.get("Link", "")
    assert "/v1/health/live" in link
    assert "successor-version" in link


def test_v1_path_does_not_carry_deprecation_header() -> None:
    with TestClient(api_main.app) as client:
        response = client.get("/v1/health/live")
    assert "Deprecation" not in response.headers
    assert "Sunset" not in response.headers


def test_ui_path_is_not_tagged() -> None:
    """The static-mount tree must never receive deprecation headers."""

    middleware = LegacyApiDeprecationMiddleware(lambda *_: None)
    assert middleware._should_tag("/ui/index.html") is False
    assert middleware._should_tag("/openapi.json") is False
    assert middleware._should_tag("/docs") is False
    assert middleware._should_tag("/redoc") is False
    # Root path is also not tagged (kept neutral for healthchecks).
    assert middleware._should_tag("/") is False


def test_v1_path_is_not_tagged() -> None:
    middleware = LegacyApiDeprecationMiddleware(lambda *_: None)
    assert middleware._should_tag("/v1/health/live") is False
    assert middleware._should_tag("/v1") is False


def test_legacy_api_path_is_tagged() -> None:
    middleware = LegacyApiDeprecationMiddleware(lambda *_: None)
    assert middleware._should_tag("/health/live") is True
    assert middleware._should_tag("/analysis/run") is True


# ---------------------------------------------------------------------------
# Standalone middleware behaviour (no full-app dependency)
# ---------------------------------------------------------------------------


def test_standalone_middleware_adds_headers_only_for_legacy_paths() -> None:
    app = FastAPI()

    @app.get("/legacy/thing")
    async def legacy() -> dict[str, str]:
        return {"path": "legacy"}

    @app.get("/v1/legacy/thing")
    async def v1() -> dict[str, str]:
        return {"path": "v1"}

    app.add_middleware(LegacyApiDeprecationMiddleware)

    with TestClient(app) as client:
        legacy_resp = client.get("/legacy/thing")
        v1_resp = client.get("/v1/legacy/thing")

    assert legacy_resp.headers.get("Deprecation") == "true"
    assert "/v1/legacy/thing" in legacy_resp.headers.get("Link", "")
    assert "Deprecation" not in v1_resp.headers

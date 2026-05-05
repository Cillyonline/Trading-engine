"""Tests for the structured exception hierarchy and X-Request-ID handling.

Covers issue #1127:
* CillyError subclasses map to the documented HTTP status codes (404/409/422).
* JSON error bodies include both ``detail`` and ``request_id`` fields.
* ``X-Request-ID`` is echoed when supplied by the client and freshly
  generated (UUIDv4) otherwise.
* The active request id is bound to ``contextvars`` and surfaces in log
  records emitted while handling the request.
"""

from __future__ import annotations

import logging
import uuid

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import api.main as api_main
from api.middleware import (
    REQUEST_ID_HEADER,
    RequestIdMiddleware,
    current_request_id,
    install_request_id_log_filter,
)
from cilly_trading.exceptions import (
    CillyError,
    ConflictError,
    NotFoundError,
    ValidationError,
)


# ---------------------------------------------------------------------------
# Unit tests for the exception hierarchy itself.
# ---------------------------------------------------------------------------


def test_exception_hierarchy_inherits_from_cilly_error() -> None:
    assert issubclass(NotFoundError, CillyError)
    assert issubclass(ValidationError, CillyError)
    assert issubclass(ConflictError, CillyError)


def test_exception_status_codes_match_specification() -> None:
    assert NotFoundError("x").http_status_code == 404
    assert ValidationError("x").http_status_code == 422
    assert ConflictError("x").http_status_code == 409


def test_exception_carries_detail_message() -> None:
    err = ValidationError("invalid_payload")
    assert err.detail == "invalid_payload"
    assert str(err) == "invalid_payload"


# ---------------------------------------------------------------------------
# Integration tests: exception handlers + request id middleware on a
# minimal FastAPI app that mirrors the registration done in api.main.
# ---------------------------------------------------------------------------


def _build_test_app() -> FastAPI:
    """Construct a tiny FastAPI app wired exactly like ``api.main`` would.

    Using a dedicated app avoids dragging in the full Cilly runtime, while
    still exercising the public-facing middleware + handler contract.
    """

    app = FastAPI()
    app.add_middleware(RequestIdMiddleware)

    from api.main import (  # local import to reuse the production handlers
        _handle_cilly_error,
        _handle_conflict_error,
        _handle_not_found_error,
        _handle_validation_error,
    )

    app.add_exception_handler(NotFoundError, _handle_not_found_error)
    app.add_exception_handler(ValidationError, _handle_validation_error)
    app.add_exception_handler(ConflictError, _handle_conflict_error)
    app.add_exception_handler(CillyError, _handle_cilly_error)

    @app.get("/raise/not-found")
    def _raise_not_found() -> None:
        raise NotFoundError("resource_missing")

    @app.get("/raise/validation")
    def _raise_validation() -> None:
        raise ValidationError("payload_invalid")

    @app.get("/raise/conflict")
    def _raise_conflict() -> None:
        raise ConflictError("state_conflict")

    @app.get("/echo/request-id")
    def _echo_request_id() -> dict[str, str | None]:
        return {"request_id": current_request_id()}

    return app


@pytest.fixture()
def test_app() -> FastAPI:
    return _build_test_app()


@pytest.mark.parametrize(
    "path, expected_status, expected_detail",
    [
        ("/raise/not-found", 404, "resource_missing"),
        ("/raise/validation", 422, "payload_invalid"),
        ("/raise/conflict", 409, "state_conflict"),
    ],
)
def test_exception_handlers_map_to_documented_status_and_body(
    test_app: FastAPI, path: str, expected_status: int, expected_detail: str
) -> None:
    with TestClient(test_app) as client:
        response = client.get(path)

    assert response.status_code == expected_status
    body = response.json()
    assert body["detail"] == expected_detail
    assert isinstance(body["request_id"], str) and body["request_id"]
    # The same id must also be exposed on the response header.
    assert response.headers[REQUEST_ID_HEADER] == body["request_id"]


def test_incoming_request_id_is_echoed(test_app: FastAPI) -> None:
    incoming = "client-supplied-id-123"
    with TestClient(test_app) as client:
        response = client.get(
            "/raise/validation", headers={REQUEST_ID_HEADER: incoming}
        )

    assert response.status_code == 422
    assert response.headers[REQUEST_ID_HEADER] == incoming
    assert response.json()["request_id"] == incoming


def test_missing_request_id_is_generated_as_uuid4(test_app: FastAPI) -> None:
    with TestClient(test_app) as client:
        response = client.get("/raise/validation")

    generated = response.headers[REQUEST_ID_HEADER]
    parsed = uuid.UUID(generated)
    assert parsed.version == 4
    assert response.json()["request_id"] == generated


def test_invalid_incoming_request_id_is_replaced_by_generated_uuid4(
    test_app: FastAPI,
) -> None:
    # Header injection attempts and overly-long values must be discarded.
    bogus = "bad value\r\nX-Injected: yes"
    with TestClient(test_app) as client:
        response = client.get(
            "/echo/request-id", headers={REQUEST_ID_HEADER: bogus}
        )

    echoed = response.headers[REQUEST_ID_HEADER]
    assert echoed != bogus
    parsed = uuid.UUID(echoed)
    assert parsed.version == 4


def test_request_id_is_available_via_context_var(test_app: FastAPI) -> None:
    incoming = "context-var-check"
    with TestClient(test_app) as client:
        response = client.get(
            "/echo/request-id", headers={REQUEST_ID_HEADER: incoming}
        )

    assert response.json() == {"request_id": incoming}


def test_request_id_appears_in_log_records(
    test_app: FastAPI, caplog: pytest.LogCaptureFixture
) -> None:
    """Logs emitted while serving a request must carry the same request_id."""

    log_filter = install_request_id_log_filter()
    log_name = "tests.api.exceptions_request_id"
    request_logger = logging.getLogger(log_name)
    request_logger.addFilter(log_filter)

    @test_app.get("/log-and-fail")
    def _log_and_fail() -> None:
        request_logger.error("about to fail")
        raise ValidationError("logged_failure")

    incoming = "log-correlation-id-xyz"
    with caplog.at_level(logging.ERROR, logger=log_name):
        # caplog's handler also needs the filter so request_id is recorded.
        for handler in caplog.handler, *logging.getLogger().handlers:
            if not any(f is log_filter for f in handler.filters):
                handler.addFilter(log_filter)

        with TestClient(test_app) as client:
            response = client.get(
                "/log-and-fail", headers={REQUEST_ID_HEADER: incoming}
            )

    assert response.status_code == 422
    assert response.headers[REQUEST_ID_HEADER] == incoming

    matching = [
        record
        for record in caplog.records
        if record.name == log_name and record.message == "about to fail"
    ]
    assert matching, "expected the request handler log record to be captured"
    assert matching[0].request_id == incoming
    # Outside of any request the contextvar must reset back to None.
    assert current_request_id() is None


# ---------------------------------------------------------------------------
# Integration test against the real api.main app: ensure the production
# wiring actually exposes the X-Request-ID header on a successful response
# and on errors raised by analysis_service (NotFoundError path).
# ---------------------------------------------------------------------------


def test_real_app_echoes_request_id_header_on_health(monkeypatch) -> None:
    monkeypatch.setattr(api_main, "start_engine_runtime", lambda: "running")
    headers = {api_main.ROLE_HEADER_NAME: "read_only"}

    with TestClient(api_main.app) as client:
        response = client.get("/health", headers=headers)

    assert response.status_code == 200
    request_id = response.headers.get(REQUEST_ID_HEADER)
    assert request_id and uuid.UUID(request_id).version == 4


def test_real_app_returns_request_id_in_validation_error_body(monkeypatch) -> None:
    monkeypatch.setattr(api_main, "start_engine_runtime", lambda: "running")

    operator_headers = {api_main.ROLE_HEADER_NAME: "operator"}
    incoming = "operator-trace-id-001"

    with TestClient(api_main.app) as client:
        response = client.post(
            "/strategy/analyze",
            headers={**operator_headers, REQUEST_ID_HEADER: incoming},
            json={
                "ingestion_run_id": "not-a-uuid",
                "symbol": "AAPL",
                "strategy": "RSI2",
                "market_type": "stock",
                "lookback_days": 200,
            },
        )

    assert response.status_code == 422
    body = response.json()
    assert body["detail"] == "invalid_ingestion_run_id"
    assert body["request_id"] == incoming
    assert response.headers[REQUEST_ID_HEADER] == incoming

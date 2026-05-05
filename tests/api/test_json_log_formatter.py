"""Tests for the structured JSON log formatter (issue #1131)."""

from __future__ import annotations

import io
import json
import logging

import pytest

from api.middleware.request_id import (
    RequestIdLogFilter,
    install_request_id_log_filter,
    request_id_var,
)
from api.services.composition_runtime_service import _JsonLogFormatter


def _capture_one_record(
    *, log_call, level: int = logging.INFO, request_id: str | None = None
) -> dict[str, object]:
    """Run ``log_call`` against an isolated logger and return the parsed JSON."""

    buffer = io.StringIO()
    handler = logging.StreamHandler(buffer)
    handler.setFormatter(_JsonLogFormatter())
    handler.addFilter(RequestIdLogFilter())

    logger = logging.getLogger(f"json_logging_test_{id(buffer)}")
    logger.handlers.clear()
    logger.addHandler(handler)
    logger.setLevel(level)
    logger.propagate = False

    token = None
    if request_id is not None:
        token = request_id_var.set(request_id)
    try:
        log_call(logger)
    finally:
        if token is not None:
            request_id_var.reset(token)

    line = buffer.getvalue().strip()
    assert line, "expected exactly one log line"
    return json.loads(line)


def test_basic_envelope_has_standard_fields() -> None:
    record = _capture_one_record(log_call=lambda log: log.info("hello world"))
    assert record["level"] == "INFO"
    assert record["message"] == "hello world"
    assert record["logger"].startswith("json_logging_test_")
    assert "timestamp" in record
    # Without a bound request id, the field must not appear.
    assert "request_id" not in record


def test_extra_fields_are_promoted_to_top_level() -> None:
    record = _capture_one_record(
        log_call=lambda log: log.warning(
            "sqlite_connection_failed",
            extra={"attempt": 2, "max_retries": 4, "db_path": "/tmp/test.db"},
        )
    )
    assert record["message"] == "sqlite_connection_failed"
    assert record["attempt"] == 2
    assert record["max_retries"] == 4
    assert record["db_path"] == "/tmp/test.db"


def test_request_id_is_included_when_bound() -> None:
    record = _capture_one_record(
        log_call=lambda log: log.info("served"),
        request_id="abc-123",
    )
    assert record["request_id"] == "abc-123"


def test_non_serializable_extra_value_falls_back_to_repr() -> None:
    class NotJsonable:
        def __repr__(self) -> str:
            return "<NotJsonable>"

    record = _capture_one_record(
        log_call=lambda log: log.info("custom", extra={"obj": NotJsonable()})
    )
    assert record["obj"] == "<NotJsonable>"


def test_exception_field_is_included() -> None:
    def _emit(log: logging.Logger) -> None:
        try:
            raise RuntimeError("boom")
        except RuntimeError:
            log.exception("explosion", extra={"site": "unit"})

    record = _capture_one_record(log_call=_emit, level=logging.ERROR)
    assert record["message"] == "explosion"
    assert "exception" in record
    assert "RuntimeError: boom" in record["exception"]
    assert record["site"] == "unit"


def test_internal_logrecord_attributes_are_filtered_out() -> None:
    record = _capture_one_record(log_call=lambda log: log.info("msg"))
    # These are LogRecord internals — never include them in JSON output.
    for forbidden in ("args", "msg", "pathname", "lineno", "process", "thread"):
        assert forbidden not in record


def test_install_request_id_log_filter_is_idempotent() -> None:
    logger = logging.getLogger("idempotent_filter_test")
    logger.filters.clear()
    f1 = install_request_id_log_filter(logger)
    f2 = install_request_id_log_filter(logger)
    assert f1 is f2
    assert sum(isinstance(f, RequestIdLogFilter) for f in logger.filters) == 1

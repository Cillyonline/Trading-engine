"""Tests for ``Secret`` and the sensitive-data logging filter."""

from __future__ import annotations

import io
import logging

import pytest

from api.security import (
    Secret,
    SensitiveDataFilter,
    install_sensitive_data_filter,
)


@pytest.fixture(autouse=True)
def _reset_root_logger():
    """Snapshot/restore the root logger filters & handlers for isolation."""
    root = logging.getLogger()
    saved_filters = list(root.filters)
    saved_handlers = list(root.handlers)
    for handler in saved_handlers:
        root.removeHandler(handler)
    for f in saved_filters:
        root.removeFilter(f)
    try:
        yield
    finally:
        for handler in list(root.handlers):
            root.removeHandler(handler)
        for f in list(root.filters):
            root.removeFilter(f)
        for handler in saved_handlers:
            root.addHandler(handler)
        for f in saved_filters:
            root.addFilter(f)


def _make_handler() -> tuple[logging.Handler, io.StringIO]:
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(logging.Formatter("%(message)s"))
    handler.setLevel(logging.DEBUG)
    return handler, stream


def test_secret_repr_and_str_are_redacted():
    secret = Secret("super-token-123")
    assert repr(secret) == "***REDACTED***"
    assert str(secret) == "***REDACTED***"
    assert f"{secret}" == "***REDACTED***"
    assert "super-token-123" not in repr(secret)
    assert secret.get_secret_value() == "super-token-123"


def test_named_logger_emits_redacted_output_through_installed_handler():
    """Regression test for the P1 follow-up on issue #1158.

    A record emitted by a *named* module logger (e.g. ``logging.getLogger(__name__)``)
    must be redacted by the time it reaches a handler installed on the root logger.
    """
    handler, stream = _make_handler()
    root = logging.getLogger()
    root.addHandler(handler)
    root.setLevel(logging.DEBUG)

    install_sensitive_data_filter()

    module_logger = logging.getLogger("cilly.tests.named_module_logger")
    module_logger.setLevel(logging.DEBUG)
    module_logger.propagate = True
    module_logger.info("Authorization: Bearer abcdef1234567890")
    module_logger.info("api_key=topsecretvalue")

    output = stream.getvalue()
    assert "abcdef1234567890" not in output
    assert "topsecretvalue" not in output
    assert "***REDACTED***" in output


def test_install_is_idempotent_no_duplicate_filters():
    handler, _ = _make_handler()
    root = logging.getLogger()
    root.addHandler(handler)

    install_sensitive_data_filter()
    install_sensitive_data_filter()
    install_sensitive_data_filter()

    sd_filters_on_root = [
        f for f in root.filters if isinstance(f, SensitiveDataFilter)
    ]
    sd_filters_on_handler = [
        f for f in handler.filters if isinstance(f, SensitiveDataFilter)
    ]
    assert len(sd_filters_on_root) == 1
    assert len(sd_filters_on_handler) == 1


def test_filter_attached_to_handlers_added_before_install():
    handler, stream = _make_handler()
    root = logging.getLogger()
    root.addHandler(handler)
    root.setLevel(logging.DEBUG)

    install_sensitive_data_filter()

    sd_filters = [f for f in handler.filters if isinstance(f, SensitiveDataFilter)]
    assert len(sd_filters) == 1

    logging.getLogger("some.child").warning("password=hunter2")
    assert "hunter2" not in stream.getvalue()
    assert "***REDACTED***" in stream.getvalue()

"""Security utilities: Secret wrapper and sensitive-data log filter."""

from __future__ import annotations

import logging
import re

_SENSITIVE_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"(?i)(bearer\s+)[A-Za-z0-9\-._~+/]+=*"),
    re.compile(r"(?i)(api[_-]?key\s*[=:]\s*)\S+"),
    re.compile(r"(?i)(secret\s*[=:]\s*)\S+"),
    re.compile(r"(?i)(password\s*[=:]\s*)\S+"),
    re.compile(r"(?i)(token\s*[=:]\s*)\S+"),
]


class Secret:
    """Wrapper for sensitive string values that masks the value in logs and reprs.

    Uses composition instead of ``str`` inheritance to prevent accidental leakage
    through string operations such as slicing, concatenation, or format directives.
    """

    __slots__ = ("_value",)

    def __init__(self, value: str) -> None:
        if not isinstance(value, str):
            raise TypeError(f"Secret requires a str, got {type(value).__name__!r}")
        self._value = value

    def __repr__(self) -> str:
        return "***REDACTED***"

    def __str__(self) -> str:
        return "***REDACTED***"

    def __format__(self, format_spec: str) -> str:
        return "***REDACTED***"

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Secret):
            return self._value == other._value
        return NotImplemented

    def __hash__(self) -> int:
        return hash(self._value)

    def get_secret_value(self) -> str:
        """Return the actual secret value."""
        return self._value


class SensitiveDataFilter(logging.Filter):
    """Logging filter that redacts known sensitive patterns from log messages."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = _redact(record.msg)
        if record.args:
            if isinstance(record.args, dict):
                record.args = {
                    k: _redact(v) if isinstance(v, str) else v
                    for k, v in record.args.items()
                }
            elif isinstance(record.args, tuple):
                record.args = tuple(
                    _redact(arg) if isinstance(arg, str) else arg
                    for arg in record.args
                )
        return True


def _redact(text: str) -> str:
    for pattern in _SENSITIVE_PATTERNS:
        text = pattern.sub(r"\g<1>***REDACTED***", text)
    return text


def _attach_filter(target: logging.Logger | logging.Handler) -> None:
    """Attach a ``SensitiveDataFilter`` to ``target`` if not already attached.

    Idempotency is achieved by checking whether the target already carries a
    ``SensitiveDataFilter`` instance, so repeated calls do not stack duplicates.
    """
    if any(isinstance(f, SensitiveDataFilter) for f in target.filters):
        return
    target.addFilter(SensitiveDataFilter())


def install_sensitive_data_filter(logger_name: str = "") -> None:
    """Install ``SensitiveDataFilter`` so all log records are redacted.

    Filters attached to a logger only run for records originating on that logger;
    they do not run for records produced by named child loggers and forwarded via
    propagation. To guarantee coverage, the filter is therefore attached to both
    the named logger *and* every handler on it (and, by default, on the root
    logger), since handler-level filters always execute on every record that the
    handler emits, regardless of the logger that produced the record.

    The function is idempotent: repeated calls do not stack duplicate filters.
    """
    logger = logging.getLogger(logger_name)
    _attach_filter(logger)
    for handler in logger.handlers:
        _attach_filter(handler)
    # Always cover root-logger handlers as well, because module loggers
    # (``logging.getLogger(__name__)``) typically propagate to the root logger
    # where the application's handlers live.
    if logger_name != "":
        root = logging.getLogger()
        for handler in root.handlers:
            _attach_filter(handler)

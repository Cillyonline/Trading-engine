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


def install_sensitive_data_filter(logger_name: str = "") -> None:
    """Install ``SensitiveDataFilter`` on the named logger (root logger by default)."""
    logging.getLogger(logger_name).addFilter(SensitiveDataFilter())

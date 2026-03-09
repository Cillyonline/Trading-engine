"""Deterministic structured logging utility for engine runtime events."""

from __future__ import annotations

import json
import logging
from decimal import Decimal
from threading import Lock
from typing import Any, Callable, Mapping

_SCHEMA_VERSION = "cilly.engine.log.v1"
_LOG_LOCK = Lock()
_EVENT_INDEX = 0
_EMITTER: Callable[[str], None] | None = None
_RUNTIME_LOGGER = logging.getLogger(__name__)


class InMemoryEngineLogSink:
    """Simple sink used by tests to collect emitted log lines."""

    def __init__(self) -> None:
        self._lines: list[str] = []

    def write(self, line: str) -> None:
        self._lines.append(line)

    @property
    def lines(self) -> tuple[str, ...]:
        return tuple(self._lines)


def configure_engine_log_emitter(emitter: Callable[[str], None] | None) -> None:
    """Configure a process-local sink for structured engine logs."""

    global _EMITTER
    with _LOG_LOCK:
        _EMITTER = emitter


def reset_engine_logging_for_tests() -> None:
    """Reset logger state for deterministic test assertions."""

    global _EVENT_INDEX, _EMITTER
    with _LOG_LOCK:
        _EVENT_INDEX = 0
        _EMITTER = None


def emit_structured_engine_log(
    event: str,
    *,
    level: str = "INFO",
    payload: Mapping[str, Any] | None = None,
) -> str:
    """Emit a deterministic structured engine log line."""

    if not isinstance(event, str) or not event.strip():
        raise ValueError("event must be a non-empty string")

    canonical_payload = _normalize_mapping(payload or {})
    with _LOG_LOCK:
        global _EVENT_INDEX
        record = {
            "component": "engine",
            "event": event,
            "event_index": _EVENT_INDEX,
            "level": level,
            "payload": canonical_payload,
            "schema_version": _SCHEMA_VERSION,
        }
        _EVENT_INDEX += 1
        line = json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        if _EMITTER is not None:
            _EMITTER(line)
        else:
            _RUNTIME_LOGGER.info("%s", line)
        return line


def _normalize_mapping(mapping: Mapping[str, Any]) -> dict[str, Any]:
    return {str(key): _normalize_value(value) for key, value in sorted(mapping.items(), key=lambda item: str(item[0]))}


def _normalize_value(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, Mapping):
        return _normalize_mapping(value)
    if isinstance(value, (list, tuple)):
        return [_normalize_value(item) for item in value]
    return str(value)

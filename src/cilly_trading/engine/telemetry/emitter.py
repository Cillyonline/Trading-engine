"""Telemetry emission utility for engine events."""

from __future__ import annotations

from threading import Lock
from typing import Any, Callable, Mapping

from .schema import build_telemetry_event, serialize_telemetry_event

_EMIT_LOCK = Lock()
_EMITTER: Callable[[str], None] | None = None


class InMemoryTelemetrySink:
    """Simple sink used by tests to collect emitted telemetry lines."""

    def __init__(self) -> None:
        self._lines: list[str] = []

    def write(self, line: str) -> None:
        self._lines.append(line)

    @property
    def lines(self) -> tuple[str, ...]:
        return tuple(self._lines)


def configure_telemetry_emitter(emitter: Callable[[str], None] | None) -> None:
    """Configure a process-local sink for serialized telemetry events."""

    global _EMITTER
    with _EMIT_LOCK:
        _EMITTER = emitter


def reset_telemetry_emission_for_tests() -> None:
    """Reset emitter state so tests can assert deterministic sequences."""

    global _EMITTER
    with _EMIT_LOCK:
        _EMITTER = None


def emit_telemetry_event(
    event: str,
    *,
    event_index: int,
    timestamp_utc: str,
    payload: Mapping[str, Any] | None = None,
) -> str:
    """Serialize and emit a canonical telemetry event when a sink is configured."""

    with _EMIT_LOCK:
        record = build_telemetry_event(
            event=event,
            event_index=event_index,
            timestamp_utc=timestamp_utc,
            payload=payload,
        )
        line = serialize_telemetry_event(record)

        if _EMITTER is not None:
            _EMITTER(line)
        return line

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from time import monotonic
from typing import Literal, Protocol, TypeAlias

ObservabilityExtensionPoint: TypeAlias = Literal["status", "health", "introspection"]
ExtensionErrorCode: TypeAlias = Literal["extension_failed", "budget_exceeded"]
JsonScalar: TypeAlias = str | int | float | bool | None
JsonValue: TypeAlias = JsonScalar | list["JsonValue"] | dict[str, "JsonValue"]
ExtensionPayload: TypeAlias = dict[str, JsonValue]


@dataclass(frozen=True)
class ObservabilityContext:
    """Read-only context passed to observability extensions.

    The context intentionally exposes only immutable metadata snapshots and no
    mutable engine/runtime handles.
    """

    runtime_id: str
    mode: str
    started_at: datetime
    updated_at: datetime
    now: datetime
    schema_version: str = "v1"


@dataclass(frozen=True)
class ExtensionExecution:
    extension_name: str
    payload: ExtensionPayload
    error_code: ExtensionErrorCode | None = None
    error_detail: str | None = None


@dataclass(frozen=True)
class ExtensionPointExecution:
    point: ObservabilityExtensionPoint
    executions: tuple[ExtensionExecution, ...]


class ObservabilityExtension(Protocol):
    def __call__(self, context: ObservabilityContext) -> ExtensionPayload: ...


@dataclass
class RuntimeObservabilityRegistry:
    """Registry and executor for runtime observability extension points."""

    _status_extensions: list[tuple[str, ObservabilityExtension]] = field(default_factory=list)
    _health_extensions: list[tuple[str, ObservabilityExtension]] = field(default_factory=list)
    _introspection_extensions: list[tuple[str, ObservabilityExtension]] = field(default_factory=list)

    def register(
        self,
        point: ObservabilityExtensionPoint,
        *,
        name: str,
        extension: ObservabilityExtension,
    ) -> None:
        extensions = self._extensions_for_point(point)
        if any(existing_name == name for existing_name, _ in extensions):
            raise ValueError(f"Duplicate extension name for point '{point}': {name}")

        extensions.append((name, extension))

    def execute(
        self,
        point: ObservabilityExtensionPoint,
        *,
        context: ObservabilityContext,
        budget_seconds: float = 0.05,
    ) -> ExtensionPointExecution:
        executions: list[ExtensionExecution] = []

        for name, extension in self._extensions_for_point(point):
            started = monotonic()
            try:
                payload = extension(context)
                _validate_serializable_payload(payload)
                elapsed = monotonic() - started
                if elapsed > budget_seconds:
                    executions.append(
                        ExtensionExecution(
                            extension_name=name,
                            payload={},
                            error_code="budget_exceeded",
                            error_detail=f"elapsed_seconds={elapsed:.6f}",
                        )
                    )
                    continue
                executions.append(ExtensionExecution(extension_name=name, payload=payload))
            except Exception as exc:
                executions.append(
                    ExtensionExecution(
                        extension_name=name,
                        payload={},
                        error_code="extension_failed",
                        error_detail=type(exc).__name__,
                    )
                )

        return ExtensionPointExecution(point=point, executions=tuple(executions))

    def _extensions_for_point(
        self,
        point: ObservabilityExtensionPoint,
    ) -> list[tuple[str, ObservabilityExtension]]:
        if point == "status":
            return self._status_extensions
        if point == "health":
            return self._health_extensions
        return self._introspection_extensions


def build_observability_context(
    *,
    runtime_id: str,
    mode: str,
    started_at: datetime,
    now: datetime | None = None,
) -> ObservabilityContext:
    resolved_now = _as_utc(now) if now is not None else datetime.now(timezone.utc)
    return ObservabilityContext(
        runtime_id=runtime_id,
        mode=mode,
        started_at=_as_utc(started_at),
        updated_at=resolved_now,
        now=resolved_now,
    )


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _validate_serializable_payload(payload: ExtensionPayload) -> None:
    json.dumps(payload)

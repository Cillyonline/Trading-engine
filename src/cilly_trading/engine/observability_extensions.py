from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from time import monotonic
from typing import Callable, Literal, Protocol, TypeAlias
import json

ObservabilityExtensionPoint: TypeAlias = Literal["status", "health", "introspection"]
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
    error: str | None = None


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
        if point == "status":
            self._status_extensions.append((name, extension))
            return
        if point == "health":
            self._health_extensions.append((name, extension))
            return
        self._introspection_extensions.append((name, extension))

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
                            error=f"budget_exceeded:{elapsed:.6f}",
                        )
                    )
                    continue
                executions.append(ExtensionExecution(extension_name=name, payload=payload))
            except Exception as exc:
                executions.append(
                    ExtensionExecution(
                        extension_name=name,
                        payload={},
                        error=f"extension_failed:{type(exc).__name__}",
                    )
                )

        return ExtensionPointExecution(point=point, executions=tuple(executions))

    def _extensions_for_point(
        self,
        point: ObservabilityExtensionPoint,
    ) -> list[tuple[str, ObservabilityExtension]]:
        if point == "status":
            return list(self._status_extensions)
        if point == "health":
            return list(self._health_extensions)
        return list(self._introspection_extensions)


def build_observability_context(*, runtime_id: str, mode: str, started_at: datetime) -> ObservabilityContext:
    now = datetime.now(timezone.utc)
    return ObservabilityContext(
        runtime_id=runtime_id,
        mode=mode,
        started_at=_as_utc(started_at),
        updated_at=now,
        now=now,
    )


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _validate_serializable_payload(payload: ExtensionPayload) -> None:
    json.dumps(payload)

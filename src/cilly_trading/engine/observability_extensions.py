from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import Event, Thread
from typing import Any, Literal, Protocol, TypeAlias

ObservabilityExtensionPoint: TypeAlias = Literal["status", "health", "introspection"]
ExtensionMetadataSource: TypeAlias = Literal["core", "extension"]
ExtensionErrorCode: TypeAlias = Literal["extension_failed", "budget_exceeded"]
ExtensionFailureType: TypeAlias = Literal["none", "exception", "timeout", "invalid_output"]
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
    failure_type: ExtensionFailureType = "none"
    failure_count: int = 0
    error_code: ExtensionErrorCode | None = None
    error_detail: str | None = None


@dataclass(frozen=True)
class ExtensionPointExecution:
    point: ObservabilityExtensionPoint
    executions: tuple[ExtensionExecution, ...]


@dataclass(frozen=True)
class ExtensionMetadata:
    name: str
    point: ObservabilityExtensionPoint
    enabled: bool
    source: ExtensionMetadataSource


@dataclass(frozen=True)
class _RegisteredExtension:
    metadata: ExtensionMetadata
    extension: ObservabilityExtension


class ObservabilityExtension(Protocol):
    def __call__(self, context: ObservabilityContext) -> ExtensionPayload: ...


@dataclass
class RuntimeObservabilityRegistry:
    """Registry and executor for runtime observability extension points."""

    _status_extensions: list[_RegisteredExtension] = field(default_factory=list)
    _health_extensions: list[_RegisteredExtension] = field(default_factory=list)
    _introspection_extensions: list[_RegisteredExtension] = field(default_factory=list)
    _failure_counters: dict[str, int] = field(default_factory=dict)
    _last_failure_type: dict[str, ExtensionFailureType] = field(default_factory=dict)

    def register(
        self,
        point: ObservabilityExtensionPoint,
        *,
        name: str,
        extension: ObservabilityExtension,
        enabled: bool = True,
        source: ExtensionMetadataSource = "extension",
    ) -> None:
        extensions = self._extensions_for_point(point)
        if any(registered.metadata.name == name for registered in extensions):
            raise ValueError(f"Duplicate extension name for point '{point}': {name}")

        extensions.append(
            _RegisteredExtension(
                metadata=ExtensionMetadata(
                    name=name,
                    point=point,
                    enabled=enabled,
                    source=source,
                ),
                extension=extension,
            )
        )

    def list_extensions_metadata(self) -> tuple[ExtensionMetadata, ...]:
        all_metadata = [
            registered.metadata
            for registered in (
                *self._status_extensions,
                *self._health_extensions,
                *self._introspection_extensions,
            )
        ]
        sorted_metadata = sorted(all_metadata, key=lambda metadata: (metadata.point, metadata.name))
        return tuple(sorted_metadata)

    def execute(
        self,
        point: ObservabilityExtensionPoint,
        *,
        context: ObservabilityContext,
        budget_seconds: float = 0.05,
    ) -> ExtensionPointExecution:
        executions: list[ExtensionExecution] = []

        for registered in self._extensions_for_point(point):
            if not registered.metadata.enabled:
                continue

            name = registered.metadata.name
            extension = registered.extension
            extension_key = _extension_key(point=point, name=name)
            try:
                payload = _run_extension_with_timeout(
                    extension=extension,
                    context=context,
                    timeout_seconds=budget_seconds,
                )
                _validate_serializable_payload(payload)
                self._mark_success(extension_key)
                executions.append(
                    ExtensionExecution(
                        extension_name=name,
                        payload=payload,
                        failure_type="none",
                        failure_count=0,
                    )
                )
            except TimeoutError:
                failure_count = self._mark_failure(extension_key, "timeout")
                executions.append(
                    ExtensionExecution(
                        extension_name=name,
                        payload={},
                        failure_type="timeout",
                        failure_count=failure_count,
                        error_code="budget_exceeded",
                        error_detail="execution_timeout",
                    )
                )
            except (TypeError, ValueError):
                failure_count = self._mark_failure(extension_key, "invalid_output")
                executions.append(
                    ExtensionExecution(
                        extension_name=name,
                        payload={},
                        failure_type="invalid_output",
                        failure_count=failure_count,
                        error_code="extension_failed",
                        error_detail="invalid_output",
                    )
                )
            except Exception as exc:
                failure_count = self._mark_failure(extension_key, "exception")
                executions.append(
                    ExtensionExecution(
                        extension_name=name,
                        payload={},
                        failure_type="exception",
                        failure_count=failure_count,
                        error_code="extension_failed",
                        error_detail=type(exc).__name__,
                    )
                )

        return ExtensionPointExecution(point=point, executions=tuple(executions))

    def _extensions_for_point(
        self,
        point: ObservabilityExtensionPoint,
    ) -> list[_RegisteredExtension]:
        if point == "status":
            return self._status_extensions
        if point == "health":
            return self._health_extensions
        return self._introspection_extensions

    def get_extension_failure_snapshot(self) -> dict[str, dict[str, str | int]]:
        snapshot: dict[str, dict[str, str | int]] = {}
        extension_keys = set(self._failure_counters) | set(self._last_failure_type)
        for extension_key in sorted(extension_keys):
            snapshot[extension_key] = {
                "failure_count": self._failure_counters.get(extension_key, 0),
                "last_failure_type": self._last_failure_type.get(extension_key, "none"),
            }
        return snapshot

    def _mark_success(self, extension_key: str) -> None:
        self._failure_counters.setdefault(extension_key, 0)
        self._last_failure_type[extension_key] = "none"

    def _mark_failure(
        self,
        extension_key: str,
        failure_type: ExtensionFailureType,
    ) -> int:
        next_count = self._failure_counters.get(extension_key, 0) + 1
        self._failure_counters[extension_key] = next_count
        self._last_failure_type[extension_key] = failure_type
        return next_count


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
    if not isinstance(payload, dict):
        raise TypeError("payload must be a dictionary")

    json.dumps(payload)


def _run_extension_with_timeout(
    *,
    extension: ObservabilityExtension,
    context: ObservabilityContext,
    timeout_seconds: float,
) -> ExtensionPayload:
    """Run one extension with a timeout by waiting on a worker thread.

    The timeout is implemented by ending the caller wait only. If the timeout is
    reached, the worker thread may continue running in the background and this is
    intentional for a simple, predictable boundary.

    There is no cancellation and no retry logic here; only the wait is
    terminated and a timeout is surfaced to the caller.
    """
    ready = Event()
    result: dict[str, Any] = {}

    def _target() -> None:
        try:
            result["payload"] = extension(context)
        except Exception as exc:  # pragma: no cover - propagated to caller
            result["exception"] = exc
        finally:
            ready.set()

    worker = Thread(target=_target, daemon=True)
    worker.start()

    if not ready.wait(timeout_seconds):
        raise TimeoutError("extension execution timed out")

    if "exception" in result:
        raise result["exception"]

    return result["payload"]


def _extension_key(*, point: ObservabilityExtensionPoint, name: str) -> str:
    return f"{point}:{name}"

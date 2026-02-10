"""Read-only runtime introspection contract for API exposure."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal, TypedDict

from cilly_trading.engine.observability_extensions import RuntimeObservabilityRegistry
from cilly_trading.engine.runtime_controller import get_runtime_controller

_RUNTIME_INTROSPECTION_SCHEMA_VERSION = "v1"
_RUNTIME_OWNERSHIP_TAG = "engine"
_RUNTIME_INTROSPECTION_STARTED_AT = datetime.now(timezone.utc)
_RUNTIME_OBSERVABILITY_REGISTRY = RuntimeObservabilityRegistry()


class RuntimeIntrospectionTimestamps(TypedDict):
    started_at: str
    updated_at: str


class RuntimeIntrospectionOwnership(TypedDict):
    owner_tag: str


class RuntimeIntrospectionExtension(TypedDict):
    name: str
    point: Literal["status", "health", "introspection"]
    enabled: bool
    source: Literal["core", "extension"]


class RuntimeIntrospectionPayload(TypedDict):
    schema_version: str
    runtime_id: str
    mode: str
    timestamps: RuntimeIntrospectionTimestamps
    ownership: RuntimeIntrospectionOwnership
    extensions: list[RuntimeIntrospectionExtension]


def get_runtime_introspection_payload() -> RuntimeIntrospectionPayload:
    """Return a strict, read-only runtime introspection payload.

    This function is intentionally side-effect free:
    - no state transitions
    - no persistence writes
    - no runtime id allocation
    """

    runtime_controller = get_runtime_controller()
    started_at_iso = _RUNTIME_INTROSPECTION_STARTED_AT.isoformat()

    return {
        "schema_version": _RUNTIME_INTROSPECTION_SCHEMA_VERSION,
        "runtime_id": f"engine-runtime-{id(runtime_controller)}",
        "mode": runtime_controller.state,
        "timestamps": {
            "started_at": started_at_iso,
            "updated_at": started_at_iso,
        },
        "ownership": {
            "owner_tag": _RUNTIME_OWNERSHIP_TAG,
        },
        "extensions": [
            {
                "name": metadata.name,
                "point": metadata.point,
                "enabled": metadata.enabled,
                "source": metadata.source,
            }
            for metadata in _RUNTIME_OBSERVABILITY_REGISTRY.list_extensions_metadata()
        ],
    }


def get_runtime_observability_registry() -> RuntimeObservabilityRegistry:
    """Return the singleton runtime observability registry for metadata introspection."""

    return _RUNTIME_OBSERVABILITY_REGISTRY


for _point in ("health", "introspection", "status"):
    _RUNTIME_OBSERVABILITY_REGISTRY.register(
        _point,
        name=f"core.{_point}",
        extension=lambda _context: {},
        source="core",
        enabled=True,
    )

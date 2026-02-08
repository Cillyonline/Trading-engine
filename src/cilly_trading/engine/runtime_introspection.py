"""Read-only runtime introspection contract for API exposure."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TypedDict

from cilly_trading.engine.runtime_controller import get_runtime_controller

_RUNTIME_INTROSPECTION_SCHEMA_VERSION = "v1"
_RUNTIME_OWNERSHIP_TAG = "engine"
_RUNTIME_INTROSPECTION_STARTED_AT = datetime.now(timezone.utc)


class RuntimeIntrospectionTimestamps(TypedDict):
    started_at: str
    updated_at: str


class RuntimeIntrospectionOwnership(TypedDict):
    owner_tag: str


class RuntimeIntrospectionPayload(TypedDict):
    schema_version: str
    runtime_id: str
    mode: str
    timestamps: RuntimeIntrospectionTimestamps
    ownership: RuntimeIntrospectionOwnership


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
    }

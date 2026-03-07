"""Read-only system state payload for operator inspection."""

from __future__ import annotations

from typing import Literal, TypedDict

from cilly_trading.engine.runtime_introspection import (
    RuntimeIntrospectionPayload,
    get_runtime_introspection_payload,
)

_SYSTEM_STATE_SCHEMA_VERSION = "v1"
_SYSTEM_STATE_SOURCE = "engine_control_plane"


class SystemStateMetadata(TypedDict):
    read_only: Literal[True]
    source: str


class SystemStatePayload(TypedDict):
    schema_version: str
    status: str
    runtime: RuntimeIntrospectionPayload
    metadata: SystemStateMetadata


def get_system_state_payload() -> SystemStatePayload:
    """Return deterministic, read-only runtime state for operator inspection."""

    runtime_payload = get_runtime_introspection_payload()
    runtime_payload.setdefault("extensions", [])
    return {
        "schema_version": _SYSTEM_STATE_SCHEMA_VERSION,
        "status": runtime_payload["mode"],
        "runtime": runtime_payload,
        "metadata": {
            "read_only": True,
            "source": _SYSTEM_STATE_SOURCE,
        },
    }

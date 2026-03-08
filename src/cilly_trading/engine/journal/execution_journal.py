"""Deterministic execution journal artifact helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable, Mapping

from cilly_trading.engine.journal.system import (
    canonical_journal_json_bytes,
    load_journal_artifact,
    write_journal_artifact,
)

EXECUTION_JOURNAL_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["artifact", "artifact_version", "run", "lifecycle"],
    "additionalProperties": False,
    "properties": {
        "artifact": {"type": "string", "enum": ["execution_journal"]},
        "artifact_version": {"type": "string", "enum": ["1"]},
        "run": {
            "type": "object",
            "required": ["run_id", "deterministic", "created_at"],
            "additionalProperties": False,
            "properties": {
                "run_id": {"type": "string"},
                "deterministic": {"type": "boolean"},
                "created_at": {"type": "string"},
            },
        },
        "lifecycle": {
            "type": "array",
            "items": {"$ref": "#/$defs/lifecycle_event"},
        },
    },
    "$defs": {
        "lifecycle_event": {
            "type": "object",
            "required": ["event_id", "phase", "status", "sequence", "snapshot_id", "timestamp", "metadata"],
            "additionalProperties": False,
            "properties": {
                "event_id": {"type": "string"},
                "phase": {"type": "string"},
                "status": {"type": "string"},
                "sequence": {"type": "integer"},
                "snapshot_id": {"type": "string"},
                "timestamp": {"type": "string"},
                "metadata": {"type": "object"},
            },
        }
    },
}


def _normalize_lifecycle_events(events: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for event in events:
        normalized.append(
            {
                "event_id": str(event["event_id"]),
                "phase": str(event["phase"]),
                "status": str(event["status"]),
                "sequence": int(event["sequence"]),
                "snapshot_id": "" if event.get("snapshot_id") is None else str(event.get("snapshot_id")),
                "timestamp": "" if event.get("timestamp") is None else str(event.get("timestamp")),
                "metadata": dict(event.get("metadata", {})),
            }
        )

    normalized.sort(
        key=lambda event: (
            event["sequence"],
            event["event_id"],
            event["phase"],
            event["status"],
            event["snapshot_id"] or "",
            event["timestamp"] or "",
        )
    )
    return normalized


def build_execution_journal_artifact(
    *,
    run_id: str,
    lifecycle_events: Iterable[Mapping[str, Any]],
    deterministic: bool = True,
    created_at: str | None = None,
) -> dict[str, Any]:
    """Build deterministic execution journal payload for a run."""
    return {
        "artifact": "execution_journal",
        "artifact_version": "1",
        "run": {
            "run_id": str(run_id),
            "deterministic": bool(deterministic),
            "created_at": "" if created_at is None else str(created_at),
        },
        "lifecycle": _normalize_lifecycle_events(lifecycle_events),
    }


def canonical_execution_journal_json_bytes(payload: Mapping[str, Any]) -> bytes:
    """Serialize execution journal payload into canonical JSON bytes."""
    return canonical_journal_json_bytes(payload)


def write_execution_journal_artifact(
    run_dir: Path,
    payload: Mapping[str, Any],
    *,
    artifact_name: str = "execution-journal.json",
    hash_name: str = "execution-journal.sha256",
) -> tuple[Path, str]:
    """Write execution journal artifact and SHA sidecar under the run directory."""
    return write_journal_artifact(
        run_dir=run_dir,
        payload=payload,
        artifact_name=artifact_name,
        hash_name=hash_name,
        serializer=canonical_execution_journal_json_bytes,
    )


def load_execution_journal_artifact(path: Path) -> dict[str, Any]:
    """Load execution journal artifact payload."""
    return load_journal_artifact(path)

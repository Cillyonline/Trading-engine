"""Shared deterministic journal artifact IO helpers."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Callable, Mapping


def canonical_journal_json_bytes(payload: Mapping[str, Any]) -> bytes:
    """Serialize a journal payload into canonical UTF-8 JSON bytes with trailing LF."""
    return (
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def write_journal_artifact(
    *,
    run_dir: Path,
    payload: Mapping[str, Any],
    artifact_name: str,
    hash_name: str,
    serializer: Callable[[Mapping[str, Any]], bytes] = canonical_journal_json_bytes,
) -> tuple[Path, str]:
    """Write deterministic journal and SHA-256 sidecar into the run directory."""
    run_dir.mkdir(parents=True, exist_ok=True)

    artifact_bytes = serializer(payload)
    artifact_path = run_dir / artifact_name
    artifact_path.write_bytes(artifact_bytes)

    artifact_sha256 = hashlib.sha256(artifact_bytes).hexdigest()
    hash_path = run_dir / hash_name
    hash_path.write_text(f"{artifact_sha256}\n", encoding="utf-8")

    return artifact_path, artifact_sha256


def load_journal_artifact(path: Path) -> dict[str, Any]:
    """Load a JSON journal artifact from disk."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("journal artifact payload must be a JSON object")
    return payload

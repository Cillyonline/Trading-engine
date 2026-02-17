"""Deterministic backtest result artifact serialization helpers."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping


def canonical_json_bytes(payload: Mapping[str, Any]) -> bytes:
    """Serialize a backtest payload into canonical JSON UTF-8 bytes with trailing LF."""
    artifact_text = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ) + "\n"
    return artifact_text.encode("utf-8")


def write_artifact(
    output_dir: Path,
    payload: Mapping[str, Any],
    artifact_name: str = "backtest-result.json",
    hash_name: str = "backtest-result.sha256",
) -> tuple[Path, str]:
    """Write deterministic artifact JSON and SHA-256 sidecar file."""
    output_dir.mkdir(parents=True, exist_ok=True)

    artifact_bytes = canonical_json_bytes(payload)
    artifact_path = output_dir / artifact_name
    artifact_path.write_bytes(artifact_bytes)

    artifact_sha256 = hashlib.sha256(artifact_bytes).hexdigest()
    hash_path = output_dir / hash_name
    hash_path.write_bytes(f"{artifact_sha256}\n".encode("utf-8"))

    return artifact_path, artifact_sha256

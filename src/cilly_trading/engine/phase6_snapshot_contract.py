"""Phase-6 deterministic snapshot contract utilities."""

from __future__ import annotations

import hashlib
import json
import os
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

SnapshotId = str
SchemaVersion = str | int

DEFAULT_SNAPSHOT_DIR = Path("data/phase6_snapshots")
DEFAULT_RUN_DIR = Path("runs/phase6")
SNAPSHOT_METADATA_FILENAME = "metadata.json"
SNAPSHOT_PAYLOAD_FILENAME = "payload.json"


class SnapshotContractError(RuntimeError):
    """Raised when Phase-6 snapshot contract requirements are violated."""


class SnapshotNotFoundError(SnapshotContractError):
    """Raised when a snapshot ID cannot be resolved."""


class SnapshotMetadataError(SnapshotContractError):
    """Raised when snapshot metadata is invalid or incomplete."""


class SnapshotChecksumError(SnapshotContractError):
    """Raised when snapshot payload checksum does not match metadata."""


@dataclass(frozen=True)
class SnapshotMetadata:
    """Immutable metadata describing a deterministic snapshot.

    Args:
        snapshot_id: Stable snapshot identifier.
        provider: Snapshot data provider.
        source: Source descriptor (endpoint, dataset name, etc.).
        created_at_utc: ISO-8601 creation timestamp in UTC.
        payload_checksum: SHA-256 checksum of the snapshot payload bytes.
        schema_version: Snapshot schema version string or integer.
        notes: Optional notes about the snapshot.
    """

    snapshot_id: SnapshotId
    provider: str
    source: str
    created_at_utc: str
    payload_checksum: str
    schema_version: SchemaVersion
    notes: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable representation.

        Returns:
            Dictionary representation with stable key names.
        """
        payload: dict[str, Any] = {
            "snapshot_id": self.snapshot_id,
            "provider": self.provider,
            "source": self.source,
            "created_at_utc": self.created_at_utc,
            "payload_checksum": self.payload_checksum,
            "schema_version": self.schema_version,
        }
        if self.notes is not None:
            payload["notes"] = self.notes
        return payload


@dataclass(frozen=True)
class ResolvedSnapshot:
    """Resolved snapshot payload and metadata.

    Args:
        snapshot_id: Snapshot identifier.
        metadata: Immutable snapshot metadata.
        payload_path: Local path to the deterministic snapshot payload.
        payload_bytes: Raw payload bytes used for deterministic replay.
    """

    snapshot_id: SnapshotId
    metadata: SnapshotMetadata
    payload_path: Path
    payload_bytes: bytes


@dataclass(frozen=True)
class Phase6RunResult:
    """Result metadata for a Phase-6 deterministic run.

    Args:
        run_id: Persisted run identifier.
        audit_path: Path to the persisted audit record.
        result_path: Path to the deterministic result artifact.
        result_bytes: Raw bytes of the deterministic result artifact.
    """

    run_id: str
    audit_path: Path
    result_path: Path
    result_bytes: bytes


def resolve_snapshot(
    snapshot_id: SnapshotId,
    *,
    snapshot_dir: Optional[Path] = None,
) -> ResolvedSnapshot:
    """Resolve a snapshot ID into deterministic local payload bytes.

    Args:
        snapshot_id: Snapshot identifier to resolve.
        snapshot_dir: Optional base directory for snapshot payloads.

    Returns:
        ResolvedSnapshot with metadata and payload bytes.

    Raises:
        SnapshotNotFoundError: If the snapshot metadata or payload is missing.
        SnapshotMetadataError: If metadata is invalid or mismatched.
        SnapshotChecksumError: If payload checksum does not match metadata.
    """
    base_dir = snapshot_dir or DEFAULT_SNAPSHOT_DIR
    snapshot_root = base_dir / snapshot_id
    metadata_path = snapshot_root / SNAPSHOT_METADATA_FILENAME
    payload_path = snapshot_root / SNAPSHOT_PAYLOAD_FILENAME

    if not metadata_path.exists():
        raise SnapshotNotFoundError(f"snapshot_metadata_missing snapshot_id={snapshot_id}")
    if not payload_path.exists():
        raise SnapshotNotFoundError(f"snapshot_payload_missing snapshot_id={snapshot_id}")

    metadata = _load_snapshot_metadata(metadata_path)
    if metadata.snapshot_id != snapshot_id:
        raise SnapshotMetadataError(
            "snapshot_id_mismatch "
            f"expected={snapshot_id} metadata={metadata.snapshot_id}"
        )

    payload_bytes = payload_path.read_bytes()
    checksum = _sha256_bytes(payload_bytes)
    if checksum != metadata.payload_checksum:
        raise SnapshotChecksumError(
            "snapshot_checksum_mismatch "
            f"expected={metadata.payload_checksum} actual={checksum}"
        )

    return ResolvedSnapshot(
        snapshot_id=snapshot_id,
        metadata=metadata,
        payload_path=payload_path,
        payload_bytes=payload_bytes,
    )


def run_phase6_snapshot(
    snapshot_id: SnapshotId,
    *,
    snapshot_dir: Optional[Path] = None,
    run_output_dir: Optional[Path] = None,
    run_id: Optional[str] = None,
) -> Phase6RunResult:
    """Execute a deterministic Phase-6 run backed by a snapshot.

    Args:
        snapshot_id: Snapshot identifier (required).
        snapshot_dir: Optional base directory for snapshots.
        run_output_dir: Optional output directory for run artifacts.
        run_id: Optional run identifier to persist.

    Returns:
        Phase6RunResult containing artifact paths and bytes.

    Raises:
        ValueError: If snapshot_id is missing.
        SnapshotContractError: If snapshot resolution fails.
    """
    if not snapshot_id or not str(snapshot_id).strip():
        raise ValueError("snapshot_id is required for Phase-6 runs")

    resolved = resolve_snapshot(snapshot_id, snapshot_dir=snapshot_dir)
    run_identifier = run_id or str(uuid.uuid4())
    output_root = run_output_dir or DEFAULT_RUN_DIR
    run_dir = output_root / run_identifier
    run_dir.mkdir(parents=True, exist_ok=True)

    audit_path = persist_phase6_audit(
        run_id=run_identifier,
        snapshot_id=snapshot_id,
        metadata=resolved.metadata,
        output_dir=run_dir,
    )

    result_payload = {
        "snapshot_id": snapshot_id,
        "payload_checksum": resolved.metadata.payload_checksum,
        "provider": resolved.metadata.provider,
        "source": resolved.metadata.source,
        "created_at_utc": resolved.metadata.created_at_utc,
        "schema_version": resolved.metadata.schema_version,
    }
    result_json = json.dumps(result_payload, sort_keys=True, separators=(",", ":"))
    result_path = run_dir / "result.json"
    result_path.write_text(result_json, encoding="utf-8")

    return Phase6RunResult(
        run_id=run_identifier,
        audit_path=audit_path,
        result_path=result_path,
        result_bytes=result_json.encode("utf-8"),
    )


def persist_phase6_audit(
    *,
    run_id: str,
    snapshot_id: SnapshotId,
    metadata: SnapshotMetadata,
    output_dir: Path,
) -> Path:
    """Persist a Phase-6 audit record with snapshot metadata.

    Args:
        run_id: Unique run identifier.
        snapshot_id: Snapshot identifier used for the run.
        metadata: Snapshot metadata.
        output_dir: Directory to store audit artifacts.

    Returns:
        Path to the persisted audit JSON file.
    """
    payload: dict[str, Any] = {
        "run_id": run_id,
        "snapshot_id": snapshot_id,
        "snapshot_metadata": metadata.to_dict(),
    }
    engine_version = _get_engine_version()
    if engine_version is not None:
        payload["engine_version"] = engine_version

    audit_json = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    audit_path = output_dir / "audit.json"
    audit_path.write_text(audit_json, encoding="utf-8")
    return audit_path


def _load_snapshot_metadata(metadata_path: Path) -> SnapshotMetadata:
    raw = json.loads(metadata_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise SnapshotMetadataError("snapshot_metadata_invalid")

    required = {
        "snapshot_id",
        "provider",
        "source",
        "created_at_utc",
        "payload_checksum",
        "schema_version",
    }
    missing = sorted(required - set(raw.keys()))
    if missing:
        raise SnapshotMetadataError(f"snapshot_metadata_missing_fields {','.join(missing)}")

    return SnapshotMetadata(
        snapshot_id=_coerce_str(raw["snapshot_id"], field="snapshot_id"),
        provider=_coerce_str(raw["provider"], field="provider"),
        source=_coerce_str(raw["source"], field="source"),
        created_at_utc=_coerce_str(raw["created_at_utc"], field="created_at_utc"),
        payload_checksum=_coerce_str(raw["payload_checksum"], field="payload_checksum"),
        schema_version=_coerce_schema_version(raw["schema_version"]),
        notes=_coerce_optional_str(raw.get("notes"), field="notes"),
    )


def _coerce_str(value: Any, *, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise SnapshotMetadataError(f"snapshot_metadata_invalid_{field}")
    return value


def _coerce_optional_str(value: Any, *, field: str) -> Optional[str]:
    if value is None:
        return None
    if not isinstance(value, str):
        raise SnapshotMetadataError(f"snapshot_metadata_invalid_{field}")
    return value


def _coerce_schema_version(value: Any) -> SchemaVersion:
    if isinstance(value, (str, int)):
        return value
    raise SnapshotMetadataError("snapshot_metadata_invalid_schema_version")


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _get_engine_version() -> Optional[str]:
    return os.getenv("CILLY_ENGINE_VERSION")

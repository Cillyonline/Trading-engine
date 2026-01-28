from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from cilly_trading.engine.phase6_snapshot_contract import (
    SnapshotNotFoundError,
    run_phase6_snapshot,
)


SNAPSHOT_ID = "test-snapshot-0001"
SNAPSHOT_DIR = Path("data/phase6_snapshots")


def test_phase6_snapshot_id_required() -> None:
    with pytest.raises(ValueError, match="snapshot_id is required"):
        run_phase6_snapshot("")


def test_phase6_unknown_snapshot_id_fails(tmp_path: Path) -> None:
    with pytest.raises(SnapshotNotFoundError, match="snapshot_metadata_missing"):
        run_phase6_snapshot("missing-snapshot", snapshot_dir=tmp_path)


def test_phase6_snapshot_audit_persisted(tmp_path: Path) -> None:
    result = run_phase6_snapshot(
        SNAPSHOT_ID,
        snapshot_dir=SNAPSHOT_DIR,
        run_output_dir=tmp_path,
    )

    audit_payload = json.loads(result.audit_path.read_text(encoding="utf-8"))
    assert audit_payload["run_id"] == result.run_id
    assert audit_payload["snapshot_id"] == SNAPSHOT_ID

    metadata = audit_payload["snapshot_metadata"]
    assert metadata["snapshot_id"] == SNAPSHOT_ID
    assert metadata["provider"] == "test-provider"
    assert metadata["source"] == "unit-test"
    assert metadata["created_at_utc"] == "2025-01-01T00:00:00Z"
    assert metadata["payload_checksum"]
    assert metadata["schema_version"] == "1"


def test_phase6_replay_is_deterministic(tmp_path: Path) -> None:
    first = run_phase6_snapshot(
        SNAPSHOT_ID,
        snapshot_dir=SNAPSHOT_DIR,
        run_output_dir=tmp_path,
    )
    second = run_phase6_snapshot(
        SNAPSHOT_ID,
        snapshot_dir=SNAPSHOT_DIR,
        run_output_dir=tmp_path,
    )

    first_hash = hashlib.sha256(first.result_bytes).hexdigest()
    second_hash = hashlib.sha256(second.result_bytes).hexdigest()

    assert first.result_bytes == second.result_bytes
    assert first_hash == second_hash

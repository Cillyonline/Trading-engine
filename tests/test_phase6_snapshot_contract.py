from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from cilly_trading.engine.phase6_snapshot_contract import (
    SnapshotChecksumError,
    SnapshotNotFoundError,
    execute_snapshot_runtime,
    run_phase6_snapshot,
)


SNAPSHOT_ID = "test-snapshot-0001"


def _create_snapshot_fixture(snapshot_root: Path, snapshot_id: str = SNAPSHOT_ID) -> Path:
    payload = {
        "rows": [
            {"close": 101.25, "high": 102.0, "low": 100.9, "symbol": "AAPL", "ts": "2025-01-01"},
            {"close": 101.6, "high": 102.1, "low": 101.2, "symbol": "AAPL", "ts": "2025-01-02"},
        ]
    }
    payload_bytes = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    payload_checksum = hashlib.sha256(payload_bytes).hexdigest()

    snapshot_dir = snapshot_root / snapshot_id
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    (snapshot_dir / "payload.json").write_bytes(payload_bytes)

    metadata = {
        "created_at_utc": "2025-01-01T00:00:00Z",
        "payload_checksum": payload_checksum,
        "provider": "test-provider",
        "schema_version": "1",
        "snapshot_id": snapshot_id,
        "source": "unit-test",
    }
    (snapshot_dir / "metadata.json").write_text(
        json.dumps(metadata, sort_keys=True, separators=(",", ":")),
        encoding="utf-8",
    )
    return snapshot_root


def test_phase6_snapshot_id_required() -> None:
    with pytest.raises(ValueError, match="snapshot_id is required"):
        run_phase6_snapshot("")


def test_phase6_unknown_snapshot_id_fails(tmp_path: Path) -> None:
    with pytest.raises(SnapshotNotFoundError, match="snapshot_metadata_missing"):
        run_phase6_snapshot("missing-snapshot", snapshot_dir=tmp_path)


def test_phase6_snapshot_audit_persisted(tmp_path: Path) -> None:
    snapshot_dir = _create_snapshot_fixture(tmp_path)

    result = run_phase6_snapshot(
        SNAPSHOT_ID,
        snapshot_dir=snapshot_dir,
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
    snapshot_dir = _create_snapshot_fixture(tmp_path)

    first = run_phase6_snapshot(
        SNAPSHOT_ID,
        snapshot_dir=snapshot_dir,
        run_output_dir=tmp_path,
    )
    second = run_phase6_snapshot(
        SNAPSHOT_ID,
        snapshot_dir=snapshot_dir,
        run_output_dir=tmp_path,
    )

    first_hash = hashlib.sha256(first.result_bytes).hexdigest()
    second_hash = hashlib.sha256(second.result_bytes).hexdigest()

    assert first.result_bytes == second.result_bytes
    assert first_hash == second_hash


def test_execute_snapshot_runtime_structure_smoke(tmp_path: Path) -> None:
    snapshot_dir = _create_snapshot_fixture(tmp_path)

    payload = execute_snapshot_runtime(SNAPSHOT_ID, snapshot_dir=snapshot_dir)

    assert set(payload.keys()) == {
        "snapshot_consistent",
        "snapshot_id",
        "snapshot_metadata",
    }
    assert isinstance(payload["snapshot_consistent"], bool)
    assert isinstance(payload["snapshot_id"], str)
    assert set(payload["snapshot_metadata"].keys()) == {
        "snapshot_id",
        "provider",
        "source",
        "created_at_utc",
        "payload_checksum",
        "schema_version",
    }
    assert isinstance(payload["snapshot_metadata"]["snapshot_id"], str)
    assert isinstance(payload["snapshot_metadata"]["provider"], str)
    assert isinstance(payload["snapshot_metadata"]["source"], str)
    assert isinstance(payload["snapshot_metadata"]["created_at_utc"], str)
    assert isinstance(payload["snapshot_metadata"]["payload_checksum"], str)
    assert isinstance(payload["snapshot_metadata"]["schema_version"], str | int)


def test_execute_snapshot_runtime_is_deterministic_across_runs(tmp_path: Path) -> None:
    snapshot_dir = _create_snapshot_fixture(tmp_path)

    runs = [execute_snapshot_runtime(SNAPSHOT_ID, snapshot_dir=snapshot_dir) for _ in range(5)]
    hashes = {
        hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
        for payload in runs
    }

    assert all(payload == runs[0] for payload in runs[1:])
    assert len(hashes) == 1


def test_execute_snapshot_runtime_snapshot_id_required() -> None:
    with pytest.raises(ValueError, match="snapshot_id is required"):
        execute_snapshot_runtime("")


def test_execute_snapshot_runtime_fails_on_corrupted_payload_checksum(tmp_path: Path) -> None:
    snapshot_dir = _create_snapshot_fixture(tmp_path)
    payload_path = snapshot_dir / SNAPSHOT_ID / "payload.json"
    payload = json.loads(payload_path.read_text(encoding="utf-8"))
    payload["rows"][0]["close"] = 999.99
    payload_path.write_text(
        json.dumps(payload, sort_keys=True, separators=(",", ":")),
        encoding="utf-8",
    )

    with pytest.raises(SnapshotChecksumError, match="snapshot_checksum_mismatch"):
        execute_snapshot_runtime(SNAPSHOT_ID, snapshot_dir=snapshot_dir)


def test_execute_snapshot_runtime_fails_when_metadata_missing(tmp_path: Path) -> None:
    snapshot_dir = _create_snapshot_fixture(tmp_path)
    metadata_path = snapshot_dir / SNAPSHOT_ID / "metadata.json"
    metadata_path.unlink()

    with pytest.raises(SnapshotNotFoundError, match="snapshot_metadata_missing"):
        execute_snapshot_runtime(SNAPSHOT_ID, snapshot_dir=snapshot_dir)


def test_execute_snapshot_runtime_logs_execution_event(
    caplog: pytest.LogCaptureFixture,
    tmp_path: Path,
) -> None:
    snapshot_dir = _create_snapshot_fixture(tmp_path)

    with caplog.at_level("INFO"):
        payload = execute_snapshot_runtime(SNAPSHOT_ID, snapshot_dir=snapshot_dir)

    assert payload["snapshot_consistent"] is True
    assert any(
        record.message.startswith("snapshot_runtime_executed snapshot_id=test-snapshot-0001 payload=")
        for record in caplog.records
    )

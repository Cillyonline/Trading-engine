from __future__ import annotations

import hashlib
from pathlib import Path

from cilly_trading.engine.journal.execution_journal import (
    EXECUTION_JOURNAL_SCHEMA,
    build_execution_journal_artifact,
    canonical_execution_journal_json_bytes,
    load_execution_journal_artifact,
    write_execution_journal_artifact,
)
from tests.utils.json_schema_validator import validate_json_schema


def _lifecycle_events() -> list[dict[str, object]]:
    return [
        {
            "event_id": "evt-run-end",
            "phase": "run",
            "status": "completed",
            "sequence": 3,
            "snapshot_id": None,
            "timestamp": "2024-01-01T00:02:00Z",
            "metadata": {"processed": 2},
        },
        {
            "event_id": "evt-s1",
            "phase": "snapshot",
            "status": "processed",
            "sequence": 2,
            "snapshot_id": "s1",
            "timestamp": "2024-01-01T00:01:00Z",
            "metadata": {"symbol": "AAPL"},
        },
        {
            "event_id": "evt-run-start",
            "phase": "run",
            "status": "started",
            "sequence": 1,
            "snapshot_id": None,
            "timestamp": "2024-01-01T00:00:00Z",
            "metadata": {"mode": "backtest"},
        },
    ]


def test_execution_journal_artifact_generation_and_run_level_storage(tmp_path: Path) -> None:
    payload = build_execution_journal_artifact(
        run_id="run-001",
        lifecycle_events=_lifecycle_events(),
        deterministic=True,
        created_at=None,
    )

    artifact_path, sha_value = write_execution_journal_artifact(tmp_path / "runs" / "run-001", payload)

    assert artifact_path == tmp_path / "runs" / "run-001" / "execution-journal.json"
    assert artifact_path.exists()
    assert (tmp_path / "runs" / "run-001" / "execution-journal.sha256").read_text(
        encoding="utf-8"
    ) == f"{sha_value}\n"

    loaded_payload = load_execution_journal_artifact(artifact_path)
    assert loaded_payload == payload


def test_execution_journal_schema_validation() -> None:
    payload = build_execution_journal_artifact(
        run_id="run-001",
        lifecycle_events=_lifecycle_events(),
    )
    errors = validate_json_schema(payload, EXECUTION_JOURNAL_SCHEMA)
    assert errors == []

    invalid_payload = dict(payload)
    invalid_payload.pop("run")
    invalid_errors = validate_json_schema(invalid_payload, EXECUTION_JOURNAL_SCHEMA)
    assert any(error.message == "Missing required property: run" for error in invalid_errors)


def test_execution_journal_serialization_is_deterministic() -> None:
    payload_a = build_execution_journal_artifact(
        run_id="run-001",
        lifecycle_events=_lifecycle_events(),
    )
    payload_b = build_execution_journal_artifact(
        run_id="run-001",
        lifecycle_events=list(reversed(_lifecycle_events())),
    )

    bytes_a = canonical_execution_journal_json_bytes(payload_a)
    bytes_b = canonical_execution_journal_json_bytes(payload_b)

    assert payload_a == payload_b
    assert bytes_a == bytes_b
    assert bytes_a.endswith(b"\n")
    assert b"\r\n" not in bytes_a
    assert hashlib.sha256(bytes_a).hexdigest() == hashlib.sha256(bytes_b).hexdigest()

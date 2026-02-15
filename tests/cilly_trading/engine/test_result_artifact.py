from __future__ import annotations

from pathlib import Path

from cilly_trading.engine.result_artifact import canonical_json_bytes, write_artifact


def _minimal_payload() -> dict[str, object]:
    return {
        "artifact_version": "1",
        "engine": {"name": "cilly_trading.engine.backtest_runner", "version": None},
        "run": {"run_id": "fixed-run", "created_at": None, "deterministic": True},
        "snapshot_linkage": {
            "mode": "timestamp",
            "start": "2024-01-01T00:00:00Z",
            "end": "2024-01-02T00:00:00Z",
            "count": 2,
        },
        "strategy": {"name": "demo", "version": None, "params": {"alpha": "1"}},
        "invocation_log": ["on_run_start", "on_snapshot:s1", "on_run_end"],
        "processed_snapshots": [
            {"id": "s1", "timestamp": "2024-01-01T00:00:00Z"},
            {"id": "s2", "timestamp": "2024-01-02T00:00:00Z"},
        ],
        "orders": [],
        "fills": [],
        "positions": [],
    }


def test_write_artifact_deterministic_hash_verification(tmp_path: Path) -> None:
    payload = _minimal_payload()

    run1_dir = tmp_path / "run1"
    run2_dir = tmp_path / "run2"

    artifact_path_1, sha_1 = write_artifact(run1_dir, payload)
    artifact_path_2, sha_2 = write_artifact(run2_dir, payload)

    artifact_bytes_1 = artifact_path_1.read_bytes()
    artifact_bytes_2 = artifact_path_2.read_bytes()

    assert artifact_bytes_1 == artifact_bytes_2
    assert sha_1 == sha_2

    sidecar_1 = (run1_dir / "backtest-result.sha256").read_text(encoding="utf-8")
    sidecar_2 = (run2_dir / "backtest-result.sha256").read_text(encoding="utf-8")
    assert sidecar_1 == f"{sha_1}\n"
    assert sidecar_2 == f"{sha_2}\n"

    assert artifact_bytes_1.endswith(b"\n")
    assert b"\r\n" not in artifact_bytes_1


def test_canonical_json_bytes_stable_key_ordering() -> None:
    payload = {
        "z": 1,
        "a": {"z": 3, "a": 2},
        "run": {"run_id": "fixed-run", "deterministic": True, "created_at": None},
    }

    rendered = canonical_json_bytes(payload).decode("utf-8")
    expected = '{"a":{"a":2,"z":3},"run":{"created_at":null,"deterministic":true,"run_id":"fixed-run"},"z":1}\n'
    assert rendered == expected

from __future__ import annotations

from pathlib import Path

from tests.determinism.determinism_gate import run_gate


def test_determinism_gate_passes(tmp_path: Path) -> None:
    result = run_gate(artifact_dir=tmp_path, runs=3)

    assert result.passed is True
    assert result.db_check_status == "PASS"
    assert len(result.artifact_paths) == 3
    assert len(result.run_hashes) == 3
    assert result.run_hashes[0] == result.run_hashes[1] == result.run_hashes[2]
    assert result.deviations == []
    assert result.deviation_file is None
    assert len(result.artifact_contents) == 3
    assert result.artifact_contents[0] == result.artifact_contents[1] == result.artifact_contents[2]
    for artifact_path in result.artifact_paths:
        assert artifact_path.exists()

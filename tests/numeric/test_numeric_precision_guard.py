from __future__ import annotations

from pathlib import Path

from tests.utils.golden_master import prepare_snapshot_db, run_fixed_analysis, stable_json_dumps
from tests.utils.numeric_precision import find_numeric_precision_violations


def _build_payload(tmp_path: Path) -> dict:
    tmp_path.mkdir(parents=True, exist_ok=True)
    db_path = tmp_path / "analysis.db"
    prepare_snapshot_db(db_path)
    return run_fixed_analysis(db_path)


def test_numeric_precision_rule(tmp_path: Path) -> None:
    payload = _build_payload(tmp_path / "precision")
    violations = find_numeric_precision_violations(payload)
    assert not violations, (
        "Numeric precision drift detected:\n"
        + "\n".join(
            f"- {violation.path}: value={violation.value} rounded={violation.rounded} delta={violation.delta}"
            for violation in violations
        )
    )


def test_numeric_output_stable_across_runs(tmp_path: Path) -> None:
    payload_a = _build_payload(tmp_path / "run_a")
    payload_b = _build_payload(tmp_path / "run_b")

    json_a = stable_json_dumps(payload_a)
    json_b = stable_json_dumps(payload_b)

    assert json_a == json_b

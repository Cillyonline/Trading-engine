from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


def _run_cli(args: list[str], env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    run_env = dict(os.environ)
    if env is not None:
        run_env.update(env)

    project_paths = [str(Path.cwd()), str(Path.cwd() / "src")]
    existing_pythonpath = run_env.get("PYTHONPATH")
    if existing_pythonpath:
        run_env["PYTHONPATH"] = os.pathsep.join(project_paths + [existing_pythonpath])
    else:
        run_env["PYTHONPATH"] = os.pathsep.join(project_paths)

    return subprocess.run(
        [sys.executable, "-m", "cilly_trading", *args],
        check=False,
        capture_output=True,
        text=True,
        env=run_env,
    )


def test_cli_backtest_happy_path_creates_artifact(tmp_path: Path) -> None:
    snapshots_path = tmp_path / "snapshots.json"
    snapshots_path.write_text(
        json.dumps(
            [
                {"id": "s1", "timestamp": "2024-01-01T00:00:00Z", "price": 10},
                {"id": "s2", "timestamp": "2024-01-02T00:00:00Z", "price": 11},
            ]
        ),
        encoding="utf-8",
    )
    out_dir = tmp_path / "out"

    result = _run_cli(
        [
            "backtest",
            "--snapshots",
            str(snapshots_path),
            "--strategy",
            "REFERENCE",
            "--out",
            str(out_dir),
        ]
    )

    assert result.returncode == 0
    artifact_path = out_dir / "backtest-result.json"
    assert artifact_path.exists()
    assert artifact_path.read_text(encoding="utf-8").endswith("\n")


def test_cli_backtest_invalid_snapshot_file_exit_20(tmp_path: Path) -> None:
    snapshots_path = tmp_path / "invalid.json"
    snapshots_path.write_text("{\"not\":\"a list\"}", encoding="utf-8")

    result = _run_cli(
        [
            "backtest",
            "--snapshots",
            str(snapshots_path),
            "--strategy",
            "REFERENCE",
            "--out",
            str(tmp_path / "out"),
        ]
    )

    assert result.returncode == 20




def test_cli_backtest_malformed_snapshot_item_exit_20(tmp_path: Path) -> None:
    snapshots_path = tmp_path / "invalid-item.json"
    snapshots_path.write_text('[{"id":"x"}]', encoding="utf-8")

    result = _run_cli(
        [
            "backtest",
            "--snapshots",
            str(snapshots_path),
            "--strategy",
            "REFERENCE",
            "--out",
            str(tmp_path / "out"),
        ]
    )

    assert result.returncode == 20

def test_cli_backtest_unknown_strategy_exit_30(tmp_path: Path) -> None:
    snapshots_path = tmp_path / "snapshots.json"
    snapshots_path.write_text("[]", encoding="utf-8")

    result = _run_cli(
        [
            "backtest",
            "--snapshots",
            str(snapshots_path),
            "--strategy",
            "definitely-not-a-real-strategy",
            "--out",
            str(tmp_path / "out"),
        ]
    )

    assert result.returncode == 30


def test_cli_backtest_determinism_violation_exit_10(tmp_path: Path) -> None:
    snapshots_path = tmp_path / "snapshots.json"
    snapshots_path.write_text("[]", encoding="utf-8")

    result = _run_cli(
        [
            "backtest",
            "--snapshots",
            str(snapshots_path),
            "--strategy-module",
            "tests.backtest_test_strategies",
            "--strategy",
            "TEST_TIME_VIOLATION",
            "--out",
            str(tmp_path / "out"),
        ],
    )

    assert result.returncode == 10
    assert "Determinism violation" in result.stderr


def test_cli_backtest_repeated_runs_emit_reproducible_evidence_with_explicit_assumptions(
    tmp_path: Path,
) -> None:
    snapshots_path = tmp_path / "snapshots.json"
    snapshots_path.write_text(
        json.dumps(
            [
                {"id": "s1", "timestamp": "2024-01-01T00:00:00Z", "symbol": "AAPL", "open": "100"},
                {"id": "s2", "timestamp": "2024-01-02T00:00:00Z", "symbol": "AAPL", "open": "101"},
            ]
        ),
        encoding="utf-8",
    )

    run_id = "evidence-run-001"
    out_one = tmp_path / "out-one"
    out_two = tmp_path / "out-two"

    first = _run_cli(
        [
            "backtest",
            "--snapshots",
            str(snapshots_path),
            "--strategy",
            "REFERENCE",
            "--out",
            str(out_one),
            "--run-id",
            run_id,
        ]
    )
    second = _run_cli(
        [
            "backtest",
            "--snapshots",
            str(snapshots_path),
            "--strategy",
            "REFERENCE",
            "--out",
            str(out_two),
            "--run-id",
            run_id,
        ]
    )

    assert first.returncode == 0
    assert second.returncode == 0

    artifact_one = out_one / "backtest-result.json"
    artifact_two = out_two / "backtest-result.json"
    hash_one = out_one / "backtest-result.sha256"
    hash_two = out_two / "backtest-result.sha256"

    assert artifact_one.read_bytes() == artifact_two.read_bytes()
    assert hash_one.read_text(encoding="utf-8") == hash_two.read_text(encoding="utf-8")

    payload = json.loads(artifact_one.read_text(encoding="utf-8"))
    run_config = payload["run_config"]
    execution_assumptions = run_config["execution_assumptions"]

    assert payload["run"]["run_id"] == run_id
    assert payload["run"]["deterministic"] is True
    assert run_config["reproducibility_metadata"]["run_id"] == run_id
    assert run_config["reproducibility_metadata"]["strategy_name"] == "REFERENCE"
    assert execution_assumptions == {
        "fill_model": "deterministic_market",
        "fill_timing": "next_snapshot",
        "price_source": "open_then_price",
        "slippage_bps": 0,
        "commission_per_order": "0",
        "partial_fills_allowed": False,
        "spread_bps": 0,
    }
    assert payload["metrics_baseline"]["assumptions"] == execution_assumptions


def test_cli_backtest_different_run_ids_change_evidence_identity(tmp_path: Path) -> None:
    snapshots_path = tmp_path / "snapshots.json"
    snapshots_path.write_text(
        json.dumps(
            [
                {"id": "s1", "timestamp": "2024-01-01T00:00:00Z", "price": 10},
                {"id": "s2", "timestamp": "2024-01-02T00:00:00Z", "price": 11},
            ]
        ),
        encoding="utf-8",
    )

    out_alpha = tmp_path / "out-alpha"
    out_beta = tmp_path / "out-beta"

    alpha = _run_cli(
        [
            "backtest",
            "--snapshots",
            str(snapshots_path),
            "--strategy",
            "REFERENCE",
            "--out",
            str(out_alpha),
            "--run-id",
            "identity-alpha",
        ]
    )
    beta = _run_cli(
        [
            "backtest",
            "--snapshots",
            str(snapshots_path),
            "--strategy",
            "REFERENCE",
            "--out",
            str(out_beta),
            "--run-id",
            "identity-beta",
        ]
    )

    assert alpha.returncode == 0
    assert beta.returncode == 0

    alpha_artifact = out_alpha / "backtest-result.json"
    beta_artifact = out_beta / "backtest-result.json"
    alpha_payload = json.loads(alpha_artifact.read_text(encoding="utf-8"))
    beta_payload = json.loads(beta_artifact.read_text(encoding="utf-8"))

    assert alpha_payload["run"]["run_id"] == "identity-alpha"
    assert beta_payload["run"]["run_id"] == "identity-beta"
    assert alpha_payload["run_config"]["reproducibility_metadata"]["run_id"] == "identity-alpha"
    assert beta_payload["run_config"]["reproducibility_metadata"]["run_id"] == "identity-beta"
    assert alpha_artifact.read_bytes() != beta_artifact.read_bytes()

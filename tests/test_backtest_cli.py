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

    env = dict(os.environ)
    env["CILLY_BACKTEST_TEST_STRATEGY_IMPORT"] = (
        "TEST_TIME_VIOLATION=tests.backtest_test_strategies:create_determinism_violation_strategy"
    )

    result = _run_cli(
        [
            "backtest",
            "--snapshots",
            str(snapshots_path),
            "--strategy",
            "TEST_TIME_VIOLATION",
            "--out",
            str(tmp_path / "out"),
        ],
        env=env,
    )

    assert result.returncode == 10
    assert "Determinism violation" in result.stderr

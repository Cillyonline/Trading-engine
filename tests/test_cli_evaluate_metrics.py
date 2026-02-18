from __future__ import annotations

import hashlib
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


def _build_artifact() -> dict[str, object]:
    return {
        "summary": {"start_equity": 10000, "end_equity": 10500},
        "equity_curve": [
            {"timestamp": "2024-01-01T00:00:00Z", "equity": 10000},
            {"timestamp": "2024-01-02T00:00:00Z", "equity": 10250},
            {"timestamp": "2024-01-03T00:00:00Z", "equity": 10500},
        ],
        "trades": [
            {"trade_id": "t1", "exit_ts": "2024-01-02T00:00:00Z", "pnl": 100},
            {"trade_id": "t2", "exit_ts": "2024-01-03T00:00:00Z", "pnl": -50},
        ],
    }


def test_cli_evaluate_is_deterministic_across_three_runs(tmp_path: Path) -> None:
    artifact_path = tmp_path / "backtest-result.json"
    artifact_path.write_text(json.dumps(_build_artifact()), encoding="utf-8")

    output_bytes: list[bytes] = []
    output_hashes: list[str] = []

    for idx in range(3):
        out_dir = tmp_path / f"out-{idx}"
        result = _run_cli(
            [
                "evaluate",
                "--artifact",
                str(artifact_path),
                "--out",
                str(out_dir),
            ]
        )

        assert result.returncode == 0
        artifact_output = out_dir / "metrics-result.json"
        assert artifact_output.exists()

        content = artifact_output.read_bytes()
        output_bytes.append(content)
        output_hashes.append(hashlib.sha256(content).hexdigest())

    assert output_bytes[0] == output_bytes[1] == output_bytes[2]
    assert output_hashes[0] == output_hashes[1] == output_hashes[2]


def test_cli_evaluate_missing_artifact_exit_20(tmp_path: Path) -> None:
    missing_path = tmp_path / "missing-artifact.json"

    result = _run_cli(
        [
            "evaluate",
            "--artifact",
            str(missing_path),
            "--out",
            str(tmp_path / "out"),
        ]
    )

    assert result.returncode == 20

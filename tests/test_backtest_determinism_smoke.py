from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path


def _run_backtest(args: list[str], env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
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


def test_backtest_cli_produces_identical_artifacts_across_three_runs(tmp_path: Path) -> None:
    snapshots_path = tmp_path / "snapshots.json"
    snapshots_path.write_text(
        json.dumps(
            [
                {"id": "s1", "timestamp": "2024-01-01T00:00:00Z", "price": 10},
                {"id": "s2", "timestamp": "2024-01-02T00:00:00Z", "price": 11},
                {"id": "s3", "timestamp": "2024-01-03T00:00:00Z", "price": 12},
            ]
        ),
        encoding="utf-8",
    )

    artifacts: list[bytes] = []
    hashes: list[str] = []

    for run_index in range(3):
        out_dir = tmp_path / f"out-{run_index}"
        result = _run_backtest(
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

        artifact_bytes = (out_dir / "backtest-result.json").read_bytes()
        artifacts.append(artifact_bytes)
        hashes.append(hashlib.sha256(artifact_bytes).hexdigest())

    assert artifacts[0] == artifacts[1] == artifacts[2]
    assert hashes[0] == hashes[1] == hashes[2]

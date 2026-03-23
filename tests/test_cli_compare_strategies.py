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


def _comparison_snapshots() -> list[dict[str, object]]:
    snapshots: list[dict[str, object]] = []
    for day in range(1, 26):
        timestamp = f"2024-01-{day:02d}T00:00:00Z"
        if day <= 20:
            close = 100
        elif day == 21:
            close = 105
        elif day == 22:
            close = 106
        else:
            close = 130

        snapshots.append(
            {
                "id": f"s{day:02d}",
                "timestamp": timestamp,
                "symbol": "AAPL",
                "open": close,
                "high": close,
                "low": close - 1,
                "close": close,
                "price": close,
            }
        )
    return snapshots


def test_cli_compare_strategies_happy_path(tmp_path: Path) -> None:
    snapshots_path = tmp_path / "snapshots.json"
    snapshots_path.write_text(json.dumps(_comparison_snapshots()), encoding="utf-8")
    out_dir = tmp_path / "out"

    result = _run_cli(
        [
            "compare-strategies",
            "--snapshots",
            str(snapshots_path),
            "--strategy",
            "REFERENCE",
            "--strategy",
            "TURTLE",
            "--benchmark-strategy",
            "REFERENCE",
            "--out",
            str(out_dir),
        ]
    )

    assert result.returncode == 0
    artifact_path = out_dir / "strategy-comparison.json"
    assert artifact_path.exists()

    payload = json.loads(artifact_path.read_text(encoding="utf-8"))
    assert payload["workflow"]["benchmark_strategy"] == "REFERENCE"
    assert [row["strategy_name"] for row in payload["ranking"]] == ["TURTLE", "REFERENCE"]


from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory


def _run_smoke(repo_root: Path) -> tuple[subprocess.CompletedProcess[str], bytes]:
    src_dir = repo_root / "src"
    fixtures_src_dir = repo_root / "fixtures" / "smoke-run"

    with TemporaryDirectory() as temp_path:
        temp_dir = Path(temp_path)
        shutil.copytree(
            fixtures_src_dir,
            temp_dir / "fixtures" / "smoke-run",
            dirs_exist_ok=True,
        )

        env = os.environ.copy()
        env["PYTHONPATH"] = str(src_dir)

        completed = subprocess.run(
            [sys.executable, "-m", "cilly_trading.smoke_run"],
            capture_output=True,
            text=True,
            env=env,
            cwd=temp_dir,
            check=False,
        )

        result_path = temp_dir / "artifacts" / "smoke-run" / "result.json"
        assert result_path.is_file()
        artifact_bytes = result_path.read_bytes()

        return completed, artifact_bytes


def test_smoke_run_module_is_deterministic() -> None:
    repo_root = Path(__file__).resolve().parents[1]

    first, first_bytes = _run_smoke(repo_root)
    second, second_bytes = _run_smoke(repo_root)

    expected_lines = [
        "SMOKE_RUN:START",
        "SMOKE_RUN:FIXTURES_OK",
        "SMOKE_RUN:CHECKS_OK",
        "SMOKE_RUN:END",
    ]

    for completed in (first, second):
        assert completed.returncode == 0
        stdout_lines = completed.stdout.splitlines()
        assert stdout_lines == expected_lines
        assert completed.stderr == ""

    assert first_bytes == second_bytes

from __future__ import annotations

from pathlib import Path
import random
import secrets
import socket
import time
import urllib.request

import pytest

from cilly_trading.engine.deterministic_guard import DeterminismViolationError, determinism_guard
from cilly_trading.engine.deterministic_run import run_deterministic_analysis


def test_deterministic_run_repeats(tmp_path: Path) -> None:
    fixtures_dir = Path(__file__).resolve().parents[1] / "fixtures" / "deterministic-analysis"
    outputs = []
    for idx in range(3):
        output_path = tmp_path / f"run_{idx}.json"
        db_path = tmp_path / f"run_{idx}.db"
        run_deterministic_analysis(
            fixtures_dir=fixtures_dir,
            output_path=output_path,
            db_path=db_path,
        )
        outputs.append(output_path.read_bytes())

    assert outputs[0] == outputs[1] == outputs[2]


def test_determinism_guard_blocks_time_random_network() -> None:
    with determinism_guard():
        with pytest.raises(
            DeterminismViolationError,
            match="determinism_guard_violation:time.time",
        ):
            time.time()
        with pytest.raises(
            DeterminismViolationError,
            match="determinism_guard_violation:random.random",
        ):
            random.random()
        with pytest.raises(
            DeterminismViolationError,
            match="determinism_guard_violation:socket.socket",
        ):
            socket.socket()
        with pytest.raises(
            DeterminismViolationError,
            match="determinism_guard_violation:secrets.token_hex",
        ):
            secrets.token_hex(8)
        with pytest.raises(
            DeterminismViolationError,
            match="determinism_guard_violation:urllib.request.urlopen",
        ):
            urllib.request.urlopen("https://example.com")  # nosec

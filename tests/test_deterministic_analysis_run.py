from __future__ import annotations

import json
from pathlib import Path
import datetime as datetime_module
import os
import random
import secrets
import socket
import time
import urllib.request

import pytest

from cilly_trading.engine.deterministic_guard import DeterminismViolationError, determinism_guard
from cilly_trading.engine.data import SnapshotIngestionError
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


def test_deterministic_run_repeats_same_db(tmp_path: Path) -> None:
    fixtures_dir = Path(__file__).resolve().parents[1] / "fixtures" / "deterministic-analysis"
    output_path = tmp_path / "run.json"
    db_path = tmp_path / "run.db"

    run_deterministic_analysis(
        fixtures_dir=fixtures_dir,
        output_path=output_path,
        db_path=db_path,
    )
    first = output_path.read_bytes()
    run_deterministic_analysis(
        fixtures_dir=fixtures_dir,
        output_path=output_path,
        db_path=db_path,
    )
    second = output_path.read_bytes()

    assert first == second


def test_deterministic_run_conflict_same_db(tmp_path: Path) -> None:
    fixtures_root = Path(__file__).resolve().parents[1] / "fixtures" / "deterministic-analysis"
    temp_fixtures = tmp_path / "fixtures"
    temp_fixtures.mkdir()
    csv_path = temp_fixtures / "aapl_d1.csv"
    csv_path.write_text(
        (fixtures_root / "aapl_d1.csv").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    config_payload = json.loads(
        (fixtures_root / "analysis_config.json").read_text(encoding="utf-8")
    )
    config_payload["snapshot"]["file"] = "aapl_d1.csv"
    config_path = temp_fixtures / "analysis_config.json"
    config_path.write_text(
        json.dumps(config_payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False),
        encoding="utf-8",
    )

    output_path = tmp_path / "run.json"
    db_path = tmp_path / "run.db"
    run_deterministic_analysis(
        fixtures_dir=temp_fixtures,
        output_path=output_path,
        db_path=db_path,
    )

    modified_csv = csv_path.read_text(encoding="utf-8").replace("185.64", "185.65", 1)
    csv_path.write_text(modified_csv, encoding="utf-8")

    with pytest.raises(
        SnapshotIngestionError,
        match="snapshot_ingestion_conflict",
    ):
        run_deterministic_analysis(
            fixtures_dir=temp_fixtures,
            output_path=output_path,
            db_path=db_path,
        )


def test_determinism_guard_blocks_time_random_network() -> None:
    with determinism_guard():
        with pytest.raises(
            DeterminismViolationError,
            match="determinism_guard_violation:time.now",
        ):
            datetime_module.datetime.now()
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
        with pytest.raises(
            DeterminismViolationError,
            match="determinism_guard_violation:random.os.urandom",
        ):
            os.urandom(1)

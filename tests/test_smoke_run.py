import json
from pathlib import Path
import shutil

import pytest

from cilly_trading.smoke_run import SmokeRunError, _determinism_guard, run_smoke_run


FIXTURES_DIR = Path("fixtures/smoke-run")


def _copy_fixtures(tmp_path: Path) -> Path:
    target = tmp_path / "fixtures"
    target.mkdir()
    for fixture in ("input.json", "expected.csv", "config.yaml"):
        shutil.copy(FIXTURES_DIR / fixture, target / fixture)
    return target


def test_smoke_run_success(tmp_path, capsys):
    fixtures_dir = _copy_fixtures(tmp_path)
    artifacts_dir = tmp_path / "artifacts"

    exit_code = run_smoke_run(fixtures_dir=fixtures_dir, artifacts_dir=artifacts_dir)

    assert exit_code == 0
    captured = capsys.readouterr()
    assert captured.out == (
        "SMOKE_RUN:START\n"
        "SMOKE_RUN:FIXTURES_OK\n"
        "SMOKE_RUN:CHECKS_OK\n"
        "SMOKE_RUN:END\n"
    )
    assert captured.err == ""

    result_path = artifacts_dir / "smoke-run" / "result.json"
    assert result_path.exists()
    expected_payload = {
        "engine_name": "cilly-trading-engine",
        "engine_version": "0.0.0",
        "precision": 2,
        "run_id": "smoke-0001",
        "status": "ok",
        "ticks": 3,
    }
    expected_bytes = json.dumps(
        expected_payload,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    assert result_path.read_bytes() == expected_bytes


def test_smoke_run_missing_fixtures(tmp_path, capsys):
    fixtures_dir = tmp_path / "fixtures"
    fixtures_dir.mkdir()
    artifacts_dir = tmp_path / "artifacts"

    exit_code = run_smoke_run(fixtures_dir=fixtures_dir, artifacts_dir=artifacts_dir)

    assert exit_code == 10
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""


def test_smoke_run_invalid_format(tmp_path, capsys):
    fixtures_dir = _copy_fixtures(tmp_path)
    (fixtures_dir / "input.json").write_text("{", encoding="utf-8")

    exit_code = run_smoke_run(fixtures_dir=fixtures_dir, artifacts_dir=tmp_path)

    assert exit_code == 11
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""


def test_smoke_run_constraint_violation(tmp_path, capsys):
    fixtures_dir = _copy_fixtures(tmp_path)
    (fixtures_dir / "input.json").write_text(
        json.dumps(
            {
                "run_id": "smoke-0001",
                "base_currency": "EUR",
                "quote_currency": "USD",
                "start_price": 100.0,
                "end_price": 101.0,
                "ticks": 1,
            }
        ),
        encoding="utf-8",
    )

    exit_code = run_smoke_run(fixtures_dir=fixtures_dir, artifacts_dir=tmp_path)

    assert exit_code == 12
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""


def test_smoke_run_output_mismatch(tmp_path, capsys):
    fixtures_dir = _copy_fixtures(tmp_path)
    artifacts_root = tmp_path / "artifacts"
    artifacts_dir = artifacts_root / "smoke-run"
    artifacts_dir.mkdir(parents=True)
    (artifacts_dir / "result.json").write_text("{}", encoding="utf-8")

    exit_code = run_smoke_run(fixtures_dir=fixtures_dir, artifacts_dir=artifacts_root)

    assert exit_code == 13
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""


def test_smoke_run_determinism_guard(tmp_path, capsys):
    with pytest.raises(SmokeRunError) as excinfo:
        with _determinism_guard():
            import socket

            socket.socket()

    assert excinfo.value.exit_code == 12
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""

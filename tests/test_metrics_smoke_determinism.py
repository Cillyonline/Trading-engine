from __future__ import annotations

import hashlib
from pathlib import Path

from cilly_trading.metrics import compute_backtest_metrics, write_metrics_artifact


DETERMINISTIC_FIXTURE_INPUT = {
    "summary": {"start_equity": 100.0, "end_equity": 120.0},
    "equity_curve": [
        {"timestamp": 0, "equity": 100.0},
        {"timestamp": 31_557_600, "equity": 120.0},
    ],
    "trades": [
        {"trade_id": "a", "exit_ts": 1, "pnl": 5.0},
        {"trade_id": "b", "exit_ts": 2, "pnl": 10.0},
        {"trade_id": "c", "exit_ts": 3, "pnl": -3.0},
    ],
}


def _run_metrics_evaluation(output_dir: Path) -> bytes:
    metrics = compute_backtest_metrics(**DETERMINISTIC_FIXTURE_INPUT)
    artifact_path = write_metrics_artifact(metrics, output_dir)
    return artifact_path.read_bytes()


def test_metrics_evaluation_smoke_is_deterministic_across_three_runs(tmp_path: Path) -> None:
    artifact_blobs = [
        _run_metrics_evaluation(tmp_path / f"run-{run_index}")
        for run_index in range(3)
    ]

    assert artifact_blobs[0] == artifact_blobs[1] == artifact_blobs[2]

    artifact_hashes = [
        hashlib.sha256(artifact_blob).hexdigest()
        for artifact_blob in artifact_blobs
    ]

    assert artifact_hashes[0] == artifact_hashes[1] == artifact_hashes[2]

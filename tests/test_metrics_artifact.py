from __future__ import annotations

import json
from pathlib import Path

from cilly_trading.metrics import (
    METRICS_ARTIFACT_FILENAME,
    build_metrics_artifact,
    canonical_json_bytes,
    compute_backtest_metrics,
    write_metrics_artifact,
)
from cilly_trading.metrics.artifact import _normalize_for_json


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


def test_metrics_artifact_three_runs_identical_bytes(tmp_path: Path) -> None:
    metrics = compute_backtest_metrics(**DETERMINISTIC_FIXTURE_INPUT)

    artifact_paths = [
        write_metrics_artifact(metrics, tmp_path / f"run-{idx}")
        for idx in range(3)
    ]

    artifact_bytes = [path.read_bytes() for path in artifact_paths]

    assert all(path.name == METRICS_ARTIFACT_FILENAME for path in artifact_paths)
    assert artifact_bytes[0] == artifact_bytes[1] == artifact_bytes[2]


def test_metrics_artifact_matches_canonical_json_bytes(tmp_path: Path) -> None:
    metrics = compute_backtest_metrics(**DETERMINISTIC_FIXTURE_INPUT)
    artifact = build_metrics_artifact(metrics)

    artifact_path = write_metrics_artifact(metrics, tmp_path)

    expected = canonical_json_bytes(artifact)
    observed = artifact_path.read_bytes()

    assert observed == expected


def test_metrics_artifact_uses_deterministic_key_ordering_and_rounding(tmp_path: Path) -> None:
    metrics = {
        "win_rate": 2.0 / 3.0,
        "cagr": -0.0,
        "profit_factor": 5,
        "total_return": 0.2,
        "max_drawdown": 0.0,
        "sharpe_ratio": None,
    }

    artifact_path = write_metrics_artifact(metrics, tmp_path)

    expected_obj = _normalize_for_json(build_metrics_artifact(metrics))
    expected_json = json.dumps(
        expected_obj,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ) + "\n"

    assert artifact_path.read_text(encoding="utf-8") == expected_json

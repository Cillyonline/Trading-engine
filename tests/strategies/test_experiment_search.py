from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from cilly_trading.strategies.experiment_search import (
    ParameterSearchExperimentConfig,
    StrategyLabConfigError,
    StrategyLabRunError,
    run_parameter_search_experiment,
)


def _search_snapshots() -> list[dict[str, object]]:
    snapshots: list[dict[str, object]] = []
    for day in range(1, 31):
        timestamp = f"2024-01-{day:02d}T00:00:00Z"
        if day <= 20:
            close = 100
        elif day <= 25:
            close = 104
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


def test_parameter_search_config_validation_rejects_oversized_grid() -> None:
    with pytest.raises(StrategyLabConfigError, match="exceeds max_trials"):
        ParameterSearchExperimentConfig(
            experiment_id="lab-p42",
            strategy_name="TURTLE",
            dataset_ref="snapshot-set-a",
            parameter_space={
                "breakout_lookback": [15, 20, 25],
                "min_score": [30.0, 40.0, 50.0],
                "proximity_threshold_pct": [0.02, 0.03, 0.04],
            },
            max_trials=12,
        )


def test_parameter_search_representative_run_outputs_expected_shape(tmp_path: Path) -> None:
    config = ParameterSearchExperimentConfig(
        experiment_id="lab-p42",
        strategy_name="TURTLE",
        dataset_ref="snapshot-set-a",
        parameter_space={
            "breakout_lookback": [20, 25],
            "min_score": [30.0],
        },
        objective_metric="total_return",
        objective_direction="max",
        max_trials=4,
        snapshot_selector={"symbol": "AAPL", "timeframe": "D1"},
    )

    result = run_parameter_search_experiment(
        config=config,
        snapshots=_search_snapshots(),
        output_dir=tmp_path / "search",
    )

    assert result.artifact_path.exists()
    assert (tmp_path / "search" / "parameter-search-result.sha256").exists()

    payload = json.loads(result.artifact_path.read_text(encoding="utf-8"))
    assert payload["artifact"] == "parameter_search_experiment"
    assert payload["experiment"]["strategy_name"] == "TURTLE"
    assert payload["run_metadata"]["trial_count"] == 2

    trials = payload["search_results"]["trials"]
    assert len(trials) == 2
    assert trials[0]["trial_id"] == "trial-001"
    assert "objective_value" in trials[0]
    for trial in trials:
        comparison_artifact = trial["comparison_artifact"]
        relpath = comparison_artifact["relpath"]
        artifact_path = tmp_path / "search" / relpath
        assert artifact_path.exists()
        actual_sha = hashlib.sha256(artifact_path.read_bytes()).hexdigest()
        assert actual_sha == comparison_artifact["sha256"]

    reports = payload["reports"]
    assert reports["strategy_comparison"]["artifact"] == "strategy_comparison"
    assert reports["performance_report"]["artifact"] == "performance_report"


def test_parameter_search_run_is_reproducible_for_same_inputs(tmp_path: Path) -> None:
    config = ParameterSearchExperimentConfig(
        experiment_id="lab-p42-repro",
        strategy_name="TURTLE",
        dataset_ref="snapshot-set-repro",
        parameter_space={
            "breakout_lookback": [20, 22],
            "min_score": [30.0],
        },
        max_trials=4,
    )

    run_a = run_parameter_search_experiment(
        config=config,
        snapshots=_search_snapshots(),
        output_dir=tmp_path / "run-a",
    )
    run_b = run_parameter_search_experiment(
        config=config,
        snapshots=_search_snapshots(),
        output_dir=tmp_path / "run-b",
    )

    assert run_a.artifact_path.read_bytes() == run_b.artifact_path.read_bytes()
    assert run_a.artifact_sha256 == run_b.artifact_sha256


def test_parameter_search_negative_invalid_snapshots_fail() -> None:
    config = ParameterSearchExperimentConfig(
        experiment_id="lab-p42-negative",
        strategy_name="TURTLE",
        dataset_ref="snapshot-set-negative",
        parameter_space={"breakout_lookback": [20]},
        max_trials=2,
    )

    with pytest.raises(StrategyLabRunError, match="at least one"):
        run_parameter_search_experiment(config=config, snapshots=[], output_dir=Path("unused"))

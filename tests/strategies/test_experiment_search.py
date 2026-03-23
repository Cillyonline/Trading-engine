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
    for day in range(1, 41):
        timestamp = f"2024-01-{day:02d}T00:00:00Z"
        if day <= 25:
            close = 100
        elif day <= 35:
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


def test_parameter_search_config_validation_rejects_invalid_validation_ratio() -> None:
    with pytest.raises(StrategyLabConfigError, match="validation_split_ratio"):
        ParameterSearchExperimentConfig(
            experiment_id="lab-p42-bad-validation-ratio",
            strategy_name="TURTLE",
            dataset_ref="snapshot-set-a",
            parameter_space={"breakout_lookback": [20]},
            validation_split_ratio=0.8,
        )


def test_parameter_search_validation_workflow_outputs_development_and_validation_segments(
    tmp_path: Path,
) -> None:
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
        validation_split_ratio=0.3,
        min_development_snapshots=20,
        min_validation_snapshots=8,
        max_validation_degradation_fraction=1.0,
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
    assert payload["run_metadata"]["development_snapshot_count"] == 28
    assert payload["run_metadata"]["validation_snapshot_count"] == 12

    trials = payload["search_results"]["trials"]
    assert len(trials) == 2
    assert trials[0]["trial_id"] == "trial-001"

    for trial in trials:
        assert "development" in trial
        assert "validation" in trial
        assert "guardrails" in trial
        assert isinstance(trial["guardrails"]["passed"], bool)

        for segment_name in ("development", "validation"):
            segment = trial[segment_name]
            assert "objective_value" in segment
            comparison_artifact = segment["comparison_artifact"]
            relpath = comparison_artifact["relpath"]
            artifact_path = tmp_path / "search" / relpath
            assert artifact_path.exists()
            actual_sha = hashlib.sha256(artifact_path.read_bytes()).hexdigest()
            assert actual_sha == comparison_artifact["sha256"]

    selection = payload["search_results"]["selection"]
    assert selection["policy"] == "best_development_trial_with_validation_guardrail"
    assert selection["selected_trial_id"] == payload["search_results"]["best_trial_id"]


def test_parameter_search_reports_distinguish_development_and_validation(tmp_path: Path) -> None:
    config = ParameterSearchExperimentConfig(
        experiment_id="lab-p42-reports",
        strategy_name="TURTLE",
        dataset_ref="snapshot-set-reports",
        parameter_space={
            "breakout_lookback": [20, 22],
            "min_score": [30.0],
        },
        max_trials=4,
        max_validation_degradation_fraction=1.0,
    )

    result = run_parameter_search_experiment(
        config=config,
        snapshots=_search_snapshots(),
        output_dir=tmp_path / "reports-run",
    )

    payload = json.loads(result.artifact_path.read_text(encoding="utf-8"))
    strategy_rows = payload["reports"]["strategy_comparison"]["strategies"]
    assert len(strategy_rows) == 2

    for row in strategy_rows:
        assert "development" in row
        assert "validation" in row
        assert "objective_value" in row["development"]
        assert "objective_value" in row["validation"]

    selected_validation = payload["reports"]["performance_report"]["selected_trial_validation"]
    assert "objective_value" in selected_validation


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
        max_validation_degradation_fraction=1.0,
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


def test_parameter_search_negative_guardrail_failure_blocks_selection(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _FakeComparisonResult:
        def __init__(self, objective_value: float) -> None:
            self.payload = {
                "strategies": [
                    {
                        "metrics": {"total_return": objective_value, "win_rate": 0.5},
                        "metrics_baseline_summary": {
                            "starting_equity": 1000.0,
                            "ending_equity_cost_aware": 1000.0 + objective_value,
                            "fill_count": 1,
                        },
                        "backtest": {"run_id": "fake"},
                    }
                ]
            }

    call_state = {"count": 0}

    def _fake_run_strategy_comparison(**kwargs: object) -> _FakeComparisonResult:
        output_dir = kwargs["output_dir"]
        assert isinstance(output_dir, Path)
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "strategy-comparison.json").write_text("{}", encoding="utf-8")

        call_state["count"] += 1
        if call_state["count"] % 2 == 1:
            return _FakeComparisonResult(objective_value=1.0)  # development
        return _FakeComparisonResult(objective_value=0.0)  # validation

    monkeypatch.setattr(
        "cilly_trading.strategies.experiment_search.run_strategy_comparison",
        _fake_run_strategy_comparison,
    )

    config = ParameterSearchExperimentConfig(
        experiment_id="lab-p42-negative-guardrail",
        strategy_name="TURTLE",
        dataset_ref="snapshot-set-negative-guardrail",
        parameter_space={"breakout_lookback": [20], "min_score": [30.0]},
        max_trials=2,
        max_validation_degradation_fraction=0.0,
    )

    with pytest.raises(StrategyLabRunError, match="validation guardrails"):
        run_parameter_search_experiment(
            config=config,
            snapshots=_search_snapshots(),
            output_dir=tmp_path / "guardrail-fail",
        )


def test_parameter_search_negative_split_requires_enough_snapshots() -> None:
    config = ParameterSearchExperimentConfig(
        experiment_id="lab-p42-negative-split",
        strategy_name="TURTLE",
        dataset_ref="snapshot-set-negative-split",
        parameter_space={"breakout_lookback": [20]},
        min_development_snapshots=30,
        min_validation_snapshots=20,
    )

    with pytest.raises(StrategyLabRunError, match="requires at least"):
        run_parameter_search_experiment(
            config=config,
            snapshots=_search_snapshots(),
            output_dir=Path("unused"),
        )

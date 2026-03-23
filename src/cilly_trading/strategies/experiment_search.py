"""Bounded Strategy Lab experiment and parameter-search framework."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Sequence

from cilly_trading.metrics.artifact import canonical_json_bytes
from cilly_trading.strategies.evaluation_harness import run_strategy_comparison

FRAMEWORK_VERSION = "2"
SEARCH_ARTIFACT_FILENAME = "parameter-search-result.json"
SEARCH_HASH_FILENAME = "parameter-search-result.sha256"
SUPPORTED_OBJECTIVE_METRICS = {
    "total_return",
    "cagr",
    "max_drawdown",
    "sharpe_ratio",
    "win_rate",
    "profit_factor",
}

_MIN_VALIDATION_SPLIT_RATIO = 0.1
_MAX_VALIDATION_SPLIT_RATIO = 0.5
_EPSILON = 1e-12


class StrategyLabConfigError(ValueError):
    """Raised when experiment/search configuration is invalid."""


class StrategyLabRunError(ValueError):
    """Raised when experiment/search execution cannot proceed."""


@dataclass(frozen=True)
class ParameterSearchExperimentConfig:
    """Explicit bounded configuration for one parameter-search experiment."""

    experiment_id: str
    strategy_name: str
    dataset_ref: str
    parameter_space: Mapping[str, Sequence[Any]]
    objective_metric: str = "total_return"
    objective_direction: str = "max"
    max_trials: int = 32
    snapshot_selector: Mapping[str, Any] = field(default_factory=dict)
    validation_split_ratio: float = 0.3
    min_development_snapshots: int = 10
    min_validation_snapshots: int = 5
    max_validation_degradation_fraction: float = 0.35
    require_guardrail_pass_for_selection: bool = True

    def __post_init__(self) -> None:
        if not isinstance(self.experiment_id, str) or not self.experiment_id.strip():
            raise StrategyLabConfigError("experiment_id must be a non-empty string")
        if not isinstance(self.strategy_name, str) or not self.strategy_name.strip():
            raise StrategyLabConfigError("strategy_name must be a non-empty string")
        if not isinstance(self.dataset_ref, str) or not self.dataset_ref.strip():
            raise StrategyLabConfigError("dataset_ref must be a non-empty string")

        if self.objective_metric not in SUPPORTED_OBJECTIVE_METRICS:
            raise StrategyLabConfigError(
                "objective_metric must be one of: "
                + ", ".join(sorted(SUPPORTED_OBJECTIVE_METRICS))
            )
        if self.objective_direction not in {"max", "min"}:
            raise StrategyLabConfigError("objective_direction must be 'max' or 'min'")
        if not isinstance(self.max_trials, int) or self.max_trials <= 0:
            raise StrategyLabConfigError("max_trials must be a positive integer")

        if not isinstance(self.parameter_space, Mapping) or not self.parameter_space:
            raise StrategyLabConfigError("parameter_space must be a non-empty mapping")

        normalized_trial_space = _normalize_parameter_space(self.parameter_space)
        if len(normalized_trial_space) > self.max_trials:
            raise StrategyLabConfigError(
                f"parameter_space expands to {len(normalized_trial_space)} trials, exceeds max_trials={self.max_trials}"
            )

        if not isinstance(self.snapshot_selector, Mapping):
            raise StrategyLabConfigError("snapshot_selector must be a mapping")

        if not isinstance(self.validation_split_ratio, (int, float)):
            raise StrategyLabConfigError("validation_split_ratio must be numeric")
        if not _MIN_VALIDATION_SPLIT_RATIO <= float(self.validation_split_ratio) <= _MAX_VALIDATION_SPLIT_RATIO:
            raise StrategyLabConfigError(
                "validation_split_ratio must be between "
                f"{_MIN_VALIDATION_SPLIT_RATIO} and {_MAX_VALIDATION_SPLIT_RATIO}"
            )

        if not isinstance(self.min_development_snapshots, int) or self.min_development_snapshots < 1:
            raise StrategyLabConfigError("min_development_snapshots must be a positive integer")
        if not isinstance(self.min_validation_snapshots, int) or self.min_validation_snapshots < 1:
            raise StrategyLabConfigError("min_validation_snapshots must be a positive integer")

        if not isinstance(self.max_validation_degradation_fraction, (int, float)):
            raise StrategyLabConfigError("max_validation_degradation_fraction must be numeric")
        if not 0.0 <= float(self.max_validation_degradation_fraction) <= 1.0:
            raise StrategyLabConfigError(
                "max_validation_degradation_fraction must be between 0.0 and 1.0"
            )

        if not isinstance(self.require_guardrail_pass_for_selection, bool):
            raise StrategyLabConfigError("require_guardrail_pass_for_selection must be a boolean")

    def to_payload(self) -> dict[str, Any]:
        return {
            "framework_version": FRAMEWORK_VERSION,
            "experiment_id": self.experiment_id.strip(),
            "strategy_name": self.strategy_name.strip().upper(),
            "dataset_ref": self.dataset_ref.strip(),
            "parameter_space": {
                key: list(values)
                for key, values in sorted(self.parameter_space.items(), key=lambda item: item[0])
            },
            "objective": {
                "metric": self.objective_metric,
                "direction": self.objective_direction,
            },
            "max_trials": self.max_trials,
            "snapshot_selector": dict(self.snapshot_selector),
            "validation_discipline": {
                "split_mode": "chronological_holdout",
                "validation_split_ratio": float(self.validation_split_ratio),
                "min_development_snapshots": self.min_development_snapshots,
                "min_validation_snapshots": self.min_validation_snapshots,
            },
            "anti_overfit_guardrails": {
                "max_validation_degradation_fraction": float(self.max_validation_degradation_fraction),
                "require_guardrail_pass_for_selection": self.require_guardrail_pass_for_selection,
            },
        }


@dataclass(frozen=True)
class ParameterSearchRunResult:
    """Run result payload + persisted artifact references."""

    artifact_path: Path
    artifact_sha256: str
    payload: dict[str, Any]


def run_parameter_search_experiment(
    *,
    config: ParameterSearchExperimentConfig,
    snapshots: Sequence[Mapping[str, Any]],
    output_dir: Path,
) -> ParameterSearchRunResult:
    """Run a bounded deterministic parameter search and persist canonical artifacts."""

    ordered_snapshots = _normalize_snapshots(snapshots)
    development_snapshots, validation_snapshots = _split_snapshots_for_validation(
        snapshots=ordered_snapshots,
        config=config,
    )

    trial_params = _normalize_parameter_space(config.parameter_space)
    if not trial_params:
        raise StrategyLabRunError("parameter_space must expand to at least one trial")

    config_payload = config.to_payload()
    config_sha = _sha256_payload(config_payload)
    snapshots_sha = _sha256_payload(ordered_snapshots)
    run_id = f"{config.experiment_id.strip()}:{_sha256_payload({'c': config_sha, 's': snapshots_sha})[:12]}"

    trial_rows: list[dict[str, Any]] = []
    for index, params in enumerate(trial_params, start=1):
        trial_id = f"trial-{index:03d}"
        trial_run_id = f"{run_id}:{trial_id}"

        development_result = _run_trial_segment(
            config=config,
            output_dir=output_dir,
            run_id=trial_run_id,
            trial_id=trial_id,
            segment_name="development",
            snapshots=development_snapshots,
            params=params,
        )
        validation_result = _run_trial_segment(
            config=config,
            output_dir=output_dir,
            run_id=trial_run_id,
            trial_id=trial_id,
            segment_name="validation",
            snapshots=validation_snapshots,
            params=params,
        )

        development_objective = float(development_result["objective_value"])
        validation_objective = float(validation_result["objective_value"])
        degradation = _validation_degradation(
            development_objective=development_objective,
            validation_objective=validation_objective,
            objective_direction=config.objective_direction,
        )
        degradation_fraction = degradation / max(abs(development_objective), _EPSILON)
        guardrail_passed = degradation_fraction <= float(config.max_validation_degradation_fraction)

        trial_rows.append(
            {
                "trial_id": trial_id,
                "run_id": trial_run_id,
                "parameters": params,
                "objective_value": development_objective,
                "metrics": dict(development_result["metrics"]),
                "metrics_baseline_summary": dict(development_result["metrics_baseline_summary"]),
                "comparison_artifact": dict(development_result["comparison_artifact"]),
                "development": dict(development_result),
                "validation": dict(validation_result),
                "guardrails": {
                    "validation_degradation": degradation,
                    "validation_degradation_fraction": degradation_fraction,
                    "max_validation_degradation_fraction": float(config.max_validation_degradation_fraction),
                    "passed": guardrail_passed,
                },
            }
        )

    best_development_trial = _select_best_trial(
        trial_rows=trial_rows,
        objective_direction=config.objective_direction,
    )

    guardrail_passed_trials = [row for row in trial_rows if _guardrail_passed(row)]
    if config.require_guardrail_pass_for_selection and not guardrail_passed_trials:
        raise StrategyLabRunError("no trial satisfies the configured validation guardrails")

    candidate_rows = guardrail_passed_trials if config.require_guardrail_pass_for_selection else trial_rows
    selected_trial = _select_best_trial(
        trial_rows=candidate_rows,
        objective_direction=config.objective_direction,
    )

    payload: dict[str, Any] = {
        "artifact": "parameter_search_experiment",
        "artifact_version": FRAMEWORK_VERSION,
        "experiment": config_payload,
        "run_metadata": {
            "run_id": run_id,
            "config_sha256": config_sha,
            "snapshots_sha256": snapshots_sha,
            "trial_count": len(trial_rows),
            "snapshot_count": len(ordered_snapshots),
            "development_snapshot_count": len(development_snapshots),
            "validation_snapshot_count": len(validation_snapshots),
        },
        "search_results": {
            "objective": {
                "metric": config.objective_metric,
                "direction": config.objective_direction,
            },
            "best_trial_id": selected_trial["trial_id"],
            "selection": {
                "policy": "best_development_trial_with_validation_guardrail",
                "best_development_trial_id": best_development_trial["trial_id"],
                "selected_trial_id": selected_trial["trial_id"],
                "guardrail_required": config.require_guardrail_pass_for_selection,
                "guardrail_passed_trial_count": len(guardrail_passed_trials),
            },
            "trials": trial_rows,
        },
        "reports": _build_reusable_reports(config, trial_rows, selected_trial),
    }

    artifact_path, artifact_sha = write_parameter_search_artifact(payload=payload, output_dir=output_dir)
    return ParameterSearchRunResult(
        artifact_path=artifact_path,
        artifact_sha256=artifact_sha,
        payload=payload,
    )


def write_parameter_search_artifact(
    *,
    payload: Mapping[str, Any],
    output_dir: Path,
) -> tuple[Path, str]:
    """Write canonical experiment search artifact and checksum."""

    output_dir.mkdir(parents=True, exist_ok=True)
    artifact_path = output_dir / SEARCH_ARTIFACT_FILENAME
    canonical_bytes = canonical_json_bytes(payload)
    artifact_path.write_bytes(canonical_bytes)

    artifact_sha = hashlib.sha256(canonical_bytes).hexdigest()
    (output_dir / SEARCH_HASH_FILENAME).write_text(f"{artifact_sha}\n", encoding="utf-8")
    return artifact_path, artifact_sha


def _run_trial_segment(
    *,
    config: ParameterSearchExperimentConfig,
    output_dir: Path,
    run_id: str,
    trial_id: str,
    segment_name: str,
    snapshots: Sequence[Mapping[str, Any]],
    params: Mapping[str, Any],
) -> dict[str, Any]:
    trial_output_dir = output_dir / "trials" / trial_id / segment_name
    segment_run_id = f"{run_id}:{segment_name}"
    comparison_artifact_relpath = Path("trials") / trial_id / segment_name / "strategy-comparison.json"
    comparison_artifact_path = output_dir / comparison_artifact_relpath

    comparison = run_strategy_comparison(
        snapshots=snapshots,
        strategy_names=[config.strategy_name],
        output_dir=trial_output_dir,
        run_id=segment_run_id,
        strategy_configs={config.strategy_name: params},
    )
    strategy_row = comparison.payload["strategies"][0]
    if not isinstance(strategy_row, Mapping):
        raise StrategyLabRunError("strategy comparison output is malformed")

    metrics_raw = strategy_row.get("metrics")
    metrics = metrics_raw if isinstance(metrics_raw, Mapping) else None
    if metrics is None:
        raise StrategyLabRunError("strategy comparison metrics are missing")

    objective_value = metrics.get(config.objective_metric)
    if not isinstance(objective_value, (int, float)):
        raise StrategyLabRunError(
            f"objective metric '{config.objective_metric}' is missing or non-numeric"
        )

    backtest = strategy_row.get("backtest")
    if not isinstance(backtest, Mapping):
        raise StrategyLabRunError("strategy comparison backtest payload is missing")

    baseline_summary_raw = strategy_row.get("metrics_baseline_summary")
    baseline_summary = baseline_summary_raw if isinstance(baseline_summary_raw, Mapping) else {}
    comparison_artifact_sha = hashlib.sha256(comparison_artifact_path.read_bytes()).hexdigest()

    return {
        "objective_value": float(objective_value),
        "metrics": dict(metrics),
        "metrics_baseline_summary": dict(baseline_summary),
        "comparison_artifact": {
            "relpath": str(comparison_artifact_relpath.as_posix()),
            "sha256": comparison_artifact_sha,
        },
        "snapshot_count": len(snapshots),
    }


def _split_snapshots_for_validation(
    *,
    snapshots: Sequence[Mapping[str, Any]],
    config: ParameterSearchExperimentConfig,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    total_count = len(snapshots)
    ratio_based_count = int(total_count * float(config.validation_split_ratio))
    validation_count = max(config.min_validation_snapshots, ratio_based_count)

    development_count = total_count - validation_count
    if development_count < config.min_development_snapshots:
        raise StrategyLabRunError(
            "validation split requires at least "
            f"{config.min_development_snapshots + config.min_validation_snapshots} snapshots "
            f"(received {total_count})"
        )

    if validation_count < 1 or development_count < 1:
        raise StrategyLabRunError("validation split produced an empty development or validation partition")

    development = [dict(snapshot) for snapshot in snapshots[:development_count]]
    validation = [dict(snapshot) for snapshot in snapshots[development_count:]]
    return development, validation


def _build_reusable_reports(
    config: ParameterSearchExperimentConfig,
    trial_rows: Sequence[Mapping[str, Any]],
    best_trial: Mapping[str, Any],
) -> dict[str, Any]:
    ranking_rows = _sorted_trial_rows(trial_rows=trial_rows, objective_direction=config.objective_direction)

    strategy_comparison: list[dict[str, Any]] = []
    for row in ranking_rows:
        development_segment = _segment_summary(row, "development")
        validation_segment = _segment_summary(row, "validation")

        strategy_comparison.append(
            {
                "strategy_id": f"{config.strategy_name.strip().upper()}:{row['trial_id']}",
                "trade_count": development_segment["trade_count"],
                "total_pnl": development_segment["total_pnl"],
                "average_pnl": development_segment["average_pnl"],
                "win_rate": development_segment["win_rate"],
                "development": development_segment,
                "validation": validation_segment,
                "guardrails": dict(row.get("guardrails") or {}),
            }
        )

    selected_development = _segment_metrics(best_trial, "development")
    selected_validation = _segment_metrics(best_trial, "validation")
    return {
        "strategy_comparison": {
            "artifact": "strategy_comparison",
            "artifact_version": "1",
            "workflow": {
                "name": "parameter_search_trial_ranking",
                "strategy": config.strategy_name.strip().upper(),
                "objective_metric": config.objective_metric,
                "objective_direction": config.objective_direction,
                "selection_rule": "best_development_trial_with_validation_guardrail",
            },
            "strategies": list(strategy_comparison),
        },
        "performance_report": {
            "artifact": "performance_report",
            "artifact_version": "1",
            "performance_summary": {
                "total_trades": sum(row["trade_count"] for row in strategy_comparison),
                "strategies_analyzed": len(strategy_comparison),
                "total_pnl": sum(
                    float(row["total_pnl"]) for row in strategy_comparison if isinstance(row["total_pnl"], (int, float))
                ),
                "winning_trades": 0,
                "losing_trades": 0,
                "breakeven_trades": 0,
            },
            "strategy_comparison": list(strategy_comparison),
            "key_metrics_overview": {
                "overall_win_rate": selected_development.get("win_rate"),
                "average_pnl_per_trade": None,
                "average_holding_time_seconds": None,
                "best_strategy_id": f"{config.strategy_name.strip().upper()}:{best_trial['trial_id']}",
                "worst_strategy_id": strategy_comparison[-1]["strategy_id"] if strategy_comparison else None,
                "risk_adjusted_metrics": None,
            },
            "selected_trial_validation": {
                "objective_value": selected_validation.get("objective_value"),
                "win_rate": selected_validation.get("win_rate"),
            },
        },
    }


def _segment_summary(row: Mapping[str, Any], segment_name: str) -> dict[str, Any]:
    metrics = _segment_metrics(row, segment_name)
    baseline = _segment_baseline(row, segment_name)
    total_pnl = _segment_total_pnl(baseline)
    fill_count = baseline.get("fill_count")

    average_pnl = None
    if total_pnl is not None and isinstance(fill_count, int) and fill_count > 0:
        average_pnl = total_pnl / float(fill_count)

    return {
        "objective_value": metrics.get("objective_value"),
        "trade_count": fill_count if isinstance(fill_count, int) else 0,
        "total_pnl": total_pnl,
        "average_pnl": average_pnl,
        "win_rate": metrics.get("win_rate"),
    }


def _segment_metrics(row: Mapping[str, Any], segment_name: str) -> Mapping[str, Any]:
    segment = row.get(segment_name)
    if not isinstance(segment, Mapping):
        return {}
    metrics = segment.get("metrics")
    if not isinstance(metrics, Mapping):
        return {"objective_value": segment.get("objective_value")}

    values = dict(metrics)
    values["objective_value"] = segment.get("objective_value")
    return values


def _segment_baseline(row: Mapping[str, Any], segment_name: str) -> Mapping[str, Any]:
    segment = row.get(segment_name)
    if not isinstance(segment, Mapping):
        return {}
    baseline = segment.get("metrics_baseline_summary")
    if isinstance(baseline, Mapping):
        return baseline
    return {}


def _segment_total_pnl(baseline: Mapping[str, Any]) -> float | None:
    starting_equity = baseline.get("starting_equity")
    ending_equity = baseline.get("ending_equity_cost_aware")

    if isinstance(starting_equity, (int, float)) and isinstance(ending_equity, (int, float)):
        return float(ending_equity) - float(starting_equity)
    return None


def _validation_degradation(
    *,
    development_objective: float,
    validation_objective: float,
    objective_direction: str,
) -> float:
    if objective_direction == "max":
        return max(0.0, development_objective - validation_objective)
    return max(0.0, validation_objective - development_objective)


def _guardrail_passed(row: Mapping[str, Any]) -> bool:
    guardrails = row.get("guardrails")
    if not isinstance(guardrails, Mapping):
        return False
    return bool(guardrails.get("passed"))


def _sorted_trial_rows(
    *,
    trial_rows: Sequence[Mapping[str, Any]],
    objective_direction: str,
) -> list[Mapping[str, Any]]:
    if objective_direction == "max":
        return sorted(
            trial_rows,
            key=lambda row: (-float(row["objective_value"]), str(row["trial_id"])),
        )
    return sorted(
        trial_rows,
        key=lambda row: (float(row["objective_value"]), str(row["trial_id"])),
    )


def _select_best_trial(
    *,
    trial_rows: Sequence[Mapping[str, Any]],
    objective_direction: str,
) -> Mapping[str, Any]:
    return _sorted_trial_rows(trial_rows=trial_rows, objective_direction=objective_direction)[0]


def _normalize_parameter_space(parameter_space: Mapping[str, Sequence[Any]]) -> list[dict[str, Any]]:
    dimensions: list[tuple[str, list[Any]]] = []
    for raw_key, raw_values in sorted(parameter_space.items(), key=lambda item: str(item[0])):
        if not isinstance(raw_key, str) or not raw_key.strip():
            raise StrategyLabConfigError("parameter names must be non-empty strings")
        if not isinstance(raw_values, Sequence) or isinstance(raw_values, (str, bytes)):
            raise StrategyLabConfigError(f"parameter '{raw_key}' must be a sequence")
        values = list(raw_values)
        if not values:
            raise StrategyLabConfigError(f"parameter '{raw_key}' must contain at least one value")
        for value in values:
            _validate_param_value(raw_key, value)
        dimensions.append((raw_key.strip(), values))

    combos: list[dict[str, Any]] = [{}]
    for key, values in dimensions:
        next_combos: list[dict[str, Any]] = []
        for combo in combos:
            for value in values:
                next_combo = dict(combo)
                next_combo[key] = value
                next_combos.append(next_combo)
        combos = next_combos
    return combos


def _validate_param_value(param_name: str, value: Any) -> None:
    if value is None or isinstance(value, (str, int, float, bool)):
        return
    raise StrategyLabConfigError(
        f"parameter '{param_name}' contains unsupported value type: {type(value).__name__}"
    )


def _normalize_snapshots(snapshots: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for raw in snapshots:
        if not isinstance(raw, Mapping):
            raise StrategyLabRunError("snapshots must contain mapping objects")
        snapshot = dict(raw)
        snapshot_id = snapshot.get("id")
        if not isinstance(snapshot_id, str) or not snapshot_id.strip():
            raise StrategyLabRunError("each snapshot must define a non-empty id")
        normalized.append(snapshot)

    if not normalized:
        raise StrategyLabRunError("snapshots must contain at least one item")

    return sorted(
        normalized,
        key=lambda snapshot: (
            str(snapshot.get("timestamp") or snapshot.get("snapshot_key") or snapshot.get("id") or ""),
            str(snapshot.get("id") or ""),
        ),
    )


def _sha256_payload(value: Any) -> str:
    bytes_payload = canonical_json_bytes(value)
    return hashlib.sha256(bytes_payload).hexdigest()


__all__ = [
    "FRAMEWORK_VERSION",
    "ParameterSearchExperimentConfig",
    "ParameterSearchRunResult",
    "SUPPORTED_OBJECTIVE_METRICS",
    "StrategyLabConfigError",
    "StrategyLabRunError",
    "run_parameter_search_experiment",
    "write_parameter_search_artifact",
]

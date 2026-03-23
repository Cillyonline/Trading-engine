"""Bounded Strategy Lab experiment and parameter-search framework."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Sequence

from cilly_trading.metrics.artifact import canonical_json_bytes
from cilly_trading.strategies.evaluation_harness import run_strategy_comparison

FRAMEWORK_VERSION = "1"
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
        trial_output_dir = output_dir / "trials" / trial_id
        trial_run_id = f"{run_id}:{trial_id}"
        comparison_artifact_relpath = Path("trials") / trial_id / "strategy-comparison.json"
        comparison_artifact_path = output_dir / comparison_artifact_relpath

        comparison = run_strategy_comparison(
            snapshots=ordered_snapshots,
            strategy_names=[config.strategy_name],
            output_dir=trial_output_dir,
            run_id=trial_run_id,
            strategy_configs={config.strategy_name: params},
        )
        strategy_row = comparison.payload["strategies"][0]
        if not isinstance(strategy_row, Mapping):
            raise StrategyLabRunError("strategy comparison output is malformed")

        metrics = strategy_row.get("metrics")
        if not isinstance(metrics, Mapping):
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

        trial_rows.append(
            {
                "trial_id": trial_id,
                "run_id": trial_run_id,
                "parameters": params,
                "objective_value": float(objective_value),
                "metrics": dict(metrics),
                "metrics_baseline_summary": dict(baseline_summary),
                "comparison_artifact": {
                    "relpath": str(comparison_artifact_relpath.as_posix()),
                    "sha256": comparison_artifact_sha,
                },
            }
        )

    best_trial = _select_best_trial(
        trial_rows=trial_rows,
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
        },
        "search_results": {
            "objective": {
                "metric": config.objective_metric,
                "direction": config.objective_direction,
            },
            "best_trial_id": best_trial["trial_id"],
            "trials": trial_rows,
        },
        "reports": _build_reusable_reports(config, trial_rows, best_trial),
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


def _build_reusable_reports(
    config: ParameterSearchExperimentConfig,
    trial_rows: Sequence[Mapping[str, Any]],
    best_trial: Mapping[str, Any],
) -> dict[str, Any]:
    ranking_rows = sorted(
        trial_rows,
        key=lambda row: (-float(row["objective_value"]), str(row["trial_id"])),
    )
    if config.objective_direction == "min":
        ranking_rows = sorted(
            trial_rows,
            key=lambda row: (float(row["objective_value"]), str(row["trial_id"])),
        )

    strategy_comparison: list[dict[str, Any]] = []
    for row in ranking_rows:
        baseline_raw = row.get("metrics_baseline_summary")
        baseline = baseline_raw if isinstance(baseline_raw, Mapping) else {}
        starting_equity = baseline.get("starting_equity")
        ending_equity = baseline.get("ending_equity_cost_aware")
        fill_count = baseline.get("fill_count")

        total_pnl = None
        if isinstance(starting_equity, (int, float)) and isinstance(ending_equity, (int, float)):
            total_pnl = float(ending_equity) - float(starting_equity)

        average_pnl = None
        if total_pnl is not None and isinstance(fill_count, int) and fill_count > 0:
            average_pnl = total_pnl / float(fill_count)

        metrics_raw = row.get("metrics")
        metrics = metrics_raw if isinstance(metrics_raw, Mapping) else {}
        strategy_comparison.append(
            {
                "strategy_id": f"{config.strategy_name.strip().upper()}:{row['trial_id']}",
                "trade_count": fill_count if isinstance(fill_count, int) else 0,
                "total_pnl": total_pnl,
                "average_pnl": average_pnl,
                "win_rate": metrics.get("win_rate"),
            }
        )

    best_metrics_raw = best_trial.get("metrics")
    best_metrics = best_metrics_raw if isinstance(best_metrics_raw, Mapping) else {}
    return {
        "strategy_comparison": {
            "artifact": "strategy_comparison",
            "artifact_version": "1",
            "workflow": {
                "name": "parameter_search_trial_ranking",
                "strategy": config.strategy_name.strip().upper(),
                "objective_metric": config.objective_metric,
                "objective_direction": config.objective_direction,
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
                "overall_win_rate": best_metrics.get("win_rate"),
                "average_pnl_per_trade": None,
                "average_holding_time_seconds": None,
                "best_strategy_id": f"{config.strategy_name.strip().upper()}:{best_trial['trial_id']}",
                "worst_strategy_id": strategy_comparison[-1]["strategy_id"] if strategy_comparison else None,
                "risk_adjusted_metrics": None,
            },
        },
    }


def _select_best_trial(
    *,
    trial_rows: Sequence[Mapping[str, Any]],
    objective_direction: str,
) -> Mapping[str, Any]:
    if objective_direction == "max":
        return sorted(
            trial_rows,
            key=lambda row: (-float(row["objective_value"]), str(row["trial_id"])),
        )[0]
    return sorted(
        trial_rows,
        key=lambda row: (float(row["objective_value"]), str(row["trial_id"])),
    )[0]


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

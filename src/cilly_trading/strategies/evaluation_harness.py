"""Deterministic comparable strategy evaluation harness."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_EVEN
from pathlib import Path
from typing import Any, Mapping, Sequence

import pandas as pd

from cilly_trading.engine.backtest_runner import BacktestRunner, BacktestRunnerConfig
from cilly_trading.metrics import canonical_json_bytes, compute_metrics
from cilly_trading.strategies.registry import (
    StrategyNotRegisteredError,
    create_strategy,
    get_registered_strategy_metadata,
)

_METRIC_KEYS = (
    "total_return",
    "cagr",
    "max_drawdown",
    "sharpe_ratio",
    "win_rate",
    "profit_factor",
)
_RUNNER_SNAPSHOT_BOUNDARY_ERROR = (
    "Snapshots must consistently define either 'timestamp' or 'snapshot_key'"
)
_QUANT = Decimal("0.000000000001")
COMPARISON_ARTIFACT_FILENAME = "strategy-comparison.json"
COMPARISON_HASH_FILENAME = "strategy-comparison.sha256"


class StrategyEvaluationInputError(ValueError):
    """Raised when strategy evaluation inputs are invalid."""


class StrategyEvaluationSelectionError(ValueError):
    """Raised when strategy selection fails for strategy evaluation."""


@dataclass(frozen=True)
class StrategyComparisonResult:
    """Result payload for deterministic strategy comparison."""

    artifact_path: Path
    artifact_sha256: str
    payload: dict[str, Any]


def run_strategy_comparison(
    *,
    snapshots: Sequence[Mapping[str, Any]],
    strategy_names: Sequence[str],
    output_dir: Path,
    run_id: str,
    benchmark_strategy: str | None = None,
    strategy_configs: Mapping[str, Mapping[str, Any]] | None = None,
) -> StrategyComparisonResult:
    """Run deterministic strategy comparison workflow and write bounded outputs."""

    normalized_strategy_names = _normalize_strategy_names(strategy_names)
    if benchmark_strategy is None:
        resolved_benchmark = normalized_strategy_names[0]
    else:
        resolved_benchmark = benchmark_strategy.strip().upper()
        if resolved_benchmark not in normalized_strategy_names:
            raise StrategyEvaluationInputError("Benchmark strategy must be included in strategy list")

    strategy_config_map = _normalize_strategy_configs(strategy_configs)
    ordered_snapshots = _sort_snapshots(snapshots)
    snapshot_linkage = _snapshot_linkage(ordered_snapshots)
    metadata_by_key = get_registered_strategy_metadata()
    runner = BacktestRunner()

    strategy_rows: list[dict[str, Any]] = []
    for strategy_name in normalized_strategy_names:
        try:
            strategy = create_strategy(strategy_name)
        except StrategyNotRegisteredError as exc:
            raise StrategyEvaluationSelectionError("Unknown strategy") from exc

        strategy_snapshot_rows, candidate_count, executable_count = _build_strategy_snapshots(
            ordered_snapshots=ordered_snapshots,
            strategy_name=strategy_name,
            strategy=strategy,
            strategy_config=strategy_config_map.get(strategy_name, {}),
        )

        strategy_output_dir = output_dir / "strategies" / strategy_name.lower()
        strategy_run_id = f"{run_id}:{strategy_name.lower()}"
        result = runner.run(
            snapshots=strategy_snapshot_rows,
            strategy_factory=_NoOpBacktestStrategy,
            config=BacktestRunnerConfig(
                output_dir=strategy_output_dir,
                run_id=strategy_run_id,
                strategy_name=strategy_name,
                strategy_params=strategy_config_map.get(strategy_name, {}),
            ),
        )

        artifact_payload = json.loads(result.artifact_path.read_text(encoding="utf-8"))
        metrics = compute_metrics(artifact_payload)
        baseline = artifact_payload.get("metrics_baseline")
        baseline_summary = baseline.get("summary") if isinstance(baseline, Mapping) else {}
        summary = artifact_payload.get("summary")
        summary_payload = summary if isinstance(summary, Mapping) else {}

        comparison_group = _require_comparison_group(metadata_by_key, strategy_name)

        strategy_rows.append(
            {
                "strategy_name": strategy_name,
                "comparison_group": comparison_group,
                "signals": {
                    "candidate_count": candidate_count,
                    "executable_count": executable_count,
                    "translation_rule": "entry_confirmed long -> BUY quantity=1 (single-open-position)",
                },
                "backtest": {
                    "run_id": strategy_run_id,
                    "artifact_relpath": f"strategies/{strategy_name.lower()}/backtest-result.json",
                    "artifact_sha256": result.artifact_sha256,
                    "invocation_log": result.invocation_log,
                },
                "summary": {
                    "start_equity": summary_payload.get("start_equity"),
                    "end_equity": summary_payload.get("end_equity"),
                },
                "metrics": {key: metrics.get(key) for key in _METRIC_KEYS},
                "metrics_baseline_summary": {
                    "starting_equity": baseline_summary.get("starting_equity"),
                    "ending_equity_cost_free": baseline_summary.get("ending_equity_cost_free"),
                    "ending_equity_cost_aware": baseline_summary.get("ending_equity_cost_aware"),
                    "total_transaction_cost": baseline_summary.get("total_transaction_cost"),
                    "total_commission": baseline_summary.get("total_commission"),
                    "total_slippage_cost": baseline_summary.get("total_slippage_cost"),
                    "fill_count": baseline_summary.get("fill_count"),
                },
            }
        )

    ranking = _build_ranking(strategy_rows)
    deltas = _build_deltas(strategy_rows, resolved_benchmark)
    payload: dict[str, Any] = {
        "artifact": "strategy_comparison",
        "artifact_version": "1",
        "semantics": {
            "signal_score": {
                "comparison_scope": "strategy_local_only",
                "cross_strategy_score_comparison_supported": False,
                "summary": (
                    "Signal score values are interpreted within each governed strategy surface and are "
                    "not calibrated as cross-strategy confidence claims."
                ),
            },
            "ranking": {
                "rank_scope": "comparison_group",
                "ranking_metric": "total_return",
                "cross_group_ordering_supported": False,
                "cross_group_delta_supported": False,
                "summary": (
                    "Ranking and benchmark deltas are evidence-backed only within each comparison_group."
                ),
            },
        },
        "workflow": {
            "name": "bounded_comparable_strategy_evaluation",
            "benchmark_strategy": resolved_benchmark,
            "snapshot_linkage": snapshot_linkage,
            "strategy_order": normalized_strategy_names,
            "signal_translation": {
                "trigger_stage": "entry_confirmed",
                "direction": "long",
                "action": "BUY",
                "quantity": "1",
                "max_open_positions": 1,
            },
        },
        "strategies": strategy_rows,
        "ranking": ranking,
        "deltas_vs_benchmark": deltas,
    }

    artifact_path, artifact_sha256 = write_strategy_comparison_artifact(
        payload=payload,
        output_dir=output_dir,
    )
    return StrategyComparisonResult(
        artifact_path=artifact_path,
        artifact_sha256=artifact_sha256,
        payload=payload,
    )


def write_strategy_comparison_artifact(
    *,
    payload: Mapping[str, Any],
    output_dir: Path,
) -> tuple[Path, str]:
    """Persist deterministic strategy comparison artifact and hash."""

    output_dir.mkdir(parents=True, exist_ok=True)
    artifact_path = output_dir / COMPARISON_ARTIFACT_FILENAME
    canonical_bytes = canonical_json_bytes(payload)
    artifact_path.write_bytes(canonical_bytes)

    artifact_sha = hashlib.sha256(canonical_bytes).hexdigest()
    (output_dir / COMPARISON_HASH_FILENAME).write_text(f"{artifact_sha}\n", encoding="utf-8")
    return artifact_path, artifact_sha


class _NoOpBacktestStrategy:
    def on_run_start(self, config: Mapping[str, Any]) -> None:
        del config

    def on_snapshot(self, snapshot: Mapping[str, Any], config: Mapping[str, Any]) -> None:
        del snapshot, config

    def on_run_end(self, config: Mapping[str, Any]) -> None:
        del config


def _normalize_strategy_names(strategy_names: Sequence[str]) -> list[str]:
    normalized: list[str] = []
    for strategy_name in strategy_names:
        if not isinstance(strategy_name, str) or not strategy_name.strip():
            raise StrategyEvaluationInputError("Strategy names must be non-empty strings")
        normalized_name = strategy_name.strip().upper()
        if normalized_name in normalized:
            raise StrategyEvaluationInputError("Strategy names must be unique")
        normalized.append(normalized_name)

    if not normalized:
        raise StrategyEvaluationInputError("At least one strategy is required")
    return normalized


def _normalize_strategy_configs(
    strategy_configs: Mapping[str, Mapping[str, Any]] | None,
) -> dict[str, dict[str, Any]]:
    if strategy_configs is None:
        return {}
    if not isinstance(strategy_configs, Mapping):
        raise StrategyEvaluationInputError("Strategy configs must be a mapping")

    normalized: dict[str, dict[str, Any]] = {}
    for raw_key, raw_value in strategy_configs.items():
        if not isinstance(raw_key, str) or not raw_key.strip():
            raise StrategyEvaluationInputError("Strategy config keys must be non-empty strings")
        if not isinstance(raw_value, Mapping):
            raise StrategyEvaluationInputError("Each strategy config must be an object")
        normalized[raw_key.strip().upper()] = dict(raw_value)
    return normalized


def _sort_snapshots(snapshots: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    sortable: list[tuple[tuple[str, str], dict[str, Any]]] = []
    for raw_snapshot in snapshots:
        if not isinstance(raw_snapshot, Mapping):
            raise StrategyEvaluationInputError("Snapshots must be objects")
        snapshot = dict(raw_snapshot)
        snapshot_id = snapshot.get("id")
        if not isinstance(snapshot_id, str) or not snapshot_id.strip():
            raise StrategyEvaluationInputError("Snapshots must define a non-empty id")
        if "timestamp" in snapshot:
            primary_key = str(snapshot.get("timestamp"))
        elif "snapshot_key" in snapshot:
            primary_key = str(snapshot.get("snapshot_key"))
        else:
            raise StrategyEvaluationInputError("Snapshots must define timestamp or snapshot_key")

        sortable.append(((primary_key, str(snapshot_id)), snapshot))

    sortable.sort(key=lambda item: item[0])
    return [item[1] for item in sortable]


def _snapshot_linkage(snapshots: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    if not snapshots:
        return {
            "mode": "timestamp",
            "start": None,
            "end": None,
            "count": 0,
        }

    has_timestamp = [("timestamp" in snapshot) for snapshot in snapshots]
    has_snapshot_key = [("snapshot_key" in snapshot) for snapshot in snapshots]
    if all(has_timestamp):
        mode = "timestamp"
        boundary_field = "timestamp"
    elif all(has_snapshot_key):
        mode = "snapshot_key"
        boundary_field = "snapshot_key"
    else:
        raise StrategyEvaluationInputError(_RUNNER_SNAPSHOT_BOUNDARY_ERROR)

    start_value = snapshots[0].get(boundary_field)
    end_value = snapshots[-1].get(boundary_field)
    return {
        "mode": mode,
        "start": str(start_value) if start_value is not None else None,
        "end": str(end_value) if end_value is not None else None,
        "count": len(snapshots),
    }


def _build_strategy_snapshots(
    *,
    ordered_snapshots: Sequence[Mapping[str, Any]],
    strategy_name: str,
    strategy: Any,
    strategy_config: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], int, int]:
    snapshot_rows: list[dict[str, Any]] = []
    candidate_count = 0
    executable_count = 0
    has_open_position = False

    for index, snapshot in enumerate(ordered_snapshots):
        history_frame = _history_frame(ordered_snapshots, index)
        candidate_signals = _to_executable_signals(
            strategy_name=strategy_name,
            snapshot=snapshot,
            strategy=strategy,
            history_frame=history_frame,
            strategy_config=strategy_config,
        )
        candidate_count += len(candidate_signals)

        executable_signals: list[dict[str, Any]] = []
        if not has_open_position and candidate_signals:
            executable_signals = [candidate_signals[0]]
            has_open_position = True
            executable_count += 1

        row = dict(snapshot)
        if executable_signals:
            row["signals"] = executable_signals
        snapshot_rows.append(row)

    return snapshot_rows, candidate_count, executable_count


def _history_frame(
    ordered_snapshots: Sequence[Mapping[str, Any]],
    index: int,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for snapshot in ordered_snapshots[: index + 1]:
        row: dict[str, Any] = {}
        for field in ("id", "timestamp", "symbol", "open", "high", "low", "close", "price", "volume"):
            if field in snapshot:
                row[field] = snapshot[field]

        price = row.get("price")
        close = row.get("close")
        if close is None and price is not None:
            row["close"] = price

        normalized_close = row.get("close")
        if normalized_close is not None:
            row.setdefault("open", normalized_close)
            row.setdefault("high", normalized_close)
            row.setdefault("low", normalized_close)

        rows.append(row)

    frame = pd.DataFrame(rows)
    for column in ("open", "high", "low", "close", "price", "volume"):
        if column in frame.columns:
            frame[column] = pd.to_numeric(frame[column], errors="coerce")

    if "timestamp" in frame.columns:
        timestamps = pd.to_datetime(frame["timestamp"], utc=True, errors="coerce")
        if timestamps.notna().all():
            frame = frame.copy()
            frame.index = timestamps

    return frame


def _to_executable_signals(
    *,
    strategy_name: str,
    snapshot: Mapping[str, Any],
    strategy: Any,
    history_frame: pd.DataFrame,
    strategy_config: Mapping[str, Any],
) -> list[dict[str, Any]]:
    try:
        generated = strategy.generate_signals(history_frame, dict(strategy_config))
    except Exception as exc:
        raise StrategyEvaluationInputError(
            f"Strategy signal generation failed: {strategy_name}"
        ) from exc

    if generated is None:
        return []
    if not isinstance(generated, list):
        raise StrategyEvaluationInputError(
            f"Strategy signals must be a list: {strategy_name}"
        )

    snapshot_id = str(snapshot.get("id", "snapshot"))
    executable_signals: list[dict[str, Any]] = []
    for index, signal in enumerate(generated, start=1):
        if not isinstance(signal, Mapping):
            continue

        stage = str(signal.get("stage", "")).strip().lower()
        direction = str(signal.get("direction", "long")).strip().lower()
        if stage != "entry_confirmed" or direction != "long":
            continue

        symbol = _normalize_symbol(signal.get("symbol", snapshot.get("symbol")))
        executable_signals.append(
            {
                "signal_id": f"{strategy_name}:{snapshot_id}:{index}",
                "action": "BUY",
                "quantity": "1",
                "symbol": symbol,
                "risk_evidence": _approved_backtest_risk_evidence(
                    strategy_name=strategy_name,
                    symbol=symbol,
                ),
            }
        )

    executable_signals.sort(key=lambda signal: (signal["signal_id"], signal["symbol"]))
    return executable_signals


def _approved_backtest_risk_evidence(*, strategy_name: str, symbol: str) -> dict[str, str]:
    return {
        "decision": "APPROVED",
        "score": "1",
        "max_allowed": "1",
        "reason": f"strategy_comparison_bounded_risk_approved:{strategy_name}:{symbol}",
        "rule_version": "strategy-comparison-backtest-risk-v1",
    }


def _normalize_symbol(value: Any) -> str:
    if not isinstance(value, str):
        return "UNKNOWN"
    normalized = value.strip().upper()
    if not normalized:
        return "UNKNOWN"
    return normalized


def _comparison_group(metadata_by_key: Mapping[str, Mapping[str, Any]], strategy_name: str) -> str | None:
    strategy_metadata = metadata_by_key.get(strategy_name)
    if not isinstance(strategy_metadata, Mapping):
        return None
    value = strategy_metadata.get("comparison_group")
    if isinstance(value, str):
        return value
    return None


def _require_comparison_group(metadata_by_key: Mapping[str, Mapping[str, Any]], strategy_name: str) -> str:
    comparison_group = _comparison_group(metadata_by_key, strategy_name)
    if comparison_group is None:
        raise StrategyEvaluationSelectionError(
            f"Strategy is outside governed comparison surfaces: {strategy_name}"
        )
    return comparison_group


def _build_ranking(strategy_rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    ranking: list[dict[str, Any]] = []
    rows_by_group: dict[str, list[Mapping[str, Any]]] = {}
    for row in strategy_rows:
        group = str(row.get("comparison_group"))
        rows_by_group.setdefault(group, []).append(row)

    for comparison_group in sorted(rows_by_group.keys()):
        group_rows = sorted(
            rows_by_group[comparison_group],
            key=lambda row: (
                _numeric_metric(row, "total_return") is None,
                -_numeric_metric(row, "total_return")
                if _numeric_metric(row, "total_return") is not None
                else 0.0,
                str(row.get("strategy_name")),
            ),
        )
        for index, row in enumerate(group_rows, start=1):
            ranking.append(
                {
                    "rank": index,
                    "strategy_name": row.get("strategy_name"),
                    "comparison_group": comparison_group,
                    "rank_scope": "comparison_group",
                    "total_return": _numeric_metric(row, "total_return"),
                }
            )
    return ranking


def _build_deltas(
    strategy_rows: Sequence[Mapping[str, Any]],
    benchmark_strategy: str,
) -> list[dict[str, Any]]:
    benchmark_metrics = None
    benchmark_comparison_group: str | None = None
    for row in strategy_rows:
        if row.get("strategy_name") == benchmark_strategy:
            benchmark_metrics = row.get("metrics")
            row_group = row.get("comparison_group")
            if isinstance(row_group, str):
                benchmark_comparison_group = row_group
            break

    benchmark_mapping = benchmark_metrics if isinstance(benchmark_metrics, Mapping) else {}
    deltas: list[dict[str, Any]] = []
    for row in strategy_rows:
        strategy_comparison_group = row.get("comparison_group")
        row_group = (
            strategy_comparison_group
            if isinstance(strategy_comparison_group, str)
            else None
        )
        is_comparable_to_benchmark = (
            benchmark_comparison_group is not None and row_group == benchmark_comparison_group
        )
        metrics = row.get("metrics")
        metrics_map = metrics if isinstance(metrics, Mapping) else {}
        delta_row: dict[str, Any] = {
            "strategy_name": row.get("strategy_name"),
            "comparison_group": row_group,
            "benchmark_strategy": benchmark_strategy,
            "benchmark_comparison_group": benchmark_comparison_group,
            "comparable_to_benchmark": is_comparable_to_benchmark,
        }
        for key in _METRIC_KEYS:
            strategy_value = metrics_map.get(key)
            benchmark_value = benchmark_mapping.get(key)
            delta_row[f"{key}_delta"] = (
                _delta(strategy_value, benchmark_value)
                if is_comparable_to_benchmark
                else None
            )
        deltas.append(delta_row)
    return deltas


def _numeric_metric(row: Mapping[str, Any], metric_key: str) -> float | None:
    metrics = row.get("metrics")
    if not isinstance(metrics, Mapping):
        return None
    value = metrics.get(metric_key)
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _delta(strategy_value: Any, benchmark_value: Any) -> float | None:
    if (
        isinstance(strategy_value, bool)
        or isinstance(benchmark_value, bool)
        or strategy_value is None
        or benchmark_value is None
    ):
        return None
    if not isinstance(strategy_value, (int, float)) or not isinstance(benchmark_value, (int, float)):
        return None

    delta = Decimal(str(float(strategy_value) - float(benchmark_value)))
    rounded = delta.quantize(_QUANT, rounding=ROUND_HALF_EVEN)
    if rounded == Decimal("0"):
        return 0.0
    return float(rounded)

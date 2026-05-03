"""Comparable strategy evaluation CLI execution helpers."""

from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path
from typing import Any, Mapping

from cilly_trading.engine.determinism_guard import (
    DeterminismViolationError,
    install_guard,
    uninstall_guard,
)
from cilly_trading.engine.walkforward import WalkForwardConfig, WalkForwardRunner
from cilly_trading.strategies.evaluation_harness import (
    StrategyEvaluationInputError,
    StrategyEvaluationSelectionError,
    run_strategy_comparison,
)


class ComparisonConfigInputError(ValueError):
    """Raised when comparison strategy configuration cannot be loaded."""


def _load_snapshots(path: Path) -> list[dict[str, Any]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise StrategyEvaluationInputError("Invalid snapshots input") from exc

    if not isinstance(payload, list):
        raise StrategyEvaluationInputError("Invalid snapshots input")

    snapshots: list[dict[str, Any]] = []
    for item in payload:
        if not isinstance(item, Mapping):
            raise StrategyEvaluationInputError("Invalid snapshots input")

        snapshot_id = item.get("id")
        if not isinstance(snapshot_id, str) or not snapshot_id.strip():
            raise StrategyEvaluationInputError("Invalid snapshots input")

        has_timestamp = isinstance(item.get("timestamp"), str) and bool(item["timestamp"].strip())
        has_snapshot_key = isinstance(item.get("snapshot_key"), str) and bool(item["snapshot_key"].strip())
        if not has_timestamp and not has_snapshot_key:
            raise StrategyEvaluationInputError("Invalid snapshots input")

        snapshots.append(dict(item))
    return snapshots


def _load_strategy_configs(path: Path | None) -> dict[str, dict[str, Any]]:
    if path is None:
        return {}

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ComparisonConfigInputError("Invalid strategy config input") from exc

    if not isinstance(payload, Mapping):
        raise ComparisonConfigInputError("Invalid strategy config input")

    normalized: dict[str, dict[str, Any]] = {}
    for strategy_name, config in payload.items():
        if not isinstance(strategy_name, str) or not strategy_name.strip():
            raise ComparisonConfigInputError("Invalid strategy config input")
        if not isinstance(config, Mapping):
            raise ComparisonConfigInputError("Invalid strategy config input")
        normalized[strategy_name.strip().upper()] = dict(config)
    return normalized


def run_compare_strategies(
    *,
    snapshots_path: Path,
    strategy_names: list[str],
    out_dir: Path,
    run_id: str,
    benchmark_strategy: str | None,
    strategy_modules: list[str] | None = None,
    strategy_config_path: Path | None = None,
) -> int:
    """Run deterministic comparable strategy evaluation command."""

    install_guard()
    try:
        snapshots = _load_snapshots(snapshots_path)

        if strategy_modules is not None:
            for module_name in strategy_modules:
                try:
                    importlib.import_module(module_name)
                except Exception as exc:
                    raise StrategyEvaluationSelectionError("Unknown strategy") from exc

        strategy_configs = _load_strategy_configs(strategy_config_path)
        result = run_strategy_comparison(
            snapshots=snapshots,
            strategy_names=strategy_names,
            output_dir=out_dir,
            run_id=run_id,
            benchmark_strategy=benchmark_strategy,
            strategy_configs=strategy_configs,
        )
        print(f"WROTE {result.artifact_path}")
        return 0
    except DeterminismViolationError as exc:
        print(str(exc), file=sys.stderr)
        return 10
    except StrategyEvaluationInputError as exc:
        print(str(exc), file=sys.stderr)
        return 20
    except ComparisonConfigInputError as exc:
        print(str(exc), file=sys.stderr)
        return 20
    except StrategyEvaluationSelectionError as exc:
        print(str(exc), file=sys.stderr)
        return 30
    except Exception as exc:  # pragma: no cover - fallback protection
        print(f"Unexpected error: {exc}", file=sys.stderr)
        return 1
    finally:
        uninstall_guard()


class WalkForwardInputError(ValueError):
    """Raised when walk-forward input files cannot be loaded."""


def _load_equity_curve(path: Path) -> list[dict[str, Any]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise WalkForwardInputError("Invalid equity_curve input") from exc

    if not isinstance(payload, list):
        raise WalkForwardInputError("Invalid equity_curve input: expected a JSON array")

    curve: list[dict[str, Any]] = []
    for item in payload:
        if not isinstance(item, Mapping):
            raise WalkForwardInputError("Invalid equity_curve input: items must be objects")
        if "timestamp" not in item or "equity" not in item:
            raise WalkForwardInputError(
                "Invalid equity_curve input: each item must have 'timestamp' and 'equity'"
            )
        curve.append(dict(item))
    return curve


def _load_trades(path: Path) -> list[dict[str, Any]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise WalkForwardInputError("Invalid trades input") from exc

    if not isinstance(payload, list):
        raise WalkForwardInputError("Invalid trades input: expected a JSON array")

    return [dict(item) for item in payload if isinstance(item, Mapping)]


def run_walk_forward(
    *,
    equity_curve_path: Path,
    out_dir: Path,
    run_id: str,
    trades_path: Path | None = None,
    in_sample_ratio: float = 0.7,
    n_windows: int = 5,
    anchored: bool = False,
) -> int:
    """Run walk-forward validation and write result artifact.

    Loads equity curve (and optionally trades) from JSON files, runs
    WalkForwardRunner, and writes the result artifact to ``out_dir``.

    Returns an integer exit code: 0 on success, non-zero on error.

    NOTE: Out-of-sample results do NOT guarantee future performance.
    """
    try:
        equity_curve = _load_equity_curve(equity_curve_path)
        trades = _load_trades(trades_path) if trades_path is not None else []

        cfg = WalkForwardConfig(
            in_sample_ratio=in_sample_ratio,
            n_windows=n_windows,
            anchored=anchored,
        )

        runner = WalkForwardRunner()
        result = runner.run(equity_curve=equity_curve, trades=trades, config=cfg)

        out_dir.mkdir(parents=True, exist_ok=True)
        artifact = result.to_artifact()
        artifact_path = out_dir / f"walkforward-{run_id}.json"
        artifact_path.write_text(
            json.dumps(artifact, sort_keys=True, separators=(",", ":"), allow_nan=False)
            + "\n",
            encoding="utf-8",
        )
        print(f"WROTE {artifact_path}")
        return 0

    except WalkForwardInputError as exc:
        print(str(exc), file=sys.stderr)
        return 20
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 20
    except Exception as exc:  # pragma: no cover - fallback protection
        print(f"Unexpected error: {exc}", file=sys.stderr)
        return 1


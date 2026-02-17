"""Backtest CLI execution helpers."""

from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path
from typing import Any, Callable, Mapping

from cilly_trading.engine.backtest_runner import BacktestRunner, BacktestRunnerConfig, BacktestStrategy
from cilly_trading.engine.determinism_guard import (
    DeterminismViolationError,
    install_guard,
    uninstall_guard,
)
from cilly_trading.strategies.registry import StrategyNotRegisteredError, create_strategy


class SnapshotInputError(ValueError):
    """Raised when snapshot input cannot be loaded for backtest."""


class StrategySelectionError(ValueError):
    """Raised when strategy selection fails for backtest."""


def _load_snapshots(path: Path) -> list[dict[str, Any]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SnapshotInputError("Invalid snapshots input") from exc

    if not isinstance(payload, list):
        raise SnapshotInputError("Invalid snapshots input")

    snapshots: list[dict[str, Any]] = []
    for item in payload:
        if not isinstance(item, Mapping):
            raise SnapshotInputError("Invalid snapshots input")
        snapshots.append(dict(item))
    return snapshots


def _resolve_strategy_factory(strategy_name: str) -> Callable[[], BacktestStrategy]:
    def _factory() -> BacktestStrategy:
        try:
            return create_strategy(strategy_name)
        except StrategyNotRegisteredError as exc:
            raise StrategySelectionError("Unknown strategy") from exc

    return _factory


def run_backtest(
    *,
    snapshots_path: Path,
    strategy_name: str,
    out_dir: Path,
    run_id: str,
    strategy_modules: list[str] | None = None,
) -> int:
    """Run deterministic backtest command and return deterministic exit code."""

    install_guard()
    try:
        snapshots = _load_snapshots(snapshots_path)

        if strategy_modules is not None:
            for module_name in strategy_modules:
                try:
                    importlib.import_module(module_name)
                except Exception as exc:
                    raise StrategySelectionError("Unknown strategy") from exc

        strategy_factory = _resolve_strategy_factory(strategy_name)

        def _backtest_strategy_factory() -> BacktestStrategy:
            strategy = strategy_factory()

            class _StrategyAdapter:
                def on_run_start(self, config: Mapping[str, Any]) -> None:
                    callback = getattr(strategy, "on_run_start", None)
                    if callable(callback):
                        callback(config)

                def on_snapshot(self, snapshot: Mapping[str, Any], config: Mapping[str, Any]) -> None:
                    callback = getattr(strategy, "on_snapshot", None)
                    if callable(callback):
                        callback(snapshot, config)

                def on_run_end(self, config: Mapping[str, Any]) -> None:
                    callback = getattr(strategy, "on_run_end", None)
                    if callable(callback):
                        callback(config)

            return _StrategyAdapter()

        runner = BacktestRunner()
        runner.run(
            snapshots=snapshots,
            strategy_factory=_backtest_strategy_factory,
            config=BacktestRunnerConfig(
                output_dir=out_dir,
                run_id=run_id,
                strategy_name=strategy_name,
            ),
        )
        return 0
    except DeterminismViolationError as exc:
        print(str(exc), file=sys.stderr)
        return 10
    except SnapshotInputError as exc:
        print(str(exc), file=sys.stderr)
        return 20
    except StrategySelectionError as exc:
        print(str(exc), file=sys.stderr)
        return 30
    except Exception as exc:  # pragma: no cover - fallback protection
        print(f"Unexpected error: {exc}", file=sys.stderr)
        return 1
    finally:
        uninstall_guard()

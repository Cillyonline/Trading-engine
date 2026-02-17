"""Backtest CLI execution helpers."""

from __future__ import annotations

import importlib
import json
import os
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


TEST_STRATEGY_IMPORT_ENV = "CILLY_BACKTEST_TEST_STRATEGY_IMPORT"


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


def _resolve_test_strategy_factory(strategy_name: str) -> Callable[[], BacktestStrategy] | None:
    """Resolve an opt-in test strategy factory via environment variable.

    This branch is intentionally disabled by default and only used in tests to
    validate deterministic guard behavior without changing production registry.
    """

    import_spec = os.environ.get(TEST_STRATEGY_IMPORT_ENV)
    if not import_spec:
        return None

    try:
        strategy_key, target = import_spec.split("=", 1)
        module_name, object_name = target.split(":", 1)
    except ValueError as exc:
        raise StrategySelectionError("Unknown strategy") from exc

    if strategy_name != strategy_key:
        return None

    try:
        module = importlib.import_module(module_name)
        factory_obj = getattr(module, object_name)
    except (ImportError, AttributeError) as exc:
        raise StrategySelectionError("Unknown strategy") from exc

    if not callable(factory_obj):
        raise StrategySelectionError("Unknown strategy")

    def _factory() -> BacktestStrategy:
        return factory_obj()

    return _factory


def _resolve_strategy_factory(strategy_name: str) -> Callable[[], BacktestStrategy]:
    test_factory = _resolve_test_strategy_factory(strategy_name)
    if test_factory is not None:
        return test_factory

    try:
        # Validate strategy selection via central registry mechanism.
        create_strategy(strategy_name)
    except StrategyNotRegisteredError as exc:
        raise StrategySelectionError("Unknown strategy") from exc

    class _NoOpBacktestStrategy:
        def on_run_start(self, config: Mapping[str, Any]) -> None:
            del config

        def on_snapshot(self, snapshot: Mapping[str, Any], config: Mapping[str, Any]) -> None:
            del snapshot, config

        def on_run_end(self, config: Mapping[str, Any]) -> None:
            del config

    return _NoOpBacktestStrategy


def run_backtest(*, snapshots_path: Path, strategy_name: str, out_dir: Path, run_id: str) -> int:
    """Run deterministic backtest command and return deterministic exit code."""

    install_guard()
    try:
        snapshots = _load_snapshots(snapshots_path)
        strategy_factory = _resolve_strategy_factory(strategy_name)
        runner = BacktestRunner()
        runner.run(
            snapshots=snapshots,
            strategy_factory=strategy_factory,
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

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Mapping

from cilly_trading.engine.backtest_runner import BacktestRunner, BacktestRunnerConfig


class SpyStrategy:
    def __init__(self) -> None:
        self.calls: List[str] = []

    def on_run_start(self, config: Mapping[str, Any]) -> None:
        self.calls.append("on_run_start")

    def on_snapshot(self, snapshot: Mapping[str, Any], config: Mapping[str, Any]) -> None:
        self.calls.append(f"on_snapshot:{snapshot['id']}")

    def on_run_end(self, config: Mapping[str, Any]) -> None:
        self.calls.append("on_run_end")


def _sample_snapshots() -> List[Dict[str, Any]]:
    return [
        {"id": "s3", "timestamp": "2024-01-02T00:00:00Z", "price": 12},
        {"id": "s1", "timestamp": "2024-01-01T00:00:00Z", "price": 10},
        {"id": "s2", "timestamp": "2024-01-01T00:00:00Z", "price": 11},
    ]


def _run_with_spy(output_dir: Path):
    container: Dict[str, SpyStrategy] = {}

    def strategy_factory() -> SpyStrategy:
        strategy = SpyStrategy()
        container["strategy"] = strategy
        return strategy

    runner = BacktestRunner()
    result = runner.run(
        snapshots=_sample_snapshots(),
        strategy_factory=strategy_factory,
        config=BacktestRunnerConfig(output_dir=output_dir),
    )
    return result, container["strategy"]


def test_backtest_runner_deterministic_repeat(tmp_path: Path) -> None:
    runner = BacktestRunner()

    def strategy_factory() -> SpyStrategy:
        return SpyStrategy()

    run1_dir = tmp_path / "run-1"
    run2_dir = tmp_path / "run-2"

    result1 = runner.run(
        snapshots=_sample_snapshots(),
        strategy_factory=strategy_factory,
        config=BacktestRunnerConfig(output_dir=run1_dir),
    )
    result2 = runner.run(
        snapshots=_sample_snapshots(),
        strategy_factory=strategy_factory,
        config=BacktestRunnerConfig(output_dir=run2_dir),
    )

    bytes1 = result1.artifact_path.read_bytes()
    bytes2 = result2.artifact_path.read_bytes()

    assert bytes1 == bytes2
    assert result1.artifact_sha256 == result2.artifact_sha256


def test_backtest_runner_snapshot_consistency_order(tmp_path: Path) -> None:
    result, _ = _run_with_spy(tmp_path / "ordered")

    processed_ids = [snapshot["id"] for snapshot in result.processed_snapshots]
    assert processed_ids == ["s1", "s2", "s3"]


def test_backtest_runner_strategy_invocation_stability(tmp_path: Path) -> None:
    result1, spy1 = _run_with_spy(tmp_path / "run-a")
    result2, spy2 = _run_with_spy(tmp_path / "run-b")

    assert result1.invocation_log == result2.invocation_log
    assert spy1.calls == spy2.calls
    assert result1.invocation_log == spy1.calls


def test_backtest_runner_smoke_artifact_created(tmp_path: Path) -> None:
    runner = BacktestRunner()

    def strategy_factory() -> SpyStrategy:
        return SpyStrategy()

    result = runner.run(
        snapshots=[
            {"id": "a", "timestamp": "2024-01-01T00:00:00Z", "price": 1},
            {"id": "b", "timestamp": "2024-01-01T00:00:00Z", "price": 2},
        ],
        strategy_factory=strategy_factory,
        config=BacktestRunnerConfig(output_dir=tmp_path / "smoke"),
    )

    assert result.artifact_path.exists()
    assert result.artifact_path.read_text(encoding="utf-8").endswith("\n")

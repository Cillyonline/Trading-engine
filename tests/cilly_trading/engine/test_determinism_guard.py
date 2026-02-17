from __future__ import annotations

import datetime
import random
import secrets
import socket
import time
from pathlib import Path
from typing import Any, Dict, List, Mapping

import pytest

from cilly_trading.engine.backtest_runner import BacktestRunner, BacktestRunnerConfig
from cilly_trading.engine.determinism_guard import (
    DeterminismViolationError,
    install_guard,
    uninstall_guard,
)


class SpyStrategy:
    def __init__(self) -> None:
        self.calls: List[str] = []

    def on_run_start(self, config: Mapping[str, Any]) -> None:
        self.calls.append("on_run_start")

    def on_snapshot(self, snapshot: Mapping[str, Any], config: Mapping[str, Any]) -> None:
        self.calls.append(f"on_snapshot:{snapshot['id']}")

    def on_run_end(self, config: Mapping[str, Any]) -> None:
        self.calls.append("on_run_end")


def test_guard_blocks_system_time() -> None:
    install_guard()
    try:
        with pytest.raises(
            DeterminismViolationError,
            match=r"Determinism violation: system time access \(time.time\)",
        ):
            time.time()
        with pytest.raises(
            DeterminismViolationError,
            match=r"Determinism violation: system time access \(time.time_ns\)",
        ):
            time.time_ns()
        with pytest.raises(
            DeterminismViolationError,
            match=r"Determinism violation: system time access \(datetime.datetime.now\)",
        ):
            datetime.datetime.now()
        with pytest.raises(
            DeterminismViolationError,
            match=r"Determinism violation: system time access \(datetime.datetime.utcnow\)",
        ):
            datetime.datetime.utcnow()
    finally:
        uninstall_guard()


def test_guard_blocks_randomness() -> None:
    install_guard()
    try:
        with pytest.raises(DeterminismViolationError, match="random.random"):
            random.random()
        with pytest.raises(DeterminismViolationError, match="random.randint"):
            random.randint(0, 1)
        with pytest.raises(DeterminismViolationError, match="random.choice"):
            random.choice([1, 2])
        with pytest.raises(DeterminismViolationError, match="random.randrange"):
            random.randrange(10)
        with pytest.raises(DeterminismViolationError, match="secrets.token_hex"):
            secrets.token_hex(16)
        with pytest.raises(DeterminismViolationError, match="secrets.token_bytes"):
            secrets.token_bytes(16)
        with pytest.raises(DeterminismViolationError, match="secrets.choice"):
            secrets.choice([1, 2])
    finally:
        uninstall_guard()


def test_guard_blocks_network() -> None:
    install_guard()
    try:
        with pytest.raises(
            DeterminismViolationError,
            match=r"Determinism violation: network access \(socket.getaddrinfo\)",
        ):
            socket.getaddrinfo("example.com", 80)
        with pytest.raises(
            DeterminismViolationError,
            match=r"Determinism violation: network access \(socket.create_connection\)",
        ):
            socket.create_connection(("example.com", 80))
    finally:
        uninstall_guard()


def test_guard_allows_backtest_smoke_run(tmp_path: Path) -> None:
    install_guard()
    try:
        runner = BacktestRunner()

        def strategy_factory() -> SpyStrategy:
            return SpyStrategy()

        snapshots: List[Dict[str, Any]] = [
            {"id": "s2", "timestamp": "2024-01-02T00:00:00Z", "price": 11.0},
            {"id": "s1", "timestamp": "2024-01-01T00:00:00Z", "price": 10.0},
        ]

        result = runner.run(
            snapshots=snapshots,
            strategy_factory=strategy_factory,
            config=BacktestRunnerConfig(output_dir=tmp_path / "guard-smoke"),
        )

        assert result.artifact_path.exists()
    finally:
        uninstall_guard()

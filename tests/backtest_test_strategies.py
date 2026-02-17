from __future__ import annotations

import time
from typing import Any, Mapping

from cilly_trading.strategies.registry import DuplicateStrategyRegistrationError, register_strategy


class DeterminismViolationStrategy:
    name = "TEST_TIME_VIOLATION"

    def generate_signals(self, df, config: dict[str, Any]):
        del df, config
        return []

    def on_run_start(self, config: Mapping[str, Any]) -> None:
        del config
        time.time()

    def on_snapshot(self, snapshot: Mapping[str, Any], config: Mapping[str, Any]) -> None:
        del snapshot, config

    def on_run_end(self, config: Mapping[str, Any]) -> None:
        del config


def create_determinism_violation_strategy() -> DeterminismViolationStrategy:
    return DeterminismViolationStrategy()


try:
    register_strategy(
        "TEST_TIME_VIOLATION",
        create_determinism_violation_strategy,
        metadata={
            "pack_id": "test-pack",
            "version": "1.0.0",
            "deterministic_hash": "test-time-violation",
            "dependencies": [],
        },
    )
except DuplicateStrategyRegistrationError:
    pass

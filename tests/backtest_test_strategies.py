from __future__ import annotations

import time
from typing import Any, Mapping


class DeterminismViolationStrategy:
    def on_run_start(self, config: Mapping[str, Any]) -> None:
        del config
        time.time()

    def on_snapshot(self, snapshot: Mapping[str, Any], config: Mapping[str, Any]) -> None:
        del snapshot, config

    def on_run_end(self, config: Mapping[str, Any]) -> None:
        del config


def create_determinism_violation_strategy() -> DeterminismViolationStrategy:
    return DeterminismViolationStrategy()

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from cilly_trading.strategies.registry import initialize_default_registry


@dataclass(frozen=True)
class ApiRuntimeSettings:
    ui_directory: Path
    journal_artifacts_root: Path
    engine_runtime_not_running_status: int
    engine_runtime_not_running_code: str
    phase_13_read_only_endpoints: frozenset[str]
    role_header_name: str
    role_precedence: dict[str, int]
    default_strategy_configs: dict[str, dict[str, Any]]


def build_default_strategy_configs() -> dict[str, dict[str, Any]]:
    initialize_default_registry()
    return {
        "RSI2": {
            "rsi_period": 2,
            "oversold_threshold": 10.0,
            "min_score": 20.0,
        },
        "TURTLE": {
            "breakout_lookback": 20,
            "proximity_threshold_pct": 0.03,
            "min_score": 30.0,
        },
    }


def build_api_runtime_settings() -> ApiRuntimeSettings:
    return ApiRuntimeSettings(
        ui_directory=Path(__file__).resolve().parents[2] / "ui",
        journal_artifacts_root=Path(__file__).resolve().parents[3] / "runs" / "phase6",
        engine_runtime_not_running_status=503,
        engine_runtime_not_running_code="engine_runtime_not_running",
        phase_13_read_only_endpoints=frozenset({"/health", "/runtime/introspection"}),
        role_header_name="X-Cilly-Role",
        role_precedence={
            "read_only": 1,
            "operator": 2,
            "owner": 3,
        },
        default_strategy_configs=build_default_strategy_configs(),
    )

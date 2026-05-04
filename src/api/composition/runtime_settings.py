from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from cilly_trading.strategies.registry import initialize_default_registry


@dataclass(frozen=True)
class ApiRuntimeSettings:
    ui_directory: Path
    journal_artifacts_root: Path
    paper_runtime_evidence_series_dir: Optional[Path]
    engine_runtime_not_running_status: int
    engine_runtime_not_running_code: str
    phase_13_read_only_endpoints: frozenset[str]
    role_header_name: str
    role_precedence: dict[str, int]
    default_strategy_configs: dict[str, dict[str, Any]]
    scheduled_analysis_enabled: bool
    scheduled_analysis_poll_interval_seconds: int
    scheduled_analysis_snapshot_scan_limit: int
    scheduled_analysis_tasks_json: str
    api_host: str
    api_port: int
    cors_origins: list[str]


def _read_bool_env(name: str, *, default: bool) -> bool:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default

    normalized = raw_value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return default


def _read_int_env(name: str, *, default: int, minimum: int) -> int:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default

    try:
        parsed = int(raw_value)
    except (TypeError, ValueError):
        return default
    return max(parsed, minimum)


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


def _read_cors_origins() -> list[str]:
    raw = os.getenv("CILLY_CORS_ORIGINS", "http://localhost:5173").strip()
    return [o.strip() for o in raw.split(",") if o.strip()]


def build_api_runtime_settings() -> ApiRuntimeSettings:
    paper_runtime_evidence_series_dir_raw = os.getenv(
        "CILLY_PAPER_RUNTIME_EVIDENCE_SERIES_DIR",
        "",
    ).strip()
    return ApiRuntimeSettings(
        ui_directory=Path(__file__).resolve().parents[2] / "ui",
        journal_artifacts_root=Path(__file__).resolve().parents[3] / "runs" / "phase6",
        paper_runtime_evidence_series_dir=(
            Path(paper_runtime_evidence_series_dir_raw)
            if paper_runtime_evidence_series_dir_raw
            else None
        ),
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
        scheduled_analysis_enabled=_read_bool_env(
            "CILLY_SCHEDULED_ANALYSIS_ENABLED",
            default=False,
        ),
        scheduled_analysis_poll_interval_seconds=_read_int_env(
            "CILLY_SCHEDULED_ANALYSIS_POLL_INTERVAL_SECONDS",
            default=300,
            minimum=1,
        ),
        scheduled_analysis_snapshot_scan_limit=_read_int_env(
            "CILLY_SCHEDULED_ANALYSIS_SNAPSHOT_SCAN_LIMIT",
            default=50,
            minimum=1,
        ),
        scheduled_analysis_tasks_json=os.getenv(
            "CILLY_SCHEDULED_ANALYSIS_TASKS_JSON",
            "",
        ).strip(),
        api_host=os.getenv("CILLY_API_HOST", "0.0.0.0"),
        api_port=_read_int_env("CILLY_API_PORT", default=8000, minimum=1),
        cors_origins=_read_cors_origins(),
    )

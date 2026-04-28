from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import Any, MutableMapping

from cilly_trading.engine.analysis import trigger_operator_analysis_run
from cilly_trading.engine.core import run_watchlist_analysis
from cilly_trading.engine.data import SnapshotDataError
from cilly_trading.engine.runtime_controller import (
    LifecycleTransitionError,
    get_runtime_controller,
    pause_engine_runtime,
    resume_engine_runtime,
    shutdown_engine_runtime,
    start_engine_runtime,
)
from cilly_trading.engine.runtime_introspection import get_runtime_introspection_payload
from cilly_trading.engine.runtime_state import get_system_state_payload
from cilly_trading.strategies.registry import create_registered_strategies, create_strategy

from ..services.composition_runtime_service import CompositionRuntimeService
from .repositories import ApiRepositories
from .runtime_settings import ApiRuntimeSettings


@dataclass(frozen=True)
class MainModuleCompatibilitySurface:
    module_name: str

    def get(self, name: str) -> Any:
        return getattr(sys.modules[self.module_name], name)

    def set(self, name: str, value: Any) -> None:
        setattr(sys.modules[self.module_name], name, value)


def bind_main_runtime_exports(
    *,
    module_globals: MutableMapping[str, Any],
    settings: ApiRuntimeSettings,
    repositories: ApiRepositories,
) -> MainModuleCompatibilitySurface:
    module_globals.update(
        {
            "UI_DIRECTORY": settings.ui_directory,
            "JOURNAL_ARTIFACTS_ROOT": settings.journal_artifacts_root,
            "PAPER_RUNTIME_EVIDENCE_SERIES_DIR": settings.paper_runtime_evidence_series_dir,
            "ENGINE_RUNTIME_NOT_RUNNING_STATUS": settings.engine_runtime_not_running_status,
            "ENGINE_RUNTIME_NOT_RUNNING_CODE": settings.engine_runtime_not_running_code,
            "ENGINE_RUNTIME_GUARD_ACTIVE": False,
            "PHASE_13_READ_ONLY_ENDPOINTS": settings.phase_13_read_only_endpoints,
            "ROLE_HEADER_NAME": settings.role_header_name,
            "ROLE_PRECEDENCE": settings.role_precedence,
            "default_strategy_configs": settings.default_strategy_configs,
            "ANALYSIS_DB_PATH": None,
            "signal_repo": repositories.signal_repo,
            "order_event_repo": repositories.order_event_repo,
            "canonical_execution_repo": repositories.canonical_execution_repo,
            "analysis_run_repo": repositories.analysis_run_repo,
            "watchlist_repo": repositories.watchlist_repo,
            "LifecycleTransitionError": LifecycleTransitionError,
            "SnapshotDataError": SnapshotDataError,
            "start_engine_runtime": start_engine_runtime,
            "shutdown_engine_runtime": shutdown_engine_runtime,
            "pause_engine_runtime": pause_engine_runtime,
            "resume_engine_runtime": resume_engine_runtime,
            "get_runtime_controller": get_runtime_controller,
            "run_watchlist_analysis": run_watchlist_analysis,
            "trigger_operator_analysis_run": trigger_operator_analysis_run,
            "create_strategy": create_strategy,
            "create_registered_strategies": create_registered_strategies,
            "get_runtime_introspection_payload": get_runtime_introspection_payload,
            "get_system_state_payload": get_system_state_payload,
        }
    )
    return MainModuleCompatibilitySurface(module_name=str(module_globals["__name__"]))


def bind_main_runtime_service_exports(
    *,
    module_globals: MutableMapping[str, Any],
    runtime_service: CompositionRuntimeService,
    scheduled_analysis_runner: Any | None = None,
) -> None:
    exports: dict[str, Any] = {
        "_runtime_service": runtime_service,
        "_assert_phase_13_read_only_endpoint": runtime_service.assert_phase_13_read_only_endpoint,
        "_require_role": runtime_service.require_role,
        "_health_now": runtime_service.health_now,
        "_resolve_analysis_db_path": runtime_service.resolve_analysis_db_path,
        "_require_ingestion_run": runtime_service.require_ingestion_run,
        "_require_snapshot_ready": runtime_service.require_snapshot_ready,
        "_require_engine_runtime_running": runtime_service.require_engine_runtime_running,
        "_run_snapshot_analysis": runtime_service.run_snapshot_analysis,
        "_analysis_service_dependencies": runtime_service.analysis_service_dependencies,
        "basic_screener": runtime_service.basic_screener,
        "read_compliance_guard_status": runtime_service.read_compliance_guard_status,
        "runtime_introspection": runtime_service.runtime_introspection,
        "system_state": runtime_service.system_state,
    }
    if scheduled_analysis_runner is not None:
        exports.update(
            {
                "scheduled_analysis_runner": scheduled_analysis_runner,
                "start_scheduled_analysis_runner": scheduled_analysis_runner.start,
                "shutdown_scheduled_analysis_runner": scheduled_analysis_runner.stop,
            }
        )
    module_globals.update(exports)

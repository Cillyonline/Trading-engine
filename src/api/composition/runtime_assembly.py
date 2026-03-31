from __future__ import annotations

import logging
from typing import Any, Callable

from cilly_trading.db import DEFAULT_DB_PATH
from cilly_trading.engine.health.evaluator import evaluate_runtime_health

from ..services.composition_runtime_service import CompositionRuntimeService
from ..services.scheduled_analysis_runner import ScheduledAnalysisRunner
from .main_compat import MainModuleCompatibilitySurface
from .router_wiring import ApiRouterWiring
from .runtime_lifecycle import RuntimeLifecycleDependencies
from .runtime_settings import ApiRuntimeSettings


def create_runtime_service(
    *,
    logger: logging.Logger,
    compat: MainModuleCompatibilitySurface,
) -> CompositionRuntimeService:
    return CompositionRuntimeService(
        logger=logger,
        default_db_path=str(DEFAULT_DB_PATH),
        role_header_name=compat.get("ROLE_HEADER_NAME"),
        role_precedence=compat.get("ROLE_PRECEDENCE"),
        phase_13_read_only_endpoints=compat.get("PHASE_13_READ_ONLY_ENDPOINTS"),
        engine_runtime_not_running_status=compat.get("ENGINE_RUNTIME_NOT_RUNNING_STATUS"),
        engine_runtime_not_running_code=compat.get("ENGINE_RUNTIME_NOT_RUNNING_CODE"),
        get_analysis_db_path_override=lambda: compat.get("ANALYSIS_DB_PATH"),
        get_analysis_run_repo=lambda: compat.get("analysis_run_repo"),
        get_signal_repo=lambda: compat.get("signal_repo"),
        get_watchlist_repo=lambda: compat.get("watchlist_repo"),
        get_default_strategy_configs=lambda: compat.get("default_strategy_configs"),
        get_create_strategy=lambda: compat.get("create_strategy"),
        get_create_registered_strategies=lambda: compat.get("create_registered_strategies"),
        get_trigger_operator_analysis_run=lambda: compat.get("trigger_operator_analysis_run"),
        get_runtime_controller=lambda: compat.get("get_runtime_controller")(),
        get_engine_runtime_guard_active=lambda: compat.get("ENGINE_RUNTIME_GUARD_ACTIVE"),
        get_run_watchlist_analysis=lambda: compat.get("run_watchlist_analysis"),
        get_require_ingestion_run_compat=lambda: compat.get("_require_ingestion_run"),
        get_require_snapshot_ready_compat=lambda: compat.get("_require_snapshot_ready"),
        get_run_snapshot_analysis_compat=lambda: compat.get("_run_snapshot_analysis"),
        get_require_engine_runtime_running_compat=lambda: compat.get("_require_engine_runtime_running"),
        snapshot_data_error_class=compat.get("SnapshotDataError"),
        get_runtime_introspection_payload=lambda: compat.get("get_runtime_introspection_payload"),
        get_system_state_payload=lambda: compat.get("get_system_state_payload"),
    )


def build_runtime_lifecycle_dependencies(
    *,
    logger: logging.Logger,
    compat: MainModuleCompatibilitySurface,
) -> RuntimeLifecycleDependencies:
    return RuntimeLifecycleDependencies(
        logger=logger,
        start_runtime=lambda: compat.get("start_engine_runtime")(),
        shutdown_runtime=lambda: compat.get("shutdown_engine_runtime")(),
        start_scheduled_analysis_runner=lambda: compat.get("start_scheduled_analysis_runner")(),
        shutdown_scheduled_analysis_runner=lambda: compat.get(
            "shutdown_scheduled_analysis_runner"
        )(),
        set_runtime_guard_active=lambda is_active: compat.set("ENGINE_RUNTIME_GUARD_ACTIVE", is_active),
        lifecycle_transition_error=compat.get("LifecycleTransitionError"),
    )


def create_scheduled_analysis_runner(
    *,
    logger: logging.Logger,
    runtime_service: CompositionRuntimeService,
    get_runtime_controller: Callable[[], Any],
    settings: ApiRuntimeSettings,
) -> ScheduledAnalysisRunner:
    return ScheduledAnalysisRunner(
        enabled=settings.scheduled_analysis_enabled,
        poll_interval_seconds=settings.scheduled_analysis_poll_interval_seconds,
        snapshot_scan_limit=settings.scheduled_analysis_snapshot_scan_limit,
        raw_tasks_json=settings.scheduled_analysis_tasks_json,
        build_analysis_service_dependencies=runtime_service.analysis_service_dependencies,
        get_runtime_controller=get_runtime_controller,
        resolve_analysis_db_path=runtime_service.resolve_analysis_db_path,
        logger=logger,
    )


def build_api_router_wiring(*, compat: MainModuleCompatibilitySurface) -> ApiRouterWiring:
    return ApiRouterWiring(
        require_role=lambda minimum_role: compat.get("_require_role")(minimum_role),
        assert_phase_13_read_only_endpoint=lambda endpoint_path: compat.get(
            "_assert_phase_13_read_only_endpoint"
        )(endpoint_path),
        get_health_now=lambda: compat.get("_health_now")(),
        get_resolve_analysis_db_path=lambda: compat.get("_resolve_analysis_db_path")(),
        get_runtime_introspection_payload=lambda: compat.get("get_runtime_introspection_payload")(),
        get_runtime_health_evaluator=lambda *args, **kwargs: evaluate_runtime_health(*args, **kwargs),
        get_system_state_payload=lambda: compat.get("get_system_state_payload")(),
        get_start_engine_runtime=lambda: compat.get("start_engine_runtime")(),
        get_shutdown_engine_runtime=lambda: compat.get("shutdown_engine_runtime")(),
        get_pause_engine_runtime=lambda: compat.get("pause_engine_runtime")(),
        get_resume_engine_runtime=lambda: compat.get("resume_engine_runtime")(),
        get_lifecycle_transition_error=lambda: compat.get("LifecycleTransitionError"),
        get_analysis_run_repo=lambda: compat.get("analysis_run_repo"),
        get_signal_repo=lambda: compat.get("signal_repo"),
        get_order_event_repo=lambda: compat.get("order_event_repo"),
        get_canonical_execution_repo=lambda: compat.get("canonical_execution_repo"),
        get_journal_artifacts_root=lambda: compat.get("JOURNAL_ARTIFACTS_ROOT"),
        get_default_strategy_configs=lambda: compat.get("default_strategy_configs"),
        get_watchlist_repo=lambda: compat.get("watchlist_repo"),
        get_require_ingestion_run=lambda *args, **kwargs: compat.get("_require_ingestion_run")(
            *args,
            **kwargs,
        ),
        get_require_snapshot_ready=lambda *args, **kwargs: compat.get("_require_snapshot_ready")(
            *args,
            **kwargs,
        ),
        get_run_snapshot_analysis=lambda *args, **kwargs: compat.get("_run_snapshot_analysis")(
            *args,
            **kwargs,
        ),
        get_create_strategy=lambda strategy_name: compat.get("create_strategy")(strategy_name),
        get_create_registered_strategies=lambda: compat.get("create_registered_strategies")(),
        get_trigger_operator_analysis_run=lambda *args, **kwargs: compat.get(
            "trigger_operator_analysis_run"
        )(
            *args,
            **kwargs,
        ),
    )

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterable, Tuple

from fastapi import APIRouter, FastAPI

from ..alerts_api import build_alerts_router
from ..routers import (
    AnalysisRouterDependencies,
    ControlPlaneRouterDependencies,
    InspectionRouterDependencies,
    JournalRouterDependencies,
    PaperRuntimeEvidenceSeriesRouterDependencies,
    WatchlistsRouterDependencies,
    build_analysis_router,
    build_control_plane_router,
    build_inspection_router,
    build_journal_router,
    build_paper_runtime_evidence_series_router,
    build_watchlists_router,
)
from ..routers.auth_router import AuthRouterDependencies, build_auth_router
from ..services.jwt_auth import JwtSettings


# Legacy (un-prefixed) URLs continue to serve responses; ``/v1/...`` is
# the new canonical API surface (issue #1135). Bumping ``API_VERSION``
# adds a new mount path without removing the legacy one, so clients can
# migrate at their own pace.
API_VERSION_PREFIX = "/v1"


@dataclass
class ApiRouterWiring:
    require_role: Callable[[str], Callable[..., str]]
    get_trade_repo: Callable[[], Any]
    assert_phase_13_read_only_endpoint: Callable[[str], None]
    get_health_now: Callable[[], Any]
    get_resolve_analysis_db_path: Callable[[], str]
    get_runtime_introspection_payload: Callable[[], dict[str, Any]]
    get_runtime_health_evaluator: Callable[..., Any]
    get_system_state_payload: Callable[[], dict[str, Any]]
    get_start_engine_runtime: Callable[[], str]
    get_shutdown_engine_runtime: Callable[[], str]
    get_pause_engine_runtime: Callable[[], str]
    get_resume_engine_runtime: Callable[[], str]
    get_lifecycle_transition_error: Callable[[], type[Exception]]
    get_analysis_run_repo: Callable[[], Any]
    get_signal_repo: Callable[[], Any]
    get_order_event_repo: Callable[[], Any]
    get_canonical_execution_repo: Callable[[], Any]
    get_journal_artifacts_root: Callable[[], Any]
    get_paper_runtime_evidence_series_dir: Callable[[], Any]
    get_default_strategy_configs: Callable[[], Dict[str, Dict[str, Any]]]
    get_watchlist_repo: Callable[[], Any]
    get_require_ingestion_run: Callable[..., None]
    get_require_snapshot_ready: Callable[..., None]
    get_run_snapshot_analysis: Callable[..., Any]
    get_create_strategy: Callable[[str], Any]
    get_create_registered_strategies: Callable[[], list[Any]]
    get_trigger_operator_analysis_run: Callable[..., Any]
    get_jwt_settings: Callable[[], JwtSettings]
    get_role_precedence: Callable[[], dict[str, int]]


def _build_routers(*, wiring: ApiRouterWiring) -> Tuple[APIRouter, ...]:
    """Build router instances once so they can be mounted multiple times.

    Each router is mounted both at the root (legacy compatibility) and
    under :data:`API_VERSION_PREFIX` (issue #1135). FastAPI's
    ``include_router`` happily accepts the same router twice with
    different prefixes; each call registers a distinct copy of the
    routes on the app.
    """

    return (
        build_auth_router(
            deps=AuthRouterDependencies(
                get_jwt_settings=wiring.get_jwt_settings,
                get_role_precedence=wiring.get_role_precedence,
            )
        ),
        build_alerts_router(wiring.require_role),
        build_journal_router(
            deps=JournalRouterDependencies(
                require_role=wiring.require_role,
                get_trade_repo=wiring.get_trade_repo,
            ),
        ),
        build_control_plane_router(
            deps=ControlPlaneRouterDependencies(
                require_role=wiring.require_role,
                assert_phase_13_read_only_endpoint=wiring.assert_phase_13_read_only_endpoint,
                get_health_now=lambda: wiring.get_health_now,
                get_resolve_analysis_db_path=lambda: wiring.get_resolve_analysis_db_path,
                get_runtime_introspection_payload=lambda: wiring.get_runtime_introspection_payload,
                get_runtime_health_evaluator=lambda: wiring.get_runtime_health_evaluator,
                get_system_state_payload=lambda: wiring.get_system_state_payload,
                get_start_engine_runtime=lambda: wiring.get_start_engine_runtime,
                get_shutdown_engine_runtime=lambda: wiring.get_shutdown_engine_runtime,
                get_pause_engine_runtime=lambda: wiring.get_pause_engine_runtime,
                get_resume_engine_runtime=lambda: wiring.get_resume_engine_runtime,
                get_lifecycle_transition_error=wiring.get_lifecycle_transition_error,
            ),
        ),
        build_inspection_router(
            deps=InspectionRouterDependencies(
                require_role=wiring.require_role,
                get_analysis_run_repo=wiring.get_analysis_run_repo,
                get_signal_repo=wiring.get_signal_repo,
                get_order_event_repo=wiring.get_order_event_repo,
                get_canonical_execution_repo=wiring.get_canonical_execution_repo,
                get_journal_artifacts_root=wiring.get_journal_artifacts_root,
                get_default_strategy_configs=wiring.get_default_strategy_configs,
            ),
        ),
        build_paper_runtime_evidence_series_router(
            deps=PaperRuntimeEvidenceSeriesRouterDependencies(
                require_role=wiring.require_role,
                get_evidence_series_dir=wiring.get_paper_runtime_evidence_series_dir,
            ),
        ),
        build_watchlists_router(
            deps=WatchlistsRouterDependencies(
                require_role=wiring.require_role,
                get_watchlist_repo=wiring.get_watchlist_repo,
                get_analysis_run_repo=wiring.get_analysis_run_repo,
                get_signal_repo=wiring.get_signal_repo,
                get_default_strategy_configs=wiring.get_default_strategy_configs,
                get_require_ingestion_run=lambda: wiring.get_require_ingestion_run,
                get_require_snapshot_ready=lambda: wiring.get_require_snapshot_ready,
                get_run_snapshot_analysis=lambda: wiring.get_run_snapshot_analysis,
                get_resolve_analysis_db_path=lambda: wiring.get_resolve_analysis_db_path,
                get_create_strategy=lambda: wiring.get_create_strategy,
                get_create_registered_strategies=lambda: wiring.get_create_registered_strategies,
                get_trigger_operator_analysis_run=lambda: wiring.get_trigger_operator_analysis_run,
            ),
        ),
        build_analysis_router(
            deps=AnalysisRouterDependencies(
                require_role=wiring.require_role,
                get_analysis_run_repo=wiring.get_analysis_run_repo,
                get_signal_repo=wiring.get_signal_repo,
                get_watchlist_repo=wiring.get_watchlist_repo,
                get_default_strategy_configs=wiring.get_default_strategy_configs,
                get_require_ingestion_run=lambda: wiring.get_require_ingestion_run,
                get_require_snapshot_ready=lambda: wiring.get_require_snapshot_ready,
                get_run_snapshot_analysis=lambda: wiring.get_run_snapshot_analysis,
                get_resolve_analysis_db_path=lambda: wiring.get_resolve_analysis_db_path,
                get_create_strategy=lambda: wiring.get_create_strategy,
                get_create_registered_strategies=lambda: wiring.get_create_registered_strategies,
                get_trigger_operator_analysis_run=lambda: wiring.get_trigger_operator_analysis_run,
            ),
        ),
    )


def include_api_routers(*, app: FastAPI, wiring: ApiRouterWiring) -> None:
    routers = _build_routers(wiring=wiring)
    # Legacy mount — preserved for backward compatibility (deprecated).
    for router in routers:
        app.include_router(router)
    # Versioned mount — canonical surface going forward (issue #1135).
    for router in routers:
        app.include_router(router, prefix=API_VERSION_PREFIX)

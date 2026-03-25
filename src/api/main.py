"""
FastAPI application for the Cilly Trading Engine (MVP).

Included endpoints:
- GET /health
- POST /strategy/analyze
- POST /screener/basic

Strategies:
- RSI2 (Rebound)
- TURTLE (Breakout)
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles

from cilly_trading.db import DEFAULT_DB_PATH
from cilly_trading.engine.analysis import trigger_operator_analysis_run
from cilly_trading.engine.core import run_watchlist_analysis
from cilly_trading.engine.data import SnapshotDataError
from cilly_trading.engine.health.evaluator import evaluate_runtime_health
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
from cilly_trading.repositories.analysis_runs_sqlite import SqliteAnalysisRunRepository
from cilly_trading.repositories.execution_core_sqlite import SqliteCanonicalExecutionRepository
from cilly_trading.repositories.signals_sqlite import SqliteSignalRepository
from cilly_trading.repositories.watchlists_sqlite import SqliteWatchlistRepository
from cilly_trading.strategies.registry import (
    create_registered_strategies,
    create_strategy,
    initialize_default_registry,
)

from .alerts_api import build_alerts_router
from .models import (
    ComplianceGuardStatusResponse,
    DecisionCardInspectionResponse,
    PaperAccountReadResponse,
    PaperPositionsReadResponse,
    PaperReconciliationReadResponse,
    PaperTradesReadResponse,
    PortfolioPositionsResponse,
    RuntimeIntrospectionResponse,
    ScreenerRequest,
    ScreenerResponse,
    SystemStateResponse,
    TradingCoreExecutionEventsReadResponse,
    TradingCoreOrdersReadResponse,
    TradingCorePositionsReadResponse,
    TradingCoreTradesReadResponse,
)
from .order_events_sqlite import SqliteOrderEventRepository
from .routers import (
    AnalysisRouterDependencies,
    ControlPlaneRouterDependencies,
    InspectionRouterDependencies,
    WatchlistsRouterDependencies,
    build_analysis_router,
    build_control_plane_router,
    build_inspection_router,
    build_watchlists_router,
)
from .services.composition_runtime_service import CompositionRuntimeService, configure_logging


configure_logging()
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Cilly Trading Engine API",
    version="0.1.0",
    description="MVP-API fuer die Cilly Trading Engine (RSI2 & Turtle, D1, SQLite).",
)

app.state.alert_configuration_store = {}
app.state.alert_history_store = []

UI_DIRECTORY = Path(__file__).resolve().parent.parent / "ui"
JOURNAL_ARTIFACTS_ROOT = Path(__file__).resolve().parents[2] / "runs" / "phase6"
app.mount("/ui", StaticFiles(directory=UI_DIRECTORY, html=True), name="ui")

logger.info("Cilly Trading Engine API starting up")

ENGINE_RUNTIME_NOT_RUNNING_STATUS = 503
ENGINE_RUNTIME_NOT_RUNNING_CODE = "engine_runtime_not_running"
ENGINE_RUNTIME_GUARD_ACTIVE = False
PHASE_13_READ_ONLY_ENDPOINTS = frozenset({"/health", "/runtime/introspection"})
ROLE_HEADER_NAME = "X-Cilly-Role"
ROLE_PRECEDENCE: dict[str, int] = {
    "read_only": 1,
    "operator": 2,
    "owner": 3,
}

initialize_default_registry()
default_strategy_configs: Dict[str, Dict[str, Any]] = {
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

ANALYSIS_DB_PATH: Optional[str] = None

signal_repo = SqliteSignalRepository()
order_event_repo = SqliteOrderEventRepository(db_path=DEFAULT_DB_PATH)
canonical_execution_repo = SqliteCanonicalExecutionRepository(db_path=DEFAULT_DB_PATH)
analysis_run_repo = SqliteAnalysisRunRepository(db_path=DEFAULT_DB_PATH)
watchlist_repo = SqliteWatchlistRepository(db_path=DEFAULT_DB_PATH)

_runtime_service = CompositionRuntimeService(
    logger=logger,
    default_db_path=str(DEFAULT_DB_PATH),
    role_header_name=ROLE_HEADER_NAME,
    role_precedence=ROLE_PRECEDENCE,
    phase_13_read_only_endpoints=PHASE_13_READ_ONLY_ENDPOINTS,
    engine_runtime_not_running_status=ENGINE_RUNTIME_NOT_RUNNING_STATUS,
    engine_runtime_not_running_code=ENGINE_RUNTIME_NOT_RUNNING_CODE,
    get_analysis_db_path_override=lambda: ANALYSIS_DB_PATH,
    get_analysis_run_repo=lambda: analysis_run_repo,
    get_signal_repo=lambda: signal_repo,
    get_watchlist_repo=lambda: watchlist_repo,
    get_default_strategy_configs=lambda: default_strategy_configs,
    get_create_strategy=lambda: create_strategy,
    get_create_registered_strategies=lambda: create_registered_strategies,
    get_trigger_operator_analysis_run=lambda: trigger_operator_analysis_run,
    get_runtime_controller=lambda: get_runtime_controller(),
    get_engine_runtime_guard_active=lambda: ENGINE_RUNTIME_GUARD_ACTIVE,
    get_run_watchlist_analysis=lambda: run_watchlist_analysis,
    get_require_ingestion_run_compat=lambda: _require_ingestion_run,
    get_require_snapshot_ready_compat=lambda: _require_snapshot_ready,
    get_run_snapshot_analysis_compat=lambda: _run_snapshot_analysis,
    get_require_engine_runtime_running_compat=lambda: _require_engine_runtime_running,
    snapshot_data_error_class=SnapshotDataError,
    get_runtime_introspection_payload=lambda: get_runtime_introspection_payload,
    get_system_state_payload=lambda: get_system_state_payload,
)

# Compatibility exports for existing test patch points.
_assert_phase_13_read_only_endpoint = _runtime_service.assert_phase_13_read_only_endpoint
_require_role = _runtime_service.require_role
_health_now = _runtime_service.health_now
_resolve_analysis_db_path = _runtime_service.resolve_analysis_db_path
_require_ingestion_run = _runtime_service.require_ingestion_run
_require_snapshot_ready = _runtime_service.require_snapshot_ready
_require_engine_runtime_running = _runtime_service.require_engine_runtime_running
_run_snapshot_analysis = _runtime_service.run_snapshot_analysis
_analysis_service_dependencies = _runtime_service.analysis_service_dependencies
basic_screener = _runtime_service.basic_screener
read_compliance_guard_status = _runtime_service.read_compliance_guard_status
runtime_introspection = _runtime_service.runtime_introspection
system_state = _runtime_service.system_state


@app.on_event("startup")
def _startup_runtime() -> None:
    global ENGINE_RUNTIME_GUARD_ACTIVE
    start_engine_runtime()
    ENGINE_RUNTIME_GUARD_ACTIVE = True


@app.on_event("shutdown")
def _shutdown_runtime() -> None:
    global ENGINE_RUNTIME_GUARD_ACTIVE
    ENGINE_RUNTIME_GUARD_ACTIVE = False
    try:
        shutdown_engine_runtime()
    except LifecycleTransitionError:
        logger.exception("Engine runtime shutdown failed")


app.include_router(build_alerts_router(_require_role))
app.include_router(
    build_control_plane_router(
        deps=ControlPlaneRouterDependencies(
            require_role=_require_role,
            assert_phase_13_read_only_endpoint=_assert_phase_13_read_only_endpoint,
            get_health_now=lambda: _health_now,
            get_resolve_analysis_db_path=lambda: _resolve_analysis_db_path,
            get_runtime_introspection_payload=lambda: get_runtime_introspection_payload,
            get_runtime_health_evaluator=lambda: evaluate_runtime_health,
            get_system_state_payload=lambda: get_system_state_payload,
            get_start_engine_runtime=lambda: start_engine_runtime,
            get_shutdown_engine_runtime=lambda: shutdown_engine_runtime,
            get_pause_engine_runtime=lambda: pause_engine_runtime,
            get_resume_engine_runtime=lambda: resume_engine_runtime,
            get_lifecycle_transition_error=lambda: LifecycleTransitionError,
        ),
    )
)
app.include_router(
    build_inspection_router(
        deps=InspectionRouterDependencies(
            require_role=_require_role,
            get_analysis_run_repo=lambda: analysis_run_repo,
            get_signal_repo=lambda: signal_repo,
            get_order_event_repo=lambda: order_event_repo,
            get_canonical_execution_repo=lambda: canonical_execution_repo,
            get_journal_artifacts_root=lambda: JOURNAL_ARTIFACTS_ROOT,
            get_default_strategy_configs=lambda: default_strategy_configs,
        ),
    )
)
app.include_router(
    build_watchlists_router(
        deps=WatchlistsRouterDependencies(
            require_role=_require_role,
            get_watchlist_repo=lambda: watchlist_repo,
            get_analysis_run_repo=lambda: analysis_run_repo,
            get_signal_repo=lambda: signal_repo,
            get_default_strategy_configs=lambda: default_strategy_configs,
            get_require_ingestion_run=lambda: _require_ingestion_run,
            get_require_snapshot_ready=lambda: _require_snapshot_ready,
            get_run_snapshot_analysis=lambda: _run_snapshot_analysis,
            get_resolve_analysis_db_path=lambda: _resolve_analysis_db_path,
            get_create_strategy=lambda: create_strategy,
            get_create_registered_strategies=lambda: create_registered_strategies,
            get_trigger_operator_analysis_run=lambda: trigger_operator_analysis_run,
        ),
    )
)
app.include_router(
    build_analysis_router(
        deps=AnalysisRouterDependencies(
            require_role=_require_role,
            get_analysis_run_repo=lambda: analysis_run_repo,
            get_signal_repo=lambda: signal_repo,
            get_watchlist_repo=lambda: watchlist_repo,
            get_default_strategy_configs=lambda: default_strategy_configs,
            get_require_ingestion_run=lambda: _require_ingestion_run,
            get_require_snapshot_ready=lambda: _require_snapshot_ready,
            get_run_snapshot_analysis=lambda: _run_snapshot_analysis,
            get_resolve_analysis_db_path=lambda: _resolve_analysis_db_path,
            get_create_strategy=lambda: create_strategy,
            get_create_registered_strategies=lambda: create_registered_strategies,
            get_trigger_operator_analysis_run=lambda: trigger_operator_analysis_run,
        ),
    )
)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)

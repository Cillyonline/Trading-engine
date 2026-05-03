from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .composition import (
    bind_main_runtime_exports,
    bind_main_runtime_service_exports,
    build_api_router_wiring,
    build_api_runtime_settings,
    build_runtime_lifecycle_dependencies,
    create_scheduled_analysis_runner,
    create_api_repositories,
    create_runtime_service,
    include_api_routers,
    register_runtime_lifecycle,
)
from .models import (
    BacktestArtifactContentResponse,
    BacktestArtifactListResponse,
    ComplianceGuardStatusResponse,
    DecisionCardInspectionResponse,
    PaperAccountReadResponse,
    PaperOperatorWorkflowReadResponse,
    PaperPositionsReadResponse,
    PaperReconciliationReadResponse,
    PaperTradesReadResponse,
    PortfolioPositionsResponse,
    RuntimeIntrospectionResponse,
    SignalDecisionSurfaceResponse,
    ScreenerRequest,
    ScreenerResponse,
    SystemStateResponse,
    TradingCoreExecutionEventsReadResponse,
    TradingCoreOrdersReadResponse,
    TradingCorePositionsReadResponse,
    TradingCoreTradesReadResponse,
)
from .services.composition_runtime_service import configure_logging
from .state import initialize_alert_state


configure_logging()
logger = logging.getLogger(__name__)

settings = build_api_runtime_settings()
UI_DIRECTORY: Path = settings.ui_directory
repositories = create_api_repositories()
_main_compat = bind_main_runtime_exports(
    module_globals=globals(),
    settings=settings,
    repositories=repositories,
)
_runtime_service = create_runtime_service(logger=logger, compat=_main_compat)
_scheduled_analysis_runner = create_scheduled_analysis_runner(
    logger=logger,
    runtime_service=_runtime_service,
    get_runtime_controller=_main_compat.get("get_runtime_controller"),
    settings=settings,
)
bind_main_runtime_service_exports(
    module_globals=globals(),
    runtime_service=_runtime_service,
    scheduled_analysis_runner=_scheduled_analysis_runner,
)

app = FastAPI(
    title="Cilly Trading Engine API",
    version="0.1.0",
    description="MVP-API fuer die Cilly Trading Engine (RSI2 & Turtle, D1, SQLite).",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

initialize_alert_state(app)
app.mount("/ui", StaticFiles(directory=str(UI_DIRECTORY), html=True), name="ui")

logger.info("Cilly Trading Engine API starting up")

_startup_runtime, _shutdown_runtime = register_runtime_lifecycle(
    app=app,
    deps=build_runtime_lifecycle_dependencies(logger=logger, compat=_main_compat),
)

include_api_routers(
    app=app,
    wiring=build_api_router_wiring(compat=_main_compat),
)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("api.main:app", host=settings.api_host, port=settings.api_port)

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict

from fastapi import APIRouter, Depends, Request

from ..models import ManualAnalysisRequest, ManualAnalysisResponse, ScreenerRequest, ScreenerResponse, StrategyAnalyzeRequest, StrategyAnalyzeResponse
from ..rate_limit import limiter
from ..services.analysis_service import AnalysisServiceDependencies, analyze_strategy, basic_screener, manual_analysis


@dataclass
class AnalysisRouterDependencies:
    require_role: Callable[[str], Callable[..., str]]
    get_analysis_run_repo: Callable[[], Any]
    get_signal_repo: Callable[[], Any]
    get_watchlist_repo: Callable[[], Any]
    get_default_strategy_configs: Callable[[], Dict[str, Dict[str, Any]]]
    get_require_ingestion_run: Callable[[], Callable[..., None]]
    get_require_snapshot_ready: Callable[[], Callable[..., None]]
    get_run_snapshot_analysis: Callable[[], Callable[..., Any]]
    get_resolve_analysis_db_path: Callable[[], Callable[[], str]]
    get_create_strategy: Callable[[], Callable[[str], Any]]
    get_create_registered_strategies: Callable[[], Callable[[], list[Any]]]
    get_trigger_operator_analysis_run: Callable[[], Callable[..., Any]]


def _service_dependencies(deps: AnalysisRouterDependencies) -> AnalysisServiceDependencies:
    return AnalysisServiceDependencies(
        analysis_run_repo=deps.get_analysis_run_repo(),
        signal_repo=deps.get_signal_repo(),
        watchlist_repo=deps.get_watchlist_repo(),
        default_strategy_configs=deps.get_default_strategy_configs(),
        require_ingestion_run=deps.get_require_ingestion_run(),
        require_snapshot_ready=deps.get_require_snapshot_ready(),
        run_snapshot_analysis=deps.get_run_snapshot_analysis(),
        resolve_analysis_db_path=deps.get_resolve_analysis_db_path(),
        create_strategy=deps.get_create_strategy(),
        create_registered_strategies=deps.get_create_registered_strategies(),
        trigger_operator_analysis_run=deps.get_trigger_operator_analysis_run(),
    )


def build_analysis_router(
    *,
    deps: AnalysisRouterDependencies,
) -> APIRouter:
    router = APIRouter()

    @router.post(
        "/strategy/analyze",
        response_model=StrategyAnalyzeResponse,
    )
    @limiter.limit("5/minute")
    def analyze_strategy_handler(
        request: Request,
        req: StrategyAnalyzeRequest,
        _: str = Depends(deps.require_role("operator")),
    ) -> StrategyAnalyzeResponse:
        return analyze_strategy(req=req, deps=_service_dependencies(deps))

    @router.post(
        "/analysis/run",
        response_model=ManualAnalysisResponse,
    )
    @limiter.limit("5/minute")
    def manual_analysis_handler(
        request: Request,
        req: ManualAnalysisRequest,
        _: str = Depends(deps.require_role("operator")),
    ) -> ManualAnalysisResponse:
        return manual_analysis(req=req, deps=_service_dependencies(deps))

    @router.post(
        "/screener/basic",
        response_model=ScreenerResponse,
    )
    @limiter.limit("10/minute")
    def basic_screener_handler(
        request: Request,
        req: ScreenerRequest,
        _: str = Depends(deps.require_role("operator")),
    ) -> ScreenerResponse:
        return basic_screener(req=req, deps=_service_dependencies(deps))

    return router

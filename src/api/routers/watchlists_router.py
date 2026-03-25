from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict

from fastapi import APIRouter, Depends, HTTPException

from ..models import (
    WatchlistCreateRequest,
    WatchlistDeleteResponse,
    WatchlistExecutionRequest,
    WatchlistExecutionResponse,
    WatchlistListResponse,
    WatchlistPayload,
    WatchlistResponse,
)
from ..services.analysis_service import AnalysisServiceDependencies, execute_watchlist, to_watchlist_response


@dataclass
class WatchlistsRouterDependencies:
    require_role: Callable[[str], Callable[..., str]]
    get_watchlist_repo: Callable[[], Any]
    get_analysis_run_repo: Callable[[], Any]
    get_signal_repo: Callable[[], Any]
    get_default_strategy_configs: Callable[[], Dict[str, Dict[str, Any]]]
    get_require_ingestion_run: Callable[[], Callable[..., None]]
    get_require_snapshot_ready: Callable[[], Callable[..., None]]
    get_run_snapshot_analysis: Callable[[], Callable[..., Any]]
    get_resolve_analysis_db_path: Callable[[], Callable[[], str]]
    get_create_strategy: Callable[[], Callable[[str], Any]]
    get_create_registered_strategies: Callable[[], Callable[[], list[Any]]]
    get_trigger_operator_analysis_run: Callable[[], Callable[..., Any]]


def _service_dependencies(deps: WatchlistsRouterDependencies) -> AnalysisServiceDependencies:
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


def build_watchlists_router(
    *,
    deps: WatchlistsRouterDependencies,
) -> APIRouter:
    router = APIRouter()

    @router.post(
        "/watchlists",
        response_model=WatchlistResponse,
    )
    def create_watchlist_handler(
        req: WatchlistCreateRequest,
        _: str = Depends(deps.require_role("operator")),
    ) -> WatchlistResponse:
        watchlist_repo = deps.get_watchlist_repo()
        try:
            watchlist = watchlist_repo.create_watchlist(
                watchlist_id=req.watchlist_id,
                name=req.name,
                symbols=req.symbols,
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return to_watchlist_response(watchlist)

    @router.get(
        "/watchlists",
        response_model=WatchlistListResponse,
    )
    def read_watchlists_handler(
        _: str = Depends(deps.require_role("read_only")),
    ) -> WatchlistListResponse:
        watchlist_repo = deps.get_watchlist_repo()
        items = [to_watchlist_response(watchlist) for watchlist in watchlist_repo.list_watchlists()]
        return WatchlistListResponse(items=items, total=len(items))

    @router.get(
        "/watchlists/{watchlist_id}",
        response_model=WatchlistResponse,
    )
    def read_watchlist_handler(
        watchlist_id: str,
        _: str = Depends(deps.require_role("read_only")),
    ) -> WatchlistResponse:
        watchlist_repo = deps.get_watchlist_repo()
        watchlist = watchlist_repo.get_watchlist(watchlist_id)
        if watchlist is None:
            raise HTTPException(status_code=404, detail="watchlist_not_found")
        return to_watchlist_response(watchlist)

    @router.put(
        "/watchlists/{watchlist_id}",
        response_model=WatchlistResponse,
    )
    def update_watchlist_handler(
        watchlist_id: str,
        req: WatchlistPayload,
        _: str = Depends(deps.require_role("operator")),
    ) -> WatchlistResponse:
        watchlist_repo = deps.get_watchlist_repo()
        try:
            watchlist = watchlist_repo.update_watchlist(
                watchlist_id=watchlist_id,
                name=req.name,
                symbols=req.symbols,
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="watchlist_not_found") from exc
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return to_watchlist_response(watchlist)

    @router.delete(
        "/watchlists/{watchlist_id}",
        response_model=WatchlistDeleteResponse,
    )
    def delete_watchlist_handler(
        watchlist_id: str,
        _: str = Depends(deps.require_role("operator")),
    ) -> WatchlistDeleteResponse:
        watchlist_repo = deps.get_watchlist_repo()
        deleted = watchlist_repo.delete_watchlist(watchlist_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="watchlist_not_found")
        return WatchlistDeleteResponse(watchlist_id=watchlist_id, deleted=True)

    @router.post(
        "/watchlists/{watchlist_id}/execute",
        response_model=WatchlistExecutionResponse,
    )
    def execute_watchlist_handler(
        watchlist_id: str,
        req: WatchlistExecutionRequest,
        _: str = Depends(deps.require_role("operator")),
    ) -> WatchlistExecutionResponse:
        return execute_watchlist(
            watchlist_id=watchlist_id,
            req=req,
            deps=_service_dependencies(deps),
        )

    return router

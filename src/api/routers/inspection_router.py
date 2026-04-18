from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from cilly_trading.models import SignalReadResponseDTO

from ..config import SCREENER_RESULTS_READ_MAX_LIMIT, SIGNALS_READ_MAX_LIMIT
from ..models import (
    BacktestArtifactContentResponse,
    BacktestArtifactListResponse,
    DecisionCardInspectionQuery,
    DecisionCardInspectionResponse,
    DecisionTraceResponse,
    ExecutionOrdersReadQuery,
    ExecutionOrdersReadResponse,
    IngestionRunItemResponse,
    JournalArtifactContentResponse,
    JournalArtifactListResponse,
    PaperAccountReadResponse,
    PaperOperatorWorkflowReadResponse,
    PaperPositionsReadQuery,
    PaperPositionsReadResponse,
    PaperReconciliationReadResponse,
    PaperTradesReadQuery,
    PaperTradesReadResponse,
    PortfolioPositionsResponse,
    SignalDecisionSurfaceResponse,
    ScreenerResultsQuery,
    ScreenerResultsResponse,
    SignalsReadQuery,
    StrategyMetadataResponse,
    TradingCoreExecutionEventsReadQuery,
    TradingCoreExecutionEventsReadResponse,
    TradingCoreOrdersReadQuery,
    TradingCoreOrdersReadResponse,
    TradingCorePositionsReadQuery,
    TradingCorePositionsReadResponse,
    TradingCoreTradesReadQuery,
    TradingCoreTradesReadResponse,
)
from ..services import inspection_service


@dataclass
class InspectionRouterDependencies:
    require_role: Callable[[str], Callable[..., str]]
    get_analysis_run_repo: Callable[[], Any]
    get_signal_repo: Callable[[], Any]
    get_order_event_repo: Callable[[], Any]
    get_canonical_execution_repo: Callable[[], Any]
    get_journal_artifacts_root: Callable[[], Path]
    get_default_strategy_configs: Callable[[], Dict[str, Dict[str, Any]]]


def _service_dependencies(deps: InspectionRouterDependencies) -> inspection_service.InspectionServiceDependencies:
    return inspection_service.InspectionServiceDependencies(
        analysis_run_repo=deps.get_analysis_run_repo(),
        signal_repo=deps.get_signal_repo(),
        order_event_repo=deps.get_order_event_repo(),
        canonical_execution_repo=deps.get_canonical_execution_repo(),
        journal_artifacts_root=deps.get_journal_artifacts_root(),
        default_strategy_configs=deps.get_default_strategy_configs(),
    )


def _get_signals_query(
    request: Request,
    symbol: Optional[str] = Query(default=None),
    strategy: Optional[str] = Query(default=None),
    timeframe: Optional[str] = Query(default=None),
    ingestion_run_id: Optional[str] = Query(default=None),
    from_: Optional[datetime] = Query(default=None, alias="from"),
    to: Optional[datetime] = Query(default=None, alias="to"),
    sort: Literal["created_at_asc", "created_at_desc"] = Query(default="created_at_desc"),
    limit: int = Query(default=50, ge=1, le=SIGNALS_READ_MAX_LIMIT),
    offset: int = Query(default=0, ge=0),
) -> SignalsReadQuery:
    if "preset" in request.query_params:
        raise HTTPException(status_code=422, detail="preset query parameter is not supported; use timeframe")
    if "start" in request.query_params:
        raise HTTPException(status_code=422, detail="start query parameter is not supported; use from")
    if "end" in request.query_params:
        raise HTTPException(status_code=422, detail="end query parameter is not supported; use to")

    resolved_from = from_
    resolved_to = to

    if resolved_from is not None and resolved_to is not None and resolved_from > resolved_to:
        raise HTTPException(status_code=422, detail="from must be less than or equal to to")

    return SignalsReadQuery(
        symbol=symbol,
        strategy=strategy,
        timeframe=timeframe,
        ingestion_run_id=ingestion_run_id,
        from_=resolved_from,
        to=resolved_to,
        sort=sort,
        limit=limit,
        offset=offset,
    )


def _get_ingestion_runs_limit(
    limit: int = Query(default=20, ge=1),
) -> int:
    return min(limit, 100)


def _get_execution_orders_query(
    symbol: Optional[str] = Query(default=None),
    strategy: Optional[str] = Query(default=None),
    run_id: Optional[str] = Query(default=None),
    order_id: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> ExecutionOrdersReadQuery:
    return ExecutionOrdersReadQuery(
        symbol=symbol,
        strategy=strategy,
        run_id=run_id,
        order_id=order_id,
        limit=limit,
        offset=offset,
    )


def _get_trading_core_orders_query(
    strategy_id: Optional[str] = Query(default=None),
    symbol: Optional[str] = Query(default=None),
    order_id: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> TradingCoreOrdersReadQuery:
    return TradingCoreOrdersReadQuery(
        strategy_id=strategy_id,
        symbol=symbol,
        order_id=order_id,
        limit=limit,
        offset=offset,
    )


def _get_trading_core_execution_events_query(
    strategy_id: Optional[str] = Query(default=None),
    symbol: Optional[str] = Query(default=None),
    order_id: Optional[str] = Query(default=None),
    trade_id: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> TradingCoreExecutionEventsReadQuery:
    return TradingCoreExecutionEventsReadQuery(
        strategy_id=strategy_id,
        symbol=symbol,
        order_id=order_id,
        trade_id=trade_id,
        limit=limit,
        offset=offset,
    )


def _get_trading_core_trades_query(
    strategy_id: Optional[str] = Query(default=None),
    symbol: Optional[str] = Query(default=None),
    position_id: Optional[str] = Query(default=None),
    trade_id: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> TradingCoreTradesReadQuery:
    return TradingCoreTradesReadQuery(
        strategy_id=strategy_id,
        symbol=symbol,
        position_id=position_id,
        trade_id=trade_id,
        limit=limit,
        offset=offset,
    )


def _get_trading_core_positions_query(
    strategy_id: Optional[str] = Query(default=None),
    symbol: Optional[str] = Query(default=None),
    position_id: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> TradingCorePositionsReadQuery:
    return TradingCorePositionsReadQuery(
        strategy_id=strategy_id,
        symbol=symbol,
        position_id=position_id,
        limit=limit,
        offset=offset,
    )


def _get_screener_results_query(
    strategy: str = Query(...),
    timeframe: str = Query(...),
    min_score: Optional[float] = Query(default=None, ge=0.0),
    limit: int = Query(default=50, ge=1, le=SCREENER_RESULTS_READ_MAX_LIMIT),
    offset: int = Query(default=0, ge=0),
) -> ScreenerResultsQuery:
    return ScreenerResultsQuery(
        strategy=strategy,
        timeframe=timeframe,
        min_score=min_score,
        limit=limit,
        offset=offset,
    )


def _get_decision_card_inspection_query(
    run_id: Optional[str] = Query(default=None),
    symbol: Optional[str] = Query(default=None),
    strategy_id: Optional[str] = Query(default=None),
    decision_card_id: Optional[str] = Query(default=None),
    qualification_state: Optional[
        Literal["reject", "watch", "paper_candidate", "paper_approved"]
    ] = Query(default=None),
    review_state: Optional[Literal["ranked", "blocked", "approved"]] = Query(default=None),
    sort: Literal["generated_at_desc", "generated_at_asc"] = Query(default="generated_at_desc"),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> DecisionCardInspectionQuery:
    return DecisionCardInspectionQuery(
        run_id=run_id,
        symbol=symbol,
        strategy_id=strategy_id,
        decision_card_id=decision_card_id,
        qualification_state=qualification_state,
        review_state=review_state,
        sort=sort,
        limit=limit,
        offset=offset,
    )


def build_inspection_router(
    *,
    deps: InspectionRouterDependencies,
) -> APIRouter:
    router = APIRouter()

    @router.get(
        "/portfolio/positions",
        response_model=PortfolioPositionsResponse,
        summary="Portfolio Positions",
        description="Read-only current portfolio positions for operator inspection.",
    )
    def read_portfolio_positions_handler(
        _: str = Depends(deps.require_role("read_only")),
    ) -> PortfolioPositionsResponse:
        return inspection_service.read_portfolio_positions(deps=_service_dependencies(deps))

    @router.get(
        "/paper/account",
        response_model=PaperAccountReadResponse,
        summary="Paper Account",
        description="Read-only paper account state for deterministic operator inspection.",
    )
    def read_paper_account_handler(
        _: str = Depends(deps.require_role("read_only")),
    ) -> PaperAccountReadResponse:
        return inspection_service.read_paper_account(deps=_service_dependencies(deps))

    @router.get(
        "/paper/workflow",
        response_model=PaperOperatorWorkflowReadResponse,
        summary="Paper Operator Workflow",
        description=(
            "Read-only bounded Phase 44 paper-trading operator workflow contract composed from "
            "canonical inspection and reconciliation surfaces."
        ),
    )
    def read_paper_operator_workflow_handler(
        _: str = Depends(deps.require_role("read_only")),
    ) -> PaperOperatorWorkflowReadResponse:
        return inspection_service.read_paper_operator_workflow(deps=_service_dependencies(deps))

    @router.get(
        "/paper/trades",
        response_model=PaperTradesReadResponse,
    )
    def read_paper_trades_handler(
        strategy_id: Optional[str] = Query(default=None),
        symbol: Optional[str] = Query(default=None),
        position_id: Optional[str] = Query(default=None),
        trade_id: Optional[str] = Query(default=None),
        limit: int = Query(default=50, ge=1, le=500),
        offset: int = Query(default=0, ge=0),
        _: str = Depends(deps.require_role("read_only")),
    ) -> PaperTradesReadResponse:
        params = PaperTradesReadQuery(
            strategy_id=strategy_id,
            symbol=symbol,
            position_id=position_id,
            trade_id=trade_id,
            limit=limit,
            offset=offset,
        )
        return inspection_service.read_paper_trades(params=params, deps=_service_dependencies(deps))

    @router.get(
        "/paper/positions",
        response_model=PaperPositionsReadResponse,
    )
    def read_paper_positions_handler(
        strategy_id: Optional[str] = Query(default=None),
        symbol: Optional[str] = Query(default=None),
        position_id: Optional[str] = Query(default=None),
        limit: int = Query(default=50, ge=1, le=500),
        offset: int = Query(default=0, ge=0),
        _: str = Depends(deps.require_role("read_only")),
    ) -> PaperPositionsReadResponse:
        params = PaperPositionsReadQuery(
            strategy_id=strategy_id,
            symbol=symbol,
            position_id=position_id,
            limit=limit,
            offset=offset,
        )
        return inspection_service.read_paper_positions(params=params, deps=_service_dependencies(deps))

    @router.get(
        "/paper/reconciliation",
        response_model=PaperReconciliationReadResponse,
    )
    def read_paper_reconciliation_handler(
        _: str = Depends(deps.require_role("read_only")),
    ) -> PaperReconciliationReadResponse:
        return inspection_service.read_paper_reconciliation(deps=_service_dependencies(deps))

    @router.get(
        "/ingestion/runs",
        response_model=list[IngestionRunItemResponse],
    )
    def read_ingestion_runs_handler(
        limit: int = Depends(_get_ingestion_runs_limit),
        _: str = Depends(deps.require_role("read_only")),
    ) -> list[IngestionRunItemResponse]:
        return inspection_service.read_ingestion_runs(limit=limit, deps=_service_dependencies(deps))

    @router.get(
        "/journal/artifacts",
        response_model=JournalArtifactListResponse,
    )
    def read_journal_artifacts_handler(
        limit: int = Query(default=50, ge=1, le=500),
        offset: int = Query(default=0, ge=0),
        _: str = Depends(deps.require_role("read_only")),
    ) -> JournalArtifactListResponse:
        return inspection_service.read_journal_artifacts(
            limit=limit,
            offset=offset,
            journal_artifacts_root=deps.get_journal_artifacts_root(),
        )

    @router.get(
        "/journal/artifacts/{run_id}/{artifact_name}",
        response_model=JournalArtifactContentResponse,
    )
    def read_journal_artifact_content_handler(
        run_id: str,
        artifact_name: str,
        _: str = Depends(deps.require_role("read_only")),
    ) -> JournalArtifactContentResponse:
        return inspection_service.read_journal_artifact_file_content(
            run_id=run_id,
            artifact_name=artifact_name,
            journal_artifacts_root=deps.get_journal_artifacts_root(),
        )

    @router.get(
        "/backtest/artifacts",
        response_model=BacktestArtifactListResponse,
        summary="Backtest Artifact Entry/Read",
        description=(
            "Read-only bounded backtest artifact listing for browser-native /ui inspection. "
            "This route is explicitly non-live and separates technical artifact visibility from "
            "trader validation and operational readiness."
        ),
    )
    def read_backtest_artifacts_handler(
        run_id: Optional[str] = Query(default=None),
        limit: int = Query(default=50, ge=1, le=500),
        offset: int = Query(default=0, ge=0),
        _: str = Depends(deps.require_role("read_only")),
    ) -> BacktestArtifactListResponse:
        return inspection_service.read_backtest_artifacts(
            limit=limit,
            offset=offset,
            run_id=run_id,
            journal_artifacts_root=deps.get_journal_artifacts_root(),
        )

    @router.get(
        "/backtest/artifacts/{run_id}/{artifact_name}",
        response_model=BacktestArtifactContentResponse,
        summary="Backtest Artifact Content Read",
        description=(
            "Read-only bounded backtest artifact content for browser-native /ui inspection. "
            "This route is explicitly non-live and does not imply trader validation or "
            "operational readiness."
        ),
    )
    def read_backtest_artifact_content_handler(
        run_id: str,
        artifact_name: str,
        _: str = Depends(deps.require_role("read_only")),
    ) -> BacktestArtifactContentResponse:
        return inspection_service.read_backtest_artifact_content(
            run_id=run_id,
            artifact_name=artifact_name,
            journal_artifacts_root=deps.get_journal_artifacts_root(),
        )

    @router.get(
        "/journal/decision-trace",
        response_model=DecisionTraceResponse,
    )
    def read_decision_trace_handler(
        run_id: str = Query(..., min_length=1),
        artifact_name: str = Query(default="audit.json", min_length=1),
        _: str = Depends(deps.require_role("read_only")),
    ) -> DecisionTraceResponse:
        return inspection_service.read_decision_trace(
            run_id=run_id,
            artifact_name=artifact_name,
            journal_artifacts_root=deps.get_journal_artifacts_root(),
        )

    @router.get(
        "/decision-cards",
        response_model=DecisionCardInspectionResponse,
        summary="Decision Card Inspection",
        description=(
            "Read-only decision inspection surface aligned to the canonical decision contract "
            "for deterministic qualification outcomes. Exposes bounded hard-gate, component-score, "
            "and rationale visibility for operator review with deterministic ordering/filtering and "
            "no write-capable mutation workflow."
        ),
    )
    def read_decision_cards_handler(
        params: DecisionCardInspectionQuery = Depends(_get_decision_card_inspection_query),
        _: str = Depends(deps.require_role("read_only")),
    ) -> DecisionCardInspectionResponse:
        return inspection_service.read_decision_cards(
            params=params,
            journal_artifacts_root=deps.get_journal_artifacts_root(),
        )

    @router.get(
        "/strategies",
        response_model=StrategyMetadataResponse,
    )
    def read_strategies_handler(
        _: str = Depends(deps.require_role("read_only")),
    ) -> StrategyMetadataResponse:
        return inspection_service.read_strategy_metadata(
            default_strategy_configs=deps.get_default_strategy_configs(),
        )

    @router.get(
        "/signals",
        response_model=SignalReadResponseDTO,
        summary="Read Signals",
        description=(
            "Read stored signals with optional filters on the deduped consumer-facing view. "
            "For undeduped raw cross-ingestion observability use /signals/raw."
        ),
    )
    def read_signals_handler(
        params: SignalsReadQuery = Depends(_get_signals_query),
        _: str = Depends(deps.require_role("read_only")),
    ) -> SignalReadResponseDTO:
        return inspection_service.read_signals(params=params, deps=_service_dependencies(deps))

    @router.get(
        "/signals/decision-surface",
        response_model=SignalDecisionSurfaceResponse,
        summary="Read Signal Decision Surface",
        description=(
            "Read bounded non-live technical decision states for reviewed signals with explicit "
            "professional qualification evidence (stage, score, confirmation-rule, entry-zone), concise rationale, "
            "missing criteria visibility, and blocking-condition visibility. This route is explicitly "
            "technical-only and does not imply trader validation or operational readiness."
        ),
    )
    def read_signal_decision_surface_handler(
        params: SignalsReadQuery = Depends(_get_signals_query),
        _: str = Depends(deps.require_role("read_only")),
    ) -> SignalDecisionSurfaceResponse:
        return inspection_service.read_signal_decision_surface(
            params=params,
            deps=_service_dependencies(deps),
        )

    @router.get(
        "/signals/raw",
        response_model=SignalReadResponseDTO,
        summary="Read Raw Signals",
        description=(
            "Read stored signals with optional filters on the undeduped raw persisted view across "
            "ingestion runs for debugging and observability."
        ),
    )
    def read_raw_signals_handler(
        params: SignalsReadQuery = Depends(_get_signals_query),
        _: str = Depends(deps.require_role("read_only")),
    ) -> SignalReadResponseDTO:
        return inspection_service.read_signals_raw(params=params, deps=_service_dependencies(deps))

    @router.get(
        "/execution/orders",
        response_model=ExecutionOrdersReadResponse,
    )
    def read_execution_orders_handler(
        params: ExecutionOrdersReadQuery = Depends(_get_execution_orders_query),
        _: str = Depends(deps.require_role("read_only")),
    ) -> ExecutionOrdersReadResponse:
        return inspection_service.read_execution_orders(params=params, deps=_service_dependencies(deps))

    @router.get(
        "/trading-core/orders",
        response_model=TradingCoreOrdersReadResponse,
    )
    def read_trading_core_orders_handler(
        params: TradingCoreOrdersReadQuery = Depends(_get_trading_core_orders_query),
        _: str = Depends(deps.require_role("read_only")),
    ) -> TradingCoreOrdersReadResponse:
        return inspection_service.read_trading_core_orders(params=params, deps=_service_dependencies(deps))

    @router.get(
        "/trading-core/execution-events",
        response_model=TradingCoreExecutionEventsReadResponse,
    )
    def read_trading_core_execution_events_handler(
        params: TradingCoreExecutionEventsReadQuery = Depends(_get_trading_core_execution_events_query),
        _: str = Depends(deps.require_role("read_only")),
    ) -> TradingCoreExecutionEventsReadResponse:
        return inspection_service.read_trading_core_execution_events(
            params=params,
            deps=_service_dependencies(deps),
        )

    @router.get(
        "/trading-core/trades",
        response_model=TradingCoreTradesReadResponse,
    )
    def read_trading_core_trades_handler(
        params: TradingCoreTradesReadQuery = Depends(_get_trading_core_trades_query),
        _: str = Depends(deps.require_role("read_only")),
    ) -> TradingCoreTradesReadResponse:
        return inspection_service.read_trading_core_trades(params=params, deps=_service_dependencies(deps))

    @router.get(
        "/trading-core/positions",
        response_model=TradingCorePositionsReadResponse,
    )
    def read_trading_core_positions_handler(
        params: TradingCorePositionsReadQuery = Depends(_get_trading_core_positions_query),
        _: str = Depends(deps.require_role("read_only")),
    ) -> TradingCorePositionsReadResponse:
        return inspection_service.read_trading_core_positions(
            params=params,
            deps=_service_dependencies(deps),
        )

    @router.get(
        "/screener/v2/results",
        response_model=ScreenerResultsResponse,
    )
    def read_screener_results_handler(
        params: ScreenerResultsQuery = Depends(_get_screener_results_query),
        _: str = Depends(deps.require_role("read_only")),
    ) -> ScreenerResultsResponse:
        return inspection_service.read_screener_results(params=params, deps=_service_dependencies(deps))

    return router

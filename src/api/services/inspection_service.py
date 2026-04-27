from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

from fastapi import HTTPException
from pydantic import ValidationError

from cilly_trading.engine.backtest_handoff_contract import build_professional_review_contract
from cilly_trading.engine.decision_card_contract import (
    ACTION_ENTRY_WIN_RATE_MIN,
    ACTION_EXIT_WIN_RATE_MAX,
    QUALIFICATION_HIGH_AGGREGATE_THRESHOLD,
    QUALIFICATION_MEDIUM_AGGREGATE_THRESHOLD,
    evaluate_bounded_end_to_end_traceability_chain,
    evaluate_bounded_trader_relevance_cases,
    validate_decision_card,
)
from cilly_trading.models import ExecutionEvent, Order, Position, SignalReadItemDTO, SignalReadResponseDTO, Trade
from cilly_trading.non_live_evaluation_contract import normalize_risk_rejection_reason_code

from ..models import (
    BacktestArtifactContentResponse,
    BacktestArtifactItemResponse,
    BacktestArtifactListResponse,
    BacktestReadBoundaryResponse,
    StrategyReadinessEvidenceResponse,
    StrategyReadinessEvidenceStateResponse,
    DecisionCardComponentScoreInspectionResponse,
    DecisionCardHardGateInspectionResponse,
    DecisionCardInspectionItemResponse,
    DecisionCardInspectionQuery,
    DecisionCardInspectionResponse,
    DecisionTraceResponse,
    ExecutionOrderEventItemResponse,
    ExecutionOrdersReadQuery,
    ExecutionOrdersReadResponse,
    IngestionRunItemResponse,
    JournalArtifactContentResponse,
    JournalArtifactItemResponse,
    JournalArtifactListResponse,
    PaperAccountReadResponse,
    PaperAccountStateResponse,
    PaperOperatorWorkflowBoundaryResponse,
    PaperOperatorWorkflowInspectionSummaryResponse,
    PaperOperatorWorkflowReferenceResponse,
    PaperOperatorWorkflowReadResponse,
    PaperOperatorWorkflowStepResponse,
    PaperOperatorWorkflowSurfaceResponse,
    PaperOperatorWorkflowValidationCheckResponse,
    PaperOperatorWorkflowValidationResponse,
    PaperPositionsReadQuery,
    PaperPositionsReadResponse,
    PaperReconciliationMismatchResponse,
    PaperReconciliationReadResponse,
    PaperReconciliationSummaryResponse,
    PaperTradesReadQuery,
    PaperTradesReadResponse,
    PortfolioPositionResponse,
    PortfolioPositionsResponse,
    SignalDecisionSurfaceBoundaryResponse,
    SignalDecisionSurfaceItemResponse,
    SignalDecisionSurfaceResponse,
    ScreenerResultItem,
    ScreenerResultsQuery,
    ScreenerResultsResponse,
    SignalsReadQuery,
    TradingCoreExecutionEventsReadQuery,
    TradingCoreExecutionEventsReadResponse,
    TradingCoreOrdersReadQuery,
    TradingCoreOrdersReadResponse,
    TradingCorePositionsReadQuery,
    TradingCorePositionsReadResponse,
    TradingCoreTradesReadQuery,
    TradingCoreTradesReadResponse,
)
from . import paper_inspection_service
from .analysis_service import build_strategy_metadata_response


BACKTEST_WORKFLOW_ID = "ui_bounded_backtest_entry_read"
SIGNAL_DECISION_SURFACE_WORKFLOW_ID = "ui_signal_decision_surface_v1"
SIGNAL_DECISION_BLOCKED_SCORE_THRESHOLD = 40.0
SIGNAL_DECISION_CANDIDATE_SCORE_THRESHOLD = 70.0
SIGNAL_DECISION_QUALIFICATION_POLICY_VERSION = "professional_non_live_signal_qualification.v1"
GOVERNED_BACKTEST_ARTIFACT_NAMES = frozenset(
    {
        "backtest-result.json",
        "backtest-result.sha256",
        "metrics-result.json",
        "trade-ledger.json",
        "trade-ledger.sha256",
        "equity-curve.json",
        "equity-curve.sha256",
        "performance-report.json",
        "performance-report.sha256",
    }
)


@dataclass
class InspectionServiceDependencies:
    analysis_run_repo: Any
    signal_repo: Any
    order_event_repo: Any
    canonical_execution_repo: Any
    journal_artifacts_root: Path
    default_strategy_configs: Dict[str, Dict[str, Any]]


def paginate_items(items: list[Any], *, limit: int, offset: int) -> tuple[list[Any], int]:
    page, total = paper_inspection_service.paginate_items(items=items, limit=limit, offset=offset)
    return list(page), total


def build_paper_account_state(
    *,
    paper_trades: list[Trade],
    paper_positions: list[Position],
) -> PaperAccountStateResponse:
    payload = paper_inspection_service.build_paper_account_state(
        paper_trades=paper_trades,
        paper_positions=paper_positions,
    )
    return PaperAccountStateResponse(**payload)


def build_paper_reconciliation_mismatches(
    *,
    orders: list[Order],
    execution_events: list[ExecutionEvent],
    trades: list[Trade],
    positions: list[Position],
    account: PaperAccountStateResponse,
) -> list[PaperReconciliationMismatchResponse]:
    payload = paper_inspection_service.build_paper_reconciliation_mismatches(
        orders=orders,
        execution_events=execution_events,
        trades=trades,
        positions=positions,
        account=account.model_dump(mode="python"),
    )
    return [PaperReconciliationMismatchResponse(**item) for item in payload]


def build_trading_core_positions(
    *,
    canonical_execution_repo: Any,
    strategy_id: Optional[str] = None,
    symbol: Optional[str] = None,
    position_id: Optional[str] = None,
) -> list[Position]:
    return paper_inspection_service.build_trading_core_positions(
        canonical_execution_repo=canonical_execution_repo,
        strategy_id=strategy_id,
        symbol=symbol,
        position_id=position_id,
    )


def portfolio_position_response(
    position: paper_inspection_service.PortfolioInspectionPositionState,
) -> PortfolioPositionResponse:
    return PortfolioPositionResponse(
        symbol=position.symbol,
        size=float(position.size),
        average_price=float(position.average_price),
        unrealized_pnl=float(position.unrealized_pnl),
        strategy_id=position.strategy_id,
    )


def load_bounded_paper_simulation_state(
    *,
    deps: InspectionServiceDependencies,
) -> paper_inspection_service.BoundedPaperSimulationState:
    return paper_inspection_service.build_bounded_paper_simulation_state(
        canonical_execution_repo=deps.canonical_execution_repo,
    )


def read_portfolio_positions(
    *,
    deps: InspectionServiceDependencies,
) -> PortfolioPositionsResponse:
    state = load_bounded_paper_simulation_state(deps=deps)
    items = [portfolio_position_response(position) for position in state.portfolio_positions]
    return PortfolioPositionsResponse(positions=items, total=len(items))


def read_paper_account(
    *,
    deps: InspectionServiceDependencies,
) -> PaperAccountReadResponse:
    state = load_bounded_paper_simulation_state(deps=deps)
    return PaperAccountReadResponse(
        account=PaperAccountStateResponse(**state.account),
    )


def read_paper_trades(
    *,
    params: PaperTradesReadQuery,
    deps: InspectionServiceDependencies,
) -> PaperTradesReadResponse:
    if params.trade_id:
        trade = deps.canonical_execution_repo.get_trade(params.trade_id)
        all_items = [] if trade is None else [trade]
        if params.strategy_id is not None:
            all_items = [item for item in all_items if item.strategy_id == params.strategy_id]
        if params.symbol is not None:
            all_items = [item for item in all_items if item.symbol == params.symbol]
        if params.position_id is not None:
            all_items = [item for item in all_items if item.position_id == params.position_id]
    else:
        all_items = deps.canonical_execution_repo.list_trades(
            strategy_id=params.strategy_id,
            symbol=params.symbol,
            position_id=params.position_id,
            limit=1_000_000,
            offset=0,
        )

    page, total = paginate_items(all_items, limit=params.limit, offset=params.offset)
    return PaperTradesReadResponse(
        items=page,
        limit=params.limit,
        offset=params.offset,
        total=total,
    )


def read_paper_positions(
    *,
    params: PaperPositionsReadQuery,
    deps: InspectionServiceDependencies,
) -> PaperPositionsReadResponse:
    state = load_bounded_paper_simulation_state(deps=deps)
    all_items = list(state.positions)
    if params.strategy_id is not None:
        all_items = [item for item in all_items if item.strategy_id == params.strategy_id]
    if params.symbol is not None:
        all_items = [item for item in all_items if item.symbol == params.symbol]
    if params.position_id is not None:
        all_items = [item for item in all_items if item.position_id == params.position_id]

    page, total = paginate_items(all_items, limit=params.limit, offset=params.offset)
    return PaperPositionsReadResponse(
        items=page,
        limit=params.limit,
        offset=params.offset,
        total=total,
    )


def read_paper_reconciliation(
    *,
    deps: InspectionServiceDependencies,
) -> PaperReconciliationReadResponse:
    state = load_bounded_paper_simulation_state(deps=deps)
    orders = list(state.orders)
    execution_events = list(state.execution_events)
    trades = list(state.trades)
    positions = list(state.positions)
    account = PaperAccountStateResponse(**state.account)
    mismatch_items = [
        PaperReconciliationMismatchResponse(**item)
        for item in state.reconciliation_mismatches
    ]
    return PaperReconciliationReadResponse(
        ok=not mismatch_items,
        summary=PaperReconciliationSummaryResponse(
            orders=len(orders),
            execution_events=len(execution_events),
            trades=len(trades),
            positions=len(positions),
            open_trades=sum(1 for trade in trades if trade.status == "open"),
            closed_trades=sum(1 for trade in trades if trade.status == "closed"),
            open_positions=sum(1 for position in positions if position.status == "open"),
            mismatches=len(mismatch_items),
        ),
        account=account,
        mismatch_items=mismatch_items,
    )


def read_paper_operator_workflow(
    *,
    deps: InspectionServiceDependencies,
) -> PaperOperatorWorkflowReadResponse:
    core_orders_items = deps.canonical_execution_repo.list_orders(limit=1_000_000, offset=0)
    core_events_items = deps.canonical_execution_repo.list_execution_events(limit=1_000_000, offset=0)
    core_trades_items = deps.canonical_execution_repo.list_trades(limit=1_000_000, offset=0)
    core_positions_items = build_trading_core_positions(
        canonical_execution_repo=deps.canonical_execution_repo,
        strategy_id=None,
        symbol=None,
        position_id=None,
    )
    paper_trades_items = deps.canonical_execution_repo.list_trades(limit=1_000_000, offset=0)
    paper_positions_items = build_trading_core_positions(
        canonical_execution_repo=deps.canonical_execution_repo,
        strategy_id=None,
        symbol=None,
        position_id=None,
    )
    portfolio_positions_items = paper_inspection_service.build_portfolio_positions_from_trades(
        trades=core_trades_items,
    )
    paper_portfolio_positions_items = paper_inspection_service.build_portfolio_positions_from_trades(
        trades=paper_trades_items,
    )
    reconciliation = read_paper_reconciliation(deps=deps)

    checks = [
        PaperOperatorWorkflowValidationCheckResponse(
            code="portfolio_to_paper_reconciliation_ok",
            ok=reconciliation.ok,
            expected="true",
            actual=str(reconciliation.ok).lower(),
        ),
        PaperOperatorWorkflowValidationCheckResponse(
            code="portfolio_to_paper_reconciliation_mismatches_zero",
            ok=reconciliation.summary.mismatches == 0,
            expected="0",
            actual=str(reconciliation.summary.mismatches),
        ),
        PaperOperatorWorkflowValidationCheckResponse(
            code="portfolio_to_paper_trades_match_canonical_trades",
            ok=paper_trades_items == core_trades_items,
            expected="true",
            actual=str(paper_trades_items == core_trades_items).lower(),
        ),
        PaperOperatorWorkflowValidationCheckResponse(
            code="portfolio_to_paper_positions_match_canonical_positions",
            ok=paper_positions_items == core_positions_items,
            expected="true",
            actual=str(paper_positions_items == core_positions_items).lower(),
        ),
        PaperOperatorWorkflowValidationCheckResponse(
            code="portfolio_inspection_positions_are_derived_from_canonical_trades",
            ok=portfolio_positions_items == paper_portfolio_positions_items,
            expected="true",
            actual=str(portfolio_positions_items == paper_portfolio_positions_items).lower(),
        ),
    ]

    return PaperOperatorWorkflowReadResponse(
        boundary=PaperOperatorWorkflowBoundaryResponse(
            workflow_id="phase44_bounded_paper_operator",
            description=(
                "One read-only decision-to-paper and portfolio-to-paper handoff contract that "
                "validates bounded paper execution evidence across canonical inspection and "
                "reconciliation surfaces."
            ),
            in_scope=[
                "covered decision-card usefulness audit against explicit matched paper-trade outcomes",
                "explicit portfolio-to-paper handoff inputs from canonical orders, execution events, trades, and positions",
                "paper-facing account, trade, and position views derived from canonical portfolio evidence",
                "portfolio position inspection derived from the same canonical trade evidence",
                "reconciliation validation with mismatch accounting",
                "bounded paper operator inspection with no readiness or operational-readiness claim",
            ],
            out_of_scope=[
                "live-trading readiness or approval",
                "broker execution readiness or approval",
                "broad dashboard expansion",
                "production trading operations",
            ],
        ),
        steps=[
            PaperOperatorWorkflowStepResponse(
                step=1,
                action="Inspect canonical order lifecycle entities that anchor the portfolio handoff.",
                endpoint="GET /trading-core/orders",
                expected_result=f"Canonical order evidence is readable (items={len(core_orders_items)}).",
            ),
            PaperOperatorWorkflowStepResponse(
                step=2,
                action="Inspect canonical execution lifecycle events that support the portfolio handoff.",
                endpoint="GET /trading-core/execution-events",
                expected_result=(
                    f"Canonical execution-event evidence is readable (items={len(core_events_items)})."
                ),
            ),
            PaperOperatorWorkflowStepResponse(
                step=3,
                action="Inspect canonical trade and position state that defines portfolio evidence.",
                endpoint="GET /trading-core/trades + GET /trading-core/positions",
                expected_result=(
                    f"Canonical portfolio evidence is readable (trades={len(core_trades_items)}, "
                    f"positions={len(core_positions_items)})."
                ),
            ),
            PaperOperatorWorkflowStepResponse(
                step=4,
                action="Inspect portfolio and paper-facing views derived from the canonical handoff.",
                endpoint="GET /portfolio/positions + GET /paper/trades + GET /paper/positions + GET /paper/account",
                expected_result=(
                    f"Bounded inspection views are readable (portfolio_positions={len(portfolio_positions_items)}, "
                    f"paper_trades={len(paper_trades_items)}, paper_positions={len(paper_positions_items)})."
                ),
            ),
            PaperOperatorWorkflowStepResponse(
                step=5,
                action="Run reconciliation and require zero mismatches before bounded operator review.",
                endpoint="GET /paper/reconciliation",
                expected_result=(
                    f"Bounded paper reconciliation ok={str(reconciliation.ok).lower()} mismatches="
                    f"{reconciliation.summary.mismatches}."
                ),
            ),
            PaperOperatorWorkflowStepResponse(
                step=6,
                action=(
                    "Inspect covered decision cards for bounded usefulness classifications against "
                    "explicit matched paper-trade outcomes."
                ),
                endpoint="GET /decision-cards",
                expected_result=(
                    "Covered decision-card outputs expose bounded usefulness classifications in "
                    "metadata without trader-validation or readiness claims."
                ),
            ),
            PaperOperatorWorkflowStepResponse(
                step=7,
                action="Confirm the explicit reference chain from decision evidence to reconciliation.",
                endpoint="GET /decision-cards + GET /portfolio/positions + GET /paper/trades + GET /paper/reconciliation",
                expected_result=(
                    "Decision, portfolio, paper execution, and reconciliation stages expose deterministic references "
                    "without inferring live or operational readiness."
                ),
            ),
        ],
        surfaces=PaperOperatorWorkflowSurfaceResponse(
            signal_inspection=[
                "/signals",
                "/signals/decision-surface",
            ],
            canonical_inspection=[
                "/decision-cards",
                "/trading-core/orders",
                "/trading-core/execution-events",
                "/trading-core/trades",
                "/trading-core/positions",
            ],
            portfolio_inspection=[
                "/portfolio/positions",
            ],
            paper_inspection=[
                "/paper/trades",
                "/paper/positions",
                "/paper/account",
            ],
            reconciliation="/paper/reconciliation",
        ),
        reference_chain=[
            PaperOperatorWorkflowReferenceResponse(
                stage="signal_evidence",
                surface="/signals + /signals/decision-surface",
                reference="analysis_run_id + symbol + strategy_id + generated_at_utc",
                continuity=(
                    "Covered signal evidence carries deterministic analysis and signal references "
                    "before decision-card inspection."
                ),
            ),
            PaperOperatorWorkflowReferenceResponse(
                stage="decision_evidence",
                surface="/decision-cards",
                reference="decision_card_id + metadata.bounded_decision_to_paper_match.paper_trade_id",
                continuity=(
                    "Covered decision evidence carries the explicit paper_trade_id reference used by "
                    "bounded usefulness and traceability audits."
                ),
            ),
            PaperOperatorWorkflowReferenceResponse(
                stage="portfolio_impact",
                surface="/portfolio/positions",
                reference="portfolio_impact_id = decision_card_id + strategy_id + symbol",
                continuity=(
                    "Portfolio impact is inspectable before paper execution through deterministic "
                    "strategy_id and symbol aggregation from canonical trades."
                ),
            ),
            PaperOperatorWorkflowReferenceResponse(
                stage="paper_order_lifecycle",
                surface="/trading-core/orders + /trading-core/execution-events",
                reference="paper_order_id + execution_event_ids",
                continuity=(
                    "Paper order lifecycle references connect portfolio handoff intent to canonical "
                    "created, submitted, fill, cancel, or terminal execution events."
                ),
            ),
            PaperOperatorWorkflowReferenceResponse(
                stage="portfolio_inspection",
                surface="/portfolio/positions",
                reference="strategy_id + symbol",
                continuity=(
                    "Portfolio inspection aggregates open canonical trades by strategy_id and symbol; "
                    "it does not introduce a separate position authority."
                ),
            ),
            PaperOperatorWorkflowReferenceResponse(
                stage="paper_execution",
                surface="/paper/trades",
                reference="paper_trade_id -> Trade.trade_id",
                continuity=(
                    "Paper-facing trades are the canonical Trade entities used by decision-card match references."
                ),
            ),
            PaperOperatorWorkflowReferenceResponse(
                stage="reconciliation",
                surface="/paper/reconciliation",
                reference="order_id + event_id + trade_id + position_id + account equations",
                continuity=(
                    "Reconciliation deterministically reports any broken reference or account equation mismatch."
                ),
            ),
            PaperOperatorWorkflowReferenceResponse(
                stage="paper_outcome",
                surface="/paper/trades + /decision-cards metadata",
                reference="paper_trade_id + paper_outcome.outcome_state",
                continuity=(
                    "Decision-card metadata explicitly classifies paper outcomes as missing, invalid, "
                    "open, or closed without inferring live or operational readiness."
                ),
            ),
        ],
        inspection_summary=PaperOperatorWorkflowInspectionSummaryResponse(
            canonical_orders=len(core_orders_items),
            canonical_execution_events=len(core_events_items),
            canonical_trades=len(core_trades_items),
            canonical_positions=len(core_positions_items),
            portfolio_positions=len(portfolio_positions_items),
            paper_trades=len(paper_trades_items),
            paper_positions=len(paper_positions_items),
            reconciliation_mismatches=reconciliation.summary.mismatches,
        ),
        validation=PaperOperatorWorkflowValidationResponse(
            ok=all(check.ok for check in checks),
            checks=checks,
        ),
    )


def read_ingestion_runs(
    *,
    limit: int,
    deps: InspectionServiceDependencies,
) -> List[IngestionRunItemResponse]:
    rows = deps.analysis_run_repo.list_ingestion_runs(limit=limit)
    return [IngestionRunItemResponse(**row) for row in rows]


def read_signals(
    *,
    params: SignalsReadQuery,
    deps: InspectionServiceDependencies,
) -> SignalReadResponseDTO:
    items, total = deps.signal_repo.read_signals(
        symbol=params.symbol,
        strategy=params.strategy,
        timeframe=params.timeframe,
        ingestion_run_id=params.ingestion_run_id,
        from_=params.from_,
        to=params.to,
        sort=params.sort,
        limit=params.limit,
        offset=params.offset,
    )

    response_items: List[SignalReadItemDTO] = []
    for signal in items:
        response_items.append(
            SignalReadItemDTO(
                symbol=signal["symbol"],
                strategy=signal["strategy"],
                direction=signal["direction"],
                score=signal["score"],
                created_at=signal["timestamp"],
                stage=signal["stage"],
                entry_zone=signal.get("entry_zone"),
                confirmation_rule=signal.get("confirmation_rule"),
                timeframe=signal["timeframe"],
                market_type=signal["market_type"],
                data_source=signal["data_source"],
            )
        )

    return SignalReadResponseDTO(
        items=response_items,
        limit=params.limit,
        offset=params.offset,
        total=total,
    )


def read_signals_raw(
    *,
    params: SignalsReadQuery,
    deps: InspectionServiceDependencies,
) -> SignalReadResponseDTO:
    items, total = deps.signal_repo.read_signals_raw(
        symbol=params.symbol,
        strategy=params.strategy,
        timeframe=params.timeframe,
        ingestion_run_id=params.ingestion_run_id,
        from_=params.from_,
        to=params.to,
        sort=params.sort,
        limit=params.limit,
        offset=params.offset,
    )

    response_items: List[SignalReadItemDTO] = []
    for signal in items:
        response_items.append(
            SignalReadItemDTO(
                symbol=signal["symbol"],
                strategy=signal["strategy"],
                direction=signal["direction"],
                score=signal["score"],
                created_at=signal["timestamp"],
                stage=signal["stage"],
                entry_zone=signal.get("entry_zone"),
                confirmation_rule=signal.get("confirmation_rule"),
                timeframe=signal["timeframe"],
                market_type=signal["market_type"],
                data_source=signal["data_source"],
            )
        )

    return SignalReadResponseDTO(
        items=response_items,
        limit=params.limit,
        offset=params.offset,
        total=total,
    )


def _build_signal_decision_surface_boundary() -> SignalDecisionSurfaceBoundaryResponse:
    return SignalDecisionSurfaceBoundaryResponse(
        mode="non_live_signal_decision_surface",
        technical_decision_state_statement=(
            "This surface provides bounded technical decision-state visibility for non-live signal review only."
        ),
        trader_validation_statement=(
            "Technical decision states are not trader validation and must not be interpreted as trader approval."
        ),
        operational_readiness_statement=(
            "Technical decision states do not establish operational readiness, live trading readiness, or "
            "broker execution readiness."
        ),
        strategy_readiness_evidence=StrategyReadinessEvidenceResponse(
            bounded_scope=(
                "One bounded API/UI evidence scope for non-live technical signal decision support on /ui."
            ),
            technical=StrategyReadinessEvidenceStateResponse(
                gate="technical_implementation",
                status="technical_in_progress",
                evidence_scope=(
                    "Technical decision-state classification and professional qualification-evidence surfacing for reviewed signals."
                ),
                non_inference_note=(
                    "Technical decision-state evidence does not imply trader validation or operational readiness."
                ),
            ),
            trader_validation=StrategyReadinessEvidenceStateResponse(
                gate="trader_validation",
                status="trader_validation_not_started",
                evidence_scope=(
                    "Trader validation evidence is outside this bounded technical decision-state contract."
                ),
                non_inference_note=(
                    "Trader validation status cannot be inferred from technical decision-state output."
                ),
            ),
            operational_readiness=StrategyReadinessEvidenceStateResponse(
                gate="operational_readiness",
                status="operational_not_started",
                evidence_scope=(
                    "Operational-readiness evidence is outside this bounded technical decision-state contract."
                ),
                non_inference_note=(
                    "Operational-readiness status cannot be inferred from technical decision-state output."
                ),
            ),
            inferred_readiness_claim="prohibited",
        ),
        in_scope=[
            "bounded technical decision-state classification for reviewed signals",
            "professional non-live qualification criteria over stage, score, confirmation-rule, and entry-zone evidence",
            "explicit qualification evidence with rationale including score contribution and stage assessment",
            "explicit missing criteria and blocking-condition visibility",
            "deterministic bounded trader-relevance case evaluation for qualification and action outputs",
        ],
        out_of_scope=[
            "trader validation outcomes",
            "paper profitability or edge claims",
            "operational readiness outcomes",
            "live trading and broker execution decisions",
        ],
    )


def _build_signal_decision_surface_item(signal: Dict[str, Any]) -> SignalDecisionSurfaceItemResponse:
    score = float(signal.get("score") or 0.0)
    stage = str(signal.get("stage") or "")
    confirmation_rule = str(signal.get("confirmation_rule") or "").strip()
    entry_zone_raw = signal.get("entry_zone")
    entry_zone = entry_zone_raw if isinstance(entry_zone_raw, dict) else None

    qualification_evidence: List[str] = []
    missing_criteria: List[str] = []
    blocking_conditions: List[str] = []

    if score < SIGNAL_DECISION_BLOCKED_SCORE_THRESHOLD:
        blocking_conditions.append(
            f"Blocking score condition: score={score:.2f} below blocking threshold "
            f"{SIGNAL_DECISION_BLOCKED_SCORE_THRESHOLD:.2f}."
        )
    else:
        qualification_evidence.append(
            f"Score hard-floor evidence: score={score:.2f} meets blocking threshold "
            f"{SIGNAL_DECISION_BLOCKED_SCORE_THRESHOLD:.2f}."
        )

    if stage == "entry_confirmed":
        qualification_evidence.append("Stage evidence: stage=entry_confirmed satisfies progression stage criterion.")
    else:
        missing_criteria.append(
            f"Missing stage evidence: stage={stage or 'unknown'}; requires entry_confirmed."
        )

    if score < SIGNAL_DECISION_CANDIDATE_SCORE_THRESHOLD:
        missing_criteria.append(
            f"Missing score evidence: score={score:.2f} below candidate threshold "
            f"{SIGNAL_DECISION_CANDIDATE_SCORE_THRESHOLD:.2f}."
        )
    else:
        qualification_evidence.append(
            f"Score quality evidence: score={score:.2f} meets candidate threshold "
            f"{SIGNAL_DECISION_CANDIDATE_SCORE_THRESHOLD:.2f}."
        )

    if confirmation_rule:
        qualification_evidence.append(
            f"Confirmation-rule evidence: confirmation_rule={confirmation_rule} is explicitly available."
        )
    else:
        missing_criteria.append(
            "Missing confirmation-rule evidence: confirmation_rule must be present for professional qualification."
        )

    entry_zone_from_raw = entry_zone.get("from_") if entry_zone is not None else None
    entry_zone_to_raw = entry_zone.get("to") if entry_zone is not None else None
    try:
        entry_zone_from = float(entry_zone_from_raw) if entry_zone_from_raw is not None else None
        entry_zone_to = float(entry_zone_to_raw) if entry_zone_to_raw is not None else None
    except (TypeError, ValueError):
        entry_zone_from = None
        entry_zone_to = None

    if entry_zone_from is None or entry_zone_to is None:
        missing_criteria.append(
            "Missing entry-zone evidence: entry_zone.from_ and entry_zone.to must be present."
        )
    elif entry_zone_from >= entry_zone_to:
        blocking_conditions.append(
            "Blocking entry-zone condition: entry_zone.from_ must be lower than entry_zone.to."
        )
    else:
        qualification_evidence.append(
            f"Entry-zone evidence: entry_zone.from_={entry_zone_from:.4f} and entry_zone.to={entry_zone_to:.4f} are valid."
        )

    if blocking_conditions:
        decision_state: Literal["blocked", "watch", "paper_candidate"] = "blocked"
        rationale_summary = (
            "Blocked: one or more professional technical qualification blocking conditions failed for this non-live surface."
        )
        score_contribution = (
            f"Score {score:.2f} contributes blocking evidence against further technical progression."
        )
    elif missing_criteria:
        decision_state = "watch"
        rationale_summary = (
            "Watch: partial professional technical qualification evidence is present, but required criteria are still missing."
        )
        score_contribution = (
            f"Score {score:.2f} contributes partial evidence and keeps this signal in watch state."
        )
    else:
        decision_state = "paper_candidate"
        rationale_summary = (
            "Paper candidate: professional non-live technical qualification criteria are satisfied for bounded review progression."
        )
        score_contribution = (
            f"Score {score:.2f} contributes positive evidence for paper_candidate technical state."
        )

    stage_assessment = (
        "Stage entry_confirmed satisfies the technical stage criterion."
        if stage == "entry_confirmed"
        else f"Stage {stage or 'unknown'} does not satisfy required entry_confirmed stage criterion."
    )

    aggregate_score = score
    if aggregate_score >= QUALIFICATION_HIGH_AGGREGATE_THRESHOLD:
        confidence_tier = "high"
    elif aggregate_score >= QUALIFICATION_MEDIUM_AGGREGATE_THRESHOLD:
        confidence_tier = "medium"
    else:
        confidence_tier = "low"

    has_blocking_failure = bool(blocking_conditions)
    if has_blocking_failure:
        qualification_state: Literal["reject", "watch", "paper_candidate", "paper_approved"] = "reject"
    elif missing_criteria:
        qualification_state = "watch"
    elif confidence_tier == "high" and aggregate_score >= QUALIFICATION_HIGH_AGGREGATE_THRESHOLD:
        qualification_state = "paper_approved"
    else:
        qualification_state = "paper_candidate"

    win_rate = max(0.0, min(1.0, round(score / 100.0, 4)))
    reward_multiplier = max(0.50, min(1.50, (score + score) / 100.0))
    expected_value = max(-1.0, min(1.0, round((win_rate * reward_multiplier) - (1.0 - win_rate), 4)))

    if has_blocking_failure:
        action: Literal["entry", "exit", "ignore"] = "ignore"
    elif expected_value < 0.0:
        action = "exit"
    elif qualification_state in {"paper_candidate", "paper_approved"} and win_rate <= ACTION_EXIT_WIN_RATE_MAX:
        action = "exit"
    elif (
        confidence_tier == "low"
        or aggregate_score < QUALIFICATION_MEDIUM_AGGREGATE_THRESHOLD
        or qualification_state in {"reject", "watch"}
    ):
        action = "ignore"
    elif qualification_state in {"paper_candidate", "paper_approved"} and win_rate >= ACTION_ENTRY_WIN_RATE_MIN:
        action = "entry"
    else:
        action = "ignore"

    boundary_statement = (
        "Boundary evidence: this deterministic decision output is bounded trader-relevance validation only; "
        "it is not trader_validation evidence, not paper profitability evidence, and not live-trading readiness evidence."
    )
    trader_relevance_validation = evaluate_bounded_trader_relevance_cases(
        qualification_state=qualification_state,
        action=action,
        win_rate=win_rate,
        expected_value=expected_value,
        qualification_summary=(
            "Qualification output remains explicitly bounded to paper-trading scope for technical review."
        ),
        rationale_summary=rationale_summary,
        final_explanation=boundary_statement,
        qualification_evidence=qualification_evidence + [boundary_statement],
        missing_criteria=missing_criteria,
        blocking_conditions=blocking_conditions,
    )
    trader_relevance_case_status = ", ".join(
        f"{item.case_id}={item.evidence_status}"
        for item in trader_relevance_validation.evaluations
    )
    qualification_evidence.append(
        "Bounded trader-relevance case review "
        f"(contract={trader_relevance_validation.contract_id}, "
        f"version={trader_relevance_validation.contract_version}, "
        f"overall={trader_relevance_validation.overall_status}): "
        f"{trader_relevance_case_status}."
    )
    qualification_evidence.append(boundary_statement)

    return SignalDecisionSurfaceItemResponse(
        symbol=str(signal.get("symbol") or ""),
        strategy=str(signal.get("strategy") or ""),
        direction=str(signal.get("direction") or ""),
        score=score,
        created_at=str(signal.get("timestamp") or ""),
        stage=stage,
        timeframe=str(signal.get("timeframe") or ""),
        market_type=str(signal.get("market_type") or ""),
        data_source=str(signal.get("data_source") or ""),
        decision_state=decision_state,
        qualification_state=qualification_state,
        action=action,
        win_rate=win_rate,
        expected_value=expected_value,
        qualification_policy_version=SIGNAL_DECISION_QUALIFICATION_POLICY_VERSION,
        rationale_summary=rationale_summary,
        qualification_evidence=qualification_evidence,
        score_contribution=score_contribution,
        stage_assessment=stage_assessment,
        missing_criteria=missing_criteria,
        blocking_conditions=blocking_conditions,
    )


def read_signal_decision_surface(
    *,
    params: SignalsReadQuery,
    deps: InspectionServiceDependencies,
) -> SignalDecisionSurfaceResponse:
    items, total = deps.signal_repo.read_signals(
        symbol=params.symbol,
        strategy=params.strategy,
        timeframe=params.timeframe,
        ingestion_run_id=params.ingestion_run_id,
        from_=params.from_,
        to=params.to,
        sort=params.sort,
        limit=params.limit,
        offset=params.offset,
    )

    decision_items = [_build_signal_decision_surface_item(signal) for signal in items]
    return SignalDecisionSurfaceResponse(
        workflow_id=SIGNAL_DECISION_SURFACE_WORKFLOW_ID,
        boundary=_build_signal_decision_surface_boundary(),
        items=decision_items,
        limit=params.limit,
        offset=params.offset,
        total=total,
    )


def read_execution_orders(
    *,
    params: ExecutionOrdersReadQuery,
    deps: InspectionServiceDependencies,
) -> ExecutionOrdersReadResponse:
    items, total = deps.order_event_repo.read_order_events(
        symbol=params.symbol,
        strategy=params.strategy,
        run_id=params.run_id,
        order_id=params.order_id,
        limit=params.limit,
        offset=params.offset,
    )

    response_items = [ExecutionOrderEventItemResponse(**item) for item in items]
    return ExecutionOrdersReadResponse(
        items=response_items,
        limit=params.limit,
        offset=params.offset,
        total=total,
    )


def read_trading_core_orders(
    *,
    params: TradingCoreOrdersReadQuery,
    deps: InspectionServiceDependencies,
) -> TradingCoreOrdersReadResponse:
    if params.order_id:
        order = deps.canonical_execution_repo.get_order(params.order_id)
        all_items = [] if order is None else [order]
        if params.strategy_id is not None:
            all_items = [item for item in all_items if item.strategy_id == params.strategy_id]
        if params.symbol is not None:
            all_items = [item for item in all_items if item.symbol == params.symbol]
    else:
        all_items = deps.canonical_execution_repo.list_orders(
            strategy_id=params.strategy_id,
            symbol=params.symbol,
            limit=1_000_000,
            offset=0,
        )

    page, total = paginate_items(all_items, limit=params.limit, offset=params.offset)
    return TradingCoreOrdersReadResponse(
        items=page,
        limit=params.limit,
        offset=params.offset,
        total=total,
    )


def read_trading_core_execution_events(
    *,
    params: TradingCoreExecutionEventsReadQuery,
    deps: InspectionServiceDependencies,
) -> TradingCoreExecutionEventsReadResponse:
    all_items = deps.canonical_execution_repo.list_execution_events(
        strategy_id=params.strategy_id,
        symbol=params.symbol,
        order_id=params.order_id,
        trade_id=params.trade_id,
        limit=1_000_000,
        offset=0,
    )
    page, total = paginate_items(all_items, limit=params.limit, offset=params.offset)
    return TradingCoreExecutionEventsReadResponse(
        items=page,
        limit=params.limit,
        offset=params.offset,
        total=total,
    )


def read_trading_core_trades(
    *,
    params: TradingCoreTradesReadQuery,
    deps: InspectionServiceDependencies,
) -> TradingCoreTradesReadResponse:
    if params.trade_id:
        trade = deps.canonical_execution_repo.get_trade(params.trade_id)
        all_items = [] if trade is None else [trade]
        if params.strategy_id is not None:
            all_items = [item for item in all_items if item.strategy_id == params.strategy_id]
        if params.symbol is not None:
            all_items = [item for item in all_items if item.symbol == params.symbol]
        if params.position_id is not None:
            all_items = [item for item in all_items if item.position_id == params.position_id]
    else:
        all_items = deps.canonical_execution_repo.list_trades(
            strategy_id=params.strategy_id,
            symbol=params.symbol,
            position_id=params.position_id,
            limit=1_000_000,
            offset=0,
        )

    page, total = paginate_items(all_items, limit=params.limit, offset=params.offset)
    return TradingCoreTradesReadResponse(
        items=page,
        limit=params.limit,
        offset=params.offset,
        total=total,
    )


def read_trading_core_positions(
    *,
    params: TradingCorePositionsReadQuery,
    deps: InspectionServiceDependencies,
) -> TradingCorePositionsReadResponse:
    all_items = build_trading_core_positions(
        canonical_execution_repo=deps.canonical_execution_repo,
        strategy_id=params.strategy_id,
        symbol=params.symbol,
        position_id=params.position_id,
    )
    page, total = paginate_items(all_items, limit=params.limit, offset=params.offset)
    return TradingCorePositionsReadResponse(
        items=page,
        limit=params.limit,
        offset=params.offset,
        total=total,
    )


def read_screener_results(
    *,
    params: ScreenerResultsQuery,
    deps: InspectionServiceDependencies,
) -> ScreenerResultsResponse:
    items, total = deps.signal_repo.read_screener_results(
        strategy=params.strategy,
        timeframe=params.timeframe,
        min_score=params.min_score,
        limit=params.limit,
        offset=params.offset,
    )
    response_items = [ScreenerResultItem(**item) for item in items]

    return ScreenerResultsResponse(
        items=response_items,
        limit=params.limit,
        offset=params.offset,
        total=total,
    )


def iter_journal_artifact_files(*, journal_artifacts_root: Path) -> List[tuple[str, Path]]:
    if not journal_artifacts_root.exists() or not journal_artifacts_root.is_dir():
        return []

    artifact_files: List[tuple[str, Path]] = []
    for run_dir in journal_artifacts_root.iterdir():
        if not run_dir.is_dir():
            continue
        run_id = run_dir.name
        for artifact_file in run_dir.iterdir():
            if artifact_file.is_file():
                artifact_files.append((run_id, artifact_file))
    return artifact_files


def resolve_journal_artifact_path(
    *,
    run_id: str,
    artifact_name: str,
    journal_artifacts_root: Path,
) -> Path:
    if "/" in run_id or "\\" in run_id:
        raise HTTPException(status_code=404, detail="journal_artifact_not_found")
    if "/" in artifact_name or "\\" in artifact_name:
        raise HTTPException(status_code=404, detail="journal_artifact_not_found")

    candidate = journal_artifacts_root / run_id / artifact_name
    try:
        resolved = candidate.resolve(strict=True)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="journal_artifact_not_found") from None

    expected_parent = (journal_artifacts_root / run_id).resolve()
    if resolved.parent != expected_parent or not resolved.is_file():
        raise HTTPException(status_code=404, detail="journal_artifact_not_found")

    return resolved


def read_journal_artifact_content(path: Path) -> tuple[Literal["json", "text"], Any]:
    raw_text = path.read_text(encoding="utf-8")
    try:
        return "json", json.loads(raw_text)
    except json.JSONDecodeError:
        return "text", raw_text


def extract_trace_entries(content: Any) -> tuple[Optional[str], List[Dict[str, Any]]]:
    trace_id: Optional[str] = None
    entries: list[Any] = []

    if isinstance(content, dict):
        trace_id_value = content.get("trace_id")
        if isinstance(trace_id_value, str):
            trace_id = trace_id_value

        candidate = None
        if "decision_trace" in content:
            candidate = content.get("decision_trace")
        elif "trace_entries" in content:
            candidate = content.get("trace_entries")
        elif "entries" in content:
            candidate = content.get("entries")

        if isinstance(candidate, dict):
            maybe_trace_id = candidate.get("trace_id")
            if isinstance(maybe_trace_id, str):
                trace_id = maybe_trace_id
            maybe_entries = candidate.get("entries")
            if isinstance(maybe_entries, list):
                entries = maybe_entries
        elif isinstance(candidate, list):
            entries = candidate
    elif isinstance(content, list):
        entries = content

    normalized_entries: List[Dict[str, Any]] = []
    for entry in entries:
        if isinstance(entry, dict):
            normalized_entries.append(entry)
        else:
            normalized_entries.append({"value": entry})
    return trace_id, normalized_entries


def _normalize_trace_reason_codes(entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    normalized_entries: List[Dict[str, Any]] = []
    candidate_fields = (
        "normalized_reason_code",
        "reason_code",
        "reason",
        "failure_reason",
        "rejection_reason",
        "risk_reason",
        "risk_reason_code",
    )

    for entry in entries:
        normalized_entry = dict(entry)
        candidate: str | None = None
        for field in candidate_fields:
            value = normalized_entry.get(field)
            if isinstance(value, str) and value.strip():
                candidate = value.strip()
                break
        if candidate is not None:
            try:
                normalized_entry["normalized_reason_code"] = (
                    normalize_risk_rejection_reason_code(candidate)
                )
            except ValueError:
                pass
        normalized_entries.append(normalized_entry)

    return normalized_entries


def extract_decision_card_candidates(content: Any) -> List[Dict[str, Any]]:
    candidates: List[Dict[str, Any]] = []

    def _walk(node: Any) -> None:
        if isinstance(node, dict):
            if {
                "contract_version",
                "decision_card_id",
                "generated_at_utc",
                "hard_gates",
                "score",
                "qualification",
                "rationale",
            }.issubset(node.keys()):
                candidates.append(node)
            for value in node.values():
                if isinstance(value, (dict, list)):
                    _walk(value)
        elif isinstance(node, list):
            for item in node:
                _walk(item)

    _walk(content)
    return candidates


def matches_decision_card_review_state(
    *,
    qualification_state: str,
    review_state: Optional[Literal["ranked", "blocked", "approved"]],
) -> bool:
    if review_state is None:
        return True
    if review_state == "blocked":
        return qualification_state == "reject"
    if review_state == "approved":
        return qualification_state == "paper_approved"
    return qualification_state != "reject"


def decision_card_item_sort_key(
    item: DecisionCardInspectionItemResponse,
    *,
    sort: Literal["generated_at_desc", "generated_at_asc"],
) -> tuple[float, str, str, str]:
    generated_at = datetime.fromisoformat(
        item.generated_at_utc.replace("Z", "+00:00")
        if item.generated_at_utc.endswith("Z")
        else item.generated_at_utc
    )
    timestamp = generated_at.timestamp()
    if sort == "generated_at_desc":
        timestamp = -timestamp
    return (timestamp, item.decision_card_id, item.run_id, item.artifact_name)


def _extract_realism_sensitivity_matrix(content: Any) -> dict[str, Any] | None:
    if isinstance(content, dict):
        metrics_baseline = content.get("metrics_baseline")
        if isinstance(metrics_baseline, dict):
            matrix = metrics_baseline.get("realism_sensitivity_matrix")
            if isinstance(matrix, dict):
                return matrix
        for value in content.values():
            matrix = _extract_realism_sensitivity_matrix(value)
            if matrix is not None:
                return matrix
        return None
    if isinstance(content, list):
        for value in content:
            matrix = _extract_realism_sensitivity_matrix(value)
            if matrix is not None:
                return matrix
    return None


def _load_run_realism_sensitivity_matrix(run_dir: Path) -> dict[str, Any] | None:
    if not run_dir.exists():
        return None

    for artifact_path in sorted(run_dir.iterdir(), key=lambda path: path.name):
        if artifact_path.suffix.casefold() != ".json" or not artifact_path.is_file():
            continue
        content_type, content = read_journal_artifact_content(artifact_path)
        if content_type != "json":
            continue
        matrix = _extract_realism_sensitivity_matrix(content)
        if matrix is not None:
            return matrix
    return None


def build_decision_card_inspection_items(
    *,
    params: DecisionCardInspectionQuery,
    journal_artifacts_root: Path,
) -> List[DecisionCardInspectionItemResponse]:
    items: List[DecisionCardInspectionItemResponse] = []
    seen: set[tuple[str, str, str, str]] = set()
    run_realism_cache: dict[str, dict[str, Any] | None] = {}

    for run_id, artifact_path in iter_journal_artifact_files(
        journal_artifacts_root=journal_artifacts_root
    ):
        if params.run_id is not None and run_id != params.run_id:
            continue

        content_type, content = read_journal_artifact_content(artifact_path)
        if content_type != "json":
            continue

        for candidate in extract_decision_card_candidates(content):
            try:
                card = validate_decision_card(candidate)
            except (ValidationError, ValueError):
                continue

            if params.decision_card_id is not None and card.decision_card_id != params.decision_card_id:
                continue
            if params.symbol is not None and card.symbol != params.symbol:
                continue
            if params.strategy_id is not None and card.strategy_id != params.strategy_id:
                continue
            if (
                params.qualification_state is not None
                and card.qualification.state != params.qualification_state
            ):
                continue
            if not matches_decision_card_review_state(
                qualification_state=card.qualification.state,
                review_state=params.review_state,
            ):
                continue

            dedupe_key = (
                run_id,
                artifact_path.name,
                card.decision_card_id,
                card.to_canonical_json(),
            )
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)

            metadata = dict(card.metadata)
            canonical_repo = paper_inspection_service.resolve_runtime_canonical_execution_repo()
            if run_id not in run_realism_cache:
                run_realism_cache[run_id] = _load_run_realism_sensitivity_matrix(
                    artifact_path.parent
                )
            realism_sensitivity_matrix = run_realism_cache[run_id]
            match_reference = metadata.get("bounded_decision_to_paper_match")
            usefulness_audit = paper_inspection_service.build_bounded_decision_to_paper_usefulness_audit(
                canonical_execution_repo=canonical_repo,
                decision_card_id=card.decision_card_id,
                generated_at_utc=card.generated_at_utc,
                symbol=card.symbol,
                strategy_id=card.strategy_id,
                action=card.action,
                qualification_state=card.qualification.state,
                match_reference=match_reference,
            )
            if usefulness_audit is not None:
                metadata["bounded_decision_to_paper_usefulness_audit"] = usefulness_audit

            signal_quality_score: float | None = None
            for component in card.score.component_scores:
                if component.category == "signal_quality":
                    signal_quality_score = float(component.score)
                    break
            stability_audit = (
                paper_inspection_service.build_bounded_signal_quality_stability_audit(
                    canonical_execution_repo=canonical_repo,
                    decision_card_id=card.decision_card_id,
                    generated_at_utc=card.generated_at_utc,
                    symbol=card.symbol,
                    strategy_id=card.strategy_id,
                    signal_quality_score=signal_quality_score,
                    match_reference=match_reference,
                )
            )
            if stability_audit is not None:
                metadata["bounded_signal_quality_stability_audit"] = stability_audit

            metadata["bounded_confidence_calibration_audit"] = (
                paper_inspection_service.build_bounded_confidence_calibration_audit(
                    canonical_execution_repo=canonical_repo,
                    decision_card_id=card.decision_card_id,
                    generated_at_utc=card.generated_at_utc,
                    symbol=card.symbol,
                    strategy_id=card.strategy_id,
                    confidence_tier=card.score.confidence_tier,
                    realism_sensitivity_matrix=realism_sensitivity_matrix,
                    match_reference=match_reference,
                )
            )
            strategy_score_calibration_audit = (
                paper_inspection_service.build_bounded_strategy_score_calibration_audit(
                    canonical_execution_repo=canonical_repo,
                    decision_card_id=card.decision_card_id,
                    generated_at_utc=card.generated_at_utc,
                    symbol=card.symbol,
                    strategy_id=card.strategy_id,
                    aggregate_score=card.score.aggregate_score,
                    confidence_tier=card.score.confidence_tier,
                    realism_sensitivity_matrix=realism_sensitivity_matrix,
                    match_reference=match_reference,
                )
            )
            if strategy_score_calibration_audit is not None:
                metadata["bounded_strategy_score_calibration_audit"] = (
                    strategy_score_calibration_audit
                )

            paper_match_status, paper_trade_id = (
                paper_inspection_service.resolve_bounded_paper_linkage_status(
                    canonical_execution_repo=canonical_repo,
                    generated_at_utc=card.generated_at_utc,
                    symbol=card.symbol,
                    strategy_id=card.strategy_id,
                    match_reference=match_reference,
                )
            )
            analysis_run_id_meta = card.metadata.get("analysis_run_id")
            analysis_run_id = (
                analysis_run_id_meta
                if isinstance(analysis_run_id_meta, str) and len(analysis_run_id_meta) > 0
                else None
            )
            signal_id_meta = card.metadata.get("signal_id")
            signal_id = (
                signal_id_meta
                if isinstance(signal_id_meta, str) and len(signal_id_meta) > 0
                else None
            )
            metadata["bounded_signal_portfolio_paper_reconciliation_audit"] = (
                paper_inspection_service.build_bounded_signal_portfolio_paper_reconciliation_audit(
                    canonical_execution_repo=canonical_repo,
                    decision_card_id=card.decision_card_id,
                    generated_at_utc=card.generated_at_utc,
                    symbol=card.symbol,
                    strategy_id=card.strategy_id,
                    action=card.action,
                    qualification_state=card.qualification.state,
                    analysis_run_id=analysis_run_id,
                    signal_id=signal_id,
                    match_reference=match_reference,
                )
            )
            traceability_chain = evaluate_bounded_end_to_end_traceability_chain(
                decision_card_id=card.decision_card_id,
                generated_at_utc=card.generated_at_utc,
                symbol=card.symbol,
                strategy_id=card.strategy_id,
                qualification_state=card.qualification.state,
                action=card.action,
                analysis_run_id=analysis_run_id,
                paper_trade_id=paper_trade_id,
                paper_match_status=paper_match_status,
            )

            items.append(
                DecisionCardInspectionItemResponse(
                    run_id=run_id,
                    artifact_name=artifact_path.name,
                    decision_card_id=card.decision_card_id,
                    generated_at_utc=card.generated_at_utc,
                    symbol=card.symbol,
                    strategy_id=card.strategy_id,
                    qualification_state=card.qualification.state,
                    action=card.action,
                    win_rate=card.score.win_rate,
                    expected_value=card.score.expected_value,
                    qualification_color=card.qualification.color,
                    qualification_summary=card.qualification.summary,
                    aggregate_score=card.score.aggregate_score,
                    confidence_tier=card.score.confidence_tier,
                    hard_gate_policy_version=card.hard_gates.policy_version,
                    hard_gate_blocking_failure=card.hard_gates.has_blocking_failure,
                    hard_gates=[
                        DecisionCardHardGateInspectionResponse(**gate.model_dump(mode="python"))
                        for gate in card.hard_gates.gates
                    ],
                    component_scores=[
                        DecisionCardComponentScoreInspectionResponse(
                            **component.model_dump(mode="python")
                        )
                        for component in card.score.component_scores
                    ],
                    rationale_summary=card.rationale.summary,
                    gate_explanations=list(card.rationale.gate_explanations),
                    score_explanations=list(card.rationale.score_explanations),
                    final_explanation=card.rationale.final_explanation,
                    metadata=metadata,
                    traceability_chain=traceability_chain.model_dump(mode="python"),
                )
            )

    items.sort(key=lambda item: decision_card_item_sort_key(item, sort=params.sort))
    return items


def read_journal_artifacts(
    *,
    limit: int,
    offset: int,
    journal_artifacts_root: Path,
) -> JournalArtifactListResponse:
    files = iter_journal_artifact_files(journal_artifacts_root=journal_artifacts_root)
    files.sort(key=lambda item: item[1].stat().st_mtime, reverse=True)

    total = len(files)
    page = files[offset : offset + limit]
    items: List[JournalArtifactItemResponse] = []
    for run_id, path in page:
        stat = path.stat()
        items.append(
            JournalArtifactItemResponse(
                run_id=run_id,
                artifact_name=path.name,
                size_bytes=stat.st_size,
                modified_at=datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
            )
        )

    return JournalArtifactListResponse(items=items, total=total)


def read_journal_artifact_file_content(
    *,
    run_id: str,
    artifact_name: str,
    journal_artifacts_root: Path,
) -> JournalArtifactContentResponse:
    path = resolve_journal_artifact_path(
        run_id=run_id,
        artifact_name=artifact_name,
        journal_artifacts_root=journal_artifacts_root,
    )
    content_type, content = read_journal_artifact_content(path)
    return JournalArtifactContentResponse(
        run_id=run_id,
        artifact_name=artifact_name,
        content_type=content_type,
        content=content,
    )


def _build_backtest_read_boundary() -> BacktestReadBoundaryResponse:
    review_contract = build_professional_review_contract()
    return BacktestReadBoundaryResponse(
        mode="non_live_backtest_read_only",
        review_contract_id=review_contract["contract_id"],
        review_contract_version=review_contract["contract_version"],
        review_required_evidence=list(review_contract["required_visible_evidence"]),
        review_comparison_axes=list(review_contract["comparison_axes"]),
        decision_relevance_statement=review_contract["decision_relevance_statement"],
        readiness_non_inference_statement=review_contract["readiness_non_inference_statement"],
        technical_availability_statement=(
            "This flow only confirms technical availability of governed backtest artifacts."
        ),
        trader_validation_statement=(
            "Technical artifact availability is not trader validation and must not be interpreted "
            "as strategy approval."
        ),
        operational_readiness_statement=(
            "Backtest artifact visibility is not operational readiness evidence for live or broker "
            "execution."
        ),
        strategy_readiness_evidence=StrategyReadinessEvidenceResponse(
            bounded_scope=(
                "One bounded API/UI evidence surfacing scope for governed non-live backtest "
                "artifact inspection."
            ),
            technical=StrategyReadinessEvidenceStateResponse(
                gate="technical_implementation",
                status="technical_in_progress",
                evidence_scope=(
                    "API/UI contract and test evidence for read-only governed backtest artifact "
                    "visibility."
                ),
                non_inference_note=(
                    "Technical evidence does not imply trader validation, operational readiness, "
                    "live trading, or production readiness."
                ),
            ),
            trader_validation=StrategyReadinessEvidenceStateResponse(
                gate="trader_validation",
                status="trader_validation_not_started",
                evidence_scope=(
                    "Trader-owned validation evidence is outside this API/UI technical contract."
                ),
                non_inference_note=(
                    "Trader validation status cannot be inferred from technical artifact "
                    "visibility."
                ),
            ),
            operational_readiness=StrategyReadinessEvidenceStateResponse(
                gate="operational_readiness",
                status="operational_not_started",
                evidence_scope=(
                    "Operational-readiness evidence is outside this API/UI technical contract and "
                    "requires governed runbook acceptance artifacts."
                ),
                non_inference_note=(
                    "Operational-readiness status cannot be inferred from technical or "
                    "trader-validation evidence fields."
                ),
            ),
            inferred_readiness_claim="prohibited",
        ),
        in_scope=[
            "read-only listing of governed backtest artifacts",
            "read-only artifact content preview for governed backtest artifacts",
            "bounded non-live technical inspection through /ui",
        ],
        out_of_scope=[
            "live trading and broker connectivity",
            "order execution enablement",
            "trader validation and operational readiness claims",
        ],
    )


def _is_governed_backtest_artifact_name(artifact_name: str) -> bool:
    return artifact_name in GOVERNED_BACKTEST_ARTIFACT_NAMES


def read_backtest_artifacts(
    *,
    limit: int,
    offset: int,
    run_id: Optional[str],
    journal_artifacts_root: Path,
) -> BacktestArtifactListResponse:
    files = iter_journal_artifact_files(journal_artifacts_root=journal_artifacts_root)
    filtered: List[tuple[str, Path]] = []
    for item_run_id, path in files:
        if run_id is not None and item_run_id != run_id:
            continue
        if not _is_governed_backtest_artifact_name(path.name):
            continue
        filtered.append((item_run_id, path))
    filtered.sort(key=lambda item: item[1].stat().st_mtime, reverse=True)

    total = len(filtered)
    page = filtered[offset : offset + limit]
    items: List[BacktestArtifactItemResponse] = []
    for item_run_id, path in page:
        stat = path.stat()
        items.append(
            BacktestArtifactItemResponse(
                run_id=item_run_id,
                artifact_name=path.name,
                size_bytes=stat.st_size,
                modified_at=datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
            )
        )

    return BacktestArtifactListResponse(
        workflow_id=BACKTEST_WORKFLOW_ID,
        boundary=_build_backtest_read_boundary(),
        items=items,
        limit=limit,
        offset=offset,
        total=total,
    )


def read_backtest_artifact_content(
    *,
    run_id: str,
    artifact_name: str,
    journal_artifacts_root: Path,
) -> BacktestArtifactContentResponse:
    if not _is_governed_backtest_artifact_name(artifact_name):
        raise HTTPException(status_code=404, detail="backtest_artifact_not_found")
    path = resolve_journal_artifact_path(
        run_id=run_id,
        artifact_name=artifact_name,
        journal_artifacts_root=journal_artifacts_root,
    )
    content_type, content = read_journal_artifact_content(path)
    return BacktestArtifactContentResponse(
        workflow_id=BACKTEST_WORKFLOW_ID,
        boundary=_build_backtest_read_boundary(),
        run_id=run_id,
        artifact_name=artifact_name,
        content_type=content_type,
        content=content,
    )


def read_decision_trace(
    *,
    run_id: str,
    artifact_name: str,
    journal_artifacts_root: Path,
) -> DecisionTraceResponse:
    path = resolve_journal_artifact_path(
        run_id=run_id,
        artifact_name=artifact_name,
        journal_artifacts_root=journal_artifacts_root,
    )
    _, content = read_journal_artifact_content(path)
    trace_id, entries = extract_trace_entries(content)
    entries = _normalize_trace_reason_codes(entries)
    return DecisionTraceResponse(
        run_id=run_id,
        artifact_name=artifact_name,
        trace_id=trace_id,
        entries=entries,
        total_entries=len(entries),
    )


def read_decision_cards(
    *,
    params: DecisionCardInspectionQuery,
    journal_artifacts_root: Path,
) -> DecisionCardInspectionResponse:
    all_items = build_decision_card_inspection_items(
        params=params,
        journal_artifacts_root=journal_artifacts_root,
    )
    page, total = paginate_items(all_items, limit=params.limit, offset=params.offset)
    return DecisionCardInspectionResponse(
        items=page,
        limit=params.limit,
        offset=params.offset,
        total=total,
    )


def read_strategy_metadata(
    *,
    default_strategy_configs: Dict[str, Dict[str, Any]],
) -> Any:
    return build_strategy_metadata_response(default_strategy_configs=default_strategy_configs)

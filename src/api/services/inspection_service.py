from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

from fastapi import HTTPException
from pydantic import ValidationError

from cilly_trading.engine.decision_card_contract import validate_decision_card
from cilly_trading.models import ExecutionEvent, Order, Position, SignalReadItemDTO, SignalReadResponseDTO, Trade

from ..models import (
    BacktestArtifactContentResponse,
    BacktestArtifactItemResponse,
    BacktestArtifactListResponse,
    BacktestReadBoundaryResponse,
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
    ]

    return PaperOperatorWorkflowReadResponse(
        boundary=PaperOperatorWorkflowBoundaryResponse(
            workflow_id="phase44_bounded_paper_operator",
            description=(
                "One read-only portfolio-to-paper handoff contract that validates bounded "
                "paper-readiness inputs across canonical inspection and reconciliation surfaces."
            ),
            in_scope=[
                "explicit portfolio-to-paper handoff inputs from canonical orders, execution events, trades, and positions",
                "paper-facing account, trade, and position views derived from canonical portfolio evidence",
                "reconciliation validation with mismatch accounting",
                "bounded paper-readiness review with no unsupported upstream claim expansion",
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
                action="Inspect canonical trade and position state that defines portfolio readiness.",
                endpoint="GET /trading-core/trades + GET /trading-core/positions",
                expected_result=(
                    f"Canonical portfolio evidence is readable (trades={len(core_trades_items)}, "
                    f"positions={len(core_positions_items)})."
                ),
            ),
            PaperOperatorWorkflowStepResponse(
                step=4,
                action="Inspect paper-facing views derived from the canonical portfolio handoff.",
                endpoint="GET /paper/trades + GET /paper/positions + GET /paper/account",
                expected_result=(
                    f"Paper-readiness views are readable (trades={len(paper_trades_items)}, "
                    f"positions={len(paper_positions_items)})."
                ),
            ),
            PaperOperatorWorkflowStepResponse(
                step=5,
                action="Run reconciliation and require zero mismatches before paper-readiness review.",
                endpoint="GET /paper/reconciliation",
                expected_result=(
                    f"Paper-readiness reconciliation ok={str(reconciliation.ok).lower()} mismatches="
                    f"{reconciliation.summary.mismatches}."
                ),
            ),
        ],
        surfaces=PaperOperatorWorkflowSurfaceResponse(
            canonical_inspection=[
                "/trading-core/orders",
                "/trading-core/execution-events",
                "/trading-core/trades",
                "/trading-core/positions",
            ],
            paper_inspection=[
                "/paper/trades",
                "/paper/positions",
                "/paper/account",
            ],
            reconciliation="/paper/reconciliation",
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


def build_decision_card_inspection_items(
    *,
    params: DecisionCardInspectionQuery,
    journal_artifacts_root: Path,
) -> List[DecisionCardInspectionItemResponse]:
    items: List[DecisionCardInspectionItemResponse] = []
    seen: set[tuple[str, str, str, str]] = set()

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

            items.append(
                DecisionCardInspectionItemResponse(
                    run_id=run_id,
                    artifact_name=artifact_path.name,
                    decision_card_id=card.decision_card_id,
                    generated_at_utc=card.generated_at_utc,
                    symbol=card.symbol,
                    strategy_id=card.strategy_id,
                    qualification_state=card.qualification.state,
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
                    metadata=dict(card.metadata),
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
    return BacktestReadBoundaryResponse(
        mode="non_live_backtest_read_only",
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

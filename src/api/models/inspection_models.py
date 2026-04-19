from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from cilly_trading.models import ExecutionEvent, Order, Position, Trade

from ..config import SCREENER_RESULTS_READ_MAX_LIMIT, SIGNALS_READ_MAX_LIMIT


class SignalsReadQuery(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    symbol: Optional[str] = Field(default=None)
    strategy: Optional[str] = Field(default=None)
    timeframe: Optional[str] = Field(default=None)
    ingestion_run_id: Optional[str] = Field(default=None)
    from_: Optional[datetime] = Field(default=None, alias="from")
    to: Optional[datetime] = Field(default=None, alias="to")
    sort: Literal["created_at_asc", "created_at_desc"] = Field(default="created_at_desc")
    limit: int = Field(
        default=50,
        ge=1,
        le=SIGNALS_READ_MAX_LIMIT,
        description=f"Maximal {SIGNALS_READ_MAX_LIMIT} Eintraege.",
    )
    offset: int = Field(default=0, ge=0)


class ExecutionOrdersReadQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    symbol: Optional[str] = Field(default=None)
    strategy: Optional[str] = Field(default=None)
    run_id: Optional[str] = Field(default=None)
    order_id: Optional[str] = Field(default=None)
    limit: int = Field(default=50, ge=1, le=500)
    offset: int = Field(default=0, ge=0)


class ExecutionOrderEventItemResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    order_id: str
    symbol: str
    strategy: str
    state: Literal["created", "submitted", "filled", "partially_filled", "cancelled"]
    event_timestamp: str
    event_sequence: int
    metadata: Optional[Dict[str, Any]] = None


class ExecutionOrdersReadResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: List[ExecutionOrderEventItemResponse]
    limit: int
    offset: int
    total: int


class TradingCoreOrdersReadQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    strategy_id: Optional[str] = Field(default=None)
    symbol: Optional[str] = Field(default=None)
    order_id: Optional[str] = Field(default=None)
    limit: int = Field(default=50, ge=1, le=500)
    offset: int = Field(default=0, ge=0)


class TradingCoreExecutionEventsReadQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    strategy_id: Optional[str] = Field(default=None)
    symbol: Optional[str] = Field(default=None)
    order_id: Optional[str] = Field(default=None)
    trade_id: Optional[str] = Field(default=None)
    limit: int = Field(default=50, ge=1, le=500)
    offset: int = Field(default=0, ge=0)


class TradingCoreTradesReadQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    strategy_id: Optional[str] = Field(default=None)
    symbol: Optional[str] = Field(default=None)
    position_id: Optional[str] = Field(default=None)
    trade_id: Optional[str] = Field(default=None)
    limit: int = Field(default=50, ge=1, le=500)
    offset: int = Field(default=0, ge=0)


class TradingCorePositionsReadQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    strategy_id: Optional[str] = Field(default=None)
    symbol: Optional[str] = Field(default=None)
    position_id: Optional[str] = Field(default=None)
    limit: int = Field(default=50, ge=1, le=500)
    offset: int = Field(default=0, ge=0)


class PaperTradesReadQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    strategy_id: Optional[str] = Field(default=None)
    symbol: Optional[str] = Field(default=None)
    position_id: Optional[str] = Field(default=None)
    trade_id: Optional[str] = Field(default=None)
    limit: int = Field(default=50, ge=1, le=500)
    offset: int = Field(default=0, ge=0)


class PaperPositionsReadQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    strategy_id: Optional[str] = Field(default=None)
    symbol: Optional[str] = Field(default=None)
    position_id: Optional[str] = Field(default=None)
    limit: int = Field(default=50, ge=1, le=500)
    offset: int = Field(default=0, ge=0)


class TradingCoreOrdersReadResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: List[Order]
    limit: int
    offset: int
    total: int


class TradingCoreExecutionEventsReadResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: List[ExecutionEvent]
    limit: int
    offset: int
    total: int


class TradingCoreTradesReadResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: List[Trade]
    limit: int
    offset: int
    total: int


class TradingCorePositionsReadResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: List[Position]
    limit: int
    offset: int
    total: int


class PaperAccountStateResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    starting_cash: Decimal
    cash: Decimal
    equity: Decimal
    realized_pnl: Decimal
    unrealized_pnl: Decimal
    total_pnl: Decimal
    open_positions: int
    open_trades: int
    closed_trades: int
    as_of: Optional[str] = None


class PaperAccountReadResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    account: PaperAccountStateResponse


class PaperTradesReadResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: List[Trade]
    limit: int
    offset: int
    total: int


class PaperPositionsReadResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: List[Position]
    limit: int
    offset: int
    total: int


class PaperReconciliationMismatchResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    message: str
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None


class PaperReconciliationSummaryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    orders: int
    execution_events: int
    trades: int
    positions: int
    open_trades: int
    closed_trades: int
    open_positions: int
    mismatches: int


class PaperReconciliationReadResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ok: bool
    summary: PaperReconciliationSummaryResponse
    account: PaperAccountStateResponse
    mismatch_items: List[PaperReconciliationMismatchResponse]


class PaperOperatorWorkflowBoundaryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workflow_id: str
    description: str
    in_scope: List[str]
    out_of_scope: List[str]


class PaperOperatorWorkflowStepResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    step: int
    action: str
    endpoint: str
    expected_result: str


class PaperOperatorWorkflowSurfaceResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    canonical_inspection: List[str]
    paper_inspection: List[str]
    reconciliation: str


class PaperOperatorWorkflowValidationCheckResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    ok: bool
    expected: str
    actual: str


class PaperOperatorWorkflowValidationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ok: bool
    checks: List[PaperOperatorWorkflowValidationCheckResponse]


class PaperOperatorWorkflowReadResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    boundary: PaperOperatorWorkflowBoundaryResponse
    steps: List[PaperOperatorWorkflowStepResponse]
    surfaces: PaperOperatorWorkflowSurfaceResponse
    validation: PaperOperatorWorkflowValidationResponse


class ScreenerResultsQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    strategy: str
    timeframe: str
    min_score: Optional[float] = Field(default=None, ge=0.0)
    limit: int = Field(default=50, ge=1, le=SCREENER_RESULTS_READ_MAX_LIMIT)
    offset: int = Field(default=0, ge=0)


class ScreenerResultItem(BaseModel):
    symbol: str
    score: float
    strategy: str
    timeframe: str
    market_type: str
    created_at: str

    model_config = ConfigDict(extra="forbid")


class ScreenerResultsResponse(BaseModel):
    items: List[ScreenerResultItem]
    limit: int
    offset: int
    total: int

    model_config = ConfigDict(extra="forbid")


class StrategyMetadataItemResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    strategy: str
    display_name: str
    default_config_keys: List[str]
    has_default_config: bool


class StrategyMetadataResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: List[StrategyMetadataItemResponse]
    total: int


class IngestionRunItemResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ingestion_run_id: str
    created_at: str
    symbols_count: int


class PortfolioPositionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    symbol: str
    size: float
    average_price: float
    unrealized_pnl: float
    strategy_id: str


class PortfolioPositionsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    positions: List[PortfolioPositionResponse]
    total: int


class JournalArtifactItemResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    artifact_name: str
    size_bytes: int
    modified_at: str


class JournalArtifactListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: List[JournalArtifactItemResponse]
    total: int


class JournalArtifactContentResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    artifact_name: str
    content_type: Literal["json", "text"]
    content: Any


class StrategyReadinessEvidenceStateResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    gate: Literal["technical_implementation", "trader_validation", "operational_readiness"]
    status: str
    evidence_scope: str
    non_inference_note: str


class StrategyReadinessEvidenceResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    bounded_scope: str
    technical: StrategyReadinessEvidenceStateResponse
    trader_validation: StrategyReadinessEvidenceStateResponse
    operational_readiness: StrategyReadinessEvidenceStateResponse
    inferred_readiness_claim: Literal["prohibited"]


class SignalDecisionSurfaceBoundaryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: Literal["non_live_signal_decision_surface"]
    technical_decision_state_statement: str
    trader_validation_statement: str
    operational_readiness_statement: str
    strategy_readiness_evidence: StrategyReadinessEvidenceResponse
    in_scope: List[str]
    out_of_scope: List[str]


class SignalDecisionSurfaceItemResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    symbol: str
    strategy: str
    direction: str
    score: float
    created_at: str
    stage: str
    timeframe: str
    market_type: str
    data_source: str
    decision_state: Literal["blocked", "watch", "paper_candidate"]
    qualification_state: Literal["reject", "watch", "paper_candidate", "paper_approved"]
    action: Literal["entry", "exit", "ignore"]
    win_rate: float = Field(ge=0.0, le=1.0)
    expected_value: float = Field(ge=-1.0, le=1.0)
    qualification_policy_version: str
    rationale_summary: str
    qualification_evidence: List[str]
    score_contribution: str
    stage_assessment: str
    missing_criteria: List[str]
    blocking_conditions: List[str]


class SignalDecisionSurfaceResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workflow_id: str
    boundary: SignalDecisionSurfaceBoundaryResponse
    items: List[SignalDecisionSurfaceItemResponse]
    limit: int
    offset: int
    total: int


class BacktestReadBoundaryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: Literal["non_live_backtest_read_only"]
    review_contract_id: str
    review_contract_version: str
    review_required_evidence: List[str]
    review_comparison_axes: List[str]
    decision_relevance_statement: str
    readiness_non_inference_statement: str
    technical_availability_statement: str
    trader_validation_statement: str
    operational_readiness_statement: str
    strategy_readiness_evidence: StrategyReadinessEvidenceResponse
    in_scope: List[str]
    out_of_scope: List[str]


class BacktestArtifactItemResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    artifact_name: str
    size_bytes: int
    modified_at: str


class BacktestArtifactListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workflow_id: str
    boundary: BacktestReadBoundaryResponse
    items: List[BacktestArtifactItemResponse]
    limit: int
    offset: int
    total: int


class BacktestArtifactContentResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workflow_id: str
    boundary: BacktestReadBoundaryResponse
    run_id: str
    artifact_name: str
    content_type: Literal["json", "text"]
    content: Any


class DecisionTraceResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    artifact_name: str
    trace_id: Optional[str] = None
    entries: List[Dict[str, Any]]
    total_entries: int


class DecisionCardHardGateInspectionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    gate_id: str
    status: Literal["pass", "fail"]
    blocking: bool
    reason: str
    evidence: List[str]
    failure_reason: Optional[str] = None


class DecisionCardComponentScoreInspectionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category: Literal[
        "signal_quality",
        "backtest_quality",
        "portfolio_fit",
        "risk_alignment",
        "execution_readiness",
    ]
    score: float
    rationale: str
    evidence: List[str]


class DecisionCardInspectionItemResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    artifact_name: str
    decision_card_id: str
    generated_at_utc: str
    symbol: str
    strategy_id: str
    qualification_state: Literal["reject", "watch", "paper_candidate", "paper_approved"]
    action: Literal["entry", "exit", "ignore"]
    win_rate: float = Field(ge=0.0, le=1.0)
    expected_value: float = Field(ge=-1.0, le=1.0)
    qualification_color: Literal["green", "yellow", "red"]
    qualification_summary: str
    aggregate_score: float
    confidence_tier: Literal["low", "medium", "high"]
    hard_gate_policy_version: str
    hard_gate_blocking_failure: bool
    hard_gates: List[DecisionCardHardGateInspectionResponse]
    component_scores: List[DecisionCardComponentScoreInspectionResponse]
    rationale_summary: str
    gate_explanations: List[str]
    score_explanations: List[str]
    final_explanation: str
    metadata: Dict[str, Any]


class DecisionCardInspectionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: List[DecisionCardInspectionItemResponse]
    limit: int
    offset: int
    total: int


class DecisionCardInspectionQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: Optional[str] = Field(default=None)
    symbol: Optional[str] = Field(default=None)
    strategy_id: Optional[str] = Field(default=None)
    decision_card_id: Optional[str] = Field(default=None)
    qualification_state: Optional[
        Literal["reject", "watch", "paper_candidate", "paper_approved"]
    ] = Field(default=None)
    review_state: Optional[Literal["ranked", "blocked", "approved"]] = Field(default=None)
    sort: Literal["generated_at_desc", "generated_at_asc"] = Field(default="generated_at_desc")
    limit: int = Field(default=50, ge=1, le=500)
    offset: int = Field(default=0, ge=0)

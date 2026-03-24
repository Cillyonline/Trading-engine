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
import os
import json
import uuid
from decimal import Decimal
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from cilly_trading.engine.analysis import trigger_operator_analysis_run
from cilly_trading.compliance.daily_loss_guard import (
    configured_daily_loss_limit,
    should_block_execution_for_daily_loss,
)
from cilly_trading.compliance.drawdown_guard import (
    configured_drawdown_threshold,
    should_block_execution_for_drawdown,
)
from cilly_trading.compliance.kill_switch import is_kill_switch_active
from cilly_trading.portfolio import PortfolioState as CompliancePortfolioState
from .alerts_api import build_alerts_router
from .config import SCREENER_RESULTS_READ_MAX_LIMIT, SIGNALS_READ_MAX_LIMIT
from cilly_trading.db import DEFAULT_DB_PATH
from cilly_trading.engine.core import (
    EngineConfig,
    compute_analysis_run_id,
    run_watchlist_analysis,
)
from cilly_trading.engine.decision_card_contract import validate_decision_card
from cilly_trading.engine.data import SnapshotDataError
from cilly_trading.engine.health.evaluator import (
    RuntimeHealthSnapshot,
    evaluate_runtime_health,
)
from cilly_trading.engine.runtime_controller import (
    LifecycleTransitionError,
    get_runtime_controller,
    pause_engine_runtime,
    resume_engine_runtime,
    shutdown_engine_runtime,
    start_engine_runtime,
)
from .order_events_sqlite import SqliteOrderEventRepository
from cilly_trading.engine.portfolio import (
    PortfolioPosition as PortfolioInspectionPosition,
    load_portfolio_state_from_env,
)
from cilly_trading.engine.runtime_introspection import get_runtime_introspection_payload
from cilly_trading.engine.runtime_state import get_system_state_payload
from cilly_trading.models import (
    ExecutionEvent,
    Order,
    Position,
    SignalReadItemDTO,
    SignalReadResponseDTO,
    Trade,
)
from cilly_trading.repositories.analysis_runs_sqlite import SqliteAnalysisRunRepository
from cilly_trading.repositories.execution_core_sqlite import SqliteCanonicalExecutionRepository
from cilly_trading.repositories.signals_sqlite import SqliteSignalRepository
from cilly_trading.repositories.watchlists_sqlite import SqliteWatchlistRepository
from cilly_trading.strategies.registry import (
    StrategyNotRegisteredError,
    create_registered_strategies,
    create_strategy,
    initialize_default_registry,
    run_registry_smoke,
)


def configure_logging() -> None:
    """
    Central logging configuration for the Cilly Trading Engine.
    Runs once during app startup.

    Note: Uvicorn with --reload can import modules multiple times.
    This guard prevents duplicate handlers.
    """
    log_level = os.getenv("CILLY_LOG_LEVEL", "INFO").upper()

    root_logger = logging.getLogger()
    if root_logger.handlers:
        # Logging is already configured (for example by reload or another setup).
        return

    logging.basicConfig(
        level=log_level,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )


configure_logging()
logger = logging.getLogger(__name__)


# --- Pydantic models for requests/responses ---


class PresetConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., min_length=1, description="Stabiler Preset-Identifier.")
    params: Dict[str, Any] = Field(
        default_factory=dict,
        description="Strategie-Parameter für dieses Preset.",
    )


class StrategyAnalyzeRequest(BaseModel):
    ingestion_run_id: str = Field(
        ...,
        min_length=1,
        description="Snapshot reference ID.",
    )
    symbol: str = Field(..., description="Ticker, z. B. 'AAPL' oder 'BTC/USDT'")
    strategy: str = Field(..., description="Name der Strategie, z. B. 'RSI2' oder 'TURTLE'")
    market_type: str = Field(
        "stock",
        description="Markttyp: 'stock' oder 'crypto'",
        pattern="^(stock|crypto)$",
    )
    lookback_days: int = Field(
        200,
        ge=30,
        le=1000,
        description="Anzahl der Tage, die mindestens geladen werden sollen.",
    )
    strategy_config: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optionale Strategie-Konfiguration (z. B. Oversold-Schwelle).",
    )
    preset_id: Optional[str] = Field(
        default=None,
        min_length=1,
        description="Optional: einzelner Preset-Identifier.",
    )
    preset_ids: Optional[List[str]] = Field(
        default=None,
        min_length=1,
        description="Optional: mehrere Preset-Identifier für Vergleich.",
    )
    presets: Optional[List[PresetConfig]] = Field(
        default=None,
        min_length=1,
        description="Optional: mehrere Presets für dieselbe Strategie (Vergleich).",
    )

    @model_validator(mode="after")
    def _validate_presets(self) -> "StrategyAnalyzeRequest":
        if self.presets and (self.preset_id or self.preset_ids):
            raise ValueError("presets cannot be combined with preset_id or preset_ids")

        if self.preset_id and self.preset_ids:
            raise ValueError("preset_id and preset_ids cannot be used together")

        if self.presets is None:
            if self.preset_ids is None:
                return self

            preset_ids = self.preset_ids
            if len(set(preset_ids)) != len(preset_ids):
                raise ValueError("preset ids must be unique")
            return self

        preset_ids = [preset.id for preset in self.presets]
        if len(set(preset_ids)) != len(preset_ids):
            raise ValueError("preset ids must be unique")

        return self


class PresetAnalysisResult(BaseModel):
    preset_id: str
    signals: List[Dict[str, Any]]


class StrategyAnalyzeResponse(BaseModel):
    symbol: str
    strategy: str
    signals: Optional[List[Dict[str, Any]]] = None
    results_by_preset: Optional[Dict[str, List[Dict[str, Any]]]] = None
    preset_results: Optional[List[PresetAnalysisResult]] = None


class ManualAnalysisRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    analysis_run_id: Optional[str] = Field(
        default=None,
        min_length=1,
        description="Optional client-provided run ID (ignored).",
    )
    ingestion_run_id: str = Field(..., min_length=1, description="Snapshot reference ID.")
    symbol: str = Field(..., description="Ticker, z. B. 'AAPL' oder 'BTC/USDT'")
    strategy: str = Field(..., description="Name der Strategie, z. B. 'RSI2' oder 'TURTLE'")
    market_type: str = Field(
        "stock",
        description="Markttyp: 'stock' oder 'crypto'",
        pattern="^(stock|crypto)$",
    )
    lookback_days: int = Field(
        200,
        ge=30,
        le=1000,
        description="Anzahl der Tage, die mindestens geladen werden sollen.",
    )
    strategy_config: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optionale Strategie-Konfiguration (z. B. Oversold-Schwelle).",
    )


class ManualAnalysisResponse(BaseModel):
    analysis_run_id: str
    ingestion_run_id: str
    symbol: str
    strategy: str
    signals: List[Dict[str, Any]]

    model_config = ConfigDict(extra="forbid")


class ScreenerRequest(BaseModel):
    """
    Request-Modell für den Basis-Screener.

    MVP:
    - Wenn keine Symbolliste angegeben ist, wird eine Default-Liste pro Markt verwendet.
    - Nutzt alle registrierten Strategien (RSI2 & TURTLE).
    """

    ingestion_run_id: str = Field(
        ...,
        min_length=1,
        description="Snapshot reference ID.",
    )
    symbols: Optional[List[str]] = Field(
        default=None,
        description="Liste von Symbolen. Wenn None, wird eine Default-Watchlist verwendet.",
    )
    market_type: str = Field(
        "stock",
        description="Markttyp: 'stock' oder 'crypto'",
        pattern="^(stock|crypto)$",
    )
    lookback_days: int = Field(
        200,
        ge=30,
        le=1000,
        description="Anzahl der Tage, die mindestens geladen werden sollen.",
    )
    min_score: float = Field(
        30.0,
        ge=0.0,
        le=100.0,
        description="Mindestscore für Setups, die im Screener erscheinen sollen.",
    )


class ScreenerSymbolResult(BaseModel):
    symbol: str
    score: Optional[float] = None
    signal_strength: Optional[float] = None
    setups: List[Dict[str, Any]]


class ScreenerResponse(BaseModel):
    market_type: str
    symbols: List[ScreenerSymbolResult]


class WatchlistExecutionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ingestion_run_id: str = Field(..., min_length=1, description="Snapshot reference ID.")
    market_type: str = Field(
        "stock",
        description="Markttyp: 'stock' oder 'crypto'",
        pattern="^(stock|crypto)$",
    )
    lookback_days: int = Field(
        200,
        ge=30,
        le=1000,
        description="Anzahl der Tage, die mindestens geladen werden sollen.",
    )
    min_score: float = Field(
        30.0,
        ge=0.0,
        le=100.0,
        description="Mindestscore fuer Setups, die im Ranking erscheinen sollen.",
    )


class WatchlistExecutionRankedItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rank: int
    symbol: str
    score: Optional[float] = None
    signal_strength: Optional[float] = None
    setups: List[Dict[str, Any]]


class WatchlistExecutionFailure(BaseModel):
    model_config = ConfigDict(extra="forbid")

    symbol: str
    code: str
    detail: str


class WatchlistExecutionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    analysis_run_id: str
    ingestion_run_id: str
    watchlist_id: str
    watchlist_name: str
    market_type: str
    ranked_results: List[WatchlistExecutionRankedItem]
    failures: List[WatchlistExecutionFailure]


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
        description=f"Maximal {SIGNALS_READ_MAX_LIMIT} Einträge.",
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


class RuntimeIntrospectionTimestampsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    started_at: str
    updated_at: str


class RuntimeIntrospectionOwnershipResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    owner_tag: str


class RuntimeIntrospectionExtensionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    point: Literal["status", "health", "introspection"]
    enabled: bool
    source: Literal["core", "extension"]


class RuntimeIntrospectionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str
    runtime_id: str
    mode: str
    timestamps: RuntimeIntrospectionTimestampsResponse
    ownership: RuntimeIntrospectionOwnershipResponse
    extensions: List[RuntimeIntrospectionExtensionResponse] = Field(default_factory=list)


class GuardStatusDecisionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool
    blocking: bool
    decision: Literal["allowing", "blocking"]


class DrawdownGuardStatusResponse(GuardStatusDecisionResponse):
    model_config = ConfigDict(extra="forbid")

    threshold_pct: float | None
    current_drawdown_pct: float


class DailyLossGuardStatusResponse(GuardStatusDecisionResponse):
    model_config = ConfigDict(extra="forbid")

    max_daily_loss_abs: float | None
    current_daily_loss_abs: float


class KillSwitchStatusResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    active: bool
    blocking: bool
    decision: Literal["allowing", "blocking"]


class GuardStatusCollectionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    drawdown_guard: DrawdownGuardStatusResponse
    daily_loss_guard: DailyLossGuardStatusResponse
    kill_switch: KillSwitchStatusResponse


class ComplianceStatusResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    blocking: bool
    decision: Literal["allowing", "blocking"]


class ComplianceGuardStatusResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    compliance: ComplianceStatusResponse
    guards: GuardStatusCollectionResponse


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


class SystemStateMetadataResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    read_only: Literal[True]
    source: str


class SystemStateResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str
    status: str
    runtime: RuntimeIntrospectionResponse
    metadata: SystemStateMetadataResponse


class ExecutionControlResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    state: str


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


class WatchlistPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=1)
    symbols: List[str] = Field(..., min_length=1)


class WatchlistCreateRequest(WatchlistPayload):
    model_config = ConfigDict(extra="forbid")

    watchlist_id: str = Field(..., min_length=1)


class WatchlistResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    watchlist_id: str
    name: str
    symbols: List[str]


class WatchlistListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: List[WatchlistResponse]
    total: int


class WatchlistDeleteResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    watchlist_id: str
    deleted: Literal[True]


app = FastAPI(
    title="Cilly Trading Engine API",
    version="0.1.0",
    description="MVP-API für die Cilly Trading Engine (RSI2 & Turtle, D1, SQLite).",
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


def _assert_phase_13_read_only_endpoint(endpoint_path: str) -> None:
    assert endpoint_path in PHASE_13_READ_ONLY_ENDPOINTS


def _require_role(minimum_role: str):
    required_rank = ROLE_PRECEDENCE[minimum_role]

    def _enforce_role(x_cilly_role: str | None = Header(default=None, alias=ROLE_HEADER_NAME)) -> str:
        if x_cilly_role is None:
            raise HTTPException(status_code=401, detail="unauthorized")

        normalized_role = x_cilly_role.strip().lower()
        caller_rank = ROLE_PRECEDENCE.get(normalized_role)
        if caller_rank is None:
            raise HTTPException(status_code=401, detail="unauthorized")
        if caller_rank < required_rank:
            raise HTTPException(status_code=403, detail="forbidden")
        return normalized_role

    return _enforce_role


app.include_router(build_alerts_router(_require_role))


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


ANALYSIS_DB_PATH: Optional[str] = None

signal_repo = SqliteSignalRepository()
order_event_repo = SqliteOrderEventRepository(db_path=DEFAULT_DB_PATH)
canonical_execution_repo = SqliteCanonicalExecutionRepository(db_path=DEFAULT_DB_PATH)
analysis_run_repo = SqliteAnalysisRunRepository(db_path=DEFAULT_DB_PATH)
watchlist_repo = SqliteWatchlistRepository(db_path=DEFAULT_DB_PATH)


def _is_uuid4(value: str) -> bool:
    try:
        parsed = uuid.UUID(value)
    except (TypeError, ValueError, AttributeError):
        return False
    return parsed.version == 4


def _require_ingestion_run(ingestion_run_id: str) -> None:
    if not _is_uuid4(ingestion_run_id):
        raise HTTPException(status_code=422, detail="invalid_ingestion_run_id")
    if not analysis_run_repo.ingestion_run_exists(ingestion_run_id):
        raise HTTPException(status_code=422, detail="ingestion_run_not_found")


def _require_snapshot_ready(
    ingestion_run_id: str,
    *,
    symbols: list[str],
    timeframe: str = "D1",
) -> None:
    if not analysis_run_repo.ingestion_run_is_ready(
        ingestion_run_id,
        symbols=symbols,
        timeframe=timeframe,
    ):
        raise HTTPException(status_code=422, detail="ingestion_run_not_ready")


def _resolve_analysis_db_path() -> str:
    if ANALYSIS_DB_PATH:
        resolved = str(ANALYSIS_DB_PATH)
        logger.debug("Analysis DB path resolved via ANALYSIS_DB_PATH override: %s", resolved)
        return resolved

    repo_path = getattr(analysis_run_repo, "_db_path", None)
    if repo_path:
        resolved = str(repo_path)
        logger.debug("Analysis DB path resolved via analysis_run_repo._db_path: %s", resolved)
        return resolved

    resolved = str(DEFAULT_DB_PATH)
    logger.debug("Analysis DB path resolved via DEFAULT_DB_PATH fallback: %s", resolved)
    return resolved


def _run_snapshot_analysis(*args: Any, **kwargs: Any) -> List[Dict[str, Any]]:
    _require_engine_runtime_running()
    try:
        return run_watchlist_analysis(*args, **kwargs, snapshot_only=True)
    except SnapshotDataError as exc:
        logger.error("Snapshot data invalid: component=api error=%s", exc)
        raise HTTPException(status_code=422, detail="snapshot_data_invalid") from exc


def _normalize_for_hashing(value: Any) -> Any:
    if isinstance(value, float):
        return format(value, ".10g")
    if isinstance(value, (str, int, bool)) or value is None:
        return value
    if isinstance(value, dict):
        return {key: _normalize_for_hashing(val) for key, val in value.items()}
    if isinstance(value, (list, tuple)):
        return [_normalize_for_hashing(item) for item in value]
    return value


def _coerce_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _max_numeric(values: List[Optional[float]]) -> Optional[float]:
    numeric_values = [value for value in values if value is not None]
    return max(numeric_values) if numeric_values else None


def _build_ranked_symbol_results(
    signals: List[Dict[str, Any]],
    *,
    min_score: float,
) -> List[ScreenerSymbolResult]:
    setup_signals = []
    for signal in signals:
        if signal.get("stage") != "setup":
            continue
        score_value = _coerce_float(signal.get("score"))
        if (score_value or 0.0) < min_score:
            continue
        setup_signals.append(signal)

    by_symbol: Dict[str, List[Dict[str, Any]]] = {}
    for signal in setup_signals:
        symbol = signal.get("symbol", "")
        if not symbol:
            continue

        setup_info: Dict[str, Any] = {
            "strategy": signal.get("strategy"),
            "score": signal.get("score"),
            "signal_strength": signal.get("signal_strength"),
            "stage": signal.get("stage"),
            "confirmation_rule": signal.get("confirmation_rule"),
            "entry_zone": signal.get("entry_zone"),
            "timeframe": signal.get("timeframe"),
            "market_type": signal.get("market_type"),
        }
        by_symbol.setdefault(symbol, []).append(setup_info)

    symbol_results: List[ScreenerSymbolResult] = []
    for symbol, setups in by_symbol.items():
        symbol_results.append(
            ScreenerSymbolResult(
                symbol=symbol,
                score=_max_numeric([_coerce_float(setup.get("score")) for setup in setups]),
                signal_strength=_max_numeric(
                    [_coerce_float(setup.get("signal_strength")) for setup in setups]
                ),
                setups=setups,
            )
        )

    symbol_results.sort(
        key=lambda item: (
            -(item.score if item.score is not None else float("-inf")),
            -(item.signal_strength if item.signal_strength is not None else float("-inf")),
            item.symbol or "",
        )
    )
    return symbol_results


def _build_watchlist_ranked_results(
    signals: List[Dict[str, Any]],
    *,
    min_score: float,
) -> List[WatchlistExecutionRankedItem]:
    ranked_symbols = _build_ranked_symbol_results(signals, min_score=min_score)
    return [
        WatchlistExecutionRankedItem(
            rank=index,
            symbol=item.symbol,
            score=item.score,
            signal_strength=item.signal_strength,
            setups=item.setups,
        )
        for index, item in enumerate(ranked_symbols, start=1)
    ]


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


def get_registered_strategy_keys() -> List[str]:
    return run_registry_smoke()


def _strategy_display_name(strategy_key: str) -> str:
    display_names: Dict[str, str] = {
        "RSI2": "RSI2 Rebound",
        "TURTLE": "Turtle Breakout",
    }
    return display_names.get(strategy_key, strategy_key)


@app.get("/health")
def health(_: str = Depends(_require_role("read_only"))) -> Dict[str, str]:
    _assert_phase_13_read_only_endpoint("/health")
    return _runtime_health_payload()


@app.get("/health/engine")
def health_engine(_: str = Depends(_require_role("read_only"))) -> Dict[str, Any]:
    payload = _runtime_health_payload()
    mode = payload["mode"]
    ready = mode in {"ready", "running", "paused"}

    return {
        "subsystem": "engine",
        "status": payload["status"],
        "ready": ready,
        "mode": mode,
        "reason": payload["reason"],
        "checked_at": payload["checked_at"],
    }


@app.get("/health/data")
def health_data(_: str = Depends(_require_role("read_only"))) -> Dict[str, Any]:
    checked_at = _health_now()
    db_path = Path(_resolve_analysis_db_path())
    ready = db_path.exists()
    status: Literal["healthy", "unavailable"] = "healthy" if ready else "unavailable"
    reason = "data_source_available" if ready else "data_source_unavailable"

    return {
        "subsystem": "data",
        "status": status,
        "ready": ready,
        "reason": reason,
        "checked_at": checked_at.isoformat(),
    }


@app.get("/health/guards")
def health_guards(_: str = Depends(_require_role("read_only"))) -> Dict[str, Any]:
    checked_at = _health_now()
    guard_status = _build_compliance_guard_status_response()
    blocking = guard_status.compliance.blocking

    return {
        "subsystem": "guards",
        "status": "degraded" if blocking else "healthy",
        "ready": not blocking,
        "decision": guard_status.compliance.decision,
        "blocking": blocking,
        "guards": {
            "drawdown_guard": {
                "enabled": guard_status.guards.drawdown_guard.enabled,
                "blocking": guard_status.guards.drawdown_guard.blocking,
            },
            "daily_loss_guard": {
                "enabled": guard_status.guards.daily_loss_guard.enabled,
                "blocking": guard_status.guards.daily_loss_guard.blocking,
            },
            "kill_switch": {
                "active": guard_status.guards.kill_switch.active,
                "blocking": guard_status.guards.kill_switch.blocking,
            },
        },
        "checked_at": checked_at.isoformat(),
    }


def _runtime_health_payload() -> Dict[str, str]:
    payload = get_runtime_introspection_payload()
    snapshot: RuntimeHealthSnapshot = {
        "mode": payload["mode"],
        "updated_at": datetime.fromisoformat(payload["timestamps"]["updated_at"]),
    }
    checked_at = _health_now()
    evaluation = evaluate_runtime_health(snapshot, now=checked_at)

    return {
        "status": evaluation.status,
        "mode": payload["mode"],
        "reason": evaluation.reason,
        "checked_at": checked_at.isoformat(),
    }


def _health_now() -> datetime:
    return datetime.now(timezone.utc)


def _guard_decision(*, blocking: bool) -> Literal["allowing", "blocking"]:
    return "blocking" if blocking else "allowing"


def _read_bool_env(*names: str) -> bool | None:
    for name in names:
        raw_value = os.getenv(name)
        if raw_value is None:
            continue
        normalized = raw_value.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
    return None


def _read_float_env(*names: str) -> float | None:
    for name in names:
        raw_value = os.getenv(name)
        if raw_value is None:
            continue
        try:
            return float(raw_value)
        except (TypeError, ValueError):
            continue
    return None


def _load_compliance_guard_status_sources() -> tuple[dict[str, object], CompliancePortfolioState]:
    kill_switch_active = _read_bool_env(
        "CILLY_EXECUTION_KILL_SWITCH_ACTIVE",
        "execution.kill_switch.active",
    )
    drawdown_max_pct = _read_float_env(
        "CILLY_EXECUTION_DRAWDOWN_MAX_PCT",
        "execution.drawdown.max_pct",
    )
    daily_loss_max_abs = _read_float_env(
        "CILLY_EXECUTION_DAILY_LOSS_MAX_ABS",
        "execution.daily_loss.max_abs",
    )

    peak_equity = _read_float_env(
        "CILLY_PORTFOLIO_PEAK_EQUITY",
        "portfolio.peak_equity",
    )
    current_equity = _read_float_env(
        "CILLY_PORTFOLIO_CURRENT_EQUITY",
        "portfolio.current_equity",
    )
    start_of_day_equity = _read_float_env(
        "CILLY_PORTFOLIO_START_OF_DAY_EQUITY",
        "portfolio.start_of_day_equity",
    )

    guard_config: dict[str, object] = {
        "execution.kill_switch.active": kill_switch_active is True,
    }
    if drawdown_max_pct is not None:
        guard_config["execution.drawdown.max_pct"] = drawdown_max_pct
    if daily_loss_max_abs is not None:
        guard_config["execution.daily_loss.max_abs"] = daily_loss_max_abs

    portfolio_state = CompliancePortfolioState(
        peak_equity=peak_equity if peak_equity is not None else 0.0,
        current_equity=current_equity if current_equity is not None else 0.0,
        start_of_day_equity=start_of_day_equity,
    )
    return guard_config, portfolio_state


def _build_compliance_guard_status_response() -> ComplianceGuardStatusResponse:
    guard_config, portfolio_state = _load_compliance_guard_status_sources()

    drawdown_threshold = configured_drawdown_threshold(config=guard_config)
    drawdown_blocking = should_block_execution_for_drawdown(
        portfolio_state=portfolio_state,
        config=guard_config,
    )
    daily_loss_limit = configured_daily_loss_limit(config=guard_config)
    daily_loss_blocking = should_block_execution_for_daily_loss(
        portfolio_state=portfolio_state,
        config=guard_config,
    )
    kill_switch_is_active = is_kill_switch_active(config=guard_config)
    overall_blocking = drawdown_blocking or daily_loss_blocking or kill_switch_is_active

    return ComplianceGuardStatusResponse(
        compliance=ComplianceStatusResponse(
            blocking=overall_blocking,
            decision=_guard_decision(blocking=overall_blocking),
        ),
        guards=GuardStatusCollectionResponse(
            drawdown_guard=DrawdownGuardStatusResponse(
                enabled=drawdown_threshold is not None,
                blocking=drawdown_blocking,
                decision=_guard_decision(blocking=drawdown_blocking),
                threshold_pct=drawdown_threshold,
                current_drawdown_pct=portfolio_state.drawdown(),
            ),
            daily_loss_guard=DailyLossGuardStatusResponse(
                enabled=daily_loss_limit is not None,
                blocking=daily_loss_blocking,
                decision=_guard_decision(blocking=daily_loss_blocking),
                max_daily_loss_abs=daily_loss_limit,
                current_daily_loss_abs=portfolio_state.daily_loss(),
            ),
            kill_switch=KillSwitchStatusResponse(
                active=kill_switch_is_active,
                blocking=kill_switch_is_active,
                decision=_guard_decision(blocking=kill_switch_is_active),
            ),
        ),
    )


def _build_runtime_introspection_response() -> RuntimeIntrospectionResponse:
    payload = get_runtime_introspection_payload()
    payload.setdefault("extensions", [])
    return RuntimeIntrospectionResponse(**payload)


def _build_system_state_response() -> SystemStateResponse:
    payload = get_system_state_payload()
    payload["runtime"].setdefault("extensions", [])
    return SystemStateResponse(**payload)


@app.get("/compliance/guards/status", response_model=ComplianceGuardStatusResponse)
def read_compliance_guard_status(
    _: str = Depends(_require_role("read_only")),
) -> ComplianceGuardStatusResponse:
    return _build_compliance_guard_status_response()


@app.get("/runtime/introspection", response_model=RuntimeIntrospectionResponse)
def runtime_introspection(_: str = Depends(_require_role("read_only"))) -> RuntimeIntrospectionResponse:
    _assert_phase_13_read_only_endpoint("/runtime/introspection")
    return _build_runtime_introspection_response()


@app.get(
    "/system/state",
    response_model=SystemStateResponse,
    summary="System State",
    description="Read-only system runtime state for operator inspection.",
)
def system_state(_: str = Depends(_require_role("read_only"))) -> SystemStateResponse:
    return _build_system_state_response()


@app.post(
    "/execution/start",
    response_model=ExecutionControlResponse,
    summary="Start Execution",
    description="Ensure the engine runtime is in running state using the existing lifecycle start semantics.",
)
def start_execution(_: str = Depends(_require_role("owner"))) -> ExecutionControlResponse:
    try:
        state = start_engine_runtime()
    except LifecycleTransitionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return ExecutionControlResponse(state=state)


@app.post(
    "/execution/stop",
    response_model=ExecutionControlResponse,
    summary="Stop Execution",
    description="Stop the engine runtime using the existing lifecycle shutdown semantics.",
)
def stop_execution(_: str = Depends(_require_role("owner"))) -> ExecutionControlResponse:
    state = shutdown_engine_runtime()
    return ExecutionControlResponse(state=state)


@app.post(
    "/execution/pause",
    response_model=ExecutionControlResponse,
    summary="Pause Execution",
    description="Pause engine execution while preserving runtime ownership and introspection state.",
)
def pause_execution(_: str = Depends(_require_role("owner"))) -> ExecutionControlResponse:
    try:
        state = pause_engine_runtime()
    except LifecycleTransitionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return ExecutionControlResponse(state=state)


@app.post(
    "/execution/resume",
    response_model=ExecutionControlResponse,
    summary="Resume Execution",
    description="Resume engine execution after an operator pause.",
)
def resume_execution(_: str = Depends(_require_role("owner"))) -> ExecutionControlResponse:
    try:
        state = resume_engine_runtime()
    except LifecycleTransitionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return ExecutionControlResponse(state=state)


def _portfolio_position_response(
    position: PortfolioInspectionPosition,
) -> PortfolioPositionResponse:
    return PortfolioPositionResponse(
        symbol=position.symbol,
        size=position.size,
        average_price=position.average_price,
        unrealized_pnl=position.unrealized_pnl,
        strategy_id=position.strategy_id,
    )


@app.get(
    "/portfolio/positions",
    response_model=PortfolioPositionsResponse,
    summary="Portfolio Positions",
    description="Read-only current portfolio positions for operator inspection.",
)
def read_portfolio_positions(
    _: str = Depends(_require_role("read_only")),
) -> PortfolioPositionsResponse:
    state = load_portfolio_state_from_env()
    items = [_portfolio_position_response(position) for position in state.positions]
    return PortfolioPositionsResponse(positions=items, total=len(items))


@app.get(
    "/paper/account",
    response_model=PaperAccountReadResponse,
    summary="Paper Account",
    description="Read-only paper account state for deterministic operator inspection.",
)
def read_paper_account(
    _: str = Depends(_require_role("read_only")),
) -> PaperAccountReadResponse:
    return PaperAccountReadResponse(
        account=_build_paper_account_state(
            paper_trades=canonical_execution_repo.list_trades(
                limit=1_000_000,
                offset=0,
            ),
            paper_positions=_build_trading_core_positions(
                strategy_id=None,
                symbol=None,
                position_id=None,
            ),
        ),
    )


@app.get("/paper/trades", response_model=PaperTradesReadResponse)
def read_paper_trades(
    strategy_id: Optional[str] = Query(default=None),
    symbol: Optional[str] = Query(default=None),
    position_id: Optional[str] = Query(default=None),
    trade_id: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    _: str = Depends(_require_role("read_only")),
) -> PaperTradesReadResponse:
    params = PaperTradesReadQuery(
        strategy_id=strategy_id,
        symbol=symbol,
        position_id=position_id,
        trade_id=trade_id,
        limit=limit,
        offset=offset,
    )
    if params.trade_id:
        trade = canonical_execution_repo.get_trade(params.trade_id)
        all_items = [] if trade is None else [trade]
        if params.strategy_id is not None:
            all_items = [item for item in all_items if item.strategy_id == params.strategy_id]
        if params.symbol is not None:
            all_items = [item for item in all_items if item.symbol == params.symbol]
        if params.position_id is not None:
            all_items = [item for item in all_items if item.position_id == params.position_id]
    else:
        all_items = canonical_execution_repo.list_trades(
            strategy_id=params.strategy_id,
            symbol=params.symbol,
            position_id=params.position_id,
            limit=1_000_000,
            offset=0,
        )

    page, total = _paginate_items(all_items, limit=params.limit, offset=params.offset)
    return PaperTradesReadResponse(
        items=page,
        limit=params.limit,
        offset=params.offset,
        total=total,
    )


@app.get("/paper/positions", response_model=PaperPositionsReadResponse)
def read_paper_positions(
    strategy_id: Optional[str] = Query(default=None),
    symbol: Optional[str] = Query(default=None),
    position_id: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    _: str = Depends(_require_role("read_only")),
) -> PaperPositionsReadResponse:
    params = PaperPositionsReadQuery(
        strategy_id=strategy_id,
        symbol=symbol,
        position_id=position_id,
        limit=limit,
        offset=offset,
    )
    all_items = _build_trading_core_positions(
        strategy_id=params.strategy_id,
        symbol=params.symbol,
        position_id=params.position_id,
    )

    page, total = _paginate_items(all_items, limit=params.limit, offset=params.offset)
    return PaperPositionsReadResponse(
        items=page,
        limit=params.limit,
        offset=params.offset,
        total=total,
    )


@app.get("/paper/reconciliation", response_model=PaperReconciliationReadResponse)
def read_paper_reconciliation(
    _: str = Depends(_require_role("read_only")),
) -> PaperReconciliationReadResponse:
    orders = canonical_execution_repo.list_orders(limit=1_000_000, offset=0)
    execution_events = canonical_execution_repo.list_execution_events(limit=1_000_000, offset=0)
    trades = canonical_execution_repo.list_trades(limit=1_000_000, offset=0)
    positions = _build_trading_core_positions(strategy_id=None, symbol=None, position_id=None)
    account = _build_paper_account_state(paper_trades=trades, paper_positions=positions)
    mismatch_items = _build_paper_reconciliation_mismatches(
        orders=orders,
        execution_events=execution_events,
        trades=trades,
        positions=positions,
        account=account,
    )
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


def _require_engine_runtime_running() -> None:
    if not ENGINE_RUNTIME_GUARD_ACTIVE:
        return

    runtime_state = get_runtime_controller().state
    if runtime_state != "running":
        raise HTTPException(
            status_code=ENGINE_RUNTIME_NOT_RUNNING_STATUS,
            detail={
                "code": ENGINE_RUNTIME_NOT_RUNNING_CODE,
                "state": runtime_state,
            },
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


def _paginate_items(items: list[Any], *, limit: int, offset: int) -> tuple[list[Any], int]:
    total = len(items)
    return items[offset : offset + limit], total


def _resolve_paper_starting_cash() -> Decimal:
    raw_value = os.getenv("CILLY_PAPER_ACCOUNT_STARTING_CASH", "100000")
    try:
        value = Decimal(raw_value)
    except Exception as exc:
        raise HTTPException(status_code=500, detail="paper_account_starting_cash_invalid") from exc
    if value < Decimal("0"):
        raise HTTPException(status_code=500, detail="paper_account_starting_cash_invalid")
    return value


def _sum_decimals(values: list[Decimal]) -> Decimal:
    return sum(values, Decimal("0"))


def _build_paper_account_state(
    *,
    paper_trades: list[Trade],
    paper_positions: list[Position],
) -> PaperAccountStateResponse:
    starting_cash = _resolve_paper_starting_cash()
    realized_pnl = _sum_decimals([trade.realized_pnl or Decimal("0") for trade in paper_trades])
    unrealized_pnl = _sum_decimals([trade.unrealized_pnl or Decimal("0") for trade in paper_trades])
    total_pnl = realized_pnl + unrealized_pnl
    cash = starting_cash + realized_pnl
    equity = cash + unrealized_pnl
    open_positions = sum(1 for position in paper_positions if position.status == "open")
    open_trades = sum(1 for trade in paper_trades if trade.status == "open")
    closed_trades = sum(1 for trade in paper_trades if trade.status == "closed")

    as_of_candidates = [
        value
        for value in [
            *[trade.closed_at for trade in paper_trades],
            *[trade.opened_at for trade in paper_trades],
        ]
        if value is not None
    ]
    as_of = max(as_of_candidates) if as_of_candidates else None

    return PaperAccountStateResponse(
        starting_cash=starting_cash,
        cash=cash,
        equity=equity,
        realized_pnl=realized_pnl,
        unrealized_pnl=unrealized_pnl,
        total_pnl=total_pnl,
        open_positions=open_positions,
        open_trades=open_trades,
        closed_trades=closed_trades,
        as_of=as_of,
    )


def _build_paper_reconciliation_mismatches(
    *,
    orders: list[Order],
    execution_events: list[ExecutionEvent],
    trades: list[Trade],
    positions: list[Position],
    account: PaperAccountStateResponse,
) -> list[PaperReconciliationMismatchResponse]:
    mismatches: list[PaperReconciliationMismatchResponse] = []
    orders_by_id = {order.order_id: order for order in orders}
    execution_events_by_id = {event.event_id: event for event in execution_events}
    trades_by_id = {trade.trade_id: trade for trade in trades}
    positions_by_id = {position.position_id: position for position in positions}

    for event in execution_events:
        if event.order_id not in orders_by_id:
            mismatches.append(
                PaperReconciliationMismatchResponse(
                    code="execution_event_order_missing",
                    message=f"execution event references unknown order_id={event.order_id}",
                    entity_type="execution_event",
                    entity_id=event.event_id,
                )
            )

    for trade in trades:
        if trade.position_id not in positions_by_id:
            mismatches.append(
                PaperReconciliationMismatchResponse(
                    code="trade_position_missing",
                    message=f"trade references unknown position_id={trade.position_id}",
                    entity_type="trade",
                    entity_id=trade.trade_id,
                )
            )

        for order_id in [*trade.opening_order_ids, *trade.closing_order_ids]:
            order = orders_by_id.get(order_id)
            if order is None:
                mismatches.append(
                    PaperReconciliationMismatchResponse(
                        code="trade_order_missing",
                        message=f"trade references unknown order_id={order_id}",
                        entity_type="trade",
                        entity_id=trade.trade_id,
                    )
                )
                continue
            if order.trade_id is not None and order.trade_id != trade.trade_id:
                mismatches.append(
                    PaperReconciliationMismatchResponse(
                        code="trade_order_trade_mismatch",
                        message=f"order trade_id={order.trade_id} does not match trade_id={trade.trade_id}",
                        entity_type="trade",
                        entity_id=trade.trade_id,
                    )
                )

        for event_id in trade.execution_event_ids:
            event = execution_events_by_id.get(event_id)
            if event is None:
                mismatches.append(
                    PaperReconciliationMismatchResponse(
                        code="trade_execution_event_missing",
                        message=f"trade references unknown execution_event_id={event_id}",
                        entity_type="trade",
                        entity_id=trade.trade_id,
                    )
                )
                continue
            if event.trade_id is not None and event.trade_id != trade.trade_id:
                mismatches.append(
                    PaperReconciliationMismatchResponse(
                        code="trade_execution_event_trade_mismatch",
                        message=f"execution event trade_id={event.trade_id} does not match trade_id={trade.trade_id}",
                        entity_type="trade",
                        entity_id=trade.trade_id,
                    )
                )

    for position in positions:
        for trade_id in position.trade_ids:
            trade = trades_by_id.get(trade_id)
            if trade is None:
                mismatches.append(
                    PaperReconciliationMismatchResponse(
                        code="position_trade_missing",
                        message=f"position references unknown trade_id={trade_id}",
                        entity_type="position",
                        entity_id=position.position_id,
                    )
                )
                continue
            if trade.position_id != position.position_id:
                mismatches.append(
                    PaperReconciliationMismatchResponse(
                        code="position_trade_position_mismatch",
                        message=f"trade position_id={trade.position_id} does not match position_id={position.position_id}",
                        entity_type="position",
                        entity_id=position.position_id,
                    )
                )

        for order_id in position.order_ids:
            order = orders_by_id.get(order_id)
            if order is None:
                mismatches.append(
                    PaperReconciliationMismatchResponse(
                        code="position_order_missing",
                        message=f"position references unknown order_id={order_id}",
                        entity_type="position",
                        entity_id=position.position_id,
                    )
                )
                continue
            if order.position_id is not None and order.position_id != position.position_id:
                mismatches.append(
                    PaperReconciliationMismatchResponse(
                        code="position_order_position_mismatch",
                        message=f"order position_id={order.position_id} does not match position_id={position.position_id}",
                        entity_type="position",
                        entity_id=position.position_id,
                    )
                )

        for event_id in position.execution_event_ids:
            event = execution_events_by_id.get(event_id)
            if event is None:
                mismatches.append(
                    PaperReconciliationMismatchResponse(
                        code="position_execution_event_missing",
                        message=f"position references unknown execution_event_id={event_id}",
                        entity_type="position",
                        entity_id=position.position_id,
                    )
                )
                continue
            if event.position_id is not None and event.position_id != position.position_id:
                mismatches.append(
                    PaperReconciliationMismatchResponse(
                        code="position_execution_event_position_mismatch",
                        message=f"execution event position_id={event.position_id} does not match position_id={position.position_id}",
                        entity_type="position",
                        entity_id=position.position_id,
                    )
                )

    expected_open_trades = sum(1 for trade in trades if trade.status == "open")
    expected_closed_trades = sum(1 for trade in trades if trade.status == "closed")
    expected_open_positions = sum(1 for position in positions if position.status == "open")
    expected_realized_pnl = _sum_decimals([trade.realized_pnl or Decimal("0") for trade in trades])
    expected_unrealized_pnl = _sum_decimals([trade.unrealized_pnl or Decimal("0") for trade in trades])
    expected_total_pnl = expected_realized_pnl + expected_unrealized_pnl
    expected_cash = account.starting_cash + expected_realized_pnl
    expected_equity = expected_cash + expected_unrealized_pnl

    if account.open_trades != expected_open_trades:
        mismatches.append(
            PaperReconciliationMismatchResponse(
                code="paper_account_open_trades_mismatch",
                message=f"open_trades={account.open_trades} expected={expected_open_trades}",
                entity_type="paper_account",
                entity_id="account",
            )
        )
    if account.closed_trades != expected_closed_trades:
        mismatches.append(
            PaperReconciliationMismatchResponse(
                code="paper_account_closed_trades_mismatch",
                message=f"closed_trades={account.closed_trades} expected={expected_closed_trades}",
                entity_type="paper_account",
                entity_id="account",
            )
        )
    if account.open_positions != expected_open_positions:
        mismatches.append(
            PaperReconciliationMismatchResponse(
                code="paper_account_open_positions_mismatch",
                message=f"open_positions={account.open_positions} expected={expected_open_positions}",
                entity_type="paper_account",
                entity_id="account",
            )
        )
    if account.realized_pnl != expected_realized_pnl:
        mismatches.append(
            PaperReconciliationMismatchResponse(
                code="paper_account_realized_pnl_mismatch",
                message=f"realized_pnl={account.realized_pnl} expected={expected_realized_pnl}",
                entity_type="paper_account",
                entity_id="account",
            )
        )
    if account.unrealized_pnl != expected_unrealized_pnl:
        mismatches.append(
            PaperReconciliationMismatchResponse(
                code="paper_account_unrealized_pnl_mismatch",
                message=f"unrealized_pnl={account.unrealized_pnl} expected={expected_unrealized_pnl}",
                entity_type="paper_account",
                entity_id="account",
            )
        )
    if account.total_pnl != expected_total_pnl:
        mismatches.append(
            PaperReconciliationMismatchResponse(
                code="paper_account_total_pnl_mismatch",
                message=f"total_pnl={account.total_pnl} expected={expected_total_pnl}",
                entity_type="paper_account",
                entity_id="account",
            )
        )
    if account.cash != expected_cash:
        mismatches.append(
            PaperReconciliationMismatchResponse(
                code="paper_account_cash_mismatch",
                message=f"cash={account.cash} expected={expected_cash}",
                entity_type="paper_account",
                entity_id="account",
            )
        )
    if account.equity != expected_equity:
        mismatches.append(
            PaperReconciliationMismatchResponse(
                code="paper_account_equity_mismatch",
                message=f"equity={account.equity} expected={expected_equity}",
                entity_type="paper_account",
                entity_id="account",
            )
        )

    return sorted(
        mismatches,
        key=lambda mismatch: (
            mismatch.code,
            mismatch.entity_type or "",
            mismatch.entity_id or "",
            mismatch.message,
        ),
    )


def _weighted_average(*, values: list[tuple[Decimal, Decimal]]) -> Optional[Decimal]:
    total_weight = _sum_decimals([weight for _, weight in values])
    if total_weight <= Decimal("0"):
        return None
    weighted_sum = _sum_decimals([value * weight for value, weight in values])
    return weighted_sum / total_weight


def _build_trading_core_positions(
    *,
    strategy_id: Optional[str] = None,
    symbol: Optional[str] = None,
    position_id: Optional[str] = None,
) -> list[Position]:
    trades = canonical_execution_repo.list_trades(
        strategy_id=strategy_id,
        symbol=symbol,
        position_id=position_id,
        limit=1_000_000,
        offset=0,
    )
    if not trades:
        return []

    orders = canonical_execution_repo.list_orders(
        strategy_id=strategy_id,
        symbol=symbol,
        limit=1_000_000,
        offset=0,
    )
    events = canonical_execution_repo.list_execution_events(
        strategy_id=strategy_id,
        symbol=symbol,
        limit=1_000_000,
        offset=0,
    )

    target_position_ids = {trade.position_id for trade in trades}
    orders_by_position: dict[str, list[Order]] = {}
    events_by_position: dict[str, list[ExecutionEvent]] = {}
    trades_by_position: dict[str, list[Trade]] = {}

    for trade in trades:
        trades_by_position.setdefault(trade.position_id, []).append(trade)
    for order in orders:
        if order.position_id is None or order.position_id not in target_position_ids:
            continue
        orders_by_position.setdefault(order.position_id, []).append(order)
    for event in events:
        if event.position_id is None or event.position_id not in target_position_ids:
            continue
        events_by_position.setdefault(event.position_id, []).append(event)

    positions: list[Position] = []
    for current_position_id in sorted(target_position_ids):
        position_trades = trades_by_position.get(current_position_id, [])
        if not position_trades:
            continue

        position_orders = orders_by_position.get(current_position_id, [])
        position_events = events_by_position.get(current_position_id, [])

        strategy_ids = {trade.strategy_id for trade in position_trades}
        symbols = {trade.symbol for trade in position_trades}
        directions = {trade.direction for trade in position_trades}
        if len(strategy_ids) != 1 or len(symbols) != 1 or len(directions) != 1:
            raise HTTPException(status_code=500, detail="trading_core_position_inconsistent")

        quantity_opened = _sum_decimals([trade.quantity_opened for trade in position_trades])
        quantity_closed = _sum_decimals([trade.quantity_closed for trade in position_trades])
        net_quantity = quantity_opened - quantity_closed

        opened_at = min(trade.opened_at for trade in position_trades)
        closed_at_candidates = [trade.closed_at for trade in position_trades if trade.closed_at is not None]

        if quantity_opened == Decimal("0") and quantity_closed == Decimal("0"):
            status: Literal["flat", "open", "closed"] = "flat"
        elif net_quantity == Decimal("0"):
            status = "closed"
        else:
            status = "open"

        average_entry_price = _weighted_average(
            values=[(trade.average_entry_price, trade.quantity_opened) for trade in position_trades]
        ) or Decimal("0")

        average_exit_price = _weighted_average(
            values=[
                (trade.average_exit_price, trade.quantity_closed)
                for trade in position_trades
                if trade.average_exit_price is not None and trade.quantity_closed > Decimal("0")
            ]
        )

        realized_pnl_values = [trade.realized_pnl for trade in position_trades if trade.realized_pnl is not None]
        realized_pnl = _sum_decimals(realized_pnl_values) if realized_pnl_values else None

        order_ids = sorted(
            set(
                [order.order_id for order in position_orders]
                + [order_id for trade in position_trades for order_id in trade.opening_order_ids]
                + [order_id for trade in position_trades for order_id in trade.closing_order_ids]
            )
        )
        execution_event_ids = sorted(
            set(
                [event.event_id for event in position_events]
                + [event_id for trade in position_trades for event_id in trade.execution_event_ids]
            )
        )
        trade_ids = sorted([trade.trade_id for trade in position_trades])

        positions.append(
            Position.model_validate(
                {
                    "position_id": current_position_id,
                    "strategy_id": next(iter(strategy_ids)),
                    "symbol": next(iter(symbols)),
                    "direction": next(iter(directions)),
                    "status": status,
                    "opened_at": opened_at,
                    "closed_at": max(closed_at_candidates) if status == "closed" and closed_at_candidates else None,
                    "quantity_opened": quantity_opened,
                    "quantity_closed": quantity_closed,
                    "net_quantity": net_quantity,
                    "average_entry_price": average_entry_price,
                    "average_exit_price": average_exit_price,
                    "realized_pnl": realized_pnl if status == "closed" else None,
                    "order_ids": order_ids,
                    "execution_event_ids": execution_event_ids,
                    "trade_ids": trade_ids,
                }
            )
        )

    return sorted(
        positions,
        key=lambda item: (
            item.opened_at,
            item.position_id,
        ),
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


def _iter_journal_artifact_files() -> List[tuple[str, Path]]:
    if not JOURNAL_ARTIFACTS_ROOT.exists() or not JOURNAL_ARTIFACTS_ROOT.is_dir():
        return []

    artifact_files: List[tuple[str, Path]] = []
    for run_dir in JOURNAL_ARTIFACTS_ROOT.iterdir():
        if not run_dir.is_dir():
            continue
        run_id = run_dir.name
        for artifact_file in run_dir.iterdir():
            if artifact_file.is_file():
                artifact_files.append((run_id, artifact_file))
    return artifact_files


def _resolve_journal_artifact_path(run_id: str, artifact_name: str) -> Path:
    if "/" in run_id or "\\" in run_id:
        raise HTTPException(status_code=404, detail="journal_artifact_not_found")
    if "/" in artifact_name or "\\" in artifact_name:
        raise HTTPException(status_code=404, detail="journal_artifact_not_found")

    candidate = JOURNAL_ARTIFACTS_ROOT / run_id / artifact_name
    try:
        resolved = candidate.resolve(strict=True)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="journal_artifact_not_found") from None

    expected_parent = (JOURNAL_ARTIFACTS_ROOT / run_id).resolve()
    if resolved.parent != expected_parent or not resolved.is_file():
        raise HTTPException(status_code=404, detail="journal_artifact_not_found")

    return resolved


def _read_journal_artifact_content(path: Path) -> tuple[Literal["json", "text"], Any]:
    raw_text = path.read_text(encoding="utf-8")
    try:
        return "json", json.loads(raw_text)
    except json.JSONDecodeError:
        return "text", raw_text


def _extract_trace_entries(content: Any) -> tuple[Optional[str], List[Dict[str, Any]]]:
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


def _extract_decision_card_candidates(content: Any) -> List[Dict[str, Any]]:
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


def _matches_decision_card_review_state(
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


def _decision_card_item_sort_key(
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


def _build_decision_card_inspection_items(
    params: DecisionCardInspectionQuery,
) -> List[DecisionCardInspectionItemResponse]:
    items: List[DecisionCardInspectionItemResponse] = []
    seen: set[tuple[str, str, str, str]] = set()

    for run_id, artifact_path in _iter_journal_artifact_files():
        if params.run_id is not None and run_id != params.run_id:
            continue

        content_type, content = _read_journal_artifact_content(artifact_path)
        if content_type != "json":
            continue

        for candidate in _extract_decision_card_candidates(content):
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
            if not _matches_decision_card_review_state(card.qualification.state, params.review_state):
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

    items.sort(key=lambda item: _decision_card_item_sort_key(item, sort=params.sort))
    return items


def _to_watchlist_response(watchlist: Any) -> WatchlistResponse:
    return WatchlistResponse(
        watchlist_id=watchlist.watchlist_id,
        name=watchlist.name,
        symbols=list(watchlist.symbols),
    )


@app.get("/ingestion/runs", response_model=List[IngestionRunItemResponse])
def read_ingestion_runs(
    limit: int = Depends(_get_ingestion_runs_limit),
    _: str = Depends(_require_role("read_only")),
) -> List[IngestionRunItemResponse]:
    rows = analysis_run_repo.list_ingestion_runs(limit=limit)
    return [IngestionRunItemResponse(**row) for row in rows]


@app.post("/watchlists", response_model=WatchlistResponse)
def create_watchlist(
    req: WatchlistCreateRequest,
    _: str = Depends(_require_role("operator")),
) -> WatchlistResponse:
    try:
        watchlist = watchlist_repo.create_watchlist(
            watchlist_id=req.watchlist_id,
            name=req.name,
            symbols=req.symbols,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return _to_watchlist_response(watchlist)


@app.get("/watchlists", response_model=WatchlistListResponse)
def read_watchlists(
    _: str = Depends(_require_role("read_only")),
) -> WatchlistListResponse:
    items = [_to_watchlist_response(watchlist) for watchlist in watchlist_repo.list_watchlists()]
    return WatchlistListResponse(items=items, total=len(items))


@app.get("/watchlists/{watchlist_id}", response_model=WatchlistResponse)
def read_watchlist(
    watchlist_id: str,
    _: str = Depends(_require_role("read_only")),
) -> WatchlistResponse:
    watchlist = watchlist_repo.get_watchlist(watchlist_id)
    if watchlist is None:
        raise HTTPException(status_code=404, detail="watchlist_not_found")
    return _to_watchlist_response(watchlist)


@app.put("/watchlists/{watchlist_id}", response_model=WatchlistResponse)
def update_watchlist(
    watchlist_id: str,
    req: WatchlistPayload,
    _: str = Depends(_require_role("operator")),
) -> WatchlistResponse:
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
    return _to_watchlist_response(watchlist)


@app.delete("/watchlists/{watchlist_id}", response_model=WatchlistDeleteResponse)
def delete_watchlist(
    watchlist_id: str,
    _: str = Depends(_require_role("operator")),
) -> WatchlistDeleteResponse:
    deleted = watchlist_repo.delete_watchlist(watchlist_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="watchlist_not_found")
    return WatchlistDeleteResponse(watchlist_id=watchlist_id, deleted=True)


@app.post(
    "/watchlists/{watchlist_id}/execute",
    response_model=WatchlistExecutionResponse,
)
def execute_watchlist(
    watchlist_id: str,
    req: WatchlistExecutionRequest,
    _: str = Depends(_require_role("operator")),
) -> WatchlistExecutionResponse:
    watchlist = watchlist_repo.get_watchlist(watchlist_id)
    if watchlist is None:
        raise HTTPException(status_code=404, detail="watchlist_not_found")

    _require_ingestion_run(req.ingestion_run_id)

    strategies = create_registered_strategies()
    strategy_names = sorted(
        getattr(strategy, "name", strategy.__class__.__name__) for strategy in strategies
    )
    run_request_payload: Dict[str, Any] = {
        "workflow": "watchlist_execution",
        "ingestion_run_id": req.ingestion_run_id,
        "watchlist_id": watchlist.watchlist_id,
        "symbols": list(watchlist.symbols),
        "strategies": strategy_names,
        "market_type": req.market_type,
        "lookback_days": req.lookback_days,
        "min_score": _normalize_for_hashing(req.min_score),
    }
    computed_run_id = compute_analysis_run_id(run_request_payload)

    existing_run = analysis_run_repo.get_run(computed_run_id)
    if existing_run is not None:
        logger.info(
            "Watchlist execution reused: component=control_plane analysis_run_id=%s ingestion_run_id=%s watchlist_id=%s",
            computed_run_id,
            existing_run["ingestion_run_id"],
            watchlist.watchlist_id,
        )
        _require_ingestion_run(existing_run["ingestion_run_id"])
        return WatchlistExecutionResponse(**existing_run["result"])

    engine_config = EngineConfig(
        timeframe="D1",
        lookback_days=req.lookback_days,
        market_type=req.market_type,
        data_source="yahoo" if req.market_type == "stock" else "binance",
    )
    symbol_failures: List[Dict[str, str]] = []
    signals = _run_snapshot_analysis(
        symbols=list(watchlist.symbols),
        strategies=strategies,
        engine_config=engine_config,
        strategy_configs=default_strategy_configs,
        signal_repo=signal_repo,
        ingestion_run_id=req.ingestion_run_id,
        db_path=_resolve_analysis_db_path(),
        run_id=computed_run_id,
        symbol_failures=symbol_failures,
        isolate_symbol_failures=True,
    )

    ranked_results = _build_watchlist_ranked_results(signals, min_score=req.min_score)
    response_payload = {
        "analysis_run_id": computed_run_id,
        "ingestion_run_id": req.ingestion_run_id,
        "watchlist_id": watchlist.watchlist_id,
        "watchlist_name": watchlist.name,
        "market_type": req.market_type,
        "ranked_results": [item.model_dump() for item in ranked_results],
        "failures": [
            WatchlistExecutionFailure(**failure).model_dump() for failure in symbol_failures
        ],
    }

    persisted_run = analysis_run_repo.save_run(
        analysis_run_id=computed_run_id,
        ingestion_run_id=req.ingestion_run_id,
        request_payload=run_request_payload,
        result_payload=response_payload,
    )

    if persisted_run is None:
        return WatchlistExecutionResponse(**response_payload)
    return WatchlistExecutionResponse(**persisted_run["result"])


@app.get("/journal/artifacts", response_model=JournalArtifactListResponse)
def read_journal_artifacts(
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    _: str = Depends(_require_role("read_only")),
) -> JournalArtifactListResponse:
    files = _iter_journal_artifact_files()
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


@app.get(
    "/journal/artifacts/{run_id}/{artifact_name}",
    response_model=JournalArtifactContentResponse,
)
def read_journal_artifact_content(
    run_id: str,
    artifact_name: str,
    _: str = Depends(_require_role("read_only")),
) -> JournalArtifactContentResponse:
    path = _resolve_journal_artifact_path(run_id=run_id, artifact_name=artifact_name)
    content_type, content = _read_journal_artifact_content(path)
    return JournalArtifactContentResponse(
        run_id=run_id,
        artifact_name=artifact_name,
        content_type=content_type,
        content=content,
    )


@app.get("/journal/decision-trace", response_model=DecisionTraceResponse)
def read_decision_trace(
    run_id: str = Query(..., min_length=1),
    artifact_name: str = Query(default="audit.json", min_length=1),
    _: str = Depends(_require_role("read_only")),
) -> DecisionTraceResponse:
    path = _resolve_journal_artifact_path(run_id=run_id, artifact_name=artifact_name)
    _, content = _read_journal_artifact_content(path)
    trace_id, entries = _extract_trace_entries(content)
    return DecisionTraceResponse(
        run_id=run_id,
        artifact_name=artifact_name,
        trace_id=trace_id,
        entries=entries,
        total_entries=len(entries),
    )


@app.get(
    "/decision-cards",
    response_model=DecisionCardInspectionResponse,
    summary="Decision Card Inspection",
    description=(
        "Read-only inspection surface for decision-card outputs with deterministic "
        "ordering, filtering, and explanation fields."
    ),
)
def read_decision_cards(
    params: DecisionCardInspectionQuery = Depends(_get_decision_card_inspection_query),
    _: str = Depends(_require_role("read_only")),
) -> DecisionCardInspectionResponse:
    all_items = _build_decision_card_inspection_items(params)
    page, total = _paginate_items(all_items, limit=params.limit, offset=params.offset)
    return DecisionCardInspectionResponse(
        items=page,
        limit=params.limit,
        offset=params.offset,
        total=total,
    )


@app.get("/strategies", response_model=StrategyMetadataResponse)
def read_strategies(_: str = Depends(_require_role("read_only"))) -> StrategyMetadataResponse:
    items: List[StrategyMetadataItemResponse] = []
    for strategy_key in get_registered_strategy_keys():
        default_config = default_strategy_configs.get(strategy_key, {})
        items.append(
            StrategyMetadataItemResponse(
                strategy=strategy_key,
                display_name=_strategy_display_name(strategy_key),
                default_config_keys=sorted(list(default_config.keys())),
                has_default_config=bool(default_config),
            )
        )
    return StrategyMetadataResponse(items=items, total=len(items))


@app.get("/signals", response_model=SignalReadResponseDTO)
def read_signals(
    params: SignalsReadQuery = Depends(_get_signals_query),
    _: str = Depends(_require_role("read_only")),
) -> SignalReadResponseDTO:
    items, total = signal_repo.read_signals(
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


@app.get("/execution/orders", response_model=ExecutionOrdersReadResponse)
def read_execution_orders(
    params: ExecutionOrdersReadQuery = Depends(_get_execution_orders_query),
    _: str = Depends(_require_role("read_only")),
) -> ExecutionOrdersReadResponse:
    items, total = order_event_repo.read_order_events(
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


@app.get("/trading-core/orders", response_model=TradingCoreOrdersReadResponse)
def read_trading_core_orders(
    params: TradingCoreOrdersReadQuery = Depends(_get_trading_core_orders_query),
    _: str = Depends(_require_role("read_only")),
) -> TradingCoreOrdersReadResponse:
    if params.order_id:
        order = canonical_execution_repo.get_order(params.order_id)
        all_items = [] if order is None else [order]
        if params.strategy_id is not None:
            all_items = [item for item in all_items if item.strategy_id == params.strategy_id]
        if params.symbol is not None:
            all_items = [item for item in all_items if item.symbol == params.symbol]
    else:
        all_items = canonical_execution_repo.list_orders(
            strategy_id=params.strategy_id,
            symbol=params.symbol,
            limit=1_000_000,
            offset=0,
        )

    page, total = _paginate_items(all_items, limit=params.limit, offset=params.offset)
    return TradingCoreOrdersReadResponse(
        items=page,
        limit=params.limit,
        offset=params.offset,
        total=total,
    )


@app.get(
    "/trading-core/execution-events",
    response_model=TradingCoreExecutionEventsReadResponse,
)
def read_trading_core_execution_events(
    params: TradingCoreExecutionEventsReadQuery = Depends(_get_trading_core_execution_events_query),
    _: str = Depends(_require_role("read_only")),
) -> TradingCoreExecutionEventsReadResponse:
    all_items = canonical_execution_repo.list_execution_events(
        strategy_id=params.strategy_id,
        symbol=params.symbol,
        order_id=params.order_id,
        trade_id=params.trade_id,
        limit=1_000_000,
        offset=0,
    )
    page, total = _paginate_items(all_items, limit=params.limit, offset=params.offset)
    return TradingCoreExecutionEventsReadResponse(
        items=page,
        limit=params.limit,
        offset=params.offset,
        total=total,
    )


@app.get("/trading-core/trades", response_model=TradingCoreTradesReadResponse)
def read_trading_core_trades(
    params: TradingCoreTradesReadQuery = Depends(_get_trading_core_trades_query),
    _: str = Depends(_require_role("read_only")),
) -> TradingCoreTradesReadResponse:
    if params.trade_id:
        trade = canonical_execution_repo.get_trade(params.trade_id)
        all_items = [] if trade is None else [trade]
        if params.strategy_id is not None:
            all_items = [item for item in all_items if item.strategy_id == params.strategy_id]
        if params.symbol is not None:
            all_items = [item for item in all_items if item.symbol == params.symbol]
        if params.position_id is not None:
            all_items = [item for item in all_items if item.position_id == params.position_id]
    else:
        all_items = canonical_execution_repo.list_trades(
            strategy_id=params.strategy_id,
            symbol=params.symbol,
            position_id=params.position_id,
            limit=1_000_000,
            offset=0,
        )

    page, total = _paginate_items(all_items, limit=params.limit, offset=params.offset)
    return TradingCoreTradesReadResponse(
        items=page,
        limit=params.limit,
        offset=params.offset,
        total=total,
    )


@app.get("/trading-core/positions", response_model=TradingCorePositionsReadResponse)
def read_trading_core_positions(
    params: TradingCorePositionsReadQuery = Depends(_get_trading_core_positions_query),
    _: str = Depends(_require_role("read_only")),
) -> TradingCorePositionsReadResponse:
    all_items = _build_trading_core_positions(
        strategy_id=params.strategy_id,
        symbol=params.symbol,
        position_id=params.position_id,
    )
    page, total = _paginate_items(all_items, limit=params.limit, offset=params.offset)
    return TradingCorePositionsReadResponse(
        items=page,
        limit=params.limit,
        offset=params.offset,
        total=total,
    )


@app.get("/screener/v2/results", response_model=ScreenerResultsResponse)
def read_screener_results(
    params: ScreenerResultsQuery = Depends(_get_screener_results_query),
    _: str = Depends(_require_role("read_only")),
) -> ScreenerResultsResponse:
    items, total = signal_repo.read_screener_results(
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


@app.post("/strategy/analyze", response_model=StrategyAnalyzeResponse)
def analyze_strategy(
    req: StrategyAnalyzeRequest,
    _: str = Depends(_require_role("operator")),
) -> StrategyAnalyzeResponse:
    logger.info(
        "Strategy analyze start: symbol=%s strategy=%s market_type=%s lookback_days=%s",
        req.symbol,
        req.strategy,
        req.market_type,
        req.lookback_days,
    )

    _require_ingestion_run(req.ingestion_run_id)
    _require_snapshot_ready(req.ingestion_run_id, symbols=[req.symbol], timeframe="D1")

    strategy_name = req.strategy.upper()
    try:
        strategy = create_strategy(strategy_name)
    except StrategyNotRegisteredError:
        logger.warning("Unknown strategy requested: %s", req.strategy)
        raise HTTPException(status_code=400, detail=f"Unknown strategy: {req.strategy}") from None

    engine_config = EngineConfig(
        timeframe="D1",
        lookback_days=req.lookback_days,
        market_type=req.market_type,
        data_source="yahoo" if req.market_type == "stock" else "binance",
    )

    if req.presets or req.preset_ids or req.preset_id:
        results_by_preset: Dict[str, List[Dict[str, Any]]] = {}
        preset_results: List[PresetAnalysisResult] = []

        if req.presets:
            preset_inputs = [(preset.id, preset.params) for preset in req.presets]
        else:
            preset_ids = req.preset_ids if req.preset_ids is not None else [req.preset_id]
            preset_inputs = [(preset_id, None) for preset_id in preset_ids]

        for preset_id, preset_params in preset_inputs:
            effective_config = default_strategy_configs.get(strategy_name, {}).copy()
            if req.presets:
                if preset_params:
                    effective_config.update(preset_params)
            elif req.strategy_config:
                effective_config.update(req.strategy_config)

            strategy_configs = {strategy_name: effective_config}

            signals = _run_snapshot_analysis(
                symbols=[req.symbol],
                strategies=[strategy],
                engine_config=engine_config,
                strategy_configs=strategy_configs,
                signal_repo=signal_repo,
                ingestion_run_id=req.ingestion_run_id,
                db_path=_resolve_analysis_db_path(),
            )

            filtered_signals = [
                s
                for s in signals
                if s.get("symbol") == req.symbol and s.get("strategy") == strategy_name
            ]

            results_by_preset[preset_id] = filtered_signals
            preset_results.append(
                PresetAnalysisResult(preset_id=preset_id, signals=filtered_signals)
            )

        return StrategyAnalyzeResponse(
            symbol=req.symbol,
            strategy=strategy_name,
            results_by_preset=results_by_preset,
            preset_results=preset_results,
        )

    effective_config = default_strategy_configs.get(strategy_name, {}).copy()
    if req.strategy_config:
        effective_config.update(req.strategy_config)

    strategy_configs = {strategy_name: effective_config}

    signals = _run_snapshot_analysis(
        symbols=[req.symbol],
        strategies=[strategy],
        engine_config=engine_config,
        strategy_configs=strategy_configs,
        signal_repo=signal_repo,
        ingestion_run_id=req.ingestion_run_id,
        db_path=_resolve_analysis_db_path(),
    )

    filtered_signals = [
        s for s in signals if s.get("symbol") == req.symbol and s.get("strategy") == strategy_name
    ]

    return StrategyAnalyzeResponse(
        symbol=req.symbol,
        strategy=strategy_name,
        signals=filtered_signals,
    )


@app.post("/analysis/run", response_model=ManualAnalysisResponse)
def manual_analysis(
    req: ManualAnalysisRequest,
    _: str = Depends(_require_role("operator")),
) -> ManualAnalysisResponse:
    strategy_name = req.strategy.upper()
    run_request_payload: Dict[str, Any] = {
        "ingestion_run_id": req.ingestion_run_id,
        "symbol": req.symbol,
        "strategy": strategy_name,
        "market_type": req.market_type,
        "lookback_days": req.lookback_days,
    }
    if req.strategy_config is not None:
        run_request_payload["strategy_config"] = _normalize_for_hashing(req.strategy_config)

    computed_run_id = compute_analysis_run_id(run_request_payload)

    existing_run = analysis_run_repo.get_run(computed_run_id)
    if existing_run is not None:
        logger.info(
            "Operator analysis run reused: component=control_plane analysis_run_id=%s ingestion_run_id=%s symbol=%s strategy=%s",
            computed_run_id,
            existing_run["ingestion_run_id"],
            req.symbol,
            strategy_name,
        )
        _require_ingestion_run(existing_run["ingestion_run_id"])
        return ManualAnalysisResponse(**existing_run["result"])

    _require_ingestion_run(req.ingestion_run_id)
    _require_snapshot_ready(req.ingestion_run_id, symbols=[req.symbol], timeframe="D1")
    try:
        strategy = create_strategy(strategy_name)
    except StrategyNotRegisteredError:
        logger.warning("Unknown strategy requested: %s", req.strategy)
        raise HTTPException(status_code=400, detail=f"Unknown strategy: {req.strategy}") from None

    engine_config = EngineConfig(
        timeframe="D1",
        lookback_days=req.lookback_days,
        market_type=req.market_type,
        data_source="yahoo" if req.market_type == "stock" else "binance",
    )

    effective_config = default_strategy_configs.get(strategy_name, {}).copy()
    if req.strategy_config:
        effective_config.update(req.strategy_config)

    strategy_configs = {strategy_name: effective_config}

    signals = trigger_operator_analysis_run(
        execute=_run_snapshot_analysis,
        symbol=req.symbol,
        strategy=strategy_name,
        ingestion_run_id=req.ingestion_run_id,
        execute_kwargs={
            "symbols": [req.symbol],
            "strategies": [strategy],
            "engine_config": engine_config,
            "strategy_configs": strategy_configs,
            "signal_repo": signal_repo,
            "ingestion_run_id": req.ingestion_run_id,
            "db_path": _resolve_analysis_db_path(),
            "run_id": computed_run_id,
        },
    )

    filtered_signals = [
        s for s in signals if s.get("symbol") == req.symbol and s.get("strategy") == strategy_name
    ]

    response_payload = {
        "analysis_run_id": computed_run_id,
        "ingestion_run_id": req.ingestion_run_id,
        "symbol": req.symbol,
        "strategy": strategy_name,
        "signals": filtered_signals,
    }

    persisted_run = analysis_run_repo.save_run(
        analysis_run_id=computed_run_id,
        ingestion_run_id=req.ingestion_run_id,
        request_payload=run_request_payload,
        result_payload=response_payload,
    )

    if persisted_run is None:
        return ManualAnalysisResponse(**response_payload)
    return ManualAnalysisResponse(**persisted_run["result"])


@app.post("/screener/basic", response_model=ScreenerResponse)
def basic_screener(
    req: ScreenerRequest,
    _: str = Depends(_require_role("operator")),
) -> ScreenerResponse:
    _require_ingestion_run(req.ingestion_run_id)
    if req.symbols is None or len(req.symbols) == 0:
        if req.market_type == "stock":
            symbols = ["AAPL", "MSFT", "NVDA", "META", "TSLA"]
        else:
            symbols = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "XRP/USDT"]
    else:
        symbols = req.symbols

    _require_snapshot_ready(req.ingestion_run_id, symbols=symbols, timeframe="D1")

    engine_config = EngineConfig(
        timeframe="D1",
        lookback_days=req.lookback_days,
        market_type=req.market_type,
        data_source="yahoo" if req.market_type == "stock" else "binance",
    )

    strategies = create_registered_strategies()
    strategy_configs = default_strategy_configs

    signals = _run_snapshot_analysis(
        symbols=symbols,
        strategies=strategies,
        engine_config=engine_config,
        strategy_configs=strategy_configs,
        signal_repo=signal_repo,
        ingestion_run_id=req.ingestion_run_id,
        db_path=_resolve_analysis_db_path(),
    )
    symbol_results = _build_ranked_symbol_results(signals, min_score=req.min_score)

    return ScreenerResponse(
        market_type=req.market_type,
        symbols=symbol_results,
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)

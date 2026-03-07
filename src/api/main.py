"""
FastAPI-Anwendung für die Cilly Trading Engine (MVP).

Enthaltene Endpunkte:
- GET /health
- POST /strategy/analyze
- POST /screener/basic

Strategien:
- RSI2 (Rebound)
- TURTLE (Breakout)
"""

from __future__ import annotations

import logging
import os
import json
import uuid
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field, model_validator

from cilly_trading.engine.analysis import trigger_operator_analysis_run
from engine.compliance.daily_loss_guard import (
    configured_daily_loss_limit,
    should_block_execution_for_daily_loss,
)
from engine.compliance.drawdown_guard import (
    configured_drawdown_threshold,
    should_block_execution_for_drawdown,
)
from engine.compliance.kill_switch import is_kill_switch_active
from engine.portfolio import PortfolioState
from .config import SIGNALS_READ_MAX_LIMIT
from cilly_trading.db import DEFAULT_DB_PATH
from cilly_trading.engine.core import (
    EngineConfig,
    compute_analysis_run_id,
    run_watchlist_analysis,
)
from cilly_trading.engine.data import SnapshotDataError
from cilly_trading.engine.health.evaluator import (
    RuntimeHealthSnapshot,
    evaluate_runtime_health,
)
from cilly_trading.engine.runtime_controller import (
    LifecycleTransitionError,
    get_runtime_controller,
    shutdown_engine_runtime,
    start_engine_runtime,
)
from .order_events_sqlite import SqliteOrderEventRepository
from cilly_trading.engine.runtime_introspection import get_runtime_introspection_payload
from cilly_trading.engine.runtime_state import get_system_state_payload
from cilly_trading.models import SignalReadItemDTO, SignalReadResponseDTO
from cilly_trading.repositories.analysis_runs_sqlite import SqliteAnalysisRunRepository
from cilly_trading.repositories.signals_sqlite import SqliteSignalRepository
from cilly_trading.strategies.registry import (
    StrategyNotRegisteredError,
    create_registered_strategies,
    create_strategy,
    initialize_default_registry,
    run_registry_smoke,
)


def configure_logging() -> None:
    """
    Zentrale Logging-Konfiguration für die Cilly Trading Engine.
    Wird einmalig beim App-Start ausgeführt.

    Hinweis: Uvicorn mit --reload kann Module mehrfach importieren.
    Daher verhindern wir doppelte Handler.
    """
    log_level = os.getenv("CILLY_LOG_LEVEL", "INFO").upper()

    root_logger = logging.getLogger()
    if root_logger.handlers:
        # Logging ist bereits konfiguriert (z. B. durch Reload / anderes Setup)
        return

    logging.basicConfig(
        level=log_level,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )


configure_logging()
logger = logging.getLogger(__name__)


# --- Pydantic-Modelle für Requests/Responses ---


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


class SignalsReadQuery(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    symbol: Optional[str] = Field(default=None)
    strategy: Optional[str] = Field(default=None)
    preset: Optional[str] = Field(default=None)
    ingestion_run_id: Optional[str] = Field(default=None)
    from_: Optional[datetime] = Field(default=None, alias="from")
    to: Optional[datetime] = Field(default=None, alias="to")
    start: Optional[datetime] = Field(default=None)
    end: Optional[datetime] = Field(default=None)
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


class ScreenerResultsQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    strategy: str
    timeframe: str
    min_score: Optional[float] = Field(default=None, ge=0.0)


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


app = FastAPI(
    title="Cilly Trading Engine API",
    version="0.1.0",
    description="MVP-API für die Cilly Trading Engine (RSI2 & Turtle, D1, SQLite).",
)

UI_DIRECTORY = Path(__file__).resolve().parent.parent / "ui"
JOURNAL_ARTIFACTS_ROOT = Path(__file__).resolve().parents[2] / "runs" / "phase6"
app.mount("/ui", StaticFiles(directory=UI_DIRECTORY, html=True), name="ui")

logger.info("Cilly Trading Engine API starting up")

ENGINE_RUNTIME_NOT_RUNNING_STATUS = 503
ENGINE_RUNTIME_NOT_RUNNING_CODE = "engine_runtime_not_running"
ENGINE_RUNTIME_GUARD_ACTIVE = False
PHASE_13_READ_ONLY_ENDPOINTS = frozenset({"/health", "/runtime/introspection"})


def _assert_phase_13_read_only_endpoint(endpoint_path: str) -> None:
    assert endpoint_path in PHASE_13_READ_ONLY_ENDPOINTS


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
analysis_run_repo = SqliteAnalysisRunRepository(db_path=DEFAULT_DB_PATH)


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
def health() -> Dict[str, str]:
    _assert_phase_13_read_only_endpoint("/health")
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


def _load_compliance_guard_status_sources() -> tuple[dict[str, object], PortfolioState]:
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

    portfolio_state = PortfolioState(
        peak_equity=peak_equity if peak_equity is not None else 0.0,
        current_equity=current_equity if current_equity is not None else 0.0,
        start_of_day_equity=start_of_day_equity,
    )
    return guard_config, portfolio_state


@app.get("/compliance/guards/status", response_model=ComplianceGuardStatusResponse)
def read_compliance_guard_status() -> ComplianceGuardStatusResponse:
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


@app.get("/runtime/introspection", response_model=RuntimeIntrospectionResponse)
def runtime_introspection() -> RuntimeIntrospectionResponse:
    _assert_phase_13_read_only_endpoint("/runtime/introspection")
    payload = get_runtime_introspection_payload()
    payload.setdefault("extensions", [])
    return RuntimeIntrospectionResponse(**payload)


@app.get(
    "/system/state",
    response_model=SystemStateResponse,
    summary="System State",
    description="Read-only system runtime state for operator inspection.",
)
def system_state() -> SystemStateResponse:
    payload = get_system_state_payload()
    payload["runtime"].setdefault("extensions", [])
    return SystemStateResponse(**payload)


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
    symbol: Optional[str] = Query(default=None),
    strategy: Optional[str] = Query(default=None),
    preset: Optional[str] = Query(default=None),
    ingestion_run_id: Optional[str] = Query(default=None),
    from_: Optional[datetime] = Query(default=None, alias="from"),
    to: Optional[datetime] = Query(default=None, alias="to"),
    start: Optional[datetime] = Query(default=None),
    end: Optional[datetime] = Query(default=None),
    sort: Literal["created_at_asc", "created_at_desc"] = Query(default="created_at_desc"),
    limit: int = Query(default=50, ge=1, le=SIGNALS_READ_MAX_LIMIT),
    offset: int = Query(default=0, ge=0),
) -> SignalsReadQuery:
    if start is not None and from_ is not None and start != from_:
        raise HTTPException(status_code=422, detail="start conflicts with from")
    if end is not None and to is not None and end != to:
        raise HTTPException(status_code=422, detail="end conflicts with to")

    resolved_from = start if start is not None else from_
    resolved_to = end if end is not None else to

    if resolved_from is not None and resolved_to is not None and resolved_from > resolved_to:
        raise HTTPException(status_code=422, detail="from must be less than or equal to to")

    return SignalsReadQuery(
        symbol=symbol,
        strategy=strategy,
        preset=preset,
        ingestion_run_id=ingestion_run_id,
        from_=resolved_from,
        to=resolved_to,
        start=start,
        end=end,
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
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> ExecutionOrdersReadQuery:
    return ExecutionOrdersReadQuery(
        symbol=symbol,
        strategy=strategy,
        run_id=run_id,
        limit=limit,
        offset=offset,
    )


def _get_screener_results_query(
    strategy: str = Query(...),
    timeframe: str = Query(...),
    min_score: Optional[float] = Query(default=None, ge=0.0),
) -> ScreenerResultsQuery:
    return ScreenerResultsQuery(
        strategy=strategy,
        timeframe=timeframe,
        min_score=min_score,
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


@app.get("/ingestion/runs", response_model=List[IngestionRunItemResponse])
def read_ingestion_runs(limit: int = Depends(_get_ingestion_runs_limit)) -> List[IngestionRunItemResponse]:
    rows = analysis_run_repo.list_ingestion_runs(limit=limit)
    return [IngestionRunItemResponse(**row) for row in rows]


@app.get("/journal/artifacts", response_model=JournalArtifactListResponse)
def read_journal_artifacts(
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
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
def read_journal_artifact_content(run_id: str, artifact_name: str) -> JournalArtifactContentResponse:
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


@app.get("/strategies", response_model=StrategyMetadataResponse)
def read_strategies() -> StrategyMetadataResponse:
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
def read_signals(params: SignalsReadQuery = Depends(_get_signals_query)) -> SignalReadResponseDTO:
    effective_from = params.from_ or params.start
    effective_to = params.to or params.end
    items, total = signal_repo.read_signals(
        symbol=params.symbol,
        strategy=params.strategy,
        preset=params.preset,
        ingestion_run_id=params.ingestion_run_id,
        from_=effective_from,
        to=effective_to,
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
) -> ExecutionOrdersReadResponse:
    items, total = order_event_repo.read_order_events(
        symbol=params.symbol,
        strategy=params.strategy,
        run_id=params.run_id,
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


@app.get("/screener/v2/results", response_model=ScreenerResultsResponse)
def read_screener_results(
    params: ScreenerResultsQuery = Depends(_get_screener_results_query),
) -> ScreenerResultsResponse:
    items = signal_repo.read_screener_results(
        strategy=params.strategy,
        timeframe=params.timeframe,
        min_score=params.min_score,
    )
    response_items = [ScreenerResultItem(**item) for item in items]

    return ScreenerResultsResponse(
        items=response_items,
        total=len(response_items),
    )


@app.post("/strategy/analyze", response_model=StrategyAnalyzeResponse)
def analyze_strategy(req: StrategyAnalyzeRequest) -> StrategyAnalyzeResponse:
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
def manual_analysis(req: ManualAnalysisRequest) -> ManualAnalysisResponse:
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

    analysis_run_repo.save_run(
        analysis_run_id=computed_run_id,
        ingestion_run_id=req.ingestion_run_id,
        request_payload=run_request_payload,
        result_payload=response_payload,
    )

    return ManualAnalysisResponse(**response_payload)


@app.post("/screener/basic", response_model=ScreenerResponse)
def basic_screener(req: ScreenerRequest) -> ScreenerResponse:
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

    def _coerce_float(value: Any) -> Optional[float]:
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    setup_signals = []
    for s in signals:
        if s.get("stage") != "setup":
            continue
        score_value = _coerce_float(s.get("score"))
        if (score_value or 0.0) < req.min_score:
            continue
        setup_signals.append(s)

    by_symbol: Dict[str, List[Dict[str, Any]]] = {}
    for s in setup_signals:
        sym = s.get("symbol", "")
        if not sym:
            continue

        setup_info: Dict[str, Any] = {
            "strategy": s.get("strategy"),
            "score": s.get("score"),
            "signal_strength": s.get("signal_strength"),
            "stage": s.get("stage"),
            "confirmation_rule": s.get("confirmation_rule"),
            "entry_zone": s.get("entry_zone"),
            "timeframe": s.get("timeframe"),
            "market_type": s.get("market_type"),
        }

        by_symbol.setdefault(sym, []).append(setup_info)

    def _max_numeric(values: List[Optional[float]]) -> Optional[float]:
        numeric_values = [value for value in values if value is not None]
        return max(numeric_values) if numeric_values else None

    symbol_results = []
    for symbol, setups in by_symbol.items():
        score = _max_numeric([_coerce_float(s.get("score")) for s in setups])
        signal_strength = _max_numeric([_coerce_float(s.get("signal_strength")) for s in setups])
        symbol_results.append(
            ScreenerSymbolResult(
                symbol=symbol,
                score=score,
                signal_strength=signal_strength,
                setups=setups,
            )
        )

    def _sorting_key(item: ScreenerSymbolResult) -> tuple:
        score = item.score if item.score is not None else float("-inf")
        signal_strength = (
            item.signal_strength if item.signal_strength is not None else float("-inf")
        )
        symbol = item.symbol or ""
        return (-score, -signal_strength, symbol)

    symbol_results.sort(key=_sorting_key)

    return ScreenerResponse(
        market_type=req.market_type,
        symbols=symbol_results,
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)

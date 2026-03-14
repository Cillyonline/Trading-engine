from __future__ import annotations

from typing import Any, Mapping, Literal

from pydantic import BaseModel, ConfigDict, Field

from cilly_trading.models import EntryZoneDTO, SignalReadResponseDTO

PHASE_39_CHART_SCHEMA_VERSION = "phase39.chart-data.v1"


class ChartContractConstraints(BaseModel):
    model_config = ConfigDict(extra="forbid")

    snapshot_first: Literal[True] = True
    live_data_allowed: Literal[False] = False
    market_data_product: Literal[False] = False
    chart_route_added: Literal[False] = False


class ChartContractSource(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_type: Literal["analysis_run", "watchlist_execution", "signal_log"]
    endpoint: Literal["/analysis/run", "/watchlists/{watchlist_id}/execute", "/signals"]
    reuse: Literal["existing_runtime_api"] = "existing_runtime_api"
    authority: Literal["authoritative", "fallback_only"]
    snapshot_binding: Literal["explicit_ingestion_run_id", "not_available_in_source"]
    order_basis: Literal["response_order", "rank_ascending"]


class ChartContractContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    runtime_surface: Literal["/ui"] = "/ui"
    analysis_run_id: str | None = None
    ingestion_run_id: str | None = None
    watchlist_id: str | None = None
    watchlist_name: str | None = None
    symbol: str | None = None
    strategy: str | None = None
    market_type: str | None = None


class ChartContractSetup(BaseModel):
    model_config = ConfigDict(extra="forbid")

    strategy: str | None = None
    score: float | None = None
    signal_strength: float | None = None
    stage: str | None = None
    timeframe: str | None = None
    market_type: str | None = None
    confirmation_rule: str | None = None
    entry_zone: EntryZoneDTO | None = None


class ChartContractPoint(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sequence: int = Field(..., ge=1)
    symbol: str
    strategy: str | None = None
    stage: str | None = None
    score: float | None = None
    signal_strength: float | None = None
    rank: int | None = None
    recorded_at: str | None = None
    timeframe: str | None = None
    market_type: str | None = None
    data_source: str | None = None
    confirmation_rule: str | None = None
    entry_zone: EntryZoneDTO | None = None
    setups: list[ChartContractSetup] = Field(default_factory=list)


class ChartContractFailure(BaseModel):
    model_config = ConfigDict(extra="forbid")

    symbol: str
    code: str
    detail: str


class RuntimeChartContract(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["phase39.chart-data.v1"] = PHASE_39_CHART_SCHEMA_VERSION
    contract_scope: Literal["runtime_visual_analysis"] = "runtime_visual_analysis"
    constraints: ChartContractConstraints = Field(default_factory=ChartContractConstraints)
    source: ChartContractSource
    context: ChartContractContext
    points: list[ChartContractPoint]
    failures: list[ChartContractFailure] = Field(default_factory=list)


class _ManualAnalysisSignal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    symbol: str
    strategy: str
    score: float
    timestamp: str
    stage: str
    timeframe: str
    market_type: str
    data_source: str
    entry_zone: EntryZoneDTO | None = None
    confirmation_rule: str | None = None


class ManualAnalysisChartSource(BaseModel):
    model_config = ConfigDict(extra="forbid")

    analysis_run_id: str
    ingestion_run_id: str
    symbol: str
    strategy: str
    signals: list[_ManualAnalysisSignal]


class _WatchlistExecutionRankedItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rank: int = Field(..., ge=1)
    symbol: str
    score: float | None = None
    signal_strength: float | None = None
    setups: list[dict[str, Any]] = Field(default_factory=list)


class _WatchlistExecutionFailure(BaseModel):
    model_config = ConfigDict(extra="forbid")

    symbol: str
    code: str
    detail: str


class WatchlistExecutionChartSource(BaseModel):
    model_config = ConfigDict(extra="forbid")

    analysis_run_id: str
    ingestion_run_id: str
    watchlist_id: str
    watchlist_name: str
    market_type: str
    ranked_results: list[_WatchlistExecutionRankedItem]
    failures: list[_WatchlistExecutionFailure] = Field(default_factory=list)


def _project_setup(payload: Mapping[str, Any]) -> ChartContractSetup:
    return ChartContractSetup(
        strategy=payload.get("strategy"),
        score=payload.get("score"),
        signal_strength=payload.get("signal_strength"),
        stage=payload.get("stage"),
        timeframe=payload.get("timeframe"),
        market_type=payload.get("market_type"),
        confirmation_rule=payload.get("confirmation_rule"),
        entry_zone=payload.get("entry_zone"),
    )


def build_analysis_run_chart_contract(
    payload: Mapping[str, Any] | ManualAnalysisChartSource,
) -> RuntimeChartContract:
    source_payload = ManualAnalysisChartSource.model_validate(payload)
    points = [
        ChartContractPoint(
            sequence=index,
            symbol=signal.symbol,
            strategy=signal.strategy,
            stage=signal.stage,
            score=signal.score,
            recorded_at=signal.timestamp,
            timeframe=signal.timeframe,
            market_type=signal.market_type,
            data_source=signal.data_source,
            confirmation_rule=signal.confirmation_rule,
            entry_zone=signal.entry_zone,
        )
        for index, signal in enumerate(source_payload.signals, start=1)
    ]
    return RuntimeChartContract(
        source=ChartContractSource(
            source_type="analysis_run",
            endpoint="/analysis/run",
            authority="authoritative",
            snapshot_binding="explicit_ingestion_run_id",
            order_basis="response_order",
        ),
        context=ChartContractContext(
            analysis_run_id=source_payload.analysis_run_id,
            ingestion_run_id=source_payload.ingestion_run_id,
            symbol=source_payload.symbol,
            strategy=source_payload.strategy,
        ),
        points=points,
    )


def build_watchlist_execution_chart_contract(
    payload: Mapping[str, Any] | WatchlistExecutionChartSource,
) -> RuntimeChartContract:
    source_payload = WatchlistExecutionChartSource.model_validate(payload)
    points = [
        ChartContractPoint(
            sequence=index,
            symbol=item.symbol,
            score=item.score,
            signal_strength=item.signal_strength,
            rank=item.rank,
            market_type=source_payload.market_type,
            setups=[_project_setup(setup) for setup in item.setups],
        )
        for index, item in enumerate(source_payload.ranked_results, start=1)
    ]
    failures = [
        ChartContractFailure(symbol=item.symbol, code=item.code, detail=item.detail)
        for item in source_payload.failures
    ]
    return RuntimeChartContract(
        source=ChartContractSource(
            source_type="watchlist_execution",
            endpoint="/watchlists/{watchlist_id}/execute",
            authority="authoritative",
            snapshot_binding="explicit_ingestion_run_id",
            order_basis="rank_ascending",
        ),
        context=ChartContractContext(
            analysis_run_id=source_payload.analysis_run_id,
            ingestion_run_id=source_payload.ingestion_run_id,
            watchlist_id=source_payload.watchlist_id,
            watchlist_name=source_payload.watchlist_name,
            market_type=source_payload.market_type,
        ),
        points=points,
        failures=failures,
    )


def build_signal_log_chart_contract(
    payload: Mapping[str, Any] | SignalReadResponseDTO,
) -> RuntimeChartContract:
    source_payload = SignalReadResponseDTO.model_validate(payload)
    points = [
        ChartContractPoint(
            sequence=index,
            symbol=item.symbol,
            strategy=item.strategy,
            stage=item.stage,
            score=item.score,
            recorded_at=item.created_at,
            timeframe=item.timeframe,
            market_type=item.market_type,
            data_source=item.data_source,
            confirmation_rule=item.confirmation_rule,
            entry_zone=item.entry_zone,
        )
        for index, item in enumerate(source_payload.items, start=1)
    ]
    return RuntimeChartContract(
        source=ChartContractSource(
            source_type="signal_log",
            endpoint="/signals",
            authority="fallback_only",
            snapshot_binding="not_available_in_source",
            order_basis="response_order",
        ),
        context=ChartContractContext(),
        points=points,
    )


def validate_runtime_chart_contract(
    payload: Mapping[str, Any] | RuntimeChartContract,
) -> RuntimeChartContract:
    return RuntimeChartContract.model_validate(payload)


__all__ = (
    "PHASE_39_CHART_SCHEMA_VERSION",
    "RuntimeChartContract",
    "build_analysis_run_chart_contract",
    "build_watchlist_execution_chart_contract",
    "build_signal_log_chart_contract",
    "validate_runtime_chart_contract",
)

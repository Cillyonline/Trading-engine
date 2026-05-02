from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, TYPE_CHECKING

from fastapi import HTTPException

from cilly_trading.engine.core import EngineConfig, compute_analysis_run_id
from cilly_trading.repositories import AnalysisRunRepository, SignalRepository, WatchlistRepository
from cilly_trading.strategies.registry import StrategyNotRegisteredError, run_registry_smoke

from ..models import (
    ManualAnalysisRequest,
    ManualAnalysisResponse,
    PresetAnalysisResult,
    ScreenerRequest,
    ScreenerResponse,
    ScreenerSymbolResult,
    StrategyAnalyzeRequest,
    StrategyAnalyzeResponse,
    StrategyMetadataItemResponse,
    StrategyMetadataResponse,
    WatchlistExecutionFailure,
    WatchlistExecutionRankedItem,
    WatchlistExecutionRequest,
    WatchlistExecutionResponse,
    WatchlistResponse,
)

logger = logging.getLogger(__name__)


@dataclass
class AnalysisServiceDependencies:
    analysis_run_repo: AnalysisRunRepository
    signal_repo: SignalRepository
    watchlist_repo: WatchlistRepository
    default_strategy_configs: Dict[str, Dict[str, Any]]
    require_ingestion_run: Callable[[str], None]
    require_snapshot_ready: Callable[..., None]
    run_snapshot_analysis: Callable[..., List[Dict[str, Any]]]
    resolve_analysis_db_path: Callable[[], str]
    create_strategy: Callable[[str], Any]
    create_registered_strategies: Callable[[], List[Any]]
    trigger_operator_analysis_run: Callable[..., List[Dict[str, Any]]]


def is_uuid4(value: str) -> bool:
    try:
        parsed = uuid.UUID(value)
    except (TypeError, ValueError, AttributeError):
        return False
    return parsed.version == 4


def require_ingestion_run(*, ingestion_run_id: str, analysis_run_repo: Any) -> None:
    if not is_uuid4(ingestion_run_id):
        raise HTTPException(status_code=422, detail="invalid_ingestion_run_id")
    if not analysis_run_repo.ingestion_run_exists(ingestion_run_id):
        raise HTTPException(status_code=422, detail="ingestion_run_not_found")


def require_snapshot_ready(
    *,
    ingestion_run_id: str,
    analysis_run_repo: Any,
    symbols: list[str],
    timeframe: str = "D1",
) -> None:
    if not analysis_run_repo.ingestion_run_is_ready(
        ingestion_run_id,
        symbols=symbols,
        timeframe=timeframe,
    ):
        raise HTTPException(status_code=422, detail="ingestion_run_not_ready")


def normalize_for_hashing(value: Any) -> Any:
    if isinstance(value, float):
        return format(value, ".10g")
    if isinstance(value, (str, int, bool)) or value is None:
        return value
    if isinstance(value, dict):
        return {key: normalize_for_hashing(val) for key, val in value.items()}
    if isinstance(value, (list, tuple)):
        return [normalize_for_hashing(item) for item in value]
    return value


def coerce_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def max_numeric(values: List[Optional[float]]) -> Optional[float]:
    numeric_values = [value for value in values if value is not None]
    return max(numeric_values) if numeric_values else None


def build_ranked_symbol_results(
    signals: List[Dict[str, Any]],
    *,
    min_score: float,
) -> List[ScreenerSymbolResult]:
    setup_signals = []
    for signal in signals:
        if signal.get("stage") != "setup":
            continue
        score_value = coerce_float(signal.get("score"))
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
                score=max_numeric([coerce_float(setup.get("score")) for setup in setups]),
                signal_strength=max_numeric(
                    [coerce_float(setup.get("signal_strength")) for setup in setups]
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


def build_watchlist_ranked_results(
    signals: List[Dict[str, Any]],
    *,
    min_score: float,
) -> List[WatchlistExecutionRankedItem]:
    ranked_symbols = build_ranked_symbol_results(signals, min_score=min_score)
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


def get_registered_strategy_keys() -> List[str]:
    return run_registry_smoke()


def strategy_display_name(strategy_key: str) -> str:
    display_names: Dict[str, str] = {
        "RSI2": "RSI2 Rebound",
        "TURTLE": "Turtle Breakout",
    }
    return display_names.get(strategy_key, strategy_key)


def build_strategy_metadata_response(
    *,
    default_strategy_configs: Dict[str, Dict[str, Any]],
) -> StrategyMetadataResponse:
    items: List[StrategyMetadataItemResponse] = []
    for strategy_key in get_registered_strategy_keys():
        default_config = default_strategy_configs.get(strategy_key, {})
        items.append(
            StrategyMetadataItemResponse(
                strategy=strategy_key,
                display_name=strategy_display_name(strategy_key),
                default_config_keys=sorted(list(default_config.keys())),
                has_default_config=bool(default_config),
            )
        )
    return StrategyMetadataResponse(items=items, total=len(items))


def analyze_strategy(
    *,
    req: StrategyAnalyzeRequest,
    deps: AnalysisServiceDependencies,
) -> StrategyAnalyzeResponse:
    logger.info(
        "Strategy analyze start: symbol=%s strategy=%s market_type=%s lookback_days=%s",
        req.symbol,
        req.strategy,
        req.market_type,
        req.lookback_days,
    )

    deps.require_ingestion_run(req.ingestion_run_id)
    deps.require_snapshot_ready(req.ingestion_run_id, symbols=[req.symbol], timeframe="D1")

    strategy_name = req.strategy.upper()
    try:
        strategy = deps.create_strategy(strategy_name)
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
            effective_config = deps.default_strategy_configs.get(strategy_name, {}).copy()
            if req.presets:
                if preset_params:
                    effective_config.update(preset_params)
            elif req.strategy_config:
                effective_config.update(req.strategy_config)

            strategy_configs = {strategy_name: effective_config}

            signals = deps.run_snapshot_analysis(
                symbols=[req.symbol],
                strategies=[strategy],
                engine_config=engine_config,
                strategy_configs=strategy_configs,
                signal_repo=deps.signal_repo,
                ingestion_run_id=req.ingestion_run_id,
                db_path=deps.resolve_analysis_db_path(),
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

    effective_config = deps.default_strategy_configs.get(strategy_name, {}).copy()
    if req.strategy_config:
        effective_config.update(req.strategy_config)

    strategy_configs = {strategy_name: effective_config}

    signals = deps.run_snapshot_analysis(
        symbols=[req.symbol],
        strategies=[strategy],
        engine_config=engine_config,
        strategy_configs=strategy_configs,
        signal_repo=deps.signal_repo,
        ingestion_run_id=req.ingestion_run_id,
        db_path=deps.resolve_analysis_db_path(),
    )

    filtered_signals = [
        s for s in signals if s.get("symbol") == req.symbol and s.get("strategy") == strategy_name
    ]

    return StrategyAnalyzeResponse(
        symbol=req.symbol,
        strategy=strategy_name,
        signals=filtered_signals,
    )


def manual_analysis(
    *,
    req: ManualAnalysisRequest,
    deps: AnalysisServiceDependencies,
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
        run_request_payload["strategy_config"] = normalize_for_hashing(req.strategy_config)

    computed_run_id = compute_analysis_run_id(run_request_payload)

    existing_run = deps.analysis_run_repo.get_run(computed_run_id)
    if existing_run is not None:
        logger.info(
            "Operator analysis run reused: component=control_plane analysis_run_id=%s ingestion_run_id=%s symbol=%s strategy=%s",
            computed_run_id,
            existing_run["ingestion_run_id"],
            req.symbol,
            strategy_name,
        )
        deps.require_ingestion_run(existing_run["ingestion_run_id"])
        return ManualAnalysisResponse(**existing_run["result"])

    deps.require_ingestion_run(req.ingestion_run_id)
    deps.require_snapshot_ready(req.ingestion_run_id, symbols=[req.symbol], timeframe="D1")
    try:
        strategy = deps.create_strategy(strategy_name)
    except StrategyNotRegisteredError:
        logger.warning("Unknown strategy requested: %s", req.strategy)
        raise HTTPException(status_code=400, detail=f"Unknown strategy: {req.strategy}") from None

    engine_config = EngineConfig(
        timeframe="D1",
        lookback_days=req.lookback_days,
        market_type=req.market_type,
        data_source="yahoo" if req.market_type == "stock" else "binance",
    )

    effective_config = deps.default_strategy_configs.get(strategy_name, {}).copy()
    if req.strategy_config:
        effective_config.update(req.strategy_config)

    strategy_configs = {strategy_name: effective_config}

    signals = deps.trigger_operator_analysis_run(
        execute=deps.run_snapshot_analysis,
        symbol=req.symbol,
        strategy=strategy_name,
        ingestion_run_id=req.ingestion_run_id,
        execute_kwargs={
            "symbols": [req.symbol],
            "strategies": [strategy],
            "engine_config": engine_config,
            "strategy_configs": strategy_configs,
            "signal_repo": deps.signal_repo,
            "ingestion_run_id": req.ingestion_run_id,
            "db_path": deps.resolve_analysis_db_path(),
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

    persisted_run = deps.analysis_run_repo.save_run(
        analysis_run_id=computed_run_id,
        ingestion_run_id=req.ingestion_run_id,
        request_payload=run_request_payload,
        result_payload=response_payload,
    )

    if persisted_run is None:
        return ManualAnalysisResponse(**response_payload)
    return ManualAnalysisResponse(**persisted_run["result"])


def basic_screener(
    *,
    req: ScreenerRequest,
    deps: AnalysisServiceDependencies,
) -> ScreenerResponse:
    deps.require_ingestion_run(req.ingestion_run_id)
    if req.symbols is None or len(req.symbols) == 0:
        if req.market_type == "stock":
            symbols = ["AAPL", "MSFT", "NVDA", "META", "TSLA"]
        else:
            symbols = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "XRP/USDT"]
    else:
        symbols = req.symbols

    deps.require_snapshot_ready(req.ingestion_run_id, symbols=symbols, timeframe="D1")

    engine_config = EngineConfig(
        timeframe="D1",
        lookback_days=req.lookback_days,
        market_type=req.market_type,
        data_source="yahoo" if req.market_type == "stock" else "binance",
    )

    strategies = deps.create_registered_strategies()
    strategy_configs = deps.default_strategy_configs

    signals = deps.run_snapshot_analysis(
        symbols=symbols,
        strategies=strategies,
        engine_config=engine_config,
        strategy_configs=strategy_configs,
        signal_repo=deps.signal_repo,
        ingestion_run_id=req.ingestion_run_id,
        db_path=deps.resolve_analysis_db_path(),
    )
    symbol_results = build_ranked_symbol_results(signals, min_score=req.min_score)

    return ScreenerResponse(
        market_type=req.market_type,
        symbols=symbol_results,
    )


def to_watchlist_response(watchlist: Any) -> WatchlistResponse:
    return WatchlistResponse(
        watchlist_id=watchlist.watchlist_id,
        name=watchlist.name,
        symbols=list(watchlist.symbols),
    )


def execute_watchlist(
    *,
    watchlist_id: str,
    req: WatchlistExecutionRequest,
    deps: AnalysisServiceDependencies,
) -> WatchlistExecutionResponse:
    watchlist = deps.watchlist_repo.get_watchlist(watchlist_id)
    if watchlist is None:
        raise HTTPException(status_code=404, detail="watchlist_not_found")

    deps.require_ingestion_run(req.ingestion_run_id)

    strategies = deps.create_registered_strategies()
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
        "min_score": normalize_for_hashing(req.min_score),
    }
    computed_run_id = compute_analysis_run_id(run_request_payload)

    existing_run = deps.analysis_run_repo.get_run(computed_run_id)
    if existing_run is not None:
        logger.info(
            "Watchlist execution reused: component=control_plane analysis_run_id=%s ingestion_run_id=%s watchlist_id=%s",
            computed_run_id,
            existing_run["ingestion_run_id"],
            watchlist.watchlist_id,
        )
        deps.require_ingestion_run(existing_run["ingestion_run_id"])
        return WatchlistExecutionResponse(**existing_run["result"])

    engine_config = EngineConfig(
        timeframe="D1",
        lookback_days=req.lookback_days,
        market_type=req.market_type,
        data_source="yahoo" if req.market_type == "stock" else "binance",
    )
    symbol_failures: List[Dict[str, str]] = []
    signals = deps.run_snapshot_analysis(
        symbols=list(watchlist.symbols),
        strategies=strategies,
        engine_config=engine_config,
        strategy_configs=deps.default_strategy_configs,
        signal_repo=deps.signal_repo,
        ingestion_run_id=req.ingestion_run_id,
        db_path=deps.resolve_analysis_db_path(),
        run_id=computed_run_id,
        symbol_failures=symbol_failures,
        isolate_symbol_failures=True,
    )

    ranked_results = build_watchlist_ranked_results(signals, min_score=req.min_score)
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

    persisted_run = deps.analysis_run_repo.save_run(
        analysis_run_id=computed_run_id,
        ingestion_run_id=req.ingestion_run_id,
        request_payload=run_request_payload,
        result_payload=response_payload,
    )

    if persisted_run is None:
        return WatchlistExecutionResponse(**response_payload)
    return WatchlistExecutionResponse(**persisted_run["result"])

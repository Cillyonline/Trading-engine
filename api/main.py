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
import uuid
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from fastapi import Depends, FastAPI, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field

from api.config import SIGNALS_READ_MAX_LIMIT
from cilly_trading.engine.core import EngineConfig, run_watchlist_analysis
from cilly_trading.models import SignalReadItemDTO, SignalReadResponseDTO
from cilly_trading.repositories.analysis_runs_sqlite import SqliteAnalysisRunRepository
from cilly_trading.repositories.signals_sqlite import SqliteSignalRepository
from cilly_trading.strategies import Rsi2Strategy, TurtleStrategy


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


class StrategyAnalyzeRequest(BaseModel):
    ingestion_run_id: Optional[str] = Field(
        default=None,
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
    # Optional: einfache Strategie-Konfiguration (überschreibt Defaults)
    strategy_config: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optionale Strategie-Konfiguration (z. B. Oversold-Schwelle).",
    )


class StrategyAnalyzeResponse(BaseModel):
    symbol: str
    strategy: str
    signals: List[Dict[str, Any]]


class ManualAnalysisRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    analysis_run_id: str = Field(..., min_length=1, description="Client-provided run ID.")
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

    ingestion_run_id: Optional[str] = Field(
        default=None,
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

# --- FastAPI-App initialisieren ---


app = FastAPI(
    title="Cilly Trading Engine API",
    version="0.1.0",
    description="MVP-API für die Cilly Trading Engine (RSI2 & Turtle, D1, SQLite).",
)

logger.info("Cilly Trading Engine API starting up")

# Repositories & Strategien als Singletons im Modul
signal_repo = SqliteSignalRepository()
analysis_run_repo = SqliteAnalysisRunRepository()


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

strategy_registry = {
    "RSI2": Rsi2Strategy(),
    "TURTLE": TurtleStrategy(),
}

# Standard-Strategie-Konfigurationen
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


# --- Endpunkte ---


@app.get("/health")
def health() -> Dict[str, str]:
    """
    Einfacher Health-Check-Endpoint.
    """
    return {"status": "ok"}


def _get_signals_query(
    symbol: Optional[str] = Query(
        default=None,
        description="Optionales Symbol-Filter (z. B. 'AAPL' oder 'BTC/USDT').",
    ),
    strategy: Optional[str] = Query(
        default=None,
        description="Optionaler Strategie-Filter (z. B. 'RSI2' oder 'TURTLE').",
    ),
    preset: Optional[str] = Query(
        default=None,
        description="Optionaler Preset-Filter (z. B. 'D1' oder 'H1').",
    ),
    from_: Optional[datetime] = Query(
        default=None,
        alias="from",
        description="Startzeit (inklusive) für created_at im ISO-8601-Format.",
    ),
    to: Optional[datetime] = Query(
        default=None,
        alias="to",
        description="Endzeit (inklusive) für created_at im ISO-8601-Format.",
    ),
    start: Optional[datetime] = Query(
        default=None,
        description="Startzeit (inklusive) für created_at im ISO-8601-Format.",
    ),
    end: Optional[datetime] = Query(
        default=None,
        description="Endzeit (inklusive) für created_at im ISO-8601-Format.",
    ),
    sort: Literal["created_at_asc", "created_at_desc"] = Query(
        default="created_at_desc",
        description=(
            "Sortierung nach created_at. "
            "'created_at_desc' liefert neueste zuerst, "
            "'created_at_asc' liefert älteste zuerst."
        ),
    ),
    limit: int = Query(
        default=50,
        ge=1,
        le=SIGNALS_READ_MAX_LIMIT,
        description=(
            "Seitenlimit für Pagination. "
            f"Maximal {SIGNALS_READ_MAX_LIMIT} Einträge."
        ),
    ),
    offset: int = Query(
        default=0,
        ge=0,
        description="Pagination-Offset: Anzahl der Einträge, die übersprungen werden.",
    ),
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
        from_=resolved_from,
        to=resolved_to,
        sort=sort,
        limit=limit,
        offset=offset,
    )


def _get_screener_results_query(
    strategy: str = Query(..., description="Strategie-Name für den Screener-Filter."),
    timeframe: str = Query(..., description="Timeframe-Filter (z. B. 'D1')."),
    min_score: Optional[float] = Query(
        default=None,
        ge=0.0,
        description="Optionaler Mindest-Score für die Screener-Ergebnisse.",
    ),
) -> ScreenerResultsQuery:
    return ScreenerResultsQuery(
        strategy=strategy,
        timeframe=timeframe,
        min_score=min_score,
    )


@app.get(
    "/signals",
    response_model=SignalReadResponseDTO,
    responses={
        200: {
            "description": "Signals read (paginated).",
            "content": {
                "application/json": {
                    "example": {
                        "items": [
                            {
                                "symbol": "AAPL",
                                "strategy": "RSI2",
                                "direction": "long",
                                "score": 42.5,
                                "created_at": "2024-01-15T09:30:00Z",
                                "stage": "setup",
                                "entry_zone": {"from_": 178.5, "to": 182.0},
                                "confirmation_rule": "RSI below 10",
                                "timeframe": "D1",
                                "market_type": "stock",
                                "data_source": "yahoo",
                            }
                        ],
                        "limit": 50,
                        "offset": 0,
                        "total": 128,
                    }
                }
            },
        },
        422: {"description": "Validation error (z. B. ungültiger Zeitraum oder limit > max)."}
    },
)
def read_signals(params: SignalsReadQuery = Depends(_get_signals_query)) -> SignalReadResponseDTO:
    items, total = signal_repo.read_signals(
        symbol=params.symbol,
        strategy=params.strategy,
        preset=params.preset,
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


@app.get(
    "/screener/v2/results",
    response_model=ScreenerResultsResponse,
    responses={
        200: {
            "description": "Screener results (filtered by strategy/timeframe).",
            "content": {
                "application/json": {
                    "example": {
                        "items": [
                            {
                                "symbol": "NVDA",
                                "score": 68.2,
                                "strategy": "TURTLE",
                                "timeframe": "D1",
                                "market_type": "stock",
                                "created_at": "2024-01-15T09:30:00Z",
                            }
                        ],
                        "total": 1,
                    }
                }
            },
        }
    },
)
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
    """
    Führt eine Analyse für ein einzelnes Symbol mit einer ausgewählten Strategie durch.
    """
    logger.info(
        "Strategy analyze start: symbol=%s strategy=%s market_type=%s lookback_days=%s",
        req.symbol,
        req.strategy,
        req.market_type,
        req.lookback_days,
    )

    if req.ingestion_run_id:
        _require_ingestion_run(req.ingestion_run_id)

    strategy_name = req.strategy.upper()
    strategy = strategy_registry.get(strategy_name)
    if strategy is None:
        logger.warning("Unknown strategy requested: %s", req.strategy)
        raise HTTPException(status_code=400, detail=f"Unknown strategy: {req.strategy}")

    engine_config = EngineConfig(
        timeframe="D1",
        lookback_days=req.lookback_days,
        market_type=req.market_type,
        data_source="yahoo" if req.market_type == "stock" else "binance",
    )

    # Konfiguration: Defaults + optional Request-Override
    effective_config = default_strategy_configs.get(strategy_name, {}).copy()
    if req.strategy_config:
        effective_config.update(req.strategy_config)

    logger.debug(
        "Effective strategy config: strategy=%s keys=%s",
        strategy_name,
        sorted(list(effective_config.keys())),
    )

    strategy_configs = {
        strategy_name: effective_config,
    }

    # Engine-Aufruf
    signals = run_watchlist_analysis(
        symbols=[req.symbol],
        strategies=[strategy],
        engine_config=engine_config,
        strategy_configs=strategy_configs,
        signal_repo=signal_repo,
        ingestion_run_id=req.ingestion_run_id,
        db_path=analysis_run_repo._db_path,
    )

    filtered_signals = [
        s for s in signals if s.get("symbol") == req.symbol and s.get("strategy") == strategy_name
    ]

    logger.info(
        "Strategy analyze finished: symbol=%s strategy=%s signals_total=%d",
        req.symbol,
        strategy_name,
        len(filtered_signals),
    )

    return StrategyAnalyzeResponse(
        symbol=req.symbol,
        strategy=strategy_name,
        signals=filtered_signals,
    )


@app.post(
    "/analysis/run",
    response_model=ManualAnalysisResponse,
    responses={
        200: {"description": "Manual analysis result (idempotent)."},
        400: {"description": "Validation error (z. B. unbekannte Strategie)."},
        422: {"description": "Snapshot fehlt oder wird nicht unterstützt."},
    },
)
def manual_analysis(req: ManualAnalysisRequest) -> ManualAnalysisResponse:
    """
    Manuelles Triggern einer Analyse mit idempotenter Run-ID.
    """
    existing_run = analysis_run_repo.get_run(req.analysis_run_id)
    if existing_run is not None:
        _require_ingestion_run(existing_run["ingestion_run_id"])
        return ManualAnalysisResponse(**existing_run["result"])

    if req.ingestion_run_id:
        _require_ingestion_run(req.ingestion_run_id)

    strategy_name = req.strategy.upper()
    strategy = strategy_registry.get(strategy_name)
    if strategy is None:
        logger.warning("Unknown strategy requested: %s", req.strategy)
        raise HTTPException(status_code=400, detail=f"Unknown strategy: {req.strategy}")

    engine_config = EngineConfig(
        timeframe="D1",
        lookback_days=req.lookback_days,
        market_type=req.market_type,
        data_source="yahoo" if req.market_type == "stock" else "binance",
    )

    effective_config = default_strategy_configs.get(strategy_name, {}).copy()
    if req.strategy_config:
        effective_config.update(req.strategy_config)

    strategy_configs = {
        strategy_name: effective_config,
    }

    signals = run_watchlist_analysis(
        symbols=[req.symbol],
        strategies=[strategy],
        engine_config=engine_config,
        strategy_configs=strategy_configs,
        signal_repo=signal_repo,
        ingestion_run_id=req.ingestion_run_id,
        db_path=analysis_run_repo._db_path,
    )

    filtered_signals = [
        s for s in signals if s.get("symbol") == req.symbol and s.get("strategy") == strategy_name
    ]

    response_payload = {
        "analysis_run_id": req.analysis_run_id,
        "ingestion_run_id": req.ingestion_run_id,
        "symbol": req.symbol,
        "strategy": strategy_name,
        "signals": filtered_signals,
    }

    analysis_run_repo.save_run(
        analysis_run_id=req.analysis_run_id,
        ingestion_run_id=req.ingestion_run_id,
        request_payload=req.model_dump(),
        result_payload=response_payload,
    )

    return ManualAnalysisResponse(**response_payload)



@app.post("/screener/basic", response_model=ScreenerResponse)
def basic_screener(req: ScreenerRequest) -> ScreenerResponse:
    """
    Einfacher Basis-Screener.

    - Wenn keine Symbole angegeben werden, nutzt der Screener eine Default-Watchlist
      (unterschiedlich für Aktien & Krypto).
    - Nutzt alle registrierten Strategien (RSI2 + TURTLE).
    - Gibt nur SETUP-Signale mit Score >= min_score zurück.
    """
    if req.ingestion_run_id:
        _require_ingestion_run(req.ingestion_run_id)
    # Default-Watchlists, MVP-Variante
    if req.symbols is None or len(req.symbols) == 0:
        if req.market_type == "stock":
            symbols = ["AAPL", "MSFT", "NVDA", "META", "TSLA"]
        else:  # crypto
            symbols = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "XRP/USDT"]
    else:
        symbols = req.symbols

    logger.info(
        "Screener start: market_type=%s lookback_days=%s min_score=%s symbols=%d",
        req.market_type,
        req.lookback_days,
        req.min_score,
        len(symbols),
    )

    engine_config = EngineConfig(
        timeframe="D1",
        lookback_days=req.lookback_days,
        market_type=req.market_type,
        data_source="yahoo" if req.market_type == "stock" else "binance",
    )

    # Alle Strategien nutzen
    strategies = list(strategy_registry.values())

    # Für den Screener nutzen wir einfach die Default-Configs
    strategy_configs = default_strategy_configs

    signals = run_watchlist_analysis(
        symbols=symbols,
        strategies=strategies,
        engine_config=engine_config,
        strategy_configs=strategy_configs,
        signal_repo=signal_repo,
        ingestion_run_id=req.ingestion_run_id,
        db_path=analysis_run_repo._db_path,
    )

    logger.info("Screener engine run finished: total_signals=%d", len(signals))

    # Nur SETUP-Signale mit Score >= min_score
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

    # Nach Symbol gruppieren
    by_symbol: Dict[str, List[Dict[str, Any]]] = {}
    for s in setup_signals:
        sym = s.get("symbol", "")
        if not sym:
            continue

        # Nur relevante Felder fürs Frontend extrahieren
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
        # Missing numeric values are normalized to -inf to guarantee deterministic ordering.
        score = item.score if item.score is not None else float("-inf")
        signal_strength = (
            item.signal_strength if item.signal_strength is not None else float("-inf")
        )
        symbol = item.symbol or ""
        return (-score, -signal_strength, symbol)

    symbol_results.sort(key=_sorting_key)

    logger.info(
        "Screener result prepared: setup_signals=%d symbols_returned=%d",
        len(setup_signals),
        len(symbol_results),
    )

    return ScreenerResponse(
        market_type=req.market_type,
        symbols=symbol_results,
    )


# Optionaler Startpunkt für lokalen Betrieb:
# uvicorn api.main:app --reload
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)

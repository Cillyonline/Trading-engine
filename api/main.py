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
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from cilly_trading.engine.core import EngineConfig, run_watchlist_analysis
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


class ScreenerRequest(BaseModel):
    """
    Request-Modell für den Basis-Screener.

    MVP:
    - Wenn keine Symbolliste angegeben ist, wird eine Default-Liste pro Markt verwendet.
    - Nutzt alle registrierten Strategien (RSI2 & TURTLE).
    """

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
    setups: List[Dict[str, Any]]


class ScreenerResponse(BaseModel):
    market_type: str
    symbols: List[ScreenerSymbolResult]


# --- FastAPI-App initialisieren ---


app = FastAPI(
    title="Cilly Trading Engine API",
    version="0.1.0",
    description="MVP-API für die Cilly Trading Engine (RSI2 & Turtle, D1, SQLite).",
)

logger.info("Cilly Trading Engine API starting up")

# Repositories & Strategien als Singletons im Modul
signal_repo = SqliteSignalRepository()

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


@app.post("/screener/basic", response_model=ScreenerResponse)
def basic_screener(req: ScreenerRequest) -> ScreenerResponse:
    """
    Einfacher Basis-Screener.

    - Wenn keine Symbole angegeben werden, nutzt der Screener eine Default-Watchlist
      (unterschiedlich für Aktien & Krypto).
    - Nutzt alle registrierten Strategien (RSI2 + TURTLE).
    - Gibt nur SETUP-Signale mit Score >= min_score zurück.
    """
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
    )

    logger.info("Screener engine run finished: total_signals=%d", len(signals))

    # Nur SETUP-Signale mit Score >= min_score
    setup_signals = [
        s
        for s in signals
        if s.get("stage") == "setup" and float(s.get("score", 0.0)) >= req.min_score
    ]

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
            "stage": s.get("stage"),
            "confirmation_rule": s.get("confirmation_rule"),
            "entry_zone": s.get("entry_zone"),
            "timeframe": s.get("timeframe"),
            "market_type": s.get("market_type"),
        }

        by_symbol.setdefault(sym, []).append(setup_info)

    symbol_results = [
        ScreenerSymbolResult(symbol=symbol, setups=setups) for symbol, setups in by_symbol.items()
    ]

    # Optional: nach höchstem Score sortieren
    symbol_results.sort(
        key=lambda item: max((s.get("score", 0.0) for s in item.setups), default=0.0),
        reverse=True,
    )

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

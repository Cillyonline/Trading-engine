"""
FastAPI-Anwendung für die Cilly Trading Engine (MVP).

Endpunkte:
- GET /health
- POST /strategy/analyze

Später:
- POST /screener/basic
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from cilly_trading.engine.core import EngineConfig, run_watchlist_analysis
from cilly_trading.repositories.signals_sqlite import SqliteSignalRepository
from cilly_trading.strategies import Rsi2Strategy, TurtleStrategy


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


# --- FastAPI-App initialisieren ---


app = FastAPI(
    title="Cilly Trading Engine API",
    version="0.1.0",
    description="MVP-API für die Cilly Trading Engine (RSI2 & Turtle, D1, SQLite).",
)


# Repositories & Strategien als Singletons im Modul
signal_repo = SqliteSignalRepository()

strategy_registry = {
    "RSI2": Rsi2Strategy(),
    "TURTLE": TurtleStrategy(),
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

    strategy_name = req.strategy.upper()
    strategy = strategy_registry.get(strategy_name)
    if strategy is None:
        raise HTTPException(status_code=400, detail=f"Unknown strategy: {req.strategy}")

    engine_config = EngineConfig(
        timeframe="D1",
        lookback_days=req.lookback_days,
        market_type=req.market_type,
        data_source="yahoo" if req.market_type == "stock" else "binance",
    )

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

    # Konfiguration aus Request überschreibt Defaults (falls vorhanden)
    effective_config = default_strategy_configs.get(strategy_name, {}).copy()
    if req.strategy_config:
        effective_config.update(req.strategy_config)

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

    # Nur die Signale dieses Symbols & dieser Strategie zurückgeben
    filtered_signals = [
        s for s in signals
        if s.get("symbol") == req.symbol and s.get("strategy") == strategy_name
    ]

    return StrategyAnalyzeResponse(
        symbol=req.symbol,
        strategy=strategy_name,
        signals=filtered_signals,
    )


# Optionaler Startpunkt für lokalen Betrieb:
# uvicorn api.main:app --reload
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)

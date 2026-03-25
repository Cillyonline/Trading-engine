from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


class PresetConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., min_length=1, description="Stabiler Preset-Identifier.")
    params: Dict[str, Any] = Field(
        default_factory=dict,
        description="Strategie-Parameter fuer dieses Preset.",
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
        description="Optional: mehrere Preset-Identifier fuer Vergleich.",
    )
    presets: Optional[List[PresetConfig]] = Field(
        default=None,
        min_length=1,
        description="Optional: mehrere Presets fuer dieselbe Strategie (Vergleich).",
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
    Request-Modell fuer den Basis-Screener.

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
        description="Mindestscore fuer Setups, die im Screener erscheinen sollen.",
    )


class ScreenerSymbolResult(BaseModel):
    symbol: str
    score: Optional[float] = None
    signal_strength: Optional[float] = None
    setups: List[Dict[str, Any]]


class ScreenerResponse(BaseModel):
    market_type: str
    symbols: List[ScreenerSymbolResult]

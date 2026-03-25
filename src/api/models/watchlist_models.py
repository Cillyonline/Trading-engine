from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


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

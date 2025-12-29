"""
Zentrale Datenmodelle für die Cilly Trading Engine.
"""

from __future__ import annotations

from typing import List, Literal, Optional, TypedDict

from pydantic import BaseModel, Field


# --- Typen / Enums -------------------------------------------------

Stage = Literal["setup", "entry_confirmed"]
MarketType = Literal["stock", "crypto"]
Direction = Literal["long"]
DataSource = Literal["yahoo", "binance"]


# --- Interne Engine- / Repository-Modelle --------------------------

class EntryZone(TypedDict):
    from_: float
    to: float


class Signal(TypedDict, total=False):
    """
    Einheitliches internes Signalmodell gemäß MVP-Spezifikation.
    Wird von Strategien + Repositories verwendet.
    """
    symbol: str
    strategy: str
    direction: Direction
    score: float
    timestamp: str          # ISO-String (SQLite-Format)
    stage: Stage
    entry_zone: Optional[EntryZone]
    confirmation_rule: str
    timeframe: str
    market_type: MarketType
    data_source: DataSource


class Trade(TypedDict, total=False):
    """
    Minimales Trade-Modell für Papertrading und spätere Backtests.
    """
    id: int
    symbol: str
    strategy: str
    stage: Stage
    entry_price: Optional[float]
    entry_date: Optional[str]
    exit_price: Optional[float]
    exit_date: Optional[str]
    reason_entry: str
    reason_exit: Optional[str]
    notes: Optional[str]
    timeframe: str
    market_type: MarketType
    data_source: DataSource


# --- API DTOs (Read-only Contracts) --------------------------------

class EntryZoneDTO(BaseModel):
    from_: float = Field(..., alias="from_")
    to: float

    class Config:
        extra = "forbid"
        allow_population_by_field_name = True


class SignalReadItemDTO(BaseModel):
    """
    Einzelnes Signal im Read-API.
    created_at ist absichtlich STRING (ISO-8601),
    um SQLite- und Runtime-Probleme zu vermeiden.
    """
    symbol: str
    strategy: str
    direction: Direction
    score: float
    created_at: str              # ← bewusst STRING, nicht datetime
    stage: Stage
    entry_zone: Optional[EntryZoneDTO] = None
    confirmation_rule: Optional[str] = None
    timeframe: str
    market_type: MarketType
    data_source: DataSource

    class Config:
        extra = "forbid"


class SignalReadResponseDTO(BaseModel):
    """
    Envelope für /signals Read-Endpoint.
    """
    items: List[SignalReadItemDTO]
    limit: int
    offset: int
    total: int

    class Config:
        extra = "forbid"

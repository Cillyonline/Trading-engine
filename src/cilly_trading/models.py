"""
Zentrale Datenmodelle für die Cilly Trading Engine.
"""

from __future__ import annotations

from typing import Literal, TypedDict, Optional


Stage = Literal["setup", "entry_confirmed"]
MarketType = Literal["stock", "crypto"]
Direction = Literal["long"]
DataSource = Literal["yahoo", "binance"]


class EntryZone(TypedDict):
    from_: float
    to: float


class Signal(TypedDict, total=False):
    """
    Einheitliches Signalmodell gemäß MVP-Spezifikation.
    """
    symbol: str
    strategy: str
    direction: Direction
    score: float
    timestamp: str      # ISO-String
    stage: Stage        # "setup" | "entry_confirmed"
    entry_zone: Optional[EntryZone]
    confirmation_rule: str
    timeframe: str      # z. B. "D1"
    market_type: MarketType
    data_source: DataSource


class Trade(TypedDict, total=False):
    """
    Minimales Trade-Modell für Papertrading und spätere Backtests.
    """
    id: int              # wird von DB vergeben
    symbol: str
    strategy: str
    stage: Stage
    entry_price: Optional[float]
    entry_date: Optional[str]   # ISO-String
    exit_price: Optional[float]
    exit_date: Optional[str]
    reason_entry: str
    reason_exit: Optional[str]
    notes: Optional[str]
    timeframe: str
    market_type: MarketType
    data_source: DataSource

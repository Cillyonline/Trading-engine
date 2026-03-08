"""Canonical market data provider contract for engine consumers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Iterator, Protocol, runtime_checkable


@dataclass(frozen=True)
class Candle:
    """Canonical candle payload returned by market data providers."""

    timestamp: datetime
    symbol: str
    timeframe: str
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal


@dataclass(frozen=True)
class MarketDataRequest:
    """Canonical request shape accepted by market data providers."""

    symbol: str
    timeframe: str
    limit: int | None = None


@runtime_checkable
class MarketDataProvider(Protocol):
    """Provider protocol for deterministic market data iteration.

    Contract:
    - For a logically identical request, providers must return candles in a stable order.
    - Repeated iteration over a request must yield the same sequence of candle objects.
    - Each yielded candle must contain the canonical OHLCV fields.
    """

    def iter_candles(self, request: MarketDataRequest) -> Iterator[Candle]:
        """Yield canonical candles for a request in deterministic order."""

        ...

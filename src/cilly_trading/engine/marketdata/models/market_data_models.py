"""Market data DTOs for deterministic, read-only ingestion."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional, Sequence


@dataclass(frozen=True)
class MarketDataRequest:
    """Request for deterministic market data snapshots."""

    symbol: str
    timeframe: str
    limit: Optional[int] = None


@dataclass(frozen=True)
class MarketDataMetadata:
    """Metadata returned alongside deterministic market data."""

    audit_id: str
    source_path: str
    delay_steps: int
    row_count: int


@dataclass(frozen=True)
class Bar:
    """Snapshot bar from a replay dataset."""

    timestamp: str
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal
    symbol: str
    timeframe: str


@dataclass(frozen=True)
class MarketDataBatch:
    """Batch of bars with deterministic metadata."""

    bars: Sequence[Bar]
    metadata: MarketDataMetadata

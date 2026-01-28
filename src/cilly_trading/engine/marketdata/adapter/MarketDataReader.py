"""Read-only market data adapter contract."""

from __future__ import annotations

from typing import Protocol

from cilly_trading.engine.marketdata.models.market_data_models import (
    MarketDataBatch,
    MarketDataRequest,
)


class MarketDataReader(Protocol):
    """Read-only adapter interface for deterministic market data."""

    def get_bars(self, request: MarketDataRequest) -> MarketDataBatch:
        """Return a deterministic batch of bars for the request."""

        ...

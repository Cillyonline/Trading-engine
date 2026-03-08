# Market Data Provider Contract

## Purpose
This contract defines the canonical interface for all engine market data providers.
Backtesting, paper trading, and future live providers must conform to this contract.

## Interface
`MarketDataProvider` is defined in:

`src/cilly_trading/engine/data/market_data_provider.py`

Required method:

- `iter_candles(request: MarketDataRequest) -> Iterator[Candle]`

## Canonical Candle Schema
Each `Candle` must expose:

- `timestamp: datetime`
- `symbol: str`
- `timeframe: str`
- `open: Decimal`
- `high: Decimal`
- `low: Decimal`
- `close: Decimal`
- `volume: Decimal`

## Deterministic Iteration Requirements
Providers must be deterministic for a logically identical request:

- Candle order must be stable.
- Repeated calls must produce the same candle sequence.
- No implicit randomness or non-deterministic ordering is allowed.

## Stability Requirement
This interface is a compatibility boundary for future providers.
Changes must be backward compatible unless an explicit versioned migration is introduced.

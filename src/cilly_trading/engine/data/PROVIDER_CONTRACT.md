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

## Validation Requirements
Incoming OHLCV data must pass deterministic integrity validation before analysis/execution:

- OHLC integrity:
  - `high >= low`
  - `high >= open`
  - `high >= close`
  - `low <= open`
  - `low <= close`
- Timestamp ordering: candles must be strictly ascending by timestamp.
- Duplicate candle detection: duplicate timestamps are rejected.

## Missing Candle Detection
Canonical candle sequences can be scanned for missing intervals using:

- `detect_missing_candle_intervals(candles, timeframe=None) -> tuple[MissingCandleInterval, ...]`

Timeframe resolution uses:

- `timeframe_to_timedelta(timeframe)`

Supported timeframe units:

- `M` (minutes), `H` (hours), `D` (days), `W` (weeks)

Deterministic gap rules:

- Input candles must represent one symbol and one timeframe.
- Timestamps must be strictly increasing.
- A gap exists when adjacent timestamps are separated by more than one timeframe step.
- Missing intervals are reported only; input data is never modified.

## Validation Error Codes
When validation fails, the following stable error codes are used:

- `snapshot_invalid_timestamp`
- `snapshot_duplicate_candle`
- `snapshot_timestamp_out_of_order`
- `snapshot_ohlc_integrity_invalid`

## Stability Requirement
This interface is a compatibility boundary for future providers.
Changes must be backward compatible unless an explicit versioned migration is introduced.

# Canonical Market Dataset Contract

## Purpose
This contract defines the canonical metadata for market datasets used by backtesting and analysis.
It is a deterministic compatibility boundary for data identity, validation, and reproducibility.

## Schema Definition
The canonical metadata schema is defined as:

- `CANONICAL_MARKET_DATASET_METADATA_SCHEMA`

in:

- `src/cilly_trading/engine/data/market_dataset_contract.py`

Required fields:

- `dataset_id` (string)
- `symbol` (string)
- `timeframe` (string)
- `source` (string)
- `start_timestamp` (ISO-8601 datetime string with timezone)
- `end_timestamp` (ISO-8601 datetime string with timezone)
- `row_count` (integer, `>= 0`)
- `created_at` (ISO-8601 datetime string with timezone)
- `content_sha256` (64-char SHA-256 hex digest)

Optional fields:

- `contract_version` (string)

## Dataset Identity Rules
`dataset_id` must be deterministic and is computed as SHA-256 of canonical JSON over the identity fields:

- `symbol`
- `timeframe`
- `source`
- `start_timestamp`
- `end_timestamp`
- `row_count`
- `content_sha256`

Identity implementation:

- `DATASET_IDENTITY_FIELDS`
- `compute_dataset_identity(metadata)`

Before hashing, `start_timestamp` and `end_timestamp` are canonicalized to timezone-aware UTC ISO-8601 strings.
Equivalent representations (for example `Z` vs `+00:00`, or non-UTC offsets representing the same instant) produce the same `dataset_id`.

`created_at` is intentionally excluded from identity so logically identical datasets produce the same `dataset_id`.

## Integrity Verification Fields
Deterministic integrity verification uses:

- `row_count` to validate expected dataset length
- `content_sha256` to validate dataset content digest

Validation enforces:

- required fields are present
- field types are correct
- timestamps are valid timezone-aware ISO-8601 values
- `start_timestamp <= end_timestamp`
- `dataset_id` equals the deterministic identity derived from canonical identity fields

Validation implementation:

- `validate_market_dataset_metadata(payload)`

## Metadata Construction
Use:

- `build_market_dataset_metadata(...)`

to construct canonical metadata with a deterministic `dataset_id` and validation.

# Phase 38 - Market Data Integration Status

Status: Partially Implemented  
Scope: Direct provider adapter presence, deterministic snapshot boundary, and runtime-safe claim evidence requirements  
Owner: Governance

## Purpose
This file is the canonical Phase 38 status and contract artifact for repository-safe market-data claims.

## Verified In-Repository Artifacts
- Direct provider loaders exist in `src/cilly_trading/engine/data.py`:
  - `_load_stock_yahoo` (yfinance)
  - `_load_crypto_binance` (ccxt/binance)
  - `load_ohlcv` (direct-provider path selector)
- Deterministic snapshot loading exists in `src/cilly_trading/engine/data.py`:
  - `load_ohlcv_snapshot`
  - `load_snapshot_metadata`
- Provider contract and deterministic failover artifacts exist in:
  - `src/cilly_trading/engine/data/market_data_provider.py`
  - `tests/data/test_market_data_provider_contract.py`
  - `tests/data/test_market_data_provider_failover_telemetry.py`

## Bounded Contract

### 1) Direct provider adapter boundary
- Direct provider loaders are implementation artifacts, not runtime determinism guarantees.
- Calls through `load_ohlcv` can vary with wall-clock time and upstream provider behavior.

### 2) Deterministic snapshot workflow boundary
- Repository-safe deterministic analysis claims apply only to snapshot-bound paths.
- Snapshot-bound paths require `ingestion_run_id` and load data through `load_ohlcv_snapshot`.
- Snapshot readiness and validation failures remain deterministic request errors.

### 3) Runtime-safe usage boundary
- Runtime-safe market-data claims must be tied to snapshot-only API enforcement, not to the mere existence of direct provider loaders.
- Direct provider adapters may exist in-repo without implying production-ready runtime integration.

## Evidence Requirements For Repository-Safe Market-Data Claims
A Phase 38 runtime-safe claim is acceptable only when all evidence classes are present together:

1. Direct adapter presence evidence  
`src/cilly_trading/engine/data.py` and/or `src/cilly_trading/engine/data/market_data_provider.py` show concrete provider-facing adapter code.

2. Deterministic usage-boundary evidence  
`docs/operations/api/usage_contract.md` documents snapshot-only API behavior and explicit non-deterministic direct engine paths.

3. Operational/runtime evidence  
Tests prove snapshot-only runtime paths do not use live provider loaders and that provider contract behavior is bounded and deterministic where claimed:
- `tests/test_api_snapshot_first_enforcement.py`
- `tests/test_api_manual_analysis_trigger.py`
- `tests/test_ui_runtime_browser_flow.py`
- `tests/data/test_market_data_provider_contract.py`

## Remaining Unimplemented Scope After Status Correction
- No claim that direct provider adapters are production-trustworthy runtime integration by themselves.
- No claim that in-repo runtime APIs serve live provider data for deterministic analysis endpoints.
- No claim that broker integration, live-trading feeds, or websocket market-data delivery is implemented.

## Documentation Alignment Rule
Phase 38 references in `docs/**` must align to this file, `docs/architecture/roadmap/execution_roadmap.md`, and `docs/operations/api/usage_contract.md`.

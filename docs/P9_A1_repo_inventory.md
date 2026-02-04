# P9-A1 Repo Inventory & Testability Assessment

## Repo Overview

This repository contains the Cilly Trading Engine MVP, including a FastAPI service, deterministic analysis workflows, fixtures, schemas, and tests.

## High-level Folder Structure

Top-level directories and their purpose:

- `api/`: FastAPI application entry point and configuration (see `api/main.py`).
- `data/`: Versioned snapshot fixture data used for Phase-6 snapshot contract testing (see `data/phase6_snapshots/test-snapshot-0001/*`).
- `docs/`: Project documentation, runbooks, and specifications (see `docs/local_run.md`, `docs/deterministic-analysis.md`, `docs/smoke-run.md`).
- `fixtures/`: Deterministic fixtures for analysis, smoke run, and market data normalization (see `fixtures/deterministic-analysis/*`, `fixtures/smoke-run/*`, `fixtures/market_data/*`).
- `schemas/`: JSON schema definitions for signal output contracts (see `schemas/signal-output.schema.json`).
- `scripts/`: Utility scripts (see `scripts/create_demo_snapshot.py`).
- `src/`: Core Python package (`cilly_trading`) containing engine, repositories, strategies, and utilities.
- `strategy/`: Strategy preset JSON configuration files (see `strategy/presets/*.json`).
- `tests/`: Pytest test suite plus test fixtures and golden data (see `tests/*`).

## Execution & Entry Points

### Existing CLI commands / scripts

- API server (FastAPI): `PYTHONPATH=src uvicorn api.main:app --reload` (documented in `docs/local_run.md`).
- Deterministic analysis run (module):
  ```bash
  python -m cilly_trading.engine.deterministic_run \
    --fixtures-dir fixtures/deterministic-analysis \
    --output tests/output/deterministic-analysis.json
  ```
  (documented in `docs/deterministic-analysis.md`).
- Deterministic smoke run (module call via `python -c`):
  ```bash
  PYTHONPATH=src python -c 'from cilly_trading.smoke_run import run_smoke_run; raise SystemExit(run_smoke_run())'
  ```
  (documented in `docs/RUNBOOK.md`).
- Demo snapshot seed script: `python scripts/create_demo_snapshot.py` (documented in script header).
- SQLite DB init module (commented invocation): `python -m src.cilly_trading.db.init_db` (documented in `src/cilly_trading/db/init_db.py`).

### How to run a deterministic workflow (exact commands, if any)

- Deterministic offline analysis run:
  ```bash
  python -m cilly_trading.engine.deterministic_run \
    --fixtures-dir fixtures/deterministic-analysis \
    --output tests/output/deterministic-analysis.json
  ```
- Deterministic smoke run:
  ```bash
  PYTHONPATH=src python -c 'from cilly_trading.smoke_run import run_smoke_run; raise SystemExit(run_smoke_run())'
  ```

## Data & Fixtures Inventory

### Versioned datasets / fixtures (repo-tracked)

- `data/phase6_snapshots/test-snapshot-0001/metadata.json` (JSON metadata). Includes `payload_checksum` hash.
- `data/phase6_snapshots/test-snapshot-0001/payload.json` (JSON payload rows).
- `fixtures/deterministic-analysis/analysis_config.json` (JSON analysis configuration).
- `fixtures/deterministic-analysis/aapl_d1.csv` (CSV OHLCV data).
- `fixtures/smoke-run/input.json` (JSON input).
- `fixtures/smoke-run/expected.csv` (CSV expected output).
- `fixtures/smoke-run/config.yaml` (YAML configuration).
- `fixtures/market_data/aapl_us_d1_2015-02/raw.csv` (CSV raw market data).
- `fixtures/market_data/aapl_us_d1_2015-02/normalized.csv` (CSV normalized market data).
- `tests/consumer/consumer_fixtures/*.json` (JSON consumer contract fixtures).
- `tests/schema/fixtures/*` (JSON and CSV schema fixtures).
- `tests/golden/analysis_output_golden_v1.json` (JSON golden master output).

### Hashes present

- `data/phase6_snapshots/test-snapshot-0001/metadata.json` includes `payload_checksum`.

## Test Inventory

### Test frameworks detected

- Pytest (tests are invoked via `pytest` / `python -m pytest` in docs and README).

### Existing tests (paths + type)

- API tests: `tests/test_api_*.py` (FastAPI endpoints).
- Engine/strategy tests: `tests/test_engine.py`, `tests/test_strategies.py`, `tests/strategies/*`.
- Determinism and smoke run tests: `tests/determinism/*`, `tests/test_smoke_run.py`.
- Schema and contract tests: `tests/schema/*`, `tests/test_signal_reason_schema.py`, `tests/consumer/*`.
- Repositories/data-layer tests: `tests/test_signal_repository_sqlite.py`, `tests/test_repositories.py`, `tests/test_data_layer_normalization.py`.
- Golden master tests: `tests/golden/test_analysis_golden_master.py`.
- Numeric precision tests: `tests/numeric/*`.

### How tests are executed (exact commands)

- `pytest`
- `python -m pytest`

## Component Capability Table

| Component | Exists (Y/N) | Entry Point | Inputs | Outputs | Deterministic (Y/N) | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| FastAPI service | Y | `api.main:app` via `uvicorn` | HTTP requests | HTTP JSON responses | N | Endpoints include `/health`, `/strategy/analyze`, `/screener/basic`. |
| Deterministic analysis run | Y | `python -m cilly_trading.engine.deterministic_run` | Fixture CSV + JSON config | JSON output artifact + SQLite DB | Y | Runs under determinism guard with fixture inputs only. |
| Deterministic smoke run | Y | `run_smoke_run` via `python -c` | Fixture JSON/CSV/YAML | stdout lines + JSON artifact | Y | Enforces deterministic constraints and required output lines. |
| SQLite DB init | Y | `python -m src.cilly_trading.db.init_db` | None (optional DB path) | SQLite DB file | Y | Creates DB schema locally. |
| Demo snapshot seed | Y | `python scripts/create_demo_snapshot.py` | None (writes demo data) | SQLite DB rows + printed IDs | Y | Creates deterministic OHLCV rows for a fixed watchlist. |
| Strategy presets | Y | JSON files under `strategy/presets/` | JSON preset files | Strategy preset configs | Y | Used as static configuration. |

## Current Capabilities (Plain Language)

- Serves a FastAPI application with health and strategy analysis endpoints.
- Runs deterministic offline analysis against fixture data and writes a canonical JSON artifact.
- Executes a deterministic smoke run using fixed fixtures, producing a required stdout sequence and JSON artifact.
- Seeds a local SQLite database with deterministic demo OHLCV data via a script.
- Stores and validates schema contracts for signal output and Phase-6 snapshot fixtures.

## Testability Gaps

- Pytest is referenced for test execution, but `requirements.txt` does not list pytest as a dependency.
- No dedicated CLI entrypoint is defined for the smoke run; the documented invocation uses `python -c`.
- No CLI entrypoint is documented for the API; documentation specifies running the service via `uvicorn`.

## Single Recommended Next Issue

**Title:** Add explicit test dependency manifest for pytest

**Scope (3–5 bullets):**
- Add a dev/test requirements file that includes `pytest`.
- Update documentation to reference the dev/test requirements file for running tests.
- Ensure the test command is reproducible with a single install step for test dependencies.

**Draft Acceptance Criteria:**
- A dedicated dev/test dependency file exists and includes `pytest`.
- README and/or test documentation references installing the dev/test dependencies before running tests.
- `python -m pytest` runs after installing the dev/test dependencies (documented as a command, not executed here).

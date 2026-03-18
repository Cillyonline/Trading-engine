# Market Data Fixtures

This document records the curated, real-world market data fixtures stored locally
for deterministic testing. Fixtures are versioned in the repository and are
intended for offline, deterministic execution only.

## Dataset: AAPL daily (Feb 2015, 5 rows)

- **Path:** `fixtures/market_data/aapl_us_d1_2015-02/`
- **Source:** Plotly public datasets repository (file: `finance-charts-apple.csv`).
- **Source URL:** https://raw.githubusercontent.com/plotly/datasets/master/finance-charts-apple.csv
- **Retrieval date:** 2025-02-16
- **License notes:** The dataset is hosted as a public sample dataset by Plotly.
  No additional license information is published in the source repository; use
  is limited here to a small, non-commercial fixture for deterministic tests.

### Files

- `raw.csv`
  - First five rows of the source CSV, preserving the original column names and
    values.
  - Columns (from source): `Date`, `AAPL.Open`, `AAPL.High`, `AAPL.Low`,
    `AAPL.Close`, `AAPL.Volume`, `AAPL.Adjusted`, `dn`, `mavg`, `up`, `direction`.
- `normalized.csv`
  - Normalized to the engine’s standard OHLCV schema.
  - Columns: `timestamp`, `open`, `high`, `low`, `close`, `volume`.

### Preprocessing steps

1. Downloaded the source CSV from the URL above.
2. Selected the first five daily rows (2015-02-17 through 2015-02-23) to keep
   the fixture small.
3. Created `normalized.csv` by:
   - Mapping `Date` to `timestamp` with `T00:00:00Z` appended.
   - Renaming OHLCV columns to lowercase.
   - Preserving numeric values exactly as published in the source.

### Numeric precision rules

- Prices are stored with up to 6 decimal places (as provided by the source).
- Volumes are stored as integer strings with no separators.
- Timestamps are ISO 8601 UTC with a `Z` suffix and no fractional seconds.

## Deterministic test execution

The deterministic smoke-run is the project’s canonical offline deterministic
check. It was executed twice with identical outputs verified via checksum of the
result artifact.

### Commands and results

1. First run:
   ```bash
   PYTHONPATH=src python -c 'from cilly_trading.smoke_run import run_smoke_run; raise SystemExit(run_smoke_run())'
   ```
   - Result: **pass**
   - Artifact: `artifacts/smoke-run/result.json`
   - SHA256: `b0e89fcd8a9db7c579aa505525e29aebb53038129060a0d1c30ffc3dab1e8f2e`

2. Second run:
   ```bash
   PYTHONPATH=src python -c 'from cilly_trading.smoke_run import run_smoke_run; raise SystemExit(run_smoke_run())'
   ```
   - Result: **pass**
   - Artifact: `artifacts/smoke-run/result.json`
   - SHA256: `b0e89fcd8a9db7c579aa505525e29aebb53038129060a0d1c30ffc3dab1e8f2e`

**Determinism check:** The checksums were identical across repeated runs.

# Deterministic Offline Analysis Run

This repository includes a deterministic offline analysis entry-run that loads
fixture data and blocks any use of network, time, or randomness during the run.

## Fixtures

Fixture data lives in `fixtures/deterministic-analysis/` and currently includes:

- `aapl_d1.csv`: daily OHLCV rows sampled from public Apple (AAPL) market data
  for early January 2024. The rows are curated for offline deterministic tests.

The run configuration is stored in `fixtures/deterministic-analysis/analysis_config.json`.

## Run locally (offline)

```bash
python -m cilly_trading.engine.deterministic_run \
  --fixtures-dir fixtures/deterministic-analysis \
  --output tests/output/deterministic-analysis.json
```

The command writes a canonical JSON artifact to the output path and uses a local
SQLite database file alongside it.

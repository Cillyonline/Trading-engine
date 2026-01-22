# Determinism Gate Contract

## Fixed Input Contract

The determinism gate runs a fixed analysis request using the following inputs:

- ingestion_run_id: determinism-ingestion-0001
- symbol: AAPL
- timeframe: D1
- strategy: RSI2
- lookback_days: 200

## Execution

Run via pytest:

- pytest tests/determinism/test_determinism_gate.py

Run via script:

- python tests/determinism/determinism_gate.py

## PASS / FAIL Definition

PASS:
- Three JSON artifacts are produced.
- Every JSON artifact is byte-identical to the baseline output.
- DB reload results are byte-identical to the in-memory outputs.
- The gate prints `DETERMINISM_GATE: PASS (runs=3)` and exits with code 0.

FAIL:
- Any byte-level mismatch across JSON artifacts or DB reload output.
- The gate prints `DETERMINISM_GATE: FAIL (runs=3)` and exits with non-zero code.
- Deviations are written to `tests/determinism/artifacts/determinism_deviations.json`.

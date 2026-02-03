# Deterministic Smoke-Run Specification

## Status
Implemented in `src/cilly_trading/smoke_run.py` via `run_smoke_run`.

## Purpose
Define a deterministic, offline smoke-run contract that validates fixed fixtures and produces fixed outputs so another developer can implement it without ambiguity.

## Non-goals
- No simulation.
- No paper trading.
- No live trading.
- No network access or external dependencies.
- No runtime clocks, timers, or real-time data.

## Determinism Rules
- No randomness: any RNG usage is forbidden.
- No time: do not read system time, timestamps, or monotonic clocks.
- No network: do not open sockets or make HTTP requests.
- Input-only: results must be derived solely from the fixture files described below.

## Invocation
- There is no CLI entrypoint; execute via `run_smoke_run` (see `docs/RUNBOOK.md` for the exact local command).

## Fixture Contract (Exact)

### Fixture Directory
- `fixtures/smoke-run/`

### Required Files
1) `fixtures/smoke-run/input.json`
2) `fixtures/smoke-run/expected.csv`
3) `fixtures/smoke-run/config.yaml`

### File Formats
- `input.json`: UTF-8 encoded JSON object.
- `expected.csv`: UTF-8 encoded CSV with header row.
- `config.yaml`: UTF-8 encoded YAML mapping.

### Required Keys / Columns
- `input.json` must contain:
  - `run_id` (string)
  - `base_currency` (string)
  - `quote_currency` (string)
  - `start_price` (number)
  - `end_price` (number)
  - `ticks` (integer)
- `expected.csv` must have header columns in this exact order:
  - `run_id`, `tick_index`, `price`
- `config.yaml` must contain:
  - `engine_name` (string)
  - `engine_version` (string)
  - `precision` (integer)

### Hard Constraints
- All files must exist; missing files are a hard failure.
- `input.json` values must be present and non-null for required keys.
- `ticks` must be an integer greater than or equal to 1.
- `start_price` and `end_price` must be finite numbers.
- `expected.csv` must contain exactly `ticks` data rows.
- `tick_index` values must be zero-based integers from `0` to `ticks - 1`.
- `run_id` must match across `input.json` and every row of `expected.csv`.
- `price` must be a finite number with no more than `precision` decimal places.
- `config.yaml` keys must be present and non-null.

## Expected Output (Exact)

### Required Stdout Lines
Stdout must contain exactly the following lines, in order, with no extra output:
1) `SMOKE_RUN:START`
2) `SMOKE_RUN:FIXTURES_OK`
3) `SMOKE_RUN:CHECKS_OK`
4) `SMOKE_RUN:END`

### Required Artifacts
- Directory: `artifacts/smoke-run/`
- Files:
  - `artifacts/smoke-run/result.json`

#### `result.json` Structure
A UTF-8 JSON object with the following exact keys and types:
- `run_id` (string)
- `status` (string, must be `ok` on success)
- `engine_name` (string)
- `engine_version` (string)
- `ticks` (integer)
- `precision` (integer)

## Exit Code Semantics

### Success Code
- `0` indicates success.

### Failure Classes and Exit Codes
- `10` — `fixtures_missing`: one or more required fixture files are missing.
- `11` — `fixtures_invalid`: required keys/columns missing or invalid formats.
- `12` — `constraints_failed`: hard constraints failed (counts, ranges, or mismatches).
- `13` — `output_mismatch`: stdout lines or artifact structure/content differ from this spec.

## Success Criteria
- All fixture files exist and pass validation.
- All hard constraints are satisfied.
- Stdout contains the required lines in the exact order with no extra output.
- `artifacts/smoke-run/result.json` exists and matches the required structure.
- Exit code is `0`.

## Failure Criteria
- Any missing or invalid fixture file.
- Any hard constraint violation.
- Any deviation in stdout lines or artifact structure/content.
- Any nonzero exit code not listed above.

## Implementation Note
The implementation is deterministic and intentionally uses only local fixtures and artifacts.

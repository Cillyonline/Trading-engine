# Backtesting

## Purpose
Backtesting runs a strategy against historical snapshots and writes deterministic results for review.

## Usage
```bash
python -m cilly_trading backtest --snapshots <PATH> --strategy <NAME> --out <DIR> [--run-id <STR>] [--strategy-module <PYMOD>]...
```

- `--snapshots`: Path to a JSON file containing snapshot data.
- `--strategy`: Strategy name to resolve and execute.
- `--out`: Output directory for backtest artifacts.
- `--run-id` (default deterministic): Optional run identifier; when omitted, a deterministic identifier is used.
- `--strategy-module` (optional, repeatable, imports module(s) before strategy resolution): Optional module path to import before strategy lookup; may be provided multiple times.

## Determinism Rules
- Determinism guard is installed during backtest execution and uninstalled in a finally block.
- Non-deterministic APIs are forbidden; violations exit with code 10.
- Snapshot input must be a JSON list.
- Each snapshot item must include:
  - `id` (non-empty string)
  - `timestamp` (non-empty string)

## Exit Codes
| Code | Meaning |
| --- | --- |
| 0 | success |
| 10 | determinism violation |
| 20 | snapshot input invalid |
| 30 | strategy selection invalid |
| 1 | unexpected error |

## Limitations
- No live trading
- No broker integrations
- No AI-based trading decisions

## Artifact Contract
- Output directory contains deterministic artifact(s)
- Artifact file: `backtest-result.json`
- Artifact content is deterministic for identical inputs

# Comparable Strategy Evaluation Harness

## Purpose

`STRAT-P42C` adds one bounded, reusable workflow for evaluating multiple strategies with the same deterministic path.

The harness is intentionally limited to comparability:

- same snapshot input set for all strategies
- same backtest engine path for all strategies
- explicit, deterministic comparison artifact output

Out of scope by design:

- parameter search/optimization loops
- notebook workflows
- UI redesign/reporting expansion
- broker or live-trading integration

## Command

```bash
python -m cilly_trading compare-strategies \
  --snapshots <PATH> \
  --strategy <NAME> \
  --strategy <NAME> \
  --out <DIR> \
  [--run-id <STR>] \
  [--benchmark-strategy <NAME>] \
  [--strategy-config <JSON_PATH>] \
  [--strategy-module <PYMOD>]...
```

## Shared Evaluation Inputs

`--snapshots` JSON must be an array of snapshot objects with:

- `id` (non-empty string)
- either `timestamp` (non-empty string) or `snapshot_key` (non-empty string)

All evaluated strategies receive the same ordered snapshot stream.

Optional per-strategy configs are provided via `--strategy-config` as:

```json
{
  "RSI2": {"oversold_threshold": 12.0},
  "TURTLE": {"breakout_lookback": 20}
}
```

## Bounded Translation Rules

Strategy output is translated into executable backtest signals with a fixed rule:

- only `stage="entry_confirmed"` and `direction="long"` are executable
- executable signal becomes one deterministic `BUY` order with `quantity="1"`
- maximum one open position per strategy in the harness flow

This keeps strategy comparison deterministic and bounded.

## Output Contract

The harness writes:

- `strategy-comparison.json`
- `strategy-comparison.sha256`
- per-strategy backtest artifacts under `strategies/<strategy>/`

`strategy-comparison.json` contains:

- workflow metadata (benchmark, snapshot linkage, translation rules)
- per-strategy bounded outputs:
  - executable/candidate signal counts
  - backtest artifact hash
  - summary (`start_equity`, `end_equity`)
  - metrics (`total_return`, `cagr`, `max_drawdown`, `sharpe_ratio`, `win_rate`, `profit_factor`)
  - `metrics_baseline.summary` alignment fields from backtest output
- deterministic ranking by `total_return`
- metric deltas vs benchmark strategy

## Alignment With Backtesting Outputs

Per-strategy comparison rows are derived from each strategy's `backtest-result.json`:

- `summary`
- `metrics_baseline.summary`
- metrics computed from `summary` + `equity_curve` + `trades`

This guarantees the comparison harness stays aligned with existing backtesting artifacts.

## Exit Codes

| Code | Meaning |
| --- | --- |
| `0` | Success |
| `2` | CLI usage / argument error |
| `10` | Determinism violation |
| `20` | Snapshot/config input invalid |
| `30` | Strategy selection invalid |
| `1` | Unexpected fallback error |


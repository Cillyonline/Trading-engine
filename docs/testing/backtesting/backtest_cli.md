# Backtest CLI

## Command

```bash
python -m cilly_trading backtest --snapshots <PATH> --strategy <NAME> --out <DIR> [--run-id <STR>] [--strategy-module <PYMOD>]...
```

- `--snapshots`: Path to a JSON file with snapshot data.
- `--strategy`: Registered strategy name.
- `--out`: Output directory for artifacts.
- `--run-id`: Optional run identifier. Default is `deterministic`.
- `--strategy-module`: Optional Python module to import before resolving the strategy.
  May be provided multiple times.

## Snapshot JSON format

The snapshots file must be a JSON array of snapshot objects:

```json
[
  {"id": "s1", "timestamp": "2024-01-01T00:00:00Z"},
  {"id": "s2", "timestamp": "2024-01-02T00:00:00Z"}
]
```

If the file cannot be read, cannot be parsed as JSON, or the top-level value is not a JSON array, the CLI exits with code `20`.

## Exit codes

| Exit code | Meaning |
| --- | --- |
| `0` | Success |
| `2` | CLI usage or invalid arguments (argparse default) |
| `10` | Determinism violation |
| `20` | Snapshot input invalid |
| `30` | Strategy selection invalid |
| `1` | Unexpected error fallback |

## Determinism guard

The `backtest` command installs the determinism guard at startup and uninstalls it in a `finally` block.
If forbidden non-deterministic APIs are used during execution, the command exits with code `10`.

## Reproducible Evidence Fields

The produced `backtest-result.json` is the trader-review evidence surface for the covered path.
For reproducible review, the following fields are mandatory:

- `run.run_id`: explicit run identity.
- `run.deterministic`: explicit deterministic execution flag (`true` on covered path).
- `snapshot_linkage`: bounded dataset window and count used for the run.
- `run_config.execution_assumptions`: explicit execution assumptions used for fill timing, slippage, commission, and price source.
- `run_config.reproducibility_metadata`: run identity context (`run_id`, strategy identity, params, engine identity).
- `metrics_baseline.assumptions`: assumption echo used for cost-aware metric interpretation.

Evidence alignment rule for covered outputs:

- `metrics_baseline.assumptions` MUST match `run_config.execution_assumptions`.

## Trader Interpretation Boundary

The produced evidence is valid only for deterministic replay under the declared assumptions and snapshot input.
It supports trader review for what this specific replay path did under those constraints.

The evidence does **not** prove:

- Live trading readiness.
- Broker fill quality or market-impact realism beyond the fixed deterministic model.
- Portfolio-level decision quality outside the covered backtest output scope.
- Future performance, out-of-sample robustness, or production profitability.

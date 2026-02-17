# Backtest CLI

## Command

```bash
python -m cilly_trading backtest --snapshots <PATH> --strategy <NAME> --out <DIR> [--run-id <STR>]
```

- `--snapshots`: Path to a JSON file with snapshot data.
- `--strategy`: Registered strategy name.
- `--out`: Output directory for artifacts.
- `--run-id`: Optional run identifier. Default is `deterministic`.

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

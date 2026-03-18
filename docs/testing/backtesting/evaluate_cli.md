# Evaluate CLI

## Command

```bash
python -m cilly_trading evaluate --artifact <PATH> --out <DIR>
```

- `--artifact`: Path to a deterministic backtest artifact JSON file (for example `backtest-result.json`).
- `--out`: Output directory for metrics artifacts. The directory is created if it does not exist.

## Behavior

- Artifact input is read as UTF-8 JSON.
- JSON constants like `NaN`, `Infinity`, and `-Infinity` are rejected.
- Metrics are computed deterministically from artifact content.
- The command writes `metrics-result.json` to `--out` with canonical JSON bytes.
- On success, stdout prints exactly one deterministic line:

```text
WROTE <path>
```

## Exit codes

| Exit code | Meaning |
| --- | --- |
| `0` | Success |
| `2` | CLI usage or invalid arguments (argparse default) |
| `10` | Determinism violation |
| `20` | Artifact input invalid (missing file, invalid JSON, or schema/type mismatch) |
| `1` | Unexpected error fallback |

## Determinism guard

The `evaluate` command installs the determinism guard at startup and uninstalls it in a `finally` block.
If forbidden non-deterministic APIs are used during execution, the command exits with code `10`.

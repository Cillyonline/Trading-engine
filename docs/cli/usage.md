# CLI Usage – Cilly Trading Engine

## 1. Running the CLI Module

Invoke the CLI by executing the package module.

### Bash

```bash
PYTHONPATH=src python -m cilly_trading
```

### PowerShell

```powershell
$env:PYTHONPATH="src"
python -m cilly_trading
```

When run without flags, the CLI prints argparse help output and exits with code `0`.

## 2. Version Command

The CLI exposes a version flag.

### Bash

```bash
PYTHONPATH=src python -m cilly_trading --version
```

### PowerShell

```powershell
$env:PYTHONPATH="src"
python -m cilly_trading --version
```

This command prints the authoritative package version and exits with code `0`.
The output value equals `cilly_trading.version`.
Do not treat documentation examples as a hard-coded version string.

## 3. Help Behavior

When no arguments are provided, argparse prints help text.
The help text includes the `--version` flag description.
The exit code remains `0`.

This document intentionally describes help behavior without copying full help output to avoid documentation drift.

## 4. Behavior Guarantees

- The CLI exposes only documented flags.
- The version source of truth is `src/cilly_trading/version.py`.
- CLI behavior follows the project versioning and compatibility policy:
  - [Version declaration](../versioning/declaration.md)
  - [Versioning model](../versioning/model.md)

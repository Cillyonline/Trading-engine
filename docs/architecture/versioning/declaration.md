# Version declaration

## Source of truth

The authoritative project version is defined in `src/cilly_trading/version.py` as:

- `__version__: str`
- `get_version() -> str`

All other version exposure mechanisms must read from this module.

## CLI exposure

The package module entrypoint exposes version output:

```bash
PYTHONPATH=src python -m cilly_trading --version
```

This prints the exact `__version__` value and exits with code `0`.

Running without flags prints help text and exits with code `0`:

```bash
PYTHONPATH=src python -m cilly_trading
```

## Python API exposure

Version is exposed through the public Python API via:

- `cilly_trading.__version__`
- `cilly_trading.version.get_version()`

These two values are contractually required to match.

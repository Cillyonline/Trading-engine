# Version declaration

## Source of truth
The authoritative engine version is declared in `src/cilly_trading/version.py`.

Contractual exports:
- `__version__: str`
- `get_version() -> str`
- `get_release_tag(version: str | None = None) -> str`
- `get_release_state(version: str | None = None) -> str`

`get_version()` and `__version__` must always match.

## Version contract
Engine versions must satisfy the bounded SemVer contract from `model.md`:

- `MAJOR.MINOR.PATCH`
- `MAJOR.MINOR.PATCH-alpha.N`
- `MAJOR.MINOR.PATCH-beta.N`
- `MAJOR.MINOR.PATCH-rc.N`

Release tags must be `v<version>` and validate against the same bounded forms.

## CLI exposure
The package module entrypoint exposes version output:

```bash
PYTHONPATH=src python -m cilly_trading --version
```

This prints the exact `__version__` value and exits with code `0`.

## Python API exposure
Version access points:

- `cilly_trading.__version__`
- `cilly_trading.version.get_version()`
- `cilly_trading.version.get_release_tag()`
- `cilly_trading.version.get_release_state()`

These APIs provide a single bounded vocabulary for engine version and release-state reporting.
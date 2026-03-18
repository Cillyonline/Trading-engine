# Testing

## Prerequisites

- Complete the canonical setup flow in `docs/GETTING_STARTED.md`.
- Use Python 3.12+ to match the package metadata.

## Run the test suite

### PowerShell (Windows)

```powershell
python -m pytest -q
```

### Bash (macOS/Linux)

```bash
python -m pytest -q
```

## Notes

- Deterministic smoke-run contract: see `docs/smoke-run.md`.
- Determinism gate: see `docs/testing/determinism.md`.
- Golden snapshot updates: see `docs/snapshot-testing.md`.
- Canonical API entry point is the `api` package under `src/api/` (via src layout).
- Test imports resolve this package through repo-controlled pytest config (`pytest.ini` sets `pythonpath = .` and `src`).

# Testing

## Setup

1) Create and activate a virtualenv:

```bash
python -m venv .venv
source .venv/bin/activate
```

2) Install test dependencies:

```bash
python -m pip install -e ".[test]"
```

This is the canonical test setup path because it uses the repository-controlled
`pyproject.toml` and its `test` optional dependency group. Use Python 3.12+ to
match the package metadata.

## Run the test suite

```bash
python -m pytest -q
```

## Notes

- Deterministic smoke-run contract: see `docs/smoke-run.md`.
- Determinism gate: see `docs/testing/determinism.md`.
- Golden snapshot updates: see `docs/snapshot-testing.md`.
- Canonical API entry point is the `api` package under `src/api/` (via src layout).
- Test imports resolve this package through repo-controlled pytest config (`pytest.ini` sets `pythonpath = .` and `src`).

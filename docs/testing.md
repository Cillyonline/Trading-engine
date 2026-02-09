# Testing

## Setup

1) Create and activate a virtualenv:

```bash
python -m venv .venv
source .venv/bin/activate
```

2) Install test dependencies:

```bash
pip install -r requirements-dev.txt
```

## Run the test suite

```bash
pytest -q
```

## Notes

- Deterministic smoke-run contract: see `docs/smoke-run.md`.
- Determinism gate: see `docs/testing/determinism.md`.
- Golden snapshot updates: see `docs/snapshot-testing.md`.
- Canonical API entry point is the `api` package under `src/api/` (via src layout).
- Test imports resolve this package through repo-controlled pytest config (`pytest.ini` sets `pythonpath = .` and `src`).

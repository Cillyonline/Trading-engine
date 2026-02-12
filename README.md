# Cilly Trading Engine

MVP v1 – Engine → SQLite → API → Trading Desk  

- Core architecture and scope: `docs/mvp_v1.md`
- Strategy configuration schema (RSI2, Turtle): `docs/strategy-configs.md`
- Local run & test commands: `docs/local_run.md`
- Canonical output snapshots (golden masters): `docs/snapshot-testing.md`
- Documentation index: `docs/index.md`

## Local CI checks

```bash
python -m compileall .
pytest
```

## Public API

The Python package-level public API for `src/api` is frozen to a single supported symbol:

- `from api import app`

Boundary policy:

- Only symbols exported via `src/api/__init__.py` are considered public/stable.
- All other modules and symbols under `src/api/**` are internal and may change without notice.

See `docs/api/public_api_boundary.md` for the full boundary definition.


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

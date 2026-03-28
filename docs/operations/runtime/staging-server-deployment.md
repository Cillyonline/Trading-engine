# Staging Server Deployment and Runtime Validation

## Purpose
This runbook defines the bounded, reproducible server deployment path for
non-productive staging mode. It is explicitly not a production or live-broker
contract.

## Canonical First-Deployment Install Path
The canonical first-deployment install path in this repository is:
- `docker compose -f docker/staging/docker-compose.staging.yml up -d --build`

## Deployment Artifacts
- Image build file:
  `docker/staging/Dockerfile`
- Compose stack:
  `docker/staging/docker-compose.staging.yml`
- Validation script:
  `scripts/validate_staging_deployment.py`

## Reproducible Build and Deploy Path
Run from repository root.

```bash
docker compose -f docker/staging/docker-compose.staging.yml config
docker compose -f docker/staging/docker-compose.staging.yml up -d --build
```

Reproducibility constraints in this path:
- Python base image is pinned (`python:3.12.8-slim`).
- Dependency resolution is lock-file gated
  (`uv sync --frozen --no-dev` with `uv.lock`).
- Runtime process entrypoint is fixed
  (`uvicorn api.main:app --host 0.0.0.0 --port 8000`).
- Legacy `requirements.txt` installation is non-canonical for first deployment
  in this repository contract.

## Health and Readiness Checks
Use read-only role headers for control-plane health endpoints.

```bash
curl -sS -H "X-Cilly-Role: read_only" http://127.0.0.1:18000/health
curl -sS -H "X-Cilly-Role: read_only" http://127.0.0.1:18000/health/engine
curl -sS -H "X-Cilly-Role: read_only" http://127.0.0.1:18000/health/data
curl -sS -H "X-Cilly-Role: read_only" http://127.0.0.1:18000/health/guards
```

Readiness expectations:
- `/health/engine` returns `ready: true`.
- `/health/data` returns `ready: true`.
- `/health/guards` returns `ready: true` and `decision: allowing` under
  bounded staging defaults.

## Logging and Observability Expectations
Staging runtime observability contract:
- Container logs are emitted to stdout and stderr.
- `CILLY_LOG_LEVEL=INFO` and `CILLY_LOG_FORMAT=json` are set in compose.
- Engine structured events are emitted as deterministic JSON log lines
  (schema `cilly.engine.log.v1`).
- Control-plane runtime visibility is available through `/health*`,
  `/runtime/introspection`, and `/system/state`.

Operator log tail command:

```bash
docker compose -f docker/staging/docker-compose.staging.yml logs -f api
```

## Restart-Safe Runtime Behavior
Runtime restart safety in this staging contract has two bounded expectations:
- Process lifecycle can re-enter running state after a prior stopped state.
- Container restart preserves SQLite-backed state through the mounted volume.

Operational restart check:

```bash
docker compose -f docker/staging/docker-compose.staging.yml restart api
curl -sS -H "X-Cilly-Role: read_only" http://127.0.0.1:18000/health/engine
```

Expected result:
- `/health/engine` reports `ready: true` after restart stabilization.

## Storage and Persistence Expectations
- Persistent volume:
  `cilly_staging_data` mounted to `/data`.
- Runtime working directory:
  `/data`.
- SQLite database file path resolves to
  `/data/cilly_trading.db` in this deployment profile.
- Deleting the named volume removes persisted staging state.

Reset command (destructive to staging state):

```bash
docker compose -f docker/staging/docker-compose.staging.yml down -v
```

## Bounded Staging Validation
Preferred single-command validation:

```bash
python scripts/validate_staging_deployment.py
```

Validation stages:
- Compose config resolution.
- Compose up/build.
- Health/readiness checks.
- API container restart.
- Post-restart health/readiness checks.
- Compose down cleanup (unless `--keep-running` is used).

Expected success markers:
- `STAGING_VALIDATE:CONFIG_OK`
- `STAGING_VALIDATE:UP_OK`
- `STAGING_VALIDATE:HEALTH_OK`
- `STAGING_VALIDATE:RESTART_OK`
- `STAGING_VALIDATE:POST_RESTART_HEALTH_OK`
- `STAGING_VALIDATE:DOWN_OK` (when `--keep-running` is not used)
- `STAGING_VALIDATE:SUCCESS`

## Test Gate
Repository validation remains mandatory:

```bash
python -m pytest
```

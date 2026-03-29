# Staging Server Deployment and Runtime Validation

## Purpose
This runbook defines the bounded staging deployment contract for non-live server
operation. It does not define production HA, broker integrations, or live
trading behavior.

The canonical first-deployment install path in this repository is:
`docker compose -f docker/staging/docker-compose.staging.yml up -d --build`

## Deployment Artifacts
Deployment artifacts used by this runbook:
- `docker/staging/Dockerfile`
- `docker/staging/docker-compose.staging.yml`
- `scripts/validate_staging_deployment.py`

Legacy `requirements.txt` installation is non-canonical for first deployment
in this repository contract.

## Canonical First-Deployment Install Path
The canonical first-deployment install path in this repository is:
`docker compose -f docker/staging/docker-compose.staging.yml up -d --build`

## Reproducible Build and Deploy Path
The canonical install path remains:
`docker compose -f docker/staging/docker-compose.staging.yml up -d --build`

```bash
docker compose -f docker/staging/docker-compose.staging.yml config
docker compose -f docker/staging/docker-compose.staging.yml up -d --build
```

Reproducibility constraints in this path:
- Base image and dependency resolution are pinned through repository deployment
  artifacts.
- Runtime process, health checks, and persistence bindings are compose-defined.

## Health and Readiness Checks
Use read-only role headers when validating control-plane health endpoints.

```bash
curl -sS -H "X-Cilly-Role: read_only" http://127.0.0.1:18000/health
curl -sS -H "X-Cilly-Role: read_only" http://127.0.0.1:18000/health/engine
curl -sS -H "X-Cilly-Role: read_only" http://127.0.0.1:18000/health/data
curl -sS -H "X-Cilly-Role: read_only" http://127.0.0.1:18000/health/guards
```

Readiness expectations:
- `/health/engine`, `/health/data`, and `/health/guards` report ready status
  for bounded staging operation.

## Logging and Observability Expectations
Operational logs are bounded to deployment use through compose-managed runtime
output and JSON log formatting for API events.

```bash
docker compose -f docker/staging/docker-compose.staging.yml logs -f api
```

## Restart-Safe Runtime Behavior
Restart safety is bounded to container restart with persisted state continuity.

```bash
docker compose -f docker/staging/docker-compose.staging.yml restart api
curl -sS -H "X-Cilly-Role: read_only" http://127.0.0.1:18000/health/engine
```

Expected result:
- Engine health returns ready and persisted runtime state remains recoverable
  through the configured staging data path.

## Storage and Persistence Expectations
Staging persistence is backed by the compose-managed `/data` volume; removing
the volume resets bounded staging state.

```bash
docker compose -f docker/staging/docker-compose.staging.yml down -v
```

## Bounded Staging Validation
Use the repository validation script to verify startup, health, logging, and
restart-safe persistence behavior in the bounded staging path.

```bash
python scripts/validate_staging_deployment.py
```

Validation stages:
- Compose config, startup, health checks, logging checks, restart checks, and
  persistence checks.

Expected success marker: `STAGING_VALIDATE:SUCCESS`.

## Test Gate
Repository gate for this issue:

```bash
python -m uv run -- python -m pytest --import-mode=importlib
```

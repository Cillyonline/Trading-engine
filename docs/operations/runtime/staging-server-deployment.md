# Staging Server Deployment and Runtime Validation

## Purpose
This runbook defines the bounded staging deployment contract for non-live server
operation. It does not define production HA, broker integrations, or live
trading behavior.

For a first-clean-server install in this repository, this runbook is the single
authoritative contract.

## Deployment Artifacts
Deployment artifacts used by this runbook:
- `docker/staging/Dockerfile`
- `docker/staging/docker-compose.staging.yml`
- `scripts/validate_staging_deployment.py`

Legacy `requirements.txt` installation is non-canonical for first deployment
in this repository contract.

## Canonical First-Clean-Server Install Contract
Docker/Compose is the canonical and only first-clean-server install path in this
repository.

The canonical first-clean-server startup command is:
`docker compose -f docker/staging/docker-compose.staging.yml up -d --build`

## Host Prerequisites and Package Contract
Required on host:
- Docker Engine (with `docker` CLI available)
- Docker Compose v2 plugin (`docker compose`)
- `curl` (for smoke and health validation commands)
- Python 3.12+ (required to run `python scripts/validate_staging_deployment.py`)

Optional on host:
- `uv` (not required for first-clean-server startup/smoke/restart validation,
  only used for optional repository-managed test execution wrappers)

## Required Directories and Persistence Paths
Required repository paths:
- `docker/staging/Dockerfile`
- `docker/staging/docker-compose.staging.yml`
- `scripts/validate_staging_deployment.py`

Required runtime persistence paths:
- Docker named volume: `cilly_staging_data`
- Container mount: `/data`
- SQLite file path: `/data/cilly_trading.db`

No host bind-mount directory is required by the canonical first-clean-server
path because persistence uses the named Docker volume above.

## Required Environment Variables (Bounded First Deploy / Paper Mode)
Required runtime environment variables for bounded first deployment:
- `PYTHONPATH=/app/src`
- `CILLY_DB_PATH=/data/cilly_trading.db`
- `CILLY_LOG_LEVEL=INFO`
- `CILLY_LOG_FORMAT=json`

## Exact Startup Commands
Run exactly from repository root:
```bash
docker compose -f docker/staging/docker-compose.staging.yml config
docker compose -f docker/staging/docker-compose.staging.yml up -d --build
```

Reproducibility constraints in this path:
- Base image and dependency resolution are pinned through repository deployment
  artifacts.
- Runtime process, health checks, and persistence bindings are compose-defined.

## Exact Smoke Commands
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

## Exact Restart Validation Commands
Restart safety is bounded to container restart with persisted state continuity.
```bash
docker compose -f docker/staging/docker-compose.staging.yml restart api
curl -sS -H "X-Cilly-Role: read_only" http://127.0.0.1:18000/health/engine
curl -sS -H "X-Cilly-Role: read_only" http://127.0.0.1:18000/health/data
curl -sS -H "X-Cilly-Role: read_only" http://127.0.0.1:18000/health/guards
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

## Conflicting Guidance Handling
Any local-run or local development installation guidance is non-canonical for
first-clean-server install. For first-clean-server install and startup, use this
runbook only.

## Acceptance-Gate Alignment
This deployment runbook defines the `server-ready (staging)` boundary only.

Status interpretation:
- `server-ready (staging)`: staging validation and readiness checks pass.
- `paper-install-ready`: requires the additional bounded acceptance gate in
  `docs/operations/runtime/paper-deployment-acceptance-gate.md`.

Required evidence output name used by the acceptance gate:
- `EVIDENCE_STAGING_VALIDATION_LOG` (captures this runbook's validation output).

## Test Gate
Repository gate for this issue:

```bash
python -m uv run -- python -m pytest --import-mode=importlib
```

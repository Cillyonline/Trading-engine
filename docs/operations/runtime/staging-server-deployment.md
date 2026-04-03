# Staging Server Deployment and Runtime Validation

## Purpose
This runbook defines the bounded staging deployment contract for non-live server
operation. It does not define production HA, broker integrations, or live
trading behavior.

For a first-clean-server install in this repository, this runbook is the single
authoritative contract.

## Access and Trust Boundary (Staging Paper)
Default access posture for staging paper operation is localhost-only:
- Bind and validate API access through `127.0.0.1` only.
- Treat `X-Cilly-Role` headers as bounded local operator-routing inputs, not as
  a public authentication model.
- Public or internet-exposed access without an external trust boundary is
  explicitly disallowed.

Remote access boundary:
- Remote access is out of default staging scope and remains unsupported unless
  an operator explicitly adds and owns an external trust boundary.
- External trust boundary decisions are operator-owned and out of this runbook's
  implementation scope.

Minimum safe operator-access posture for staging paper operation:
1. Keep API access localhost-only by default.
2. Use role headers only for bounded non-public operator workflows.
3. Do not expose the API publicly without an operator-managed external trust
   boundary.

## Deployment Artifacts
Deployment artifacts used by this runbook:
- `docker/staging/Dockerfile`
- `docker/staging/docker-compose.staging.yml`
- `.env.example`
- `scripts/validate_staging_deployment.py`

Legacy `requirements.txt` installation is non-canonical for first deployment
in this repository contract.

## Canonical First-Clean-Server Install Contract
Docker/Compose is the canonical and only first-clean-server install path in this
repository.

The canonical first-clean-server startup command is:
`docker compose --env-file .env -f docker/staging/docker-compose.staging.yml up -d --build`

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
- `.env.example`
- `scripts/validate_staging_deployment.py`

Required host bind-mounted directories (configure in `.env`):
- `CILLY_STAGING_DB_DIR` -> container `/data/db`
- `CILLY_STAGING_ARTIFACT_DIR` -> container `/data/artifacts`
- `CILLY_STAGING_JOURNAL_DIR` -> container `/app/runs/phase6`
- `CILLY_STAGING_LOG_DIR` -> container `/data/logs`
- `CILLY_STAGING_RUNTIME_STATE_DIR` -> container `/data/runtime-state`

Path definitions for bounded first deployment:
- Database path (persistent): `/data/db/cilly_trading.db`
- Artifact path (bind-mounted; writer behavior not guaranteed in this stage): `/data/artifacts`
- Journal path (persistent): `/app/runs/phase6`
- Runtime-state path (bind-mounted; in-memory runtime authority remains canonical): `/data/runtime-state`
- Log path (bind-mounted path reserved for operator tooling): `/data/logs`

Required persistent directories are explicit:
- Database host directory (`CILLY_STAGING_DB_DIR`) MUST persist across container restart/redeploy.
- Journal host directory (`CILLY_STAGING_JOURNAL_DIR`) MUST persist across container restart/redeploy.

## Required Environment Variables (Bounded First Deploy / Paper Mode)
Required runtime environment variables for bounded first deployment:
- `PYTHONPATH=/app/src`
- `CILLY_DB_PATH=/data/db/cilly_trading.db`
- `CILLY_LOG_LEVEL=INFO`
- `CILLY_LOG_FORMAT=json`

Required ownership/permission environment variables:
- `CILLY_CONTAINER_UID`
- `CILLY_CONTAINER_GID`

Required host path environment variables:
- `CILLY_STAGING_DB_DIR`
- `CILLY_STAGING_ARTIFACT_DIR`
- `CILLY_STAGING_JOURNAL_DIR`
- `CILLY_STAGING_LOG_DIR`
- `CILLY_STAGING_RUNTIME_STATE_DIR`

Conditional provider secret requirements are explicit:
- Canonical first paper deployment is snapshot-first and requires no provider
  secret variables.
- If a future provider integration is explicitly enabled, provider secrets are
  mandatory for that provider and are outside this stage contract.

## Ownership and Permission Expectations
Ownership expectations are explicit:
- Compose runs the API container as `${CILLY_CONTAINER_UID}:${CILLY_CONTAINER_GID}`.
- Each required host bind-mounted directory MUST be writable by this UID/GID.
- If host ownership differs, operators MUST pre-create directories and set
  ownership/permissions before `docker compose up`.

Unsupported in this stage:
- Automatic host permission repair inside the container.
- External secret manager integration.

## Exact Startup Commands
Run exactly from repository root:
```bash
cp .env.example .env
mkdir -p /srv/cilly/staging/db /srv/cilly/staging/artifacts /srv/cilly/staging/journal /srv/cilly/staging/logs /srv/cilly/staging/runtime-state
docker compose --env-file .env -f docker/staging/docker-compose.staging.yml config
docker compose --env-file .env -f docker/staging/docker-compose.staging.yml up -d --build
```

Reproducibility constraints in this path:
- Base image and dependency resolution are pinned through repository deployment
  artifacts.
- Runtime process, health checks, and persistence bindings are compose-defined.
- Required env and bind mounts are bounded and validated through compose variable
  expansion.

## Exact Smoke Commands
Use read-only role headers when validating control-plane health endpoints.
```bash
curl -sS -H "X-Cilly-Role: read_only" http://127.0.0.1:18000/health
curl -sS -H "X-Cilly-Role: read_only" http://127.0.0.1:18000/health/engine
curl -sS -H "X-Cilly-Role: read_only" http://127.0.0.1:18000/health/data
curl -sS -H "X-Cilly-Role: read_only" http://127.0.0.1:18000/health/guards
```

Readiness expectations:
- `/health` and `/health/engine` use `ready: true` as the canonical bounded
  staging readiness signal.
- If `/health` or `/health/engine` also include `runtime_status` or
  `runtime_reason`, those fields are freshness diagnostics and do not override a
  bounded-ready interpretation while `ready: true` remains true.
- `/health/engine`, `/health/data`, and `/health/guards` report ready status
  for bounded staging operation.

## Logging and Observability Expectations
Operational logs are bounded to deployment use through compose-managed runtime
output and JSON log formatting for API events.

```bash
docker compose --env-file .env -f docker/staging/docker-compose.staging.yml logs -f api
```

File-based log persistence in `/data/logs` is explicitly non-authoritative in
this stage; stdout/stderr compose logs remain authoritative.

## Exact Restart Validation Commands
Restart safety is bounded to container restart with persisted state continuity.
```bash
docker compose --env-file .env -f docker/staging/docker-compose.staging.yml restart api
curl -sS -H "X-Cilly-Role: read_only" http://127.0.0.1:18000/health/engine
curl -sS -H "X-Cilly-Role: read_only" http://127.0.0.1:18000/health/data
curl -sS -H "X-Cilly-Role: read_only" http://127.0.0.1:18000/health/guards
```

Expected result:
- Engine health returns ready and persisted runtime state remains recoverable
  through the configured staging data path.

## Storage and Persistence Expectations
Persistence expectations across restart and redeploy are explicit:
- Container restart (`docker compose restart api`) preserves DB and journal data.
- Container redeploy (`docker compose up -d --build`) preserves DB and journal
  data if bind-mounted host directories are unchanged.
- Deleting bind-mounted host directory contents resets bounded staging state.

```bash
docker compose --env-file .env -f docker/staging/docker-compose.staging.yml down --remove-orphans
```

## Bounded Staging Validation
Use the repository validation script to verify startup, health, logging, and
restart-safe persistence behavior in the bounded staging path.

```bash
python scripts/validate_staging_deployment.py
```

The validation script uses `.env` by default for all compose calls and accepts
`--env-file` only to override that bounded contract path explicitly.

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

## Session Progress Note (2026-04-03)
For the bounded server session progress verified on 2026-04-03, including
localhost binding correction, staging validation markers, and open follow-up
evidence steps, see:
- `docs/operations/runtime/staging-paper-progress-2026-04-03.md`

## Test Gate
Repository gate for this issue:

```bash
python -m uv run -- python -m pytest --import-mode=importlib
```

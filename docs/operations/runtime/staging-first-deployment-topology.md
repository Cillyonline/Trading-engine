# Staging-First Deployment Topology and Runtime Contract

## Goal
Define the canonical staging-first deployment topology, runtime contract, and
environment boundary for bounded non-live server operation.

## Canonical Topology Claim
Exactly one canonical staging-first topology is valid in this stage:
- one staging host
- one `api` service process (`uvicorn api.main:app`)
- one local SQLite persistence volume mounted at `/data`
- no broker process
- no live trading process

Primary deployment profile:
- `docker/staging/docker-compose.staging.yml`
- host port `18000` mapped to container port `8000`
- named volume `cilly_staging_data` mounted at `/data`

No alternative equal-status topology is defined for this stage.

## Canonical First-Deployment Install Path
The canonical first-deployment install path in this stage is:
- `docker compose -f docker/staging/docker-compose.staging.yml up -d --build`

## Runtime Topology

```text
[Operator client or bounded automation]
                 |
                 v
       [HTTP API: FastAPI/Uvicorn]
                 |
                 v
 [Engine runtime + control-plane lifecycle]
                 |
                 v
        [SQLite persistence at /data]
```

## Runtime Contract and Service Boundary
Required runtime services in this topology:
- HTTP API service (`api.main:app`)
- in-process engine runtime and control plane
- SQLite persistence file on the mounted staging volume

Operating assumptions:
- single runtime authority instance per staging host
- API and runtime share one process boundary in this stage
- bounded non-live operation only
- deterministic runtime behavior remains enforced by existing runtime contracts

Service boundaries:
- API/control plane: request validation, health exposure, runtime control.
- Engine runtime: lifecycle ownership, bounded execution orchestration, state
  transitions (`init`, `ready`, `running`, `paused`, `stopping`, `stopped`).
- Persistence: local SQLite durability only; no distributed storage or
  multi-writer assumptions.

## Environment Boundary
This deployment stage is explicitly bounded to staging and must not be mixed
with production-like scope.

Staging environment boundary:
- non-live server operation only
- no live order routing
- no broker integration dependency
- no production HA or horizontal scaling contract

Configuration layers for this stage:
1. Process environment (`PYTHONPATH`, `CILLY_LOG_LEVEL`, `CILLY_LOG_FORMAT`).
2. Runtime/API defaults from code-owned constants.
3. Request-scoped parameters supplied by API clients.
4. Strategy schema defaults and validation behavior.

Authoritative ownership of configuration semantics remains:
- `docs/architecture/configuration_boundary.md`

## Persistence, Logging, and Health Expectations
Persistence expectations at topology level:
- canonical persistence is SQLite at `/data/cilly_trading.db`
- durability boundary is the mounted staging volume (`cilly_staging_data`)
- volume removal resets staging state

Logging expectations at topology level:
- runtime logs emitted to stdout/stderr
- JSON logging contract remains enabled through environment settings
- no external observability backend is required for this stage

Health boundary expectations at topology level:
- `GET /health` and `GET /health/*` remain the primary readiness boundary
- readiness requires healthy engine runtime and data boundary
- health checks are non-broker and non-live by design

## Non-Goals and Excluded Runtime Modes
Explicit non-goals for this deployment stage:
- live trading
- broker integrations
- production high availability
- multi-region or active-active runtime
- unrelated UI redesign
- strategy logic changes

Excluded runtime modes:
- any runtime mode that places live market orders
- any runtime mode requiring external broker connectivity
- any runtime mode that assumes production SLO/SLA guarantees

## Install-Ready Versus Later Scope
`install-ready (staging)` and `paper-operational` remain distinct:
- `install-ready (staging)`: canonical topology is deployed and healthy.
- `paper-operational`: additional accepted evidence beyond deployment health.

Passing staging deployment validation does not declare production readiness.

## Validation and Verification Path
Canonical validation references:
- deployment runbook: `docs/operations/runtime/staging-server-deployment.md`
- bounded validation command: `python scripts/validate_staging_deployment.py`
- full repository gate: `python -m pytest`

## Related References
- `docs/operations/runbook.md`
- `docs/operations/runtime/staging-server-deployment.md`
- `docs/operations/runtime/paper-deployment-acceptance-gate.md`
- `docs/operations/runtime/paper-deployment-operator-checklist.md`
- `docs/architecture/engine_runtime_lifecycle_contract.md`
- `docs/architecture/configuration_boundary.md`

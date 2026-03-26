# Staging-First Deployment Topology and Runtime Contract

## Purpose
Define the canonical non-productive server deployment target for the engine.
This contract is staging-first and paper-trading-ready only after explicit
acceptance gates. It is not a production or live-trading declaration.

## Scope
In scope:
- Canonical server deployment target.
- Runtime topology and process boundaries.
- Environment and config separation.
- Runtime dependencies and storage expectations.
- Non-productive deployment scope and non-goals.

Out of scope:
- Live trading release.
- Broker connectivity.
- Full production HA design.
- Dashboard redesign.

## Canonical Deployment Target
The canonical server target is a single non-productive staging host running:
- one API/runtime process (`uvicorn api.main:app`)
- one local SQLite persistence volume
- no broker process
- no live execution integration

Primary deployment profile:
- `docker compose` using
  `docker/staging/docker-compose.staging.yml`
- single service: `api`
- mapped API port: `18000` (host) to `8000` (container)
- persistent volume mounted at `/data` for SQLite

This topology is the bounded default for staging and later paper-trading mode.
It must not be described as production-ready.

## Runtime Topology

```text
[Operator or automation client]
            |
            v
    [HTTP API: FastAPI/Uvicorn]
            |
            v
  [Engine runtime + control plane]
            |
            v
      [SQLite at /data]
```

### Topology Rules
- Exactly one runtime authority instance per staging host.
- API and runtime execute in the same process boundary in this topology.
- Persistence is local SQLite; no distributed storage assumptions.
- No external market or broker side effects are permitted.

## Runtime Responsibilities and Service Boundaries

### API and control-plane boundary
- Accepts and validates HTTP requests.
- Exposes health, introspection, and control endpoints.
- Delegates lifecycle state transitions to the engine-owned runtime controller.

### Engine runtime boundary
- Owns runtime lifecycle, analysis execution, and deterministic behavior
  contracts.
- Owns enforcement of runtime state transitions (`init`, `ready`, `running`,
  `paused`, `stopping`, `stopped`).
- Must not imply broker execution responsibilities in staging.

### Persistence boundary
- SQLite is the only canonical persistence dependency for this topology.
- Data durability is constrained to the mounted staging volume.
- Schema and init behavior remains owned by existing DB initialization code.

## Environment and Configuration Boundary
Configuration is explicitly separated into bounded layers:

1. Process environment layer:
   - `PYTHONPATH` for module resolution.
   - `CILLY_LOG_LEVEL` for logging verbosity.

2. Runtime defaults/constants layer:
   - Runtime and API module constants (for example API read limits).

3. Request-scoped layer:
   - Endpoint request payload values and strategy/runtime request fields.

4. Strategy schema layer:
   - Strategy defaults, normalization, and validation semantics.

Authoritative config ownership rules are defined in:
- `docs/architecture/configuration_boundary.md`

This deployment contract defines where configuration is supplied in staging
operations. It does not introduce new ownership semantics.

## Required Runtime Dependencies
Required for canonical staging deployment:
- Python runtime and project dependencies.
- FastAPI/Uvicorn runtime entrypoint (`api.main:app`).
- Writable filesystem path for SQLite data (`/data` in container profile).

Expected runtime artifacts and storage behavior:
- SQLite database file stored in mounted volume.
- Smoke-run artifacts under `artifacts/smoke-run/` when smoke-run is executed.
- No dependence on external broker services.

## Non-Productive Scope and Release Boundary
This topology is non-productive by default.

The deployment remains non-productive unless explicit future acceptance gates
are passed, including at least:
- paper-trading operator workflow acceptance
- explicit release/governance approval for mode change
- documented runtime safety and operational gate review

Until those gates exist and are accepted, this topology must be treated as:
- staging for controlled validation
- no live order execution
- no broker-integrated production behavior

## Validation and Verification Path

### Canonical Staging Artifact Path
- Docker image build:
  `docker/staging/Dockerfile`
- Compose stack:
  `docker/staging/docker-compose.staging.yml`
- Bounded validation command:
  `python scripts/validate_staging_deployment.py`
- Operator run instructions:
  `docs/operations/runtime/staging-server-deployment.md`

### Documentation Review
- Confirm this document is the canonical topology reference for staging-first
  server deployment.

### Config Validation (Compose Profile)
Run:

```bash
docker compose -f docker/staging/docker-compose.staging.yml config
```

Pass condition:
- Compose configuration resolves successfully.

### Smoke-Run Verification Path
Run:

```bash
PYTHONPATH=src python -c 'from cilly_trading.smoke_run import run_smoke_run; raise SystemExit(run_smoke_run())'
```

Pass condition:
- Exit code `0` with the documented deterministic smoke-run stdout contract.

### Full Test Suite Gate
Run:

```bash
python -m pytest
```

Pass condition:
- Full repository test suite remains green.

## Related References
- `docs/operations/runbook.md`
- `docs/operations/paper-trading.md`
- `docs/architecture/engine_runtime_lifecycle_contract.md`
- `docs/architecture/configuration_boundary.md`

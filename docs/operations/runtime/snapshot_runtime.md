# Snapshot Runtime – Scheduling & Ownership Status

## Status
IN-REPOSITORY EXECUTION CAPABILITY; EXTERNAL SCHEDULING RESPONSIBILITY

## Operational Boundary — Snapshot Runtime vs Scheduling
The snapshot runtime execution logic, including `execute_snapshot_runtime`, is implemented in this repository.

The runtime layer is deterministic and internally callable within repository-owned execution paths.

Scheduling mechanisms (for example cron jobs, infrastructure schedulers, or cloud trigger services) are external to this repository.

The repository does not provide a scheduler implementation.

Execution capability and scheduling responsibility are intentionally decoupled as a governance boundary.

Hourly Snapshot Runtime refers to execution capability, not in-repo scheduling.

## Current Implementation State
The repository contains snapshot runtime execution logic and deterministic runtime contracts.

The repository does not contain an internal scheduler, cron job, background worker, or runtime loop responsible for automated hourly triggering.

## Scheduling Responsibility
Scheduling remains an external operational responsibility.

This may include:
- External cron jobs
- Hosting platform schedulers
- CI-based scheduled triggers
- Infrastructure-level automation

No in-repository scheduler artifact exists.

## Ownership Boundary
The Cilly Trading Engine repository provides:
- Snapshot runtime execution logic
- Deterministic execution contracts

It does NOT provide:
- Scheduling orchestration
- Runtime background services
- Deployment-level automation

## Phase Planning Status
As of this document revision, there is no approved Phase defining an in-repo scheduler implementation.

Any future scheduler implementation must be:
- Defined in a dedicated Phase
- Backed by repository-verifiable artifacts
- Explicitly accepted via governance workflow

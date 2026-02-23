# Snapshot Runtime – Scheduling & Ownership Status

## Status
OUT-OF-BAND SCHEDULING

## Current Implementation State
The repository does not contain an internal scheduler,
cron job, background worker, or runtime loop
responsible for hourly snapshot execution.

Snapshot ingestion logic exists,
but scheduling is not implemented in-repo.

## Scheduling Responsibility
Snapshot scheduling is currently considered
an external operational responsibility.

This may include:
- External cron jobs
- Hosting platform schedulers
- CI-based scheduled triggers
- Infrastructure-level automation

No in-repository scheduler artifact exists.

## Ownership Boundary
The Cilly Trading Engine repository provides:
- Snapshot ingestion logic
- Deterministic execution contracts

It does NOT provide:
- Scheduling orchestration
- Runtime background services
- Deployment-level automation

## Phase Planning Status
As of this document revision,
there is no approved Phase defining
an in-repo snapshot scheduler implementation.

Any future scheduler implementation must be:
- Defined in a dedicated Phase
- Backed by repository-verifiable artifacts
- Explicitly accepted via governance workflow

## Explicit Declaration
Hourly snapshot scheduling remains
OUT-OF-BAND and is not implemented
as an in-repo runtime component.

This declaration removes ambiguity
regarding runtime scope and ownership.

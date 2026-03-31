# Snapshot Runtime - Scheduling & Ownership Status

## Status
IN-REPOSITORY SCHEDULED ANALYSIS CAPABILITY; SINGLE-SERVER BOUNDED EXECUTION

## Operational Boundary

The repository now includes one bounded in-process scheduled analysis runner for
server operation.

That runner is intentionally limited to:

- selecting the newest valid persisted snapshot deterministically
- executing bounded snapshot-only analysis tasks already covered by the
  authoritative API contracts
- executing persisted watchlists through the same bounded watchlist execution
  contract
- reusing existing deterministic request/result persistence keyed by
  `analysis_run_id`
- keeping symbol-level watchlist failures explicit and reviewable

The runner does not provide:

- live provider reads during analysis
- UI-triggered scheduling workflows
- distributed scheduling, leader election, or cross-host coordination
- general-purpose job orchestration

## Deterministic Snapshot Selection

The in-repository runner does not use an implicit "latest snapshot" shortcut.
Instead, it scans persisted `ingestion_runs` in deterministic order:

1. `created_at DESC`
2. `ingestion_run_id ASC`

It binds the scheduled task to the first run that satisfies the task-specific
validity rule:

- single-symbol analysis requires a ready and valid snapshot for the scheduled
  symbol and timeframe
- watchlist execution requires at least one valid snapshot-backed member symbol
  for the saved watchlist, while remaining member-symbol failures stay explicit
  in the response and persisted result payload

## Execution Boundaries

The scheduled runner reuses the existing authoritative server-side execution
paths:

- `POST /analysis/run` contract for canonical single-symbol analysis
- `POST /watchlists/{watchlist_id}/execute` contract for persisted watchlists

This means scheduled execution stays bounded to the same snapshot-only rules,
deterministic run identity rules, and persistence rules already enforced by the
manual operator paths.

## Single-Process Concurrency Rule

Only one scheduled execution loop may be active per server process.

Within that loop:

- only one scheduled pass may execute at a time
- overlapping wake-ups are skipped, not run in parallel
- repeated passes against the same newest valid snapshot are skipped after the
  task has already completed for that `ingestion_run_id`

This is a bounded single-server guard, not a distributed coordination claim.

## Ownership Boundary

The repository provides:

- deterministic scheduled analysis execution on the server
- deterministic snapshot selection rules
- reuse of existing attributable persistence for analysis and watchlist runs

The repository does not provide:

- deployment-wide orchestration across multiple hosts
- infrastructure scheduler management
- general scheduling platform capabilities

## Operational Configuration

The bounded runner is controlled by server configuration:

- `CILLY_SCHEDULED_ANALYSIS_ENABLED`
- `CILLY_SCHEDULED_ANALYSIS_POLL_INTERVAL_SECONDS`
- `CILLY_SCHEDULED_ANALYSIS_SNAPSHOT_SCAN_LIMIT`
- `CILLY_SCHEDULED_ANALYSIS_TASKS_JSON`

`CILLY_SCHEDULED_ANALYSIS_TASKS_JSON` defines the bounded scheduled work list.
Supported task kinds are:

- `analysis`: one canonical symbol/strategy analysis run
- `watchlist`: one persisted watchlist execution run

The configuration does not widen the repository contract beyond those bounded
task types.

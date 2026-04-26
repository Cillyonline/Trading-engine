# Repository Snapshot - Neutral Analysis for Onboarding

## Purpose of the Repository

This repository describes a bounded, non-live trading analysis engine intended
to support deterministic strategy analysis, snapshot-first data ingestion,
persistence, bounded evidence generation, and API inspection surfaces. Current
materials cover market data ingestion, indicator calculation, strategy-based
signal generation, deterministic smoke-run behavior, bounded backtest evidence,
portfolio/paper inspection surfaces, and bounded paper-runtime operations.

The repository remains explicitly non-live. Current documentation and runtime
boundaries do not authorize live trading, broker integrations, real-capital
order execution, production-readiness claims, trader-validation claims, or
AI-based signal generation.

## High-Level Project State

Current materials include detailed scope, architecture, workflow, runtime, and
deterministic contracts captured in markdown files. The documentation defines
bounded implementation evidence and the limits of that evidence. Where evidence
is partial, the wording remains conservative and defers phase status authority
to `ROADMAP_MASTER.md`.

Verified current surfaces include:

- deterministic smoke-run execution and documentation
- snapshot-first analysis through local API paths
- bounded backtest evidence contracts and tests
- bounded portfolio and paper inspection read surfaces
- bounded daily paper-runtime workflow and one-command runner documentation
- roadmap traceability and documentation-alignment governance for Phase 25 and
  Phase 26

These surfaces do not imply live-trading readiness, broker readiness, production
readiness, or trader validation.

## Repository Structure Overview

Top-level directories include:

- `docs/`: Documentation for scope, architecture, governance, operations,
  testing, runtime contracts, and specifications.
- `src/`: Core source code directory. Implementation details are not described
  in this snapshot.
- `tests/`: Test suite directory, including documentation and bounded contract
  tests.
- `fixtures/`: Deterministic fixture and sample snapshot data.
- `scripts/`: Bounded utility and operator helper scripts.

Documentation, governance, and specifications primarily live in `docs/`,
including runbooks, governance rules, MVP scope, runtime contracts, testing
contracts, and deterministic smoke-run specifications.

## Governance & Workflow Model

Work is structured around a single active issue with explicit acceptance
criteria, allowed files, and test expectations. The runbook defines a staged
process: define the issue and acceptance criteria, execute implementation,
verify with tests, pass a review gate, and close the issue with a PR linked to
the issue. Codex B implements the active issue, while Codex A provides a review
gate decision after tests and before merge.

Roadmap authority is split conservatively:

- `ROADMAP_MASTER.md` governs canonical phase maturity/status labels.
- `docs/architecture/roadmap/execution_roadmap.md` governs audited phase
  meaning and taxonomy.
- Secondary documents are evidence-bearing or explanatory unless their status
  claims are reflected in the authoritative roadmap surfaces.

## Key Documents

- `docs/operations/runbook.md`: Working SOP that defines the end-to-end
  workflow, review gate, Definition of Done, and deterministic smoke-run
  execution steps. It also points bounded paper-runtime operation to the
  dedicated OPS-P63 and OPS-P64 runtime documents.
- `docs/testing/smoke-run.md`: Deterministic smoke-run specification with exact
  fixtures, output, and exit codes.
- `docs/architecture/mvp-spec.md`: MVP scope and exclusions. Treat this as a
  scoped MVP document rather than a blanket denial of later bounded evidence.
- `docs/architecture/mvp-v1.md`: MVP v1 system overview and component
  breakdown with scope and non-goals.
- `docs/getting-started/local-run.md`: Canonical local development startup and
  API usage path.
- `docs/operations/runtime/p63-daily-bounded-paper-runtime-workflow.md`: Daily
  bounded paper-runtime workflow.
- `docs/operations/runtime/p64-one-command-bounded-daily-paper-runtime-runner.md`:
  One-command bounded daily paper-runtime runner contract.
- `docs/architecture/governance/*` and `docs/governance/*`: Governance
  documents for execution modes, claim boundaries, readiness separation, and
  review authority.

## Entry Points for a New Developer

A new developer can start with:

1. `README.md` for high-level orientation and pointers to core documents.
2. `docs/getting-started/getting-started.md` for local setup.
3. `docs/getting-started/local-run.md` for local API startup and snapshot-first
   analysis flow.
4. `docs/testing/index.md` and `docs/testing/smoke-run.md` for repository tests
   and deterministic smoke-run behavior.
5. `docs/operations/runbook.md` for issue workflow, review gates, and Definition
   of Done.
6. `docs/operations/runtime/p63-daily-bounded-paper-runtime-workflow.md` and
   `docs/operations/runtime/p64-one-command-bounded-daily-paper-runtime-runner.md`
   for bounded paper-runtime operation.
7. `ROADMAP_MASTER.md` for canonical phase maturity/status labels.

They should not expect a live trading workflow, broker connectivity,
real-capital order execution, production-readiness guarantee, or trader
validation evidence from the current repository. Bounded paper-runtime commands
and read surfaces exist for local/staging evidence workflows only.

## Known Gaps / Explicit Boundaries

The following remain explicit boundaries in the current repository state:

- No live trading workflow is authorized.
- No broker integration or real-capital execution path is authorized.
- Bounded paper-runtime evidence does not imply production readiness,
  operational readiness, trader validation, or profitability.
- Backtest and portfolio evidence remains bounded and must not be read as
  broker, live-trading, or production-readiness approval.
- AI-based signal generation or automated discretionary decision-making is not
  part of the current bounded implementation claim.

These boundaries are part of the current governed state rather than defects.

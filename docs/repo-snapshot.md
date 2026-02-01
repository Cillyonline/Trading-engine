# Repository Snapshot – Neutral Analysis for Onboarding

## Purpose of the Repository

This repository describes a trading analysis engine intended to support a website-based trading analysis tool with deterministic strategy outputs, persistence, and an API layer. The project targets market data ingestion, indicator calculation, strategy-based signal generation, and storage of results for retrieval through an API. The scope explicitly excludes live trading, broker integrations, order execution, portfolio management, backtesting frameworks, and AI-based signal generation in the current MVP definition. The deterministic smoke-run is specified but explicitly not implemented in the repository.

## High-Level Project State

Current materials include detailed scope, architecture, workflow, and deterministic contracts captured in markdown files. The documentation defines what the MVP should cover and what it excludes, while the deterministic smoke-run is defined as a spec-only contract with no implementation. Documentation states that paper trading/simulation is not available and that no smoke-run execution exists. Trading, simulation, and smoke-run execution are explicitly not implemented.

## Repository Structure Overview

Top-level directories include:

- `docs/`: Documentation for scope, architecture, governance, runbooks, and specifications (including the smoke-run spec and MVP documents).
- `documentation/`: Additional documentation content separate from `docs/` (directory present at the root level).
- `api/`: API-related source code directory (implementation details are not described here).
- `src/`: Core source code directory (implementation details are not described here).
- `tests/`: Test suite directory.
- `schemas/`: Schema definitions used by the project.
- `strategy/`: Strategy-related materials/configuration directory.
- `data/`: Data-related files and assets.
- `scripts/`: Utility or helper scripts.

Documentation, governance, and specifications primarily live in `docs/`, including the runbook, governance rules, MVP scope, and deterministic smoke-run specification.

## Governance & Workflow Model

Work is structured around a single active Issue with an explicit execution workflow. The runbook defines a staged process: define the issue and acceptance criteria, execute implementation, verify with tests, pass a review gate, and close the issue with a PR linked to the issue. Codex B implements the active Issue, while Codex A provides a review gate decision after tests and before merge. Test-gated execution mode defines non-negotiable requirements such as green CI, issue linkage in the PR, and Codex A review authority, with stop conditions and merge authority described in governance documents.

## Key Documents

- `RUNBOOK.md`: Working SOP that defines the end-to-end workflow, review gate, Definition of Done, and the statement that the deterministic smoke-run exists only as a spec. It also states that paper trading/simulation is not available.
- `docs/smoke-run.md`: Deterministic smoke-run specification with exact fixtures, output, and exit codes, explicitly marked as not implemented.
- `docs/MVP_SPEC.md`: Product scope and exclusions for MVP v1, including explicit exclusions such as live trading, broker integrations, backtesting, and AI-based signal generation.
- `docs/mvp_v1.md`: Detailed MVP v1 system overview and component breakdown (engine, persistence, API, and trading desk) with scope and non-goals.
- `docs/local_run.md`: Local development steps and API usage expectations, including the note that there is no CLI entrypoint and that the API is used directly.
- `docs/governance/*`: Governance documents for execution modes, test-gated execution requirements, and stop conditions/merge authority.

## Entry Points for a New Developer

A new developer can start with:

1. `README.md` for the high-level orientation and pointers to core documents.
2. `docs/MVP_SPEC.md` and `docs/mvp_v1.md` for scope, architecture, and MVP boundaries.
3. `RUNBOOK.md` and `docs/governance/*` for workflow, review gates, and test/merge rules.
4. `docs/local_run.md` for how the API is invoked in local development.
5. `docs/smoke-run.md` to understand the deterministic smoke-run contract that exists only as a spec.

They should not expect to run a smoke-run command, a paper-trading or simulation entrypoint, or a live trading workflow, because these are explicitly not implemented. There is also no CLI entrypoint documented; API usage via `uvicorn` is the described path. The documentation provides the scope and operational workflow; implementation specifics are in `src/` and `api/` and are outside the scope of this snapshot.

## Known Gaps / Non-Implemented Areas

The following components are explicitly absent or described as not implemented in the current repository state:

- Deterministic smoke-run execution (specification exists; implementation does not).
- Paper trading or simulation execution.
- Live trading, broker integrations, or order execution.
- Backtesting frameworks.
- AI-based signal generation or automated decision-making.
- A CLI entrypoint for running the engine; API-only invocation is documented.

These are documented as out of scope or not yet implemented, and are part of the current state rather than defects.

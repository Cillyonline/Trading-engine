# Repository Snapshot – Neutral Analysis for Onboarding

## Purpose of the Repository

This repository describes a trading analysis engine intended to support a website-based trading analysis tool with deterministic strategy outputs, persistence, and an API layer. The project targets market data ingestion, indicator calculation, strategy-based signal generation, and storage of results for retrieval through an API. The scope explicitly excludes live trading, broker integrations, order execution, portfolio management, backtesting frameworks, and AI-based signal generation in the current MVP definition. The deterministic smoke-run is implemented and documented in the runbook/spec.

## High-Level Project State

Current materials include detailed scope, architecture, workflow, and deterministic contracts captured in markdown files. The documentation defines what the MVP should cover and what it excludes, while the deterministic smoke-run is defined and implemented. An engine-level deterministic paper-trading simulator artifact is implemented and test-verified. This simulator does not provide live trading, broker integration, or a production operator runtime entrypoint.

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

- `docs/RUNBOOK.md`: Working SOP that defines the end-to-end workflow, review gate, Definition of Done, and the local deterministic smoke-run execution steps. It also documents that an engine-level deterministic paper-trading simulator artifact exists without introducing live trading, broker integrations, or a production operator runtime entrypoint.
- `docs/smoke-run.md`: Deterministic smoke-run specification with exact fixtures, output, and exit codes.
- `docs/MVP_SPEC.md`: Product scope and exclusions for MVP v1, including explicit exclusions such as live trading, broker integrations, backtesting, and AI-based signal generation.
- `docs/mvp_v1.md`: Detailed MVP v1 system overview and component breakdown (engine, persistence, API, and trading desk) with scope and non-goals.
- `docs/local_run.md`: Local development steps and API usage expectations, including the note that there is no CLI entrypoint and that the API is used directly.
- `docs/governance/*`: Governance documents for execution modes, test-gated execution requirements, and stop conditions/merge authority.

## Entry Points for a New Developer

A new developer can start with:

1. `README.md` for the high-level orientation and pointers to core documents.
2. `docs/MVP_SPEC.md` and `docs/mvp_v1.md` for scope, architecture, and MVP boundaries.
3. `docs/RUNBOOK.md` and `docs/governance/*` for workflow, review gates, and test/merge rules.
4. `docs/local_run.md` for how the API is invoked in local development.
5. `docs/smoke-run.md` to understand the deterministic smoke-run contract and its implementation details.

They should not expect a production operator CLI/entrypoint for paper-trading simulation, and they should not expect a live trading workflow. The deterministic paper-trading simulator exists as an engine-level, test-verified artifact only, with no broker connectivity or real-capital execution path. There is no CLI entrypoint documented; API usage via `uvicorn` is the described path, and the smoke-run is executed via the documented local command. The documentation provides the scope and operational workflow; implementation specifics are in `src/` and `api/` and are outside the scope of this snapshot.

## Known Gaps / Non-Implemented Areas

The following components are explicitly absent or described as not implemented in the current repository state:

- A production operator CLI/runtime entrypoint for paper-trading simulation (the engine-level deterministic simulator artifact exists and is test-verified).
- Live trading, broker integrations, or order execution.
- Backtesting frameworks.
- AI-based signal generation or automated decision-making.
- A CLI entrypoint for running the engine; API-only invocation is documented.

Deterministic smoke-run execution is implemented and documented in the runbook/spec.
These are documented as out of scope or not yet implemented, and are part of the current state rather than defects.

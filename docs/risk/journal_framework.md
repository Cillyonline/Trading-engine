# Journal Framework – Architectural Boundary Declaration

## 1. Purpose
The journal framework defines the deterministic decision trace artifact layer. It captures portfolio decision outcomes in a stable, reproducible `DecisionTrace` artifact for governance, auditability, and verification.

## 2. Scope
Included in scope:
- `engine/journal_framework` module.
- `DecisionTrace` immutable contract.
- Deterministic trace generation from:
  - `PortfolioExposureSummary`.
  - `CapitalAllocationAssessment`.
- Canonical serialization and deterministic trace ID generation.
- Deep-freeze and immutability expectations for trace payload structures.
- Test-enforced determinism across repeated runs with identical inputs.

## 3. Non-Goals (Out of Scope)
Explicitly out of scope:
- Execution logic.
- Broker logging.
- Persistence infrastructure (databases/files).
- Observability tooling.
- Live trading integration.

## 4. Architectural Boundary
The journal framework is a standalone boundary:
- Positioned above Portfolio Framework outputs.
- No runtime wiring into execution paths.
- No side effects.
- Strict isolation from execution, broker, orchestrator, and risk framework domains.

## 5. Import Direction Rules
Import rules are mandatory:
- MAY import: Python stdlib, `engine.portfolio_framework.*`.
- MUST NOT import: `engine.execution*`, `engine.orchestrator*`, `engine.broker*`, `engine.risk_framework*`, `src.*`.
- Any import-boundary violation must fail CI.

## 6. Relationship to Portfolio Framework
- Portfolio Framework computes exposure outputs and capital enforcement outcomes.
- Journal Framework consumes those outputs and produces `DecisionTrace` artifacts.
- Journal Framework does not modify, override, or reinterpret portfolio enforcement results.

## 7. Determinism Guarantees
The journal framework guarantees deterministic output by design:
- No global state.
- No I/O.
- No time dependence.
- No randomness.
- Stable ordering and canonical JSON serialization.
- Identical input yields identical output.
- Trace identity is derived via deterministic SHA256 hashing.

## 8. Guardrails
Enforced guardrails:
- Immutable dataclasses only.
- Pure functions only.
- Import boundaries enforced via AST tests.
- Coverage expectation: `>=95%` for `engine/journal_framework`.

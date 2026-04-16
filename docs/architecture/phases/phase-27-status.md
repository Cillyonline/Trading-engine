# Phase 27 - Risk Framework

## Document Role
Derived evidence snapshot for Phase 27 risk-framework artifacts.

Canonical authority:
- Phase maturity/status labels: `ROADMAP_MASTER.md`
- Audited phase taxonomy/meaning: `docs/architecture/roadmap/execution_roadmap.md`

## Taxonomy Alignment
Phase 27 means `Risk Framework` in the authoritative taxonomy source:
`docs/architecture/roadmap/execution_roadmap.md`

This phase remains distinct from Phase 27b pipeline-enforcement artifacts.

## Verified Existing Artifacts
The repository contains standalone Phase 27 risk-framework artifacts, including:
- Risk contracts in `src/risk/contracts.py`
- Concrete risk-gate implementation and guard helpers in `src/cilly_trading/engine/risk/gate.py`
- Risk framework architecture artifacts in `docs/architecture/risk_framework.md` and `docs/architecture/risk/risk_framework.md`
- Pipeline integration using `RiskGate` in `src/cilly_trading/engine/pipeline/orchestrator.py`
- Risk-gate tests in `tests/cilly_trading/engine/test_risk_gate.py`
- Execution-path enforcement tests in `tests/cilly_trading/engine/test_risk_enforcement_bypass.py`, `tests/cilly_trading/engine/test_order_execution_model.py`, and `tests/cilly_trading/engine/test_observability_integration.py`

## Current Evidence Boundary
Verified repository evidence supports that Phase 27 is no longer accurately described as "not implemented" or "no standalone framework artifact verified."

This status artifact records verified framework artifacts only. It does not redefine Phase 27 taxonomy and does not treat Phase 27b as interchangeable with Phase 27.

## Explicit Declaration
As of this revision, repository-verifiable Risk Framework artifacts exist for Phase 27.
Phase 27 evidence should not be described in audited documents as absent where these artifacts are present.
This file does not set canonical phase maturity/status.

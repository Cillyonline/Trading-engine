# Phase 25 - Strategy Lifecycle Management

## Document Role
Derived evidence snapshot for Phase 25 lifecycle artifacts.

Canonical authority:
- Phase maturity/status labels: `ROADMAP_MASTER.md`
- Audited phase taxonomy/meaning: `docs/architecture/roadmap/execution_roadmap.md`

## Taxonomy Alignment
Phase 25 means `Strategy Lifecycle Management` in the authoritative taxonomy source:
`docs/architecture/roadmap/execution_roadmap.md`

## Objective
Phase 25 covers the strategy lifecycle governance artifacts that are verifiably present in this repository:
- Lifecycle state model
- Deterministic transition matrix
- Promotion service API
- Production-only execution enforcement in the orchestrator

## Verified Repository Evidence
- Lifecycle state model: `src/cilly_trading/engine/strategy_lifecycle/model.py`
- Transition rules: `src/cilly_trading/engine/strategy_lifecycle/transitions.py`
- Promotion service API: `src/cilly_trading/engine/strategy_lifecycle/service.py`
- Production-only orchestration enforcement: `src/cilly_trading/engine/pipeline/orchestrator.py`
- State-model tests: `tests/strategy_lifecycle/test_state_model.py`
- Transition-matrix tests: `tests/strategy_lifecycle/test_transitions.py`
- Promotion-service tests: `tests/strategy_lifecycle/test_service.py`
- Orchestrator enforcement tests: `tests/cilly_trading/engine/test_orchestrator_lifecycle_enforcement.py`

## Lifecycle States
The verified lifecycle model defines four states:
- **DRAFT**
- **EVALUATION**
- **PRODUCTION**
- **DEPRECATED**

**Terminal state definition:**
- **DEPRECATED** is the terminal state. No transitions are permitted out of DEPRECATED.

## Promotion Rules
Verified allowed transitions are:
- DRAFT -> EVALUATION
- DRAFT -> DEPRECATED
- EVALUATION -> PRODUCTION
- EVALUATION -> DEPRECATED
- PRODUCTION -> DEPRECATED

All other transitions are rejected by lifecycle governance.

## Execution Enforcement Rule
Execution is governed by a strict production-only policy:
- Only **PRODUCTION** strategies may execute.
- The orchestrator checks lifecycle state before execution.
- Non-production strategies are rejected before execution.

## Explicit Declaration
This artifact is evidence-based and reflects repository artifacts present and tested in-tree.
It does not set canonical phase maturity/status.

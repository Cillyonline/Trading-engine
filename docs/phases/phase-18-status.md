# Phase 18 — Operational Snapshot Runtime

## 1. Goal

Phase 18 introduces the Operational Snapshot Runtime as a governance-tracked execution phase positioned between Phase 17b (Owner Dashboard) and Phase 23 (Research Dashboard / Metrics integration).

The purpose of this phase is to formalize deterministic snapshot execution capability and runtime observability as explicit, repository-verifiable governance artifacts.

## 2. Explicit Deliverables

Phase 18 delivers the following explicit artifacts:

- Deterministic snapshot runtime entrypoint: `execute_snapshot_runtime` in `src/cilly_trading/engine/phase6_snapshot_contract.py`.
- Runtime determinism validation tests in `tests/test_phase6_snapshot_contract.py`, including deterministic repeat-run assertions for snapshot execution.
- Runtime status contract (observability status object) in `src/cilly_trading/engine/phase6_snapshot_contract.py`, including persisted runtime status retrieval and structured status fields.
- Governance declaration of runtime vs scheduling boundary in `docs/runtime/snapshot_runtime.md` and `docs/interfaces/batch_execution.md`.
- Documentation artifacts defining the operational boundary in `docs/runtime/snapshot_runtime.md` and `docs/audit/roadmap_compliance_report.md`.

## 3. Explicitly Out of Scope

Phase 18 explicitly excludes the following:

- Scheduler implementation.
- Cron or background workers.
- Dashboard UI changes.
- Risk logic changes.
- Trading logic changes.
- Live trading.
- Broker integration.

## 4. Acceptance Evidence Requirements

Phase 18 is complete only when all of the following conditions are satisfied:

- Deterministic runtime execution exists in-repo.
- A runtime status artifact is retrievable via an internal interface.
- The governance boundary between execution and scheduling is documented.
- Associated tests pass in CI.
- Documentation artifacts exist and are reviewable.

## 5. Roadmap Alignment

This phase status artifact aligns to the canonical Execution Roadmap in `docs/roadmap/execution_roadmap.md`.

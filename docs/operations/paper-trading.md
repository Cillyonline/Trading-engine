# Paper Trading

## Scope
The repository contains a deterministic engine-level paper-trading simulator. It is intended for governed simulation workflows and readiness validation, not for live execution.

## Verified Artifacts
- Simulator implementation: `src/cilly_trading/engine/paper_trading.py`
- Simulator tests: `tests/test_paper_trading_simulator.py`
- Related runtime and persistence integration appears in the engine and trade persistence surfaces.

## Current Capability
- Deterministic simulated order and position handling is implemented in-repo.
- The simulator is suitable for controlled paper-trading validation inside the repository boundary.
- The simulator does not require a broker connection and does not place real orders.
- Deterministic paper order lifecycle simulation is implemented with explicit Trading Core states and transitions.

## Deterministic Paper Order Lifecycle
- Submission flow is explicit: `created -> submitted`.
- Fill progression is explicit and bounded: `submitted -> partially_filled -> filled`.
- Cancel progression is explicit and bounded: `submitted -> cancelled` and `partially_filled -> cancelled`.
- Terminal states are explicit and enforced: `filled`, `cancelled`, `rejected`.
- Fill quantities are bounded per step by remaining quantity and optional per-step cap.
- Representative lifecycle simulations are reproducible for identical request/step inputs.

## Trading Core Alignment
- Paper order states use the canonical Trading Core order status values.
- Transition legality and invariant checks are validated through the shared lifecycle guardrails.
- Fill/cancel lifecycle events use canonical execution event shapes and deterministic event identity.
- Paper inspection/account state is derived from canonical Trading Core entities (`Order`, `ExecutionEvent`, `Trade`) and derived canonical `Position` state, without legacy paper-trade payloads as authoritative truth.

## Runtime State Flow (Authoritative)
1. Paper order lifecycle simulator produces canonical order and execution-event transitions.
2. Canonical entities are persisted through the Trading Core repository boundary.
3. Canonical trades are read from Trading Core persistence for paper inspection.
4. Canonical positions are deterministically derived from canonical trade/order/event relations.
5. Paper account totals (`cash`, `equity`, `pnl`) are derived from canonical trade and position state.

## Explicit Boundaries
- No live trading is implemented.
- No broker integration runtime is implemented.
- No owner-facing production runtime command for paper-trading execution is declared in the runbook.
- This document does not claim a complete user-facing paper-trading product workflow.

## Server Deployment Acceptance Gate
For server-based paper usage, "running on a server" is not sufficient.

Staging install readiness and paper-operational readiness are separate states:
- Staging install readiness: deployment mechanics and runtime health checks pass.
- Paper-operational readiness: staging readiness plus acceptance evidence defined
  in `docs/operations/runtime/paper-deployment-acceptance-gate.md`.

Operator sign-off must use:
- `docs/operations/runtime/paper-deployment-operator-checklist.md`

Passing the paper-operational gate still does not imply live-trading readiness
or broker go-live approval.

## Roadmap Readiness Interpretation
- Phase 24 focuses on documentation and governance alignment for the simulator and its boundaries.
- Phase 44 remains the broader paper-trading product phase and should only be treated as complete when workflow, operator surfaces, and broader runtime handling are fully verified.

# Paper Deployment Acceptance Gate (Staging -> Paper-Operational)

## Purpose
Define the explicit acceptance gate that must pass before a server deployment is
treated as paper-operational for serious paper-trading usage.

This gate exists to prevent a false equivalence between:
- "the engine is installed and running on a server", and
- "the engine is operationally ready for paper-trading decisions".

## Scope
In scope:
- staging-to-paper acceptance gate definition
- minimum evidence categories and pass requirements
- operator-facing decision rule for paper-operational declaration

Out of scope:
- live-trading go-live criteria
- broker launch process
- product/marketing readiness claims

## Boundary: Server Install vs Paper-Operational
Server install readiness is a prerequisite only. It means deployment mechanics
and basic runtime health checks pass on a staging host.

Paper-operational readiness is a stricter state. It is reached only when all
acceptance-gate evidence categories in this document are satisfied.

Decision rule:
- If any required evidence item is missing or fails, status remains `staging`.
- Only when every required evidence item passes, status may be declared
  `paper-operational`.

## Required Evidence Categories (Minimum)

### 1) Backtesting Evidence
Minimum required evidence:
- A bounded backtest evidence set exists for the exact strategy/config inputs
  intended for paper usage.
- Evidence includes run context (symbol universe, timeframe/window, config
  identity, and execution timestamp).
- The evidence shows deterministic reproducibility for the same inputs (no
  unexplained result drift between repeated runs).
- Any strategy candidate proposed for paper usage has no unresolved blocking
  risk findings in the recorded evidence set.

### 2) Decision-Card Behavior Evidence
Minimum required evidence:
- Decision cards are produced and reviewable for the candidates in scope.
- Contract behavior is consistent with documented semantics in
  `docs/architecture/decision_card_contract.md`.
- Blocking hard-gate failures resolve to reject outcomes.
- Candidates considered for paper operation resolve only through explicit
  qualification states (`paper_candidate` or `paper_approved`), with rationale
  fields present.

### 3) Runtime Health Evidence
Minimum required evidence:
- Staging deployment validation passes using
  `python scripts/validate_staging_deployment.py`.
- Required success markers are captured, including
  `STAGING_VALIDATE:SUCCESS`.
- Read-only health endpoints show readiness for `engine`, `data`, and `guards`
  according to `docs/operations/runtime/staging-server-deployment.md`.
- Restart validation is included and health remains ready after restart.

### 4) Paper-Trading Consistency Evidence
Minimum required evidence:
- Paper-trading lifecycle behavior remains deterministic and bounded to
  simulation-only semantics.
- Canonical paper-trading tests remain passing, including
  `tests/test_paper_trading_simulator.py`.
- Paper inspection outputs are consistent with canonical order/event/trade
  semantics documented in `docs/operations/paper-trading.md`.
- Evidence explicitly confirms no live order routing or broker side effects.

## Mandatory Validation Artifacts
The following artifacts are required for gate review:
- Completed operator checklist:
  `docs/operations/runtime/paper-deployment-operator-checklist.md`
- Captured staging validation output including success markers.
- Captured repository test evidence (`python -m pytest` remains mandatory).

## Operator Gate Outcome
Use the operator checklist final decision rule:
- Any `NO` item -> Gate result `NOT ACCEPTED`, deployment remains `staging`.
- All items `YES` -> Gate result `ACCEPTED`, deployment may be treated as
  `paper-operational` (still non-live, non-broker).

## Explicit Non-Goals Relative to Live Trading
Passing this gate does not imply:
- live-trading readiness
- broker connectivity approval
- capital-at-risk authorization
- production incident/SRE maturity for live execution


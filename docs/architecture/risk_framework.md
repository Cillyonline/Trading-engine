# Risk Framework Architecture

## Purpose
The risk framework defines a **mandatory, pre-execution gate** that every candidate execution request must pass before any order-side effect is allowed. This document establishes the architecture contract and governance rule for risk evaluation, independent of execution implementation details.

## Architectural Position
- Risk evaluation sits at the boundary between intent generation and execution authorization.
- The risk layer owns policy evaluation and explicit decision output only.
- The execution layer is a downstream consumer of a `RiskDecision` contract and is not permitted to bypass it.
- This architecture is design-level only in Phase P27 and introduces no runtime wiring.

## RiskGate Interface (Contract Only)
The canonical risk contract is defined in `src/risk/contracts.py`:
- `RiskGate.evaluate(request) -> RiskDecision`
- `RiskEvaluationRequest` is a placeholder request shape for stable contract exchange.
- `RiskGate` is a minimal protocol with no side effects and no runtime dependencies on execution, simulator, or lifecycle modules.

Contract stability principles:
1. Keep the interface minimal and deterministic.
2. Return explicit decision objects, never boolean pass/fail values.
3. Preserve compatibility by versioning policy via `rule_version` in `RiskDecision`.

## RiskDecision Model
`RiskDecision` is the mandatory schema for risk outcomes and includes:
- `decision: "APPROVED" | "REJECTED"`
- `score: float`
- `max_allowed: float`
- `reason: str`
- `timestamp: datetime (UTC)`
- `rule_version: str`

Interpretation:
- `APPROVED` means the request is eligible for execution authorization.
- `REJECTED` means execution authorization must not occur.
- `score` and `max_allowed` provide traceable policy context for audit and governance.

## Exposure Scoring Concept
Exposure scoring is a normalized risk measure computed per request.

Conceptual components (documentation-level):
- Position sizing pressure (e.g., requested notional relative to configured limits)
- Concentration pressure (e.g., symbol or strategy concentration)
- Market condition pressure (e.g., volatility/illiquidity multipliers)
- Policy overlays (e.g., temporary tightening rules)

The resulting `score` is compared to `max_allowed` under the active `rule_version`. The scoring algorithm is intentionally unspecified here and remains implementation-defined in later phases.

## Enforcement Boundary
**Boundary definition:**
- Upstream systems may create candidate requests.
- Only the risk framework may issue `RiskDecision`.
- Downstream execution authorization requires a `RiskDecision` with `decision == "APPROVED"`.
- Any missing decision, malformed decision, or `REJECTED` decision is treated as a hard stop.

This boundary prohibits advisory-only risk behavior for execution eligibility.

## Governance Enforcement Rule
**Mandatory rule:** No execution authorization is permitted unless a valid `RiskDecision` exists and its `decision` field is exactly `"APPROVED"`.

Governance implications:
- `REJECTED` is terminal for the candidate request.
- Absence of risk evaluation is equivalent to rejection.
- Boolean-style checks (`True`/`False`) are non-compliant with the architecture contract.
- Policy changes must be traceable through `rule_version`.

## Non-Goals
- No execution refactor or runtime integration in this phase.
- No simulator changes.
- No lifecycle or orchestration changes.
- No portfolio model updates.
- No definition of concrete scoring implementation details beyond conceptual architecture.

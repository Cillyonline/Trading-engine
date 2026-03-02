# Portfolio Framework – Architectural Boundary Declaration

## 1. Purpose

The portfolio framework is the deterministic aggregation and capital allocation boundary for portfolio-level controls.

Its purpose is to:
- Aggregate exposures across strategies in a deterministic manner.
- Enforce portfolio-level capital allocation constraints.
- Provide predictable, repeatable outcomes for identical inputs.

## 2. Scope

The portfolio framework scope is explicitly limited to:

- **Exposure aggregation**
  - Deterministic aggregation of exposure inputs across participating strategies and positions.
- **Capital allocation enforcement**
  - Deterministic enforcement of cross-strategy capital limits, caps, and allocation constraints.
- **Deterministic behavior**
  - All outputs are fully determined by provided inputs and configuration.
- **Pure-function constraint**
  - Computation is implemented as pure transformations with no side effects.

## 3. Non-Goals (Out of Scope)

The following areas are explicitly out of scope for the portfolio framework:

- Trading logic
- Broker integration
- Optimization theory
- Execution integration
- Live rebalancing
- RiskEvaluator override

## 4. Architectural Boundary

The portfolio framework boundary is defined as follows:

- The portfolio framework is a standalone module.
- It operates above request-level risk enforcement.
- It does not call execution or broker layers.
- It must remain import-safe and side-effect free.

## 5. Import Direction Rules

Import direction is constrained by the following rules:

- `engine.portfolio_framework` **MAY** import:
  - Python standard library (`stdlib`)
  - `engine.portfolio_framework.*`

- `engine.portfolio_framework` **MUST NOT** import:
  - `engine.execution`
  - `engine.orchestrator`
  - `engine.broker`
  - `src.*`

- Higher layers **MAY** depend on `engine.portfolio_framework`.

## 6. Relationship to Risk Framework

The relationship between frameworks is defined as:

- The risk framework enforces per-request constraints.
- The portfolio framework enforces cross-strategy capital caps.
- No bidirectional dependency is permitted.

## 7. Determinism Guarantees

The portfolio framework must satisfy all determinism guarantees below:

- No global state.
- No IO.
- No time-dependence.
- No randomness.
- Stable ordering guarantees.
- Equal input → equal output.

## 8. Guardrails

The following guardrails are mandatory:

- Pure functions only.
- Immutable contracts.
- Coverage expectations are defined and maintained for framework behavior.
- Enforcement must be test-verified.

# Compliance & Safety Layer Architecture

## 1. Purpose

The Compliance & Safety layer is an execution-time control boundary that evaluates hard safety and governance constraints after risk acceptance and before execution dispatch.

Its purpose is to ensure that the trading engine can deterministically prevent order routing when predefined safety conditions are violated, without altering strategy outputs or portfolio state.

## 2. Architectural Position

Canonical pipeline:

`Trigger → Analysis → Signal → Risk Gate → Execution Adapter → Journal`

Extended pipeline with Compliance & Safety:

`Trigger → Analysis → Signal → Risk Gate → Compliance Guards → Execution Adapter → Journal`

The Compliance Guards stage is inserted strictly between `Risk Gate` and `Execution Adapter`.

- Inputs: risk-approved execution intent and current in-process runtime context.
- Output: binary decision (`allow` or `block`) for execution continuation.
- Side effects: none outside control flow gating.

## 3. Guard Categories

The Compliance & Safety layer contains the following guard categories.

### 3.1 Global Kill Switch

**Purpose**
- Provide an immediate, system-wide administrative stop mechanism.

**Behavior**
- When active, all execution intents are blocked.
- When inactive, this guard passes control to the next guard.

**Dependencies**
- Deterministic in-process kill-switch state source (e.g., runtime configuration/state flag loaded locally).

### 3.2 Maximum Drawdown Guard

**Purpose**
- Prevent further execution once configured maximum drawdown limits are breached.

**Behavior**
- Compares current drawdown metric to configured maximum drawdown threshold.
- Blocks execution if current drawdown exceeds or equals threshold.
- Allows execution otherwise.

**Dependencies**
- Deterministic, locally available drawdown metric derived from internal portfolio/accounting state.
- Static/local configuration threshold.

### 3.3 Daily Loss Limit Guard

**Purpose**
- Enforce a daily loss cap to reduce intraday capital erosion.

**Behavior**
- Compares realized and/or marked daily P/L against configured daily loss limit.
- Blocks execution when daily loss limit is reached or exceeded.
- Allows execution otherwise.

**Dependencies**
- Deterministic, locally computed daily P/L metric.
- Trading-day boundary definition from internal clock/session calendar rules.
- Static/local configuration threshold.

### 3.4 Emergency Execution Stop

**Purpose**
- Provide a dedicated emergency halt independent of strategy/risk signals for critical operating conditions.

**Behavior**
- If emergency stop condition is active, block all execution intents.
- If inactive, pass control to downstream outcome.

**Dependencies**
- Deterministic local emergency state source (in-process flag or equivalent local state).

## 4. Guard Evaluation Order

Guards are evaluated in a strict, deterministic sequence:

1. Global Kill Switch
2. Emergency Execution Stop
3. Maximum Drawdown Guard
4. Daily Loss Limit Guard

Evaluation model:

- Short-circuit blocking: first blocking guard terminates evaluation and returns `block`.
- Full pass requirement: execution is allowed only if every guard returns `allow`.
- Stable ordering is mandatory and must not vary by runtime conditions.

## 5. Determinism Requirements

All Compliance Guards must be deterministic:

- Identical inputs must produce identical `allow/block` outcomes.
- No dependence on nondeterministic or remote state.
- No asynchronous external fetches during decision evaluation.
- Time usage (if any) must be based on standardized internal clock semantics already available to the engine runtime.

## 6. Architectural Constraints

Compliance Guards must:

- Be deterministic.
- Not call external services.
- Not modify portfolio state.
- Not modify signals.
- Not trigger execution.

Permitted action surface:

- Allow execution to proceed.
- Block execution from proceeding.

They function as policy gates only, not as transformation or execution components.

## 7. Integration Points

Primary integration points in the engine flow:

1. **Upstream input from Risk Gate**
   - Receives execution intents that already passed risk validation.

2. **Downstream control to Execution Adapter**
   - Forwards intent only when all guards allow.
   - Prevents adapter invocation when any guard blocks.

3. **Journal coupling**
   - Guard decision outcome is expected to be journaled by existing journaling mechanisms as part of normal pipeline observability.
   - Compliance layer does not directly perform execution or state mutation.

## 8. Non-Goals

The Compliance & Safety layer does not:

- Replace risk modeling or strategy logic.
- Re-score or rewrite trade signals.
- Execute hedging, liquidation, or corrective orders.
- Introduce external policy decision services.
- Provide discretionary/manual signal generation.

## 9. Summary

The Compliance & Safety architecture introduces a deterministic guard stage between Risk Gate and Execution Adapter.

By evaluating Global Kill Switch, Emergency Execution Stop, Maximum Drawdown, and Daily Loss constraints in a fixed short-circuit order, the layer enforces governance boundaries while preserving existing strategy, risk, execution, and journaling responsibilities.

Its design is intentionally minimal: policy gating only, with binary allow/block outcomes and no mutation of signals, portfolio state, or execution pathways.

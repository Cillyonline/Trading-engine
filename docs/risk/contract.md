# P27-DESIGN Risk Evaluation Contract

## Purpose
This document defines the deterministic and immutable contract surface for risk
assessment in Issue #482.

## Module
- `engine/risk_framework/contract.py`

## Design Constraints
- Use frozen dataclasses.
- No business logic.
- No imports from `engine.execution` or `engine.orchestrator`.
- Deterministic contract behavior through explicit, value-based fields.

## Types

### `RiskEvaluationRequest`
Frozen dataclass fields:
- `strategy_id: str`
- `symbol: str`
- `proposed_position_size: float`
- `account_equity: float`
- `current_exposure: float`

### `RiskEvaluationResponse`
Frozen dataclass fields:
- `approved: bool`
- `reason: str`
- `adjusted_position_size: Optional[float]`
- `risk_score: float`

### `RiskEvaluator` (optional protocol)
Method signature:
- `evaluate(request: RiskEvaluationRequest) -> RiskEvaluationResponse`

## Out of Scope
- Policy/risk business logic
- Runtime orchestration
- Execution integration

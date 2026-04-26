# P27-DESIGN Risk Evaluation Contract

## Purpose
This document defines the deterministic and immutable contract surface for risk
assessment in Issue #482.

## Module
- `src/cilly_trading/risk_framework/contract.py`

## Design Constraints
- Use frozen dataclasses.
- No business logic.
- No imports from `cilly_trading.execution` or `cilly_trading.orchestrator`.
- Deterministic contract behavior through explicit, value-based fields.

## Types

### `RiskEvaluationRequest`
Frozen dataclass fields:
- `strategy_id: str`
- `symbol: str`
- `proposed_position_size: float`
- `account_equity: float`
- `current_exposure: float`
- `entry_price: Optional[float] = None`
- `stop_loss_price: Optional[float] = None`
- `strategy_risk_used: float = 0.0`
- `symbol_risk_used: float = 0.0`
- `portfolio_risk_used: float = 0.0`
- `require_bounded_risk_evidence: bool = False`

### `RiskEvaluationResponse`
Frozen dataclass fields:
- `approved: bool`
- `reason: str`
- `adjusted_position_size: Optional[float]`
- `risk_score: float`
- `policy_evidence: tuple[NonLiveEvaluationEvidence, ...] = ()`

The optional bounded-risk request fields support deterministic stop-loss,
position-sizing, trade-risk, strategy-risk, symbol-risk, and portfolio-risk
evidence for non-live evaluation only. Missing or contradictory required
bounded evidence fails closed. These fields do not introduce live trading,
broker execution, trader-validation, or operational-readiness claims.

### `RiskEvaluator` (optional protocol)
Method signature:
- `evaluate(request: RiskEvaluationRequest) -> RiskEvaluationResponse`

## Out of Scope
- Policy/risk business logic
- Runtime orchestration
- Execution integration
- Live trading
- Broker integration
- Trader validation

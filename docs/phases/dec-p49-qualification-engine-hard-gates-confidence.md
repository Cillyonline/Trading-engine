# DEC-P49 - Decision-Layer Integration (Backtest, Portfolio Fit, Sentiment)

## Goal

Integrate bounded backtest evidence, bounded portfolio-fit input, and a bounded
sentiment overlay into the canonical decision layer with deterministic,
reviewable output.

## Scope

In scope:

- bounded qualification engine behavior
- hard-gate behavior in covered evaluation paths
- bounded confidence tiers
- deterministic traffic-light decision output
- bounded backtest evidence integration into `backtest_quality`
- bounded portfolio-fit input integration into `portfolio_fit`
- bounded sentiment overlay impact on aggregate score only
- evidence semantics alignment with the canonical decision-card contract
- validation coverage for integration behavior

Out of scope:

- live trading approval workflows
- broker execution
- unrestricted sentiment ingestion
- unrelated dashboard or sentiment platform expansion
- strategy-lab expansion

## Runtime Contract

The DEC-P49 implementation in this repository is bounded as follows:

- hard-gate behavior is deterministic and blocking failures resolve to `reject`/`red`
- confidence tiers are explicit and bounded (`low`, `medium`, `high`) from fixed thresholds
- traffic-light output is deterministic and inspectable through qualification state/color
- backtest evidence and portfolio-fit inputs can only modify their covered component categories
- sentiment is strictly a bounded overlay and cannot become a primary scoring category
- rationale language remains paper-trading scoped and explicitly denies live-trading approval

Canonical runtime surfaces:

- `src/cilly_trading/engine/qualification_engine.py`
- `src/cilly_trading/engine/decision_card_contract.py`
- `GET /decision-cards` in `src/api/routers/inspection_router.py` (read-only decision inspection surface)
- `docs/api/decision_card_inspection.md` (bounded operator inspection wording contract)

## Validation

DEC-P49 coverage is validated through:

- `tests/cilly_trading/engine/test_qualification_engine.py`
- `tests/cilly_trading/engine/test_decision_card_contract.py`
- `tests/decision/test_decision_integration_layer.py`
- decision-card inspection API tests under `tests/test_api_decision_card_inspection_read.py`

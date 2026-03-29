# DEC-P49 - Qualification Engine

## Goal

Implement one bounded qualification engine for the covered decision flow with deterministic,
reviewable output.

## Scope

In scope:

- bounded qualification engine behavior
- hard-gate behavior in covered evaluation paths
- bounded confidence tiers
- deterministic traffic-light decision output
- validation coverage for qualification behavior

Out of scope:

- live trading approval workflows
- broker execution
- unrestricted model expansion
- unrelated dashboard or sentiment platform expansion

## Runtime Contract

The DEC-P49 implementation in this repository is bounded as follows:

- hard-gate behavior is deterministic and blocking failures resolve to `reject`/`red`
- confidence tiers are explicit and bounded (`low`, `medium`, `high`) from fixed thresholds
- traffic-light output is deterministic and inspectable through qualification state/color
- rationale language remains paper-trading scoped and explicitly denies live-trading approval

Canonical runtime surfaces:

- `src/cilly_trading/engine/qualification_engine.py`
- `src/cilly_trading/engine/decision_card_contract.py`

## Validation

DEC-P49 coverage is validated through:

- `tests/cilly_trading/engine/test_qualification_engine.py`
- `tests/cilly_trading/engine/test_decision_card_contract.py`
- decision-card inspection API tests under `tests/test_api_decision_card_inspection_read.py`

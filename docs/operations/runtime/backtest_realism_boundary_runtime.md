# Backtest Realism Boundary - Runtime Disclosure

## Status

IN-REPOSITORY DETERMINISTIC BACKTEST DISCLOSURE; NON-LIVE BOUNDED EVIDENCE ONLY.

## Operational Boundary

This runtime document describes how the canonical backtest realism boundary defined
in `docs/governance/backtest-realism-boundary-contract.md` is exposed by the
deterministic backtest runtime path in this repository.

The deterministic backtest runtime is intentionally bounded:

- It produces bounded technical evidence under the covered execution assumptions.
- It does not place live orders, call broker APIs, or risk real capital.
- It does not constitute live-trading readiness or trader validation.

Operators MUST NOT interpret backtest runtime output as evidence of live execution,
broker fill quality, or trader-validated edge.

## Runtime Realism Disclosure Surface

Every deterministic backtest run exposes the canonical realism boundary in its
artifact payload under `realism_boundary`. The surface is composed of:

- `boundary_version`: canonical version of the realism boundary contract surface.
- `modeled_assumptions`:
  - `bounded_risk_decisions`: required signal risk evidence, deterministic
    approve/reject decisions, and deterministic missing-evidence rejection policy
  - `fees`: `commission_model` and `commission_per_order`
  - `slippage`: `slippage_bps` and `slippage_model`
  - `fills`: `fill_model`, `fill_timing`, `partial_fills_allowed`, `price_source`
- `unmodeled_assumptions`:
  - `market_hours`: not modeled (sessions, halts, auctions, after-hours excluded)
  - `broker_behavior`: not modeled (routing, broker rejects, cancels, broker policies excluded)
  - `liquidity_and_microstructure`: not modeled (depth, queue, latency, impact excluded)
- `evidence_boundary`:
  - `supported_interpretation`: deterministic replay under declared assumptions and
    cost-aware metrics bounded to fixed commission and fixed basis-point slippage
  - `unsupported_claims`: live-trading readiness, broker execution realism,
    market-hours compliance realism, liquidity/microstructure realism,
    future profitability or out-of-sample robustness
  - `qualification_constraint`: backtest evidence is bounded and MUST NOT be used
    alone for qualification, trader approval, or live-trading decisions
  - `decision_use_constraint`: qualification and decision documents MUST treat
    this artifact as bounded backtest evidence only

These fields are canonical and authoritative; any tooling that consumes backtest
artifacts MUST treat unrecognized claim categories as out of contract.

## Deterministic Replay Runtime Behavior

For identical inputs and identical run-config covered execution assumptions, the
deterministic backtest runtime MUST produce byte-stable artifact payloads, including
the realism boundary disclosure, the cost-aware baseline, and the deterministic
realism sensitivity matrix.

This replay stability is exercised by regression tests in `tests/`.

## Bounded Cost-Sensitivity Runtime Behavior

The deterministic backtest runtime emits a bounded realism sensitivity matrix that
compares `configured_baseline`, `cost_free_reference`, and `bounded_cost_stress`
profiles using the same snapshot inputs. Operators MUST interpret the matrix as
technical-only comparison evidence:

- `cost_free_reference.total_transaction_cost == 0`
- `bounded_cost_stress.total_transaction_cost >= configured_baseline.total_transaction_cost`

The matrix MUST NOT be used as evidence of live execution behavior, broker fill
quality, or trader-validated edge.

## Bounded Risk-Decision Runtime Behavior

Signal-derived backtest orders require deterministic risk evidence. The runtime
records the resulting `risk_decisions` in the artifact. If required risk evidence
is absent, the order is rejected with `missing_required_risk_evidence` and is
preserved under `rejected_orders` and `rejection_events`.

These rejected orders and rejection events are bounded backtest evidence only.
They do not model broker rejects, live routing, venue behavior, liquidity,
latency, or market access controls.

## Non-Live Boundary

The deterministic backtest runtime operates exclusively within the bounded
non-live evaluation boundary:

- No live orders are placed.
- No broker APIs are called.
- No real capital is at risk.
- Backtest evidence is bounded and does not imply live-trading readiness or
  broker go-live approval.
- Backtest evidence does not constitute trader validation.

Trader validation status for the deterministic backtest implementation remains
`trader_validation_not_started`.

## Authority

For wording, modeled/unmodeled coverage, replay stability, and bounded sensitivity
semantics, this runtime document defers to the canonical governance contract:
`docs/governance/backtest-realism-boundary-contract.md`.

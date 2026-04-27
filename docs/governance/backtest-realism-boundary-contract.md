# Backtest Realism Boundary - Canonical Contract

## Purpose

This contract is the canonical governance authority for the bounded realism interpretation
of deterministic backtest output in this repository. It hardens the wording, evidence, and
interpretation rules around the execution assumptions that the deterministic backtest
already implements, so backtest output is harder to overread as live-execution evidence
or trader validation.

This contract does not introduce new strategies, new execution behavior, broker behavior,
or any live-trading scope. Existing strategy logic and runtime execution behavior remain
unchanged.

## Scope

In scope:

- canonical wording for covered execution assumptions (slippage, commission, fill timing,
  price source, fill model, partial-fills policy)
- canonical wording for deterministic bounded risk-decision evidence, including
  missing-evidence rejection handling
- canonical wording for the modeled vs unmodeled realism boundary already exposed by the
  deterministic backtest
- canonical interpretation rules that prevent overreading bounded backtest output as
  live-execution proof or trader validation
- canonical reference to deterministic replay stability and bounded sensitivity coverage

Out of scope:

- strategy retuning
- new strategies
- market-data provider expansion
- browser workflow expansion
- live trading scope
- broker integration
- profitability claims

## Canonical Covered Execution Assumptions

The deterministic backtest covers exactly the following execution assumptions. Any
assumption not listed here is explicitly out of contract for backtest evidence.

### Fill assumptions (canonical)

- `fill_model` is fixed to `deterministic_market`.
- `fill_timing` is one of `next_snapshot` or `same_snapshot`, declared per run.
- `price_source` is fixed to `open_then_price` (use `open` when present; otherwise `price`).
- `partial_fills_allowed` is fixed to `false`.

### Cost assumptions (canonical)

- Slippage model is fixed basis points by side (`fixed_basis_points_by_side`).
  - BUY adjusts the reference price upward by `slippage_bps`.
  - SELL adjusts the reference price downward by `slippage_bps`.
  - `slippage_bps` is bounded `>= 0` and capped by the engine assumption limit.
- Commission model is fixed per filled order (`fixed_per_filled_order`).
  - `commission_per_order` is bounded `>= 0` and capped by the engine assumption limit.

### Reproducibility assumptions (canonical)

- Snapshots are sorted deterministically by snapshot key and id.
- Signals are translated to deterministic market orders with deterministic ordering.
- Signal-derived orders require deterministic risk evidence. Present risk evidence is
  represented as an explicit risk decision; missing required risk evidence is classified
  as `missing_required_risk_evidence` and rejects the order deterministically.
- Rejected orders remain represented in the artifact as rejected orders and rejection
  execution events; they do not silently disappear.
- Identical inputs and identical run-config assumptions MUST produce identical outputs.

## Canonical Realism Boundary Disclosure

Every backtest artifact MUST carry, under `realism_boundary`, both:

- `modeled_assumptions`: the covered execution assumptions above with their declared
  values for the run.
- `unmodeled_assumptions`: explicit disclosure of realism dimensions that are NOT
  modeled in the deterministic backtest:
  - market hours, exchange sessions, holidays, halts, auctions, after-hours restrictions
  - broker routing, venue selection, broker rejects, cancels, broker-specific policies
  - order-book depth, queue position, latency, fill probability, market impact

Both lists are canonical and authoritative for what the backtest does and does not model.
Adding new modeled dimensions requires updating this contract first.

Backtest risk rejections are bounded deterministic artifact evidence only. They do not
model broker rejects, broker routing, venue behavior, market access controls, or live
risk management.

## Deterministic Replay Stability (Canonical)

For identical inputs (snapshots, run id, strategy name, run contract) under identical
covered execution assumptions, the deterministic backtest MUST produce byte-stable
artifact payloads, including:

- `execution_assumptions`
- `realism_boundary.modeled_assumptions`
- `realism_boundary.unmodeled_assumptions`
- deterministic `risk_decisions`, `rejected_orders`, and `rejection_events`
- the cost-aware metrics baseline summary, equity curve, and metrics
- the deterministic realism sensitivity matrix (profile order, per-profile assumptions,
  summaries, metrics, and `delta_vs_baseline`)

Replay stability is enforced by deterministic regression tests in `tests/`.

## Bounded Sensitivity Under Materially Different Cost Assumptions (Canonical)

Materially different covered cost assumptions MUST produce bounded, explainable, and
direction-stable changes in the cost-aware baseline summary:

- Increasing `slippage_bps` (with all other covered assumptions held constant) MUST NOT decrease `total_slippage_cost` and MUST NOT decrease `total_transaction_cost`.
- Increasing `commission_per_order` (with all other covered assumptions held constant) MUST NOT decrease `total_commission` and MUST NOT decrease `total_transaction_cost`.
- The `bounded_cost_stress` realism profile MUST report `total_transaction_cost` greater
  than or equal to `configured_baseline`, and the `cost_free_reference` profile MUST
  report `total_transaction_cost == 0`.

These bounded sensitivity properties are enforced by regression tests in `tests/`.

They are technical-only comparison evidence. They are not evidence of live execution
quality, broker fill quality, or trader-validated edge.

## Canonical Interpretation Boundary

Backtest output is bounded technical evidence for deterministic replay under the
covered execution assumptions only. Backtest output, including the deterministic
sensitivity matrix, MUST NOT be used as evidence for any of the following:

- live-trading readiness or approval
- broker execution realism or broker fill quality
- market-hours compliance realism
- liquidity or market microstructure realism
- trader validation or trader approval
- future profitability or out-of-sample robustness

Qualification and decision documents MUST treat backtest output as bounded backtest evidence only. Backtest output is non-live by design and does not constitute trader validation.

## Status Wording

Classification: technically bounded, traderically not validated.

Rationale:

- technically bounded: covered execution assumptions are deterministic, capped, and
  test-validated; deterministic replay stability and bounded cost sensitivity are
  enforced by regression tests.
- traderically not validated: key market-realism dimensions are intentionally
  unmodeled; trader validation status remains `trader_validation_not_started`.

## Authority

This document is the single canonical governance authority for backtest realism
boundary wording. Other documents that reference backtest realism, modeled vs
unmodeled assumptions, or interpretation discipline MUST defer to this contract.

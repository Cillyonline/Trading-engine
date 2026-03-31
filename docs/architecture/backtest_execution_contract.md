# Backtest Execution Contract (BT-P42B)

## Goal

Define one explicit contract for deterministic backtest execution so runs are reproducible and operational assumptions are visible in the artifact.

## Contract Boundary

The backtest contract is bounded to:

- run configuration validation
- signal-to-order translation
- deterministic order execution assumptions
- reproducibility metadata written into the run artifact

Out of scope:

- portfolio optimization
- paper-trading runtime
- broker integrations
- UI workflows

## Run Configuration Model

Backtests use `BacktestRunContract` with explicit sections:

- `contract_version`: currently `1.0.0`
- `signal_translation`:
  - `signal_collection_field`
  - `signal_id_field`
  - `action_field`
  - `quantity_field`
  - `symbol_field`
  - `action_to_side`
- `execution_assumptions`:
  - `fill_model` = `deterministic_market`
  - `fill_timing` = `next_snapshot` or `same_snapshot`
  - `price_source` = `open_then_price`
  - `slippage_bps` (integer, `>= 0`)
  - `commission_per_order` (decimal, `>= 0`)
  - `partial_fills_allowed` = `false`
- `reproducibility_metadata`:
  - `run_id`
  - `strategy_name`
  - `strategy_params`
  - `engine_name`
  - `engine_version`

## Signal -> Order -> Fill Semantics

Signal translation is deterministic:

1. Snapshots are sorted by `timestamp` / `snapshot_key`, then by `id`.
2. Signals in each snapshot are sorted by `signal_id`, then `symbol`.
3. Each translated order is market-only and receives a deterministic `order_id`.

Execution assumptions are explicit and testable:

- no partial fills
- fill price source is `open`, then fallback `price`
- side-aware slippage:
  - BUY: `price * (1 + bps/10000)`
  - SELL: `price * (1 - bps/10000)`
- fixed commission per filled order
- deterministic decimal quantization

## Reproducibility

For identical snapshots and identical run contract:

- translated orders are identical
- fills and resulting positions are identical
- `backtest-result.json` bytes and hash remain identical

The run artifact now surfaces both the explicit `run_config` contract and realized `orders` / `fills` / `positions`.

## Canonical Handoff (Phase 42b -> Phase 43 -> Phase 44)

The canonical handoff from backtest evidence is explicit in `backtest-result.json` under `phase_handoff`.

- `phase_handoff.source_phase` MUST be `42b`.
- `phase_handoff.target_phases` MUST include `43` and `44`.
- `phase_handoff.required_evidence.phase_43_portfolio_simulation` defines the required fields for Phase 43 consumers.
- `phase_handoff.required_evidence.phase_44_paper_trading_readiness` defines the additional required fields for Phase 44 evidence consumers.
- `phase_handoff.authoritative_outputs.trader_interpretation` defines which outputs are authoritative for trader-facing interpretation.
- `phase_handoff.assumption_alignment.run_config_execution_assumptions_match_metrics_baseline_assumptions` MUST be true before readiness evidence is considered valid.
- `phase_handoff.artifact_lineage`: provenance chain from backtest output to downstream consumers.
- `phase_handoff.canonical_handoffs.backtest_to_portfolio`: canonical handoff record from backtest to portfolio simulation.
- `phase_handoff.canonical_handoffs.portfolio_to_paper`: canonical handoff record from portfolio simulation to paper trading.
- `realism_boundary`: explicit disclosure of modeled and unmodeled assumptions in the run artifact.

Acceptance gates are explicit and non-inferential:

- `phase_handoff.acceptance_gates.technically_valid_backtest_artifact`
  distinguishes "artifact is structurally valid" from downstream readiness claims.
- `phase_handoff.acceptance_gates.phase_43_portfolio_simulation_ready`
  indicates evidence is complete and aligned for Phase 43 portfolio simulation usage.
- `phase_handoff.acceptance_gates.phase_44_paper_trading_readiness_evidence_ready`
  indicates evidence handoff completeness for Phase 44 readiness review.

Boundary clarification:

- Passing the handoff gates does not implement portfolio simulation or paper-trading workflows.
- Passing the handoff gates does not imply live trading or broker readiness.
- Artifact consumers MUST treat the output as bounded backtest evidence only.

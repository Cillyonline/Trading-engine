# Backtest CLI

## Command

```bash
python -m cilly_trading backtest --snapshots <PATH> --strategy <NAME> --out <DIR> [--run-id <STR>] [--strategy-module <PYMOD>]...
```

- `--snapshots`: Path to a JSON file with snapshot data.
- `--strategy`: Registered strategy name.
- `--out`: Output directory for artifacts.
- `--run-id`: Optional run identifier. Default is `deterministic`.
- `--strategy-module`: Optional Python module to import before resolving the strategy.
  May be provided multiple times.

## Snapshot JSON format

The snapshots file must be a JSON array of snapshot objects:

```json
[
  {"id": "s1", "timestamp": "2024-01-01T00:00:00Z"},
  {"id": "s2", "timestamp": "2024-01-02T00:00:00Z"}
]
```

If the file cannot be read, cannot be parsed as JSON, or the top-level value is not a JSON array, the CLI exits with code `20`.

## Exit codes

| Exit code | Meaning |
| --- | --- |
| `0` | Success |
| `2` | CLI usage or invalid arguments (argparse default) |
| `10` | Determinism violation |
| `20` | Snapshot input invalid |
| `30` | Strategy selection invalid |
| `1` | Unexpected error fallback |

## Determinism guard

The `backtest` command installs the determinism guard at startup and uninstalls it in a `finally` block.
If forbidden non-deterministic APIs are used during execution, the command exits with code `10`.

## Reproducible Evidence Fields

The produced `backtest-result.json` is the trader-review evidence surface for the covered path.
For reproducible review, the following fields are mandatory:

- `run.run_id`: explicit run identity.
- `run.deterministic`: explicit deterministic execution flag (`true` on covered path).
- `snapshot_linkage`: bounded dataset window and count used for the run.
- `run_config.execution_assumptions`: explicit execution assumptions used for fill timing, slippage, commission, and price source.
- `run_config.reproducibility_metadata`: run identity context (`run_id`, strategy identity, params, engine identity).
- `realism_boundary.modeled_assumptions`: explicit modeled assumptions consumed by downstream review.
- `realism_boundary.unmodeled_assumptions`: explicit non-modeled realism disclosures that bound interpretation.
- `metrics_baseline.assumptions`: assumption echo used for cost-aware metric interpretation.

Evidence alignment rule for covered outputs:

- `metrics_baseline.assumptions` MUST match `run_config.execution_assumptions`.

## Realism Boundary

Backtest output carries a bounded realism disclosure under `realism_boundary`.

Modeled assumptions:

- declared fill model, fill timing, price source, slippage, commission, and partial-fill policy.

Unmodeled assumptions:

- Market hours are not modeled.
- Broker behavior is not modeled.
- Liquidity and microstructure are not modeled.

Unsupported claims that MUST remain excluded:

- live-trading readiness or approval
- broker execution realism
- market-hours compliance realism
- liquidity or market microstructure realism
- future profitability or out-of-sample robustness

Qualification and decision docs must treat backtest output as bounded evidence only.

## Phase 42b -> 43 -> 44 Handoff Contract

The produced artifact includes explicit downstream handoff metadata at `phase_handoff`:

- `phase_handoff.required_evidence.phase_43_portfolio_simulation`: required evidence fields for Phase 43.
- `phase_handoff.required_evidence.phase_44_paper_trading_readiness`: additional evidence fields for Phase 44.
- `phase_handoff.authoritative_outputs.trader_interpretation`: authoritative outputs for trader-facing interpretation.
- `phase_handoff.artifact_lineage`: explicit lineage completeness state for downstream consumers.
- `phase_handoff.acceptance_gates.technically_valid_backtest_artifact`: structural validity gate only.
- `phase_handoff.acceptance_gates.phase_43_portfolio_simulation_ready`: Phase 43 readiness evidence gate.
- `phase_handoff.acceptance_gates.phase_44_paper_trading_readiness_evidence_ready`: Phase 44 readiness evidence gate.
- `phase_handoff.canonical_handoffs.backtest_to_portfolio`: canonical bounded handoff into Phase 43.
- `phase_handoff.canonical_handoffs.portfolio_to_paper`: canonical bounded handoff into Phase 44.

Review interpretation rule:

- A technically valid artifact is not automatically Phase 43/44 readiness evidence.
- Phase 43/44 usage MUST follow the explicit handoff gate outcomes.

## Trader Interpretation Boundary

The produced evidence is valid only for deterministic replay under the declared assumptions and snapshot input.
It supports trader review for what this specific replay path did under those constraints.

The evidence does **not** prove:

- Live trading readiness.
- Broker fill quality or market-impact realism beyond the fixed deterministic model.
- Portfolio-level decision quality outside the covered backtest output scope.
- Future performance, out-of-sample robustness, or production profitability.

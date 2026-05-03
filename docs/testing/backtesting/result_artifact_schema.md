# Backtest Result Artifact Schema (P22-RESULT-ARTIFACT)

## Artifact files and byte-level file policy

- Primary artifact file name: `backtest-result.json`
- Sidecar hash file name: `backtest-result.sha256`
- Encoding for both files: UTF-8
- Newline policy for both files: LF (`\n`) only
- `backtest-result.json` MUST end with exactly one trailing LF (`\n`)
- `backtest-result.sha256` MUST be exactly `"<sha256-hex>\n"`

## Canonical JSON / stable serialization rules

`backtest-result.json` MUST be serialized canonically with the following rules:

- Object keys sorted lexicographically, equivalent to Python:
  - `json.dumps(payload, sort_keys=True, ...)`
- No extra whitespace:
  - `separators=(",", ":")`
- UTF-8 JSON characters emitted directly:
  - `ensure_ascii=False`
- NaN/Infinity forbidden:
  - `allow_nan=False`
- Serialized content MUST append exactly one trailing LF:
  - `json.dumps(...) + "\n"`
- Arrays MUST be emitted in deterministic order.
  - The engine is responsible for deterministic array ordering before serialization.

## Data quality warnings and survivorship bias disclosure

The artifact always includes a `data_quality_warnings` array at the top level.
When `yfinance` is the active data source (the current default), the array
contains the following survivorship-bias warning:

> **SURVIVORSHIP BIAS**: This backtest uses yfinance as the data source.
> yfinance only returns data for currently listed and actively traded assets.
> Delisted stocks, bankrupt companies, and assets removed from indices are absent
> from the data universe. Backtest performance figures are therefore structurally
> inflated and must not be interpreted as unbiased historical returns.

### Interpretation guidance

- Backtest metrics (win rate, Sharpe, CAGR, etc.) reflect only assets that
  survived to the present and were liquid enough for yfinance to return data.
- Strategies that select assets based on current availability are inherently
  exposed to this bias; there is no way to eliminate it without a survivorship-
  bias-free data provider.
- The `data_quality_warnings` field is machine-readable to allow downstream
  consumers (API clients, dashboards) to surface this disclosure automatically.
- The absence of a survivorship-bias-free data source is an explicit gap, not an
  oversight. It is tracked as a future roadmap item.

## Minimal schema

Top-level object keys and minimal semantics:

- `artifact_version` (required): string literal `"1"`
- `data_quality_warnings` (required): array of strings
  - Contains the survivorship-bias warning when `yfinance` is the data source.
  - Empty array when a survivorship-bias-free data source is configured.
- `engine` (required): object
  - `name` (required): string
  - `version` (required): string or `null`
- `run` (required): object
  - `run_id` (required): string
  - `created_at` (required): string or `null`
    - May only be populated if provided by input; no runtime clock/time sources.
  - `deterministic` (required): boolean literal `true`
- `snapshot_linkage` (required): object
  - `mode` (required): `"timestamp"` or `"snapshot_key"`
  - `start` (required): string or `null`
  - `end` (required): string or `null`
  - `count` (required): integer
- `strategy` (required): object
  - `name` (required): string
  - `version` (required): string or `null`
  - `params` (required): object
- `invocation_log` (required): array of strings
- `processed_snapshots` (required): array of objects
  - Each entry MUST include at least one stable snapshot identifier field:
    - `id` and/or `timestamp` and/or `snapshot_key`
- `orders` (required): array (may be empty)
- `fills` (required): array (may be empty)
- `positions` (required): array (may be empty)
- `phase_handoff` (required): object
  - `contract_version` (required): string
  - `source_phase` (required): string literal `"42b"`
  - `target_phases` (required): array containing `"43"` and `"44"`
  - `artifact_lineage` (required): object
    - `complete` (required): boolean
    - `required_fields` (required): array of field-path strings
    - `missing_fields` (required): array of field-path strings
  - `required_evidence` (required): object
    - `phase_43_portfolio_simulation` (required): array of field-path strings
    - `phase_44_paper_trading_readiness` (required): array of field-path strings
  - `authoritative_outputs` (required): object
    - `trader_interpretation` (required): array of field-path strings
  - `canonical_handoffs` (required): object
    - `backtest_to_portfolio` (required): bounded Phase 43 handoff metadata
    - `portfolio_to_paper` (required): bounded Phase 44 handoff metadata
  - `assumption_alignment` (required): object
    - `run_config_execution_assumptions_match_metrics_baseline_assumptions` (required): boolean
  - `acceptance_gates` (required): object
    - `technically_valid_backtest_artifact` (required): object with `passed`, `missing_fields`, `reasons`
    - `phase_43_portfolio_simulation_ready` (required): object with `passed`, `missing_fields`, `reasons`
    - `phase_44_paper_trading_readiness_evidence_ready` (required): object with `passed`, `missing_fields`, `reasons`
codex/ops-p51-write-only-evidence
- `realism_boundary` (required): object
  - modeled assumptions: explicit fill, fee, slippage, and price-source assumptions
  - unmodeled assumptions: explicit realism gaps such as market hours, broker behavior, and liquidity/microstructure
  - `evidence_boundary.unsupported_claims`: Unsupported realism claims that remain out of scope

  - `artifact_lineage` (required): object documenting provenance chain from backtest output to downstream consumers.
  - `canonical_handoffs` (required): object containing canonical handoff records.
    - `backtest_to_portfolio`: canonical handoff record from backtest to portfolio simulation.
    - `portfolio_to_paper`: canonical handoff record from portfolio simulation to paper trading.
- `realism_boundary` (required): object documenting modeled and unmodeled assumptions.
  - `modeled_assumptions` (required): explicit list of realism assumptions included in this run (e.g., fixed slippage, fixed commission, deterministic fill timing).
  - `unmodeled_assumptions` (required): explicit list of assumptions excluded from this run (e.g., market hours, exchange session rules, order book depth).
  - Unsupported realism claims (e.g., live-trading readiness, broker fill quality guarantees) MUST remain excluded from artifact assertions.
main

## Hash reproducibility

- Hash algorithm: SHA-256
- Hash input: exact UTF-8 bytes of `backtest-result.json`, including trailing LF
- Sidecar file: `backtest-result.sha256`
- Sidecar content format: `"<hex>\n"`

Any change in payload bytes (including key order, whitespace, newline style, or trailing newline count) changes the hash and is therefore non-compliant.

# CODE-B6 Duplication Audit

## Scope

This audit reviews duplicated helper logic and repeated shared behavior across the current codebase, with emphasis on:

- hashing
- normalization
- canonical serialization
- signal identity construction
- configuration parsing

The audit is descriptive only. It does not propose refactors, move code, or change runtime behavior.

## Classification legend

- `exact duplicate`: the same helper logic is implemented twice or more with materially identical control flow and semantics.
- `near duplicate`: helpers share the same structure or algorithm but differ slightly in payload shape, output format, or validation.
- `divergent duplicate`: helpers solve the same category of problem in parallel but already embed different contracts or domain assumptions.

## Findings

### 1. Canonical JSON + SHA-256 + signal identity stack is duplicated between domain and engine layers

- Classification: `exact duplicate`
- Why it matters: the codebase has two independent implementations of canonical serialization and signal identity construction. Any future change to canonicalization rules would need to stay synchronized across both modules.

Affected implementations:

- [`src/cilly_trading/models.py:96`](../../src/cilly_trading/models.py)
- [`src/cilly_trading/models.py:109`](../../src/cilly_trading/models.py)
- [`src/cilly_trading/models.py:132`](../../src/cilly_trading/models.py)
- [`src/cilly_trading/models.py:151`](../../src/cilly_trading/models.py)
- [`src/cilly_trading/models.py:163`](../../src/cilly_trading/models.py)
- [`src/cilly_trading/models.py:181`](../../src/cilly_trading/models.py)
- [`src/cilly_trading/engine/core.py:70`](../../src/cilly_trading/engine/core.py)
- [`src/cilly_trading/engine/core.py:83`](../../src/cilly_trading/engine/core.py)
- [`src/cilly_trading/engine/core.py:106`](../../src/cilly_trading/engine/core.py)
- [`src/cilly_trading/engine/core.py:120`](../../src/cilly_trading/engine/core.py)
- [`src/cilly_trading/engine/core.py:235`](../../src/cilly_trading/engine/core.py)
- [`src/cilly_trading/engine/core.py:253`](../../src/cilly_trading/engine/core.py)

Audit notes:

- `_normalize_assets`, `_normalize_canonical_value`, `canonical_json`, and `sha256_hex` are duplicated line-for-line in both modules.
- `_signal_identity_payload` and `compute_signal_id` also use the same identity field set in both modules.
- `compute_analysis_run_id` in [`src/cilly_trading/engine/core.py:223`](../../src/cilly_trading/engine/core.py) reuses the same duplicated canonicalization/hash stack for a different identity type.
- This duplication is specific enough to support a consolidation issue around one canonical identity utility boundary.

### 2. Alert event identity hashing is a parallel implementation of the same canonical identity pattern

- Classification: `near duplicate`
- Why it matters: alert identity creation is not byte-for-byte identical to the signal identity code, but it repeats the same normalization -> canonical JSON -> SHA-256 pattern with slightly different payload rules.

Affected implementations:

- [`src/cilly_trading/alerts/alert_models.py:38`](../../src/cilly_trading/alerts/alert_models.py)
- [`src/cilly_trading/alerts/alert_models.py:56`](../../src/cilly_trading/alerts/alert_models.py)
- [`src/cilly_trading/alerts/alert_models.py:89`](../../src/cilly_trading/alerts/alert_models.py)
- [`src/cilly_trading/models.py:132`](../../src/cilly_trading/models.py)
- [`src/cilly_trading/models.py:151`](../../src/cilly_trading/models.py)
- [`src/cilly_trading/models.py:163`](../../src/cilly_trading/models.py)
- [`src/cilly_trading/engine/core.py:106`](../../src/cilly_trading/engine/core.py)
- [`src/cilly_trading/engine/core.py:120`](../../src/cilly_trading/engine/core.py)

Audit notes:

- `_normalize_payload` performs recursive payload normalization similar to `_normalize_canonical_value`, but it permits floats while the canonical signal serializer rejects them.
- `compute_alert_event_id` repeats canonical `json.dumps(..., sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)` followed by SHA-256 digest construction.
- `signal_to_alert_event` then re-derives `source_id` from the same signal identity path already implemented elsewhere.
- Consolidation would need to preserve alert-specific prefixing (`alert_`) and payload normalization rules, so this is not an exact clone.

### 3. Trade-ledger post-processing helpers are duplicated across equity and performance artifacts

- Classification: `exact duplicate`
- Why it matters: the same numeric conversion, rounding, ordering, and ordered-trade extraction helpers exist in two artifact builders. Any bug fix in trade ordering or decimal handling would need to be applied twice.

Affected implementations:

- [`src/cilly_trading/equity_curve.py:13`](../../src/cilly_trading/equity_curve.py)
- [`src/cilly_trading/equity_curve.py:31`](../../src/cilly_trading/equity_curve.py)
- [`src/cilly_trading/equity_curve.py:38`](../../src/cilly_trading/equity_curve.py)
- [`src/cilly_trading/equity_curve.py:44`](../../src/cilly_trading/equity_curve.py)
- [`src/cilly_trading/equity_curve.py:56`](../../src/cilly_trading/equity_curve.py)
- [`src/cilly_trading/performance_report.py:13`](../../src/cilly_trading/performance_report.py)
- [`src/cilly_trading/performance_report.py:31`](../../src/cilly_trading/performance_report.py)
- [`src/cilly_trading/performance_report.py:38`](../../src/cilly_trading/performance_report.py)
- [`src/cilly_trading/performance_report.py:44`](../../src/cilly_trading/performance_report.py)
- [`src/cilly_trading/performance_report.py:56`](../../src/cilly_trading/performance_report.py)

Audit notes:

- `_to_decimal`, `_round_12`, `_to_float`, `_trade_sort_key`, and `_ordered_trades` are materially identical between the two files.
- The duplication sits below two different report builders, so a follow-up issue can target only the shared helper layer without changing artifact schemas.

### 4. Risk-adjusted metrics repeats the same numeric and ordering helper family with minor variation

- Classification: `near duplicate`
- Why it matters: `risk_adjusted_metrics.py` uses the same decimal normalization and trade ordering primitives as the artifact builders, but consumes a raw trade sequence instead of a full payload object.

Affected implementations:

- [`src/cilly_trading/risk_adjusted_metrics.py:11`](../../src/cilly_trading/risk_adjusted_metrics.py)
- [`src/cilly_trading/risk_adjusted_metrics.py:28`](../../src/cilly_trading/risk_adjusted_metrics.py)
- [`src/cilly_trading/risk_adjusted_metrics.py:35`](../../src/cilly_trading/risk_adjusted_metrics.py)
- [`src/cilly_trading/risk_adjusted_metrics.py:41`](../../src/cilly_trading/risk_adjusted_metrics.py)
- [`src/cilly_trading/equity_curve.py:13`](../../src/cilly_trading/equity_curve.py)
- [`src/cilly_trading/equity_curve.py:31`](../../src/cilly_trading/equity_curve.py)
- [`src/cilly_trading/equity_curve.py:38`](../../src/cilly_trading/equity_curve.py)
- [`src/cilly_trading/equity_curve.py:44`](../../src/cilly_trading/equity_curve.py)
- [`src/cilly_trading/performance_report.py:13`](../../src/cilly_trading/performance_report.py)
- [`src/cilly_trading/performance_report.py:31`](../../src/cilly_trading/performance_report.py)
- [`src/cilly_trading/performance_report.py:38`](../../src/cilly_trading/performance_report.py)
- [`src/cilly_trading/performance_report.py:44`](../../src/cilly_trading/performance_report.py)

Audit notes:

- `_to_decimal`, `_round_12`, `_to_float`, and `_trade_sort_key` follow the same algorithm and naming pattern.
- The divergence is limited to `_extract_trade_pnls_and_returns`, which operates on a sequence instead of a payload object.
- This supports a consolidation issue for deterministic trade numeric helpers, not for the higher-level metrics math itself.

### 5. Canonical artifact serialization and SHA sidecar writing appears in multiple modules

- Classification: `near duplicate`
- Why it matters: several modules serialize JSON canonically, append a trailing newline, write the artifact, and optionally write a `.sha256` sidecar. The file names differ, but the persistence pattern is repeated.

Affected implementations:

- [`src/cilly_trading/trade_ledger.py:170`](../../src/cilly_trading/trade_ledger.py)
- [`src/cilly_trading/trade_ledger.py:175`](../../src/cilly_trading/trade_ledger.py)
- [`src/cilly_trading/equity_curve.py:178`](../../src/cilly_trading/equity_curve.py)
- [`src/cilly_trading/equity_curve.py:183`](../../src/cilly_trading/equity_curve.py)
- [`src/cilly_trading/performance_report.py:173`](../../src/cilly_trading/performance_report.py)
- [`src/cilly_trading/performance_report.py:178`](../../src/cilly_trading/performance_report.py)
- [`src/cilly_trading/engine/result_artifact.py:11`](../../src/cilly_trading/engine/result_artifact.py)
- [`src/cilly_trading/engine/result_artifact.py:21`](../../src/cilly_trading/engine/result_artifact.py)
- [`src/cilly_trading/metrics/artifact.py:40`](../../src/cilly_trading/metrics/artifact.py)
- [`src/cilly_trading/metrics/artifact.py:58`](../../src/cilly_trading/metrics/artifact.py)

Audit notes:

- `trade_ledger`, `equity_curve`, `performance_report`, and `engine/result_artifact` all use canonical JSON bytes with sorted keys and compact separators, then write the bytes to disk.
- `trade_ledger`, `equity_curve`, `performance_report`, and `engine/result_artifact` also compute SHA-256 over the written bytes and persist sidecar hash files.
- `metrics/artifact.py` diverges slightly by normalizing floats first and not writing a hash sidecar.
- This family is broad enough to support follow-up issues for a shared deterministic artifact writer and a separate shared canonical serializer.

### 6. Market-data identity and audit hashing repeat the same digest construction pattern

- Classification: `divergent duplicate`
- Why it matters: multiple modules compute deterministic IDs from canonical payloads, but each one owns a separate field contract and normalization policy.

Affected implementations:

- [`src/cilly_trading/engine/data/market_dataset_contract.py:71`](../../src/cilly_trading/engine/data/market_dataset_contract.py)
- [`src/cilly_trading/engine/data/market_dataset_contract.py:84`](../../src/cilly_trading/engine/data/market_dataset_contract.py)
- [`src/cilly_trading/engine/marketdata/adapter/impl/local_replay_reader.py:66`](../../src/cilly_trading/engine/marketdata/adapter/impl/local_replay_reader.py)
- [`src/cilly_trading/engine/core.py:223`](../../src/cilly_trading/engine/core.py)
- [`src/cilly_trading/alerts/alert_models.py:89`](../../src/cilly_trading/alerts/alert_models.py)

Audit notes:

- `compute_dataset_identity` hashes canonical dataset metadata identity fields.
- `_compute_audit_id` hashes file bytes plus canonicalized adapter config.
- `compute_analysis_run_id` hashes canonical run request payloads.
- `compute_alert_event_id` hashes alert identity payloads.
- These are similar enough to show repeated infrastructure behavior, but each implementation already has distinct input contracts, so consolidation would need a carefully scoped abstraction.

### 7. Strategy configuration parsing is split between schema normalization and strategy-local config dataclasses

- Classification: `divergent duplicate`
- Why it matters: the repository has one structured config normalization path and separate hand-rolled config extraction inside individual strategies. This means configuration behavior can drift by strategy.

Affected implementations:

- [`src/cilly_trading/strategies/config_schema.py:17`](../../src/cilly_trading/strategies/config_schema.py)
- [`src/cilly_trading/strategies/config_schema.py:31`](../../src/cilly_trading/strategies/config_schema.py)
- [`src/cilly_trading/strategies/config_schema.py:48`](../../src/cilly_trading/strategies/config_schema.py)
- [`src/cilly_trading/strategies/config_schema.py:85`](../../src/cilly_trading/strategies/config_schema.py)
- [`src/cilly_trading/strategies/config_schema.py:222`](../../src/cilly_trading/strategies/config_schema.py)
- [`src/cilly_trading/strategies/config_schema.py:233`](../../src/cilly_trading/strategies/config_schema.py)
- [`src/cilly_trading/strategies/rsi2.py:27`](../../src/cilly_trading/strategies/rsi2.py)
- [`src/cilly_trading/strategies/rsi2.py:65`](../../src/cilly_trading/strategies/rsi2.py)
- [`src/cilly_trading/strategies/turtle.py:29`](../../src/cilly_trading/strategies/turtle.py)
- [`src/cilly_trading/strategies/turtle.py:60`](../../src/cilly_trading/strategies/turtle.py)

Audit notes:

- `config_schema.py` already defines reusable coercion and normalization helpers for booleans, ints, floats, and per-strategy schemas.
- `Rsi2Strategy.generate_signals` and `TurtleStrategy.generate_signals` still parse config from raw dict values into local dataclasses using direct `config.get(...)` extraction and different key names.
- Example drift: `config_schema.py` uses keys such as `oversold`, `overbought`, `entry_lookback`, and `exit_lookback`, while strategy implementations still read `oversold_threshold`, `breakout_lookback`, and `proximity_threshold_pct`.
- This is a strong candidate for a later consolidation issue because behavior is parallel but not yet aligned enough to be an exact duplicate.

### 8. Lightweight string/list normalization is repeated in multiple validation entry points

- Classification: `divergent duplicate`
- Why it matters: several modules trim strings, reject blanks, and normalize collections independently. They are not identical, but they solve the same helper problem repeatedly.

Affected implementations:

- [`src/api/alerts_api.py:25`](../../src/api/alerts_api.py)
- [`src/cilly_trading/repositories/watchlists_sqlite.py:29`](../../src/cilly_trading/repositories/watchlists_sqlite.py)
- [`src/data_layer/ingestion_validation.py:15`](../../src/data_layer/ingestion_validation.py)
- [`src/data_layer/normalization.py:29`](../../src/data_layer/normalization.py)
- [`src/cilly_trading/strategies/validation.py:23`](../../src/cilly_trading/strategies/validation.py)
- [`src/cilly_trading/strategies/registry.py:52`](../../src/cilly_trading/strategies/registry.py)

Audit notes:

- Alert tags, watchlist symbols, snapshot sources, strategy keys, and timestamp column names all have local normalization helpers.
- `_normalize_key` in `registry.py` is only a wrapper over `validate_strategy_key`, which makes that specific pair a small exact duplicate-by-delegation.
- The rest of the family is divergent because each validator normalizes different fields with different business constraints.

### 9. Compliance guard configuration parsing is implemented as three parallel helpers

- Classification: `near duplicate`
- Why it matters: drawdown, daily loss, and kill-switch state each parse a `dict[str, object] | None` config using the same overall pattern: null-check, look up one key, validate type/value, return deterministic state.

Affected implementations:

- [`src/cilly_trading/compliance/daily_loss_guard.py:11`](../../src/cilly_trading/compliance/daily_loss_guard.py)
- [`src/cilly_trading/compliance/daily_loss_guard.py:27`](../../src/cilly_trading/compliance/daily_loss_guard.py)
- [`src/cilly_trading/compliance/daily_loss_guard.py:36`](../../src/cilly_trading/compliance/daily_loss_guard.py)
- [`src/cilly_trading/compliance/drawdown_guard.py:11`](../../src/cilly_trading/compliance/drawdown_guard.py)
- [`src/cilly_trading/compliance/drawdown_guard.py:27`](../../src/cilly_trading/compliance/drawdown_guard.py)
- [`src/cilly_trading/compliance/drawdown_guard.py:36`](../../src/cilly_trading/compliance/drawdown_guard.py)
- [`src/cilly_trading/compliance/kill_switch.py:9`](../../src/cilly_trading/compliance/kill_switch.py)
- [`src/api/main.py:985`](../../src/api/main.py)
- [`src/api/main.py:998`](../../src/api/main.py)
- [`src/api/main.py:1010`](../../src/api/main.py)

Audit notes:

- The daily-loss and drawdown modules are close structural matches: parse one config key, validate its numeric range, and expose a boolean decision helper.
- `api/main.py` then repeats low-level environment parsing for booleans and floats before assembling `guard_config`.
- The kill-switch helper follows the same shape but uses a different key namespace and no numeric validation.
- This cluster is a good basis for a later consolidation issue around shared config readers for guard state.

### 10. Portfolio state is modeled twice for related but different control paths

- Classification: `divergent duplicate`
- Why it matters: the codebase contains two `PortfolioState` types in separate namespaces, both representing deterministic portfolio state but with incompatible fields and helper behavior.

Affected implementations:

- [`src/cilly_trading/portfolio/state.py:9`](../../src/cilly_trading/portfolio/state.py)
- [`src/cilly_trading/portfolio/state.py:48`](../../src/cilly_trading/portfolio/state.py)
- [`src/cilly_trading/portfolio/state.py:66`](../../src/cilly_trading/portfolio/state.py)
- [`src/cilly_trading/engine/portfolio/state.py:25`](../../src/cilly_trading/engine/portfolio/state.py)
- [`src/cilly_trading/engine/portfolio/state.py:31`](../../src/cilly_trading/engine/portfolio/state.py)
- [`src/cilly_trading/engine/portfolio/state.py:69`](../../src/cilly_trading/engine/portfolio/state.py)

Audit notes:

- `cilly_trading.portfolio.PortfolioState` models drawdown and daily PnL inputs.
- `cilly_trading.engine.portfolio.PortfolioState` models current positions for control-plane inspection.
- Both modules expose deterministic portfolio helpers and naming, but they are already separated by domain purpose, so any consolidation would need to preserve those boundaries.

### 11. Small canonical JSON helpers also repeat in paper trading and persistence code

- Classification: `near duplicate`
- Why it matters: there are additional one-off canonical JSON helpers outside the larger artifact families, which indicates a broad pattern of local helper reimplementation.

Affected implementations:

- [`src/cilly_trading/engine/paper_trading.py:69`](../../src/cilly_trading/engine/paper_trading.py)
- [`src/cilly_trading/repositories/signals_sqlite.py:53`](../../src/cilly_trading/repositories/signals_sqlite.py)
- [`src/api/order_events_sqlite.py:80`](../../src/api/order_events_sqlite.py)
- [`src/cilly_trading/smoke_run.py:79`](../../src/cilly_trading/smoke_run.py)

Audit notes:

- These helpers all use sorted-key JSON serialization for deterministic persistence or notes payloads.
- They differ on newline handling, `ensure_ascii`, `allow_nan`, and whether they hash the bytes afterward.
- They are not the strongest duplication candidates individually, but together they reinforce that canonical JSON behavior is scattered.

## Consolidation-ready issue seeds

The codebase is specific enough to support follow-up consolidation issues in at least these areas:

1. Shared canonical identity utilities for signal/run/event hashing.
2. Shared deterministic trade numeric and ordering helpers for post-trade artifact builders.
3. Shared canonical artifact serialization/writer helpers, with optional SHA sidecar support.
4. Shared guard/config parsing helpers for compliance state assembly.
5. Strategy configuration normalization alignment between `config_schema.py` and strategy-local parsing.

## Manual validation performed

Manual validation for this audit consisted of direct source review of the referenced modules and helper definitions listed above. No runtime code paths were changed.

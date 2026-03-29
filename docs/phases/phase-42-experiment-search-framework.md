# LAB-P42 Experiment and Parameter Search Framework

## Scope

This phase defines one bounded, reproducible experiment and parameter-search framework for Strategy Lab.

## Bounded Framework Definition

- Module: `src/cilly_trading/strategies/experiment_search.py`
- Entry point: `run_parameter_search_experiment(...)`
- Configuration model: `ParameterSearchExperimentConfig`
- Output model: `ParameterSearchRunResult`

Bounded constraints:

- A search run requires an explicit experiment config.
- Parameter space must be explicit and finite.
- Expanded trial count must not exceed `max_trials`.
- Only supported objective metrics are accepted.
- Snapshot inputs must be explicit and non-empty.

## Validation Discipline

Validation is explicit and enforced during optimization:

- Split mode: chronological holdout (`development` first, `validation` tail).
- Config bounds:
  - `validation_split_ratio` must be between `0.1` and `0.5`.
  - `min_development_snapshots` must be >= `1`.
  - `min_validation_snapshots` must be >= `1`.
- Runtime enforcement:
  - The run fails if the split cannot satisfy both minimum segment sizes.
  - Every trial is evaluated on both segments.
  - Trial selection uses development objective ranking only.

## Anti-Overfit Guardrails

Guardrails are bounded and enforced in selection:

- Guardrail config:
  - `max_validation_degradation_fraction` in `[0.0, 1.0]`.
  - `require_guardrail_pass_for_selection` boolean.
- Per-trial computed values:
  - `validation_degradation`
  - `validation_degradation_fraction`
  - `passed`
- Enforcement:
  - If `require_guardrail_pass_for_selection=true`, only guardrail-passing trials are eligible for final selection.
  - If no trial passes, the run fails with an explicit error.

## Reproducibility Model

Each run is deterministic from explicit inputs:

- Canonical config payload (`config_sha256`)
- Canonical ordered snapshots payload (`snapshots_sha256`)
- Deterministic `run_id` derived from those hashes
- Canonical artifact serialization (`canonical_json_bytes`)
- Artifact checksum file (`parameter-search-result.sha256`)

Given identical config and snapshot inputs, produced artifact bytes and SHA256 are identical.

## Inputs and Outputs

### Inputs

`ParameterSearchExperimentConfig` includes:

- `experiment_id`
- `strategy_name`
- `dataset_ref`
- `parameter_space`
- `objective_metric`
- `objective_direction`
- `max_trials`
- `snapshot_selector`
- `validation_split_ratio`
- `min_development_snapshots`
- `min_validation_snapshots`
- `max_validation_degradation_fraction`
- `require_guardrail_pass_for_selection`

Runtime input:

- `snapshots` sequence
- `output_dir`

### Outputs

Search artifact files:

- `parameter-search-result.json`
- `parameter-search-result.sha256`

Artifact payload sections:

- `experiment` (explicit configuration, validation discipline, guardrails)
- `run_metadata` (hashes, run id, trial count, split counts)
- `search_results` (objective definition, selection policy, trial rows)
- `reports` (aligned reusable report structures)

Within each `search_results.trials[*]`:

- `development` segment metrics/artifact linkage
- `validation` segment metrics/artifact linkage
- `guardrails` status
- legacy trial summary fields retained for development segment compatibility

Within each segment comparison-artifact entry:

- `relpath` points to `trials/<trial_id>/<segment>/strategy-comparison.json`
- `sha256` is the SHA256 of the exact file bytes at that `relpath`

### Strategy Comparison Semantics Boundary

Trial segment artifacts inherit bounded comparison semantics from the strategy comparison harness:

- Signal score interpretation remains strategy-local.
- Ranking scope is `comparison_group`, not unrestricted cross-strategy confidence ordering.
- Cross-group benchmark deltas are intentionally unsupported (`null`).

This keeps experiment search outputs aligned with evidence-backed strategy boundaries.

## Comparison and Reporting Conventions

The framework now emits explicit development/validation distinctions in report payloads:

- `reports.strategy_comparison.strategies[*].development`
- `reports.strategy_comparison.strategies[*].validation`
- `reports.performance_report.selected_trial_validation`

Selection metadata is always explicit:

- `search_results.selection.policy`
- `search_results.selection.best_development_trial_id`
- `search_results.selection.selected_trial_id`
- `search_results.selection.guardrail_passed_trial_count`

## Tests

Representative coverage in `tests/strategies/test_experiment_search.py` includes:

- validation workflow tests (segment split and dual-segment trial outputs)
- negative tests for invalid setup (invalid ratio, insufficient split size)
- negative tests for guardrail enforcement (no eligible trial)
- representative report/output tests (development vs validation report shape)
- reproducibility test for identical inputs

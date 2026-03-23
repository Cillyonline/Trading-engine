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

Runtime input:

- `snapshots` sequence
- `output_dir`

### Outputs

Search artifact files:

- `parameter-search-result.json`
- `parameter-search-result.sha256`

Artifact payload sections:

- `experiment` (explicit configuration)
- `run_metadata` (hashes, run id, trial count)
- `search_results` (objective definition, best trial, trial rows)
- `reports` (aligned reusable report structures)

Within each `search_results.trials[*].comparison_artifact` entry:

- `relpath` points to `trials/<trial_id>/strategy-comparison.json`
- `sha256` is the SHA256 of the exact file bytes at that `relpath`

## Reusable Report Alignment

The framework emits report-aligned structures in `reports`:

- `strategy_comparison` artifact-shaped payload
- `performance_report` artifact-shaped payload

This allows future research runs to use consistent report conventions instead of ad hoc output schemas.

## Tests

Added representative test coverage in `tests/strategies/test_experiment_search.py`:

- configuration validation test
- representative search-run test
- reproducibility test
- negative execution test

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

## Minimal schema

Top-level object keys and minimal semantics:

- `artifact_version` (required): string literal `"1"`
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

## Hash reproducibility

- Hash algorithm: SHA-256
- Hash input: exact UTF-8 bytes of `backtest-result.json`, including trailing LF
- Sidecar file: `backtest-result.sha256`
- Sidecar content format: `"<hex>\n"`

Any change in payload bytes (including key order, whitespace, newline style, or trailing newline count) changes the hash and is therefore non-compliant.

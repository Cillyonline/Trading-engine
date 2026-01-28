# Phase-6 Deterministic Snapshot Contract

## Snapshot ID rules

- Phase-6 runs **must** provide a `snapshot_id`.
- In this system, `snapshot_id` is the `ingestion_run_id` used by snapshot-only engine runs.
- The snapshot resolves to the SQLite snapshot store (`ingestion_runs` + `ohlcv_snapshots`) using that `ingestion_run_id`.

## Metadata fields

Snapshot metadata is immutable and stored in `metadata.json` with the following fields:

- `snapshot_id` (string)
- `provider` (string)
- `source` (string, endpoint or dataset name)
- `created_at_utc` (ISO-8601 string)
- `payload_checksum` (string, SHA-256 of payload bytes)
- `schema_version` (string or int)
- `notes` (optional string)

## Audit persistence

Every Phase-6 run persists a deterministic audit record to:

```
runs/phase6/<run_id>/audit.json
```

The audit record includes:

- `run_id`
- `snapshot_id`
- `snapshot_metadata` (full metadata object)
- `engine_version` (if `CILLY_ENGINE_VERSION` is set)

Audit JSON serialization uses sorted keys for stable byte output.

## Deterministic replay

- Replays resolve snapshot payload bytes directly from `payload.json`.
- Snapshot payload bytes are verified against the stored checksum.
- Result artifacts are serialized with sorted keys to ensure byte-identical output when reusing the same snapshot.

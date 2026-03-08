"""Canonical market dataset contract for deterministic metadata and identity."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Mapping

DATASET_CONTRACT_VERSION = "1.0.0"

DATASET_IDENTITY_FIELDS: tuple[str, ...] = (
    "symbol",
    "timeframe",
    "source",
    "start_timestamp",
    "end_timestamp",
    "row_count",
    "content_sha256",
)

CANONICAL_MARKET_DATASET_METADATA_SCHEMA: dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "https://cilly-trading.dev/schemas/market-dataset-metadata.json",
    "title": "CanonicalMarketDatasetMetadata",
    "type": "object",
    "required": [
        "dataset_id",
        "symbol",
        "timeframe",
        "source",
        "start_timestamp",
        "end_timestamp",
        "row_count",
        "created_at",
        "content_sha256",
    ],
    "additionalProperties": False,
    "properties": {
        "dataset_id": {"type": "string", "minLength": 1},
        "symbol": {"type": "string", "minLength": 1},
        "timeframe": {"type": "string", "minLength": 1},
        "source": {"type": "string", "minLength": 1},
        "start_timestamp": {"type": "string", "format": "date-time"},
        "end_timestamp": {"type": "string", "format": "date-time"},
        "row_count": {"type": "integer", "minimum": 0},
        "created_at": {"type": "string", "format": "date-time"},
        "content_sha256": {
            "type": "string",
            "pattern": "^[a-fA-F0-9]{64}$",
        },
        "contract_version": {"type": "string", "minLength": 1},
    },
}


class DatasetMetadataValidationError(ValueError):
    """Raised when canonical dataset metadata validation fails."""


def _parse_iso8601(value: Any, field_name: str) -> datetime:
    if not isinstance(value, str):
        raise DatasetMetadataValidationError(f"{field_name} must be a string")
    normalized = value.replace("Z", "+00:00") if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise DatasetMetadataValidationError(
            f"{field_name} must be a valid ISO-8601 timestamp"
        ) from exc

    if parsed.tzinfo is None:
        raise DatasetMetadataValidationError(
            f"{field_name} must include timezone information"
        )
    return parsed.astimezone(timezone.utc)


def _normalize_identity_payload(metadata: Mapping[str, Any]) -> dict[str, Any]:
    identity_payload: dict[str, Any] = {}
    for field in DATASET_IDENTITY_FIELDS:
        if field not in metadata:
            raise DatasetMetadataValidationError(
                f"missing identity field for dataset_id: {field}"
            )
        value = metadata[field]
        if field in ("start_timestamp", "end_timestamp"):
            value = _parse_iso8601(value, field).isoformat()
        identity_payload[field] = value
    return identity_payload


def compute_dataset_identity(metadata: Mapping[str, Any]) -> str:
    """Compute deterministic dataset identity from canonical identity fields."""

    identity_payload = _normalize_identity_payload(metadata)
    canonical = json.dumps(identity_payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def build_market_dataset_metadata(
    *,
    symbol: str,
    timeframe: str,
    source: str,
    start_timestamp: str,
    end_timestamp: str,
    row_count: int,
    content_sha256: str,
    created_at: str | None = None,
    contract_version: str = DATASET_CONTRACT_VERSION,
) -> dict[str, Any]:
    """Build canonical market dataset metadata with deterministic dataset_id."""

    metadata: dict[str, Any] = {
        "symbol": symbol,
        "timeframe": timeframe,
        "source": source,
        "start_timestamp": start_timestamp,
        "end_timestamp": end_timestamp,
        "row_count": row_count,
        "content_sha256": content_sha256,
        "created_at": created_at
        or datetime.now(tz=timezone.utc).replace(microsecond=0).isoformat(),
        "contract_version": contract_version,
    }
    metadata["dataset_id"] = compute_dataset_identity(metadata)
    return validate_market_dataset_metadata(metadata)


def validate_market_dataset_metadata(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Validate canonical market dataset metadata payload."""

    if not isinstance(payload, Mapping):
        raise DatasetMetadataValidationError("metadata payload must be an object")

    required_fields = tuple(CANONICAL_MARKET_DATASET_METADATA_SCHEMA["required"])
    missing = [field for field in required_fields if field not in payload]
    if missing:
        raise DatasetMetadataValidationError(
            f"missing required metadata field(s): {', '.join(missing)}"
        )

    allowed_fields = set(CANONICAL_MARKET_DATASET_METADATA_SCHEMA["properties"].keys())
    extra_fields = [field for field in payload if field not in allowed_fields]
    if extra_fields:
        raise DatasetMetadataValidationError(
            f"unknown metadata field(s): {', '.join(extra_fields)}"
        )

    dataset_id = payload["dataset_id"]
    if not isinstance(dataset_id, str) or not dataset_id:
        raise DatasetMetadataValidationError("dataset_id must be a non-empty string")

    for field_name in ("symbol", "timeframe", "source"):
        value = payload[field_name]
        if not isinstance(value, str) or not value:
            raise DatasetMetadataValidationError(
                f"{field_name} must be a non-empty string"
            )

    row_count = payload["row_count"]
    if not isinstance(row_count, int) or isinstance(row_count, bool):
        raise DatasetMetadataValidationError("row_count must be an integer")
    if row_count < 0:
        raise DatasetMetadataValidationError("row_count must be >= 0")

    start = _parse_iso8601(payload["start_timestamp"], "start_timestamp")
    end = _parse_iso8601(payload["end_timestamp"], "end_timestamp")
    _parse_iso8601(payload["created_at"], "created_at")

    if start > end:
        raise DatasetMetadataValidationError(
            "start_timestamp must be <= end_timestamp"
        )

    content_sha256 = payload["content_sha256"]
    if (
        not isinstance(content_sha256, str)
        or len(content_sha256) != 64
        or any(char not in "0123456789abcdefABCDEF" for char in content_sha256)
    ):
        raise DatasetMetadataValidationError(
            "content_sha256 must be a valid 64-char SHA-256 hex digest"
        )

    expected_dataset_id = compute_dataset_identity(payload)
    if dataset_id != expected_dataset_id:
        raise DatasetMetadataValidationError(
            "dataset_id does not match canonical identity fields"
        )

    normalized = dict(payload)
    normalized["start_timestamp"] = start.isoformat()
    normalized["end_timestamp"] = end.isoformat()
    normalized["created_at"] = _parse_iso8601(
        payload["created_at"], "created_at"
    ).isoformat()
    return normalized

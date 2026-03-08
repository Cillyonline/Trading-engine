from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _load_contract_module():
    root = Path(__file__).resolve().parents[2]
    module_path = (
        root / "src" / "cilly_trading" / "engine" / "data" / "market_dataset_contract.py"
    )
    spec = importlib.util.spec_from_file_location("market_dataset_contract", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load market_dataset_contract module")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


module = _load_contract_module()
build_market_dataset_metadata = module.build_market_dataset_metadata
compute_dataset_identity = module.compute_dataset_identity
validate_market_dataset_metadata = module.validate_market_dataset_metadata
DatasetMetadataValidationError = module.DatasetMetadataValidationError
CANONICAL_MARKET_DATASET_METADATA_SCHEMA = module.CANONICAL_MARKET_DATASET_METADATA_SCHEMA


def _valid_payload() -> dict[str, object]:
    payload = {
        "symbol": "BTC/USDT",
        "timeframe": "1H",
        "source": "binance.spot.ohlcv",
        "start_timestamp": "2025-01-01T00:00:00+00:00",
        "end_timestamp": "2025-01-02T00:00:00+00:00",
        "row_count": 24,
        "created_at": "2025-01-03T12:00:00+00:00",
        "content_sha256": "a" * 64,
    }
    payload["dataset_id"] = compute_dataset_identity(payload)
    return payload


def test_schema_defines_required_canonical_fields() -> None:
    required = set(CANONICAL_MARKET_DATASET_METADATA_SCHEMA["required"])
    assert {
        "dataset_id",
        "symbol",
        "timeframe",
        "source",
        "start_timestamp",
        "end_timestamp",
        "row_count",
        "created_at",
    }.issubset(required)


def test_validate_market_dataset_metadata_accepts_valid_payload() -> None:
    validated = validate_market_dataset_metadata(_valid_payload())

    assert validated["dataset_id"]
    assert validated["symbol"] == "BTC/USDT"
    assert validated["row_count"] == 24


def test_validate_market_dataset_metadata_rejects_missing_required_field() -> None:
    invalid = _valid_payload()
    invalid.pop("source")

    try:
        validate_market_dataset_metadata(invalid)
    except DatasetMetadataValidationError as exc:
        assert "missing required metadata field" in str(exc)
    else:
        raise AssertionError("Expected validation failure for missing required field")


def test_validate_market_dataset_metadata_rejects_incorrect_type() -> None:
    invalid = _valid_payload()
    invalid["row_count"] = "24"

    try:
        validate_market_dataset_metadata(invalid)
    except DatasetMetadataValidationError as exc:
        assert "row_count must be an integer" in str(exc)
    else:
        raise AssertionError("Expected validation failure for incorrect row_count type")


def test_compute_dataset_identity_is_deterministic_for_logically_identical_datasets() -> None:
    first = _valid_payload()
    second = _valid_payload()
    second["created_at"] = "2025-02-01T00:00:00+00:00"

    first_id = compute_dataset_identity(first)
    second_id = compute_dataset_identity(second)

    assert first_id == second_id


def test_compute_dataset_identity_normalizes_z_and_utc_offset_timestamps() -> None:
    from_z = _valid_payload()
    from_z["start_timestamp"] = "2025-01-01T00:00:00Z"
    from_z["end_timestamp"] = "2025-01-02T00:00:00Z"

    from_offset = _valid_payload()
    from_offset["start_timestamp"] = "2025-01-01T00:00:00+00:00"
    from_offset["end_timestamp"] = "2025-01-02T00:00:00+00:00"

    assert compute_dataset_identity(from_z) == compute_dataset_identity(from_offset)


def test_compute_dataset_identity_normalizes_non_utc_offsets_to_same_instant() -> None:
    utc_payload = _valid_payload()
    utc_payload["start_timestamp"] = "2025-01-01T00:00:00+00:00"
    utc_payload["end_timestamp"] = "2025-01-01T01:00:00+00:00"

    non_utc_payload = _valid_payload()
    non_utc_payload["start_timestamp"] = "2024-12-31T19:00:00-05:00"
    non_utc_payload["end_timestamp"] = "2024-12-31T20:00:00-05:00"

    assert compute_dataset_identity(utc_payload) == compute_dataset_identity(
        non_utc_payload
    )


def test_validate_market_dataset_metadata_rejects_non_deterministic_dataset_id() -> None:
    invalid = _valid_payload()
    invalid["dataset_id"] = "f" * 64

    try:
        validate_market_dataset_metadata(invalid)
    except DatasetMetadataValidationError as exc:
        assert "dataset_id does not match canonical identity fields" in str(exc)
    else:
        raise AssertionError("Expected validation failure for non-canonical dataset_id")


def test_validate_market_dataset_metadata_compares_against_canonicalized_identity() -> None:
    canonical_base = _valid_payload()
    canonical_base["start_timestamp"] = "2025-01-01T00:00:00+00:00"
    canonical_base["end_timestamp"] = "2025-01-02T00:00:00+00:00"
    canonical_dataset_id = compute_dataset_identity(canonical_base)

    equivalent_payload = _valid_payload()
    equivalent_payload["start_timestamp"] = "2025-01-01T00:00:00Z"
    equivalent_payload["end_timestamp"] = "2025-01-02T00:00:00Z"
    equivalent_payload["dataset_id"] = canonical_dataset_id

    validated = validate_market_dataset_metadata(equivalent_payload)
    assert validated["dataset_id"] == canonical_dataset_id
    assert validated["start_timestamp"] == "2025-01-01T00:00:00+00:00"
    assert validated["end_timestamp"] == "2025-01-02T00:00:00+00:00"


def test_build_market_dataset_metadata_creates_canonical_payload() -> None:
    built = build_market_dataset_metadata(
        symbol="ETH/USDT",
        timeframe="4H",
        source="kraken.spot.ohlcv",
        start_timestamp="2025-01-01T00:00:00+00:00",
        end_timestamp="2025-01-02T00:00:00+00:00",
        row_count=6,
        content_sha256="b" * 64,
        created_at="2025-01-04T00:00:00+00:00",
    )

    assert built["dataset_id"] == compute_dataset_identity(built)
    assert built["symbol"] == "ETH/USDT"
    assert built["row_count"] == 6

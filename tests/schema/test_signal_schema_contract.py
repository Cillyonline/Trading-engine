from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from tests.utils.golden_master import prepare_snapshot_db, run_fixed_analysis
from tests.utils.json_schema_validator import SchemaError, validate_json_schema

def _schema_path() -> Path:
    return Path(__file__).resolve().parents[2] / "schemas" / "signal-output.schema.json"


def _load_schema() -> Dict[str, Any]:
    return json.loads(_schema_path().read_text(encoding="utf-8"))


def _format_errors(errors: List[SchemaError]) -> str:
    lines = [f"{err.path}: {err.message}" for err in errors]
    return "\n".join(lines)


def _schema_version(schema: Dict[str, Any]) -> str:
    version_enum = schema["properties"]["schema_version"]["enum"]
    if not isinstance(version_enum, list) or not version_enum:
        raise ValueError("schema_version enum must contain at least one version")
    return str(version_enum[0])


def _build_signal_payload(tmp_path: Path, *, schema_version: str) -> Dict[str, Any]:
    db_path = tmp_path / "schema_validation.db"
    prepare_snapshot_db(db_path)
    return run_fixed_analysis(db_path, schema_version=schema_version)


def test_signal_schema_validates_fixed_analysis_output(tmp_path: Path) -> None:
    schema = _load_schema()
    payload = _build_signal_payload(tmp_path, schema_version=_schema_version(schema))

    errors = validate_json_schema(payload, schema)

    assert errors == [], _format_errors(errors)


def test_signal_schema_missing_version_fails(tmp_path: Path) -> None:
    schema = _load_schema()
    payload = _build_signal_payload(tmp_path, schema_version=_schema_version(schema))
    payload.pop("schema_version", None)

    errors = validate_json_schema(payload, schema)

    assert errors, "Expected schema validation to fail when schema_version is missing"
    assert "schema_version" in _format_errors(errors)


def test_signal_schema_wrong_version_fails(tmp_path: Path) -> None:
    schema = _load_schema()
    payload = _build_signal_payload(tmp_path, schema_version=_schema_version(schema))
    payload["schema_version"] = "9.9.9"

    errors = validate_json_schema(payload, schema)

    assert errors, "Expected schema validation to fail when schema_version is incorrect"
    assert "enum" in _format_errors(errors)


def test_signal_schema_rejects_additional_fields(tmp_path: Path) -> None:
    schema = _load_schema()
    payload = _build_signal_payload(tmp_path, schema_version=_schema_version(schema))
    payload["unexpected"] = True

    errors = validate_json_schema(payload, schema)

    assert errors, "Expected schema validation to fail when additional fields are present"
    assert "Additional property not allowed" in _format_errors(errors)

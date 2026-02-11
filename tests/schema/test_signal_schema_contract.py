from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from tests.utils.json_schema_validator import SchemaError, validate_json_schema

FIXTURE_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "schema"
SCHEMA_DIR = Path(__file__).resolve().parents[2] / "schemas"


def _schema_path(filename: str) -> Path:
    return SCHEMA_DIR / filename


def _fixture_path(filename: str) -> Path:
    return FIXTURE_DIR / filename


def _load_schema(filename: str) -> Dict[str, Any]:
    return json.loads(_schema_path(filename).read_text(encoding="utf-8"))


def _load_fixture(filename: str) -> Dict[str, Any]:
    return json.loads(_fixture_path(filename).read_text(encoding="utf-8"))


def _format_errors(errors: List[SchemaError]) -> str:
    lines = [f"{err.path}: {err.message}" for err in errors]
    return "\n".join(lines)


def test_signal_schema_v0_fixture_validates() -> None:
    schema = _load_schema("signal-output.schema.v0.json")
    payload = _load_fixture("signal_output_v0.json")

    errors = validate_json_schema(payload, schema)

    assert errors == [], _format_errors(errors)


def test_signal_schema_v1_fixture_validates() -> None:
    schema = _load_schema("signal-output.schema.json")
    payload = _load_fixture("signal_output_v1.json")

    errors = validate_json_schema(payload, schema)

    assert errors == [], _format_errors(errors)


def test_signal_schema_missing_version_fails() -> None:
    schema = _load_schema("signal-output.schema.json")
    payload = _load_fixture("signal_output_v1.json")
    payload.pop("schema_version", None)

    errors = validate_json_schema(payload, schema)

    assert errors, "Expected schema validation to fail when schema_version is missing"
    assert "schema_version" in _format_errors(errors)


def test_signal_schema_wrong_version_fails() -> None:
    schema = _load_schema("signal-output.schema.json")
    payload = _load_fixture("signal_output_v1.json")
    payload["schema_version"] = "9.9.9"

    errors = validate_json_schema(payload, schema)

    assert errors, "Expected schema validation to fail when schema_version is incorrect"
    assert "schema_version" in _format_errors(errors).lower()


def test_signal_schema_rejects_additional_fields() -> None:
    schema = _load_schema("signal-output.schema.json")
    payload = _load_fixture("signal_output_v1.json")
    payload["unexpected"] = True

    errors = validate_json_schema(payload, schema)

    assert errors, "Expected schema validation to fail when additional fields are present"
    msg = _format_errors(errors).lower()
    assert "unexpected" in msg or "additional" in msg

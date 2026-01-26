from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

from tests.utils.json_schema_validator import SchemaError, validate_json_schema


@dataclass(frozen=True)
class ConsumerReadResult:
    payload: Dict[str, Any]
    errors: List[SchemaError]


FIXTURE_DIR = Path(__file__).resolve().parents[1] / "consumer" / "consumer_fixtures"
SCHEMA_DIR = Path(__file__).resolve().parents[2] / "schemas"

SUPPORTED_CONSUMER_SCHEMAS = ["signal-output.schema.v0.json"]


def load_fixture(name: str) -> Dict[str, Any]:
    path = FIXTURE_DIR / name
    return json.loads(path.read_text())


def load_schema(name: str) -> Dict[str, Any]:
    path = SCHEMA_DIR / name
    return json.loads(path.read_text())


def iter_supported_consumer_schemas() -> List[str]:
    return list(SUPPORTED_CONSUMER_SCHEMAS)


def deserialize_tolerant(instance: Dict[str, Any], schema: Dict[str, Any]) -> ConsumerReadResult:
    pruned = _prune_unknown_fields(instance, schema, root_schema=schema)
    errors = validate_json_schema(pruned, schema)
    return ConsumerReadResult(payload=pruned, errors=errors)


def assert_consumer_can_read_output(
    instance: Dict[str, Any],
    *,
    schema_name: str,
    accepted_versions: List[str],
) -> Dict[str, Any]:
    schema = load_schema(schema_name)
    schema = _with_schema_versions(schema, accepted_versions)
    result = deserialize_tolerant(instance, schema)
    if result.errors:
        formatted = ", ".join(error.message for error in result.errors)
        raise AssertionError(
            f"Consumer could not read output with schema {schema_name}: {formatted}"
        )
    return result.payload


def assert_consumer_can_read_v0_from_v1_output(instance: Dict[str, Any]) -> Dict[str, Any]:
    return assert_consumer_can_read_output(
        instance,
        schema_name="signal-output.schema.v0.json",
        accepted_versions=["0.9.0", "1.0.0"],
    )


def _prune_unknown_fields(instance: Any, schema: Dict[str, Any], *, root_schema: Dict[str, Any]) -> Any:
    resolved = _resolve_ref(schema, root_schema)
    expected_type = resolved.get("type")

    if expected_type == "object" and isinstance(instance, dict):
        properties = resolved.get("properties", {})
        return {
            key: _prune_unknown_fields(value, properties[key], root_schema=root_schema)
            for key, value in instance.items()
            if key in properties
        }

    if expected_type == "array" and isinstance(instance, list):
        items_schema = resolved.get("items")
        if items_schema is None:
            return list(instance)
        return [_prune_unknown_fields(item, items_schema, root_schema=root_schema) for item in instance]

    return instance


def _resolve_ref(schema: Dict[str, Any], root_schema: Dict[str, Any]) -> Dict[str, Any]:
    if "$ref" not in schema:
        return schema
    ref = schema["$ref"]
    if not isinstance(ref, str) or not ref.startswith("#/"):
        return schema
    parts = [part for part in ref.lstrip("#/").split("/") if part]
    resolved: Any = root_schema
    for part in parts:
        if not isinstance(resolved, dict) or part not in resolved:
            return schema
        resolved = resolved[part]
    return resolved if isinstance(resolved, dict) else schema


def _with_schema_versions(schema: Dict[str, Any], versions: List[str]) -> Dict[str, Any]:
    updated = json.loads(json.dumps(schema))
    properties = updated.get("properties", {})
    version_schema = properties.get("schema_version")
    if isinstance(version_schema, dict):
        version_schema["enum"] = list(versions)
    return updated

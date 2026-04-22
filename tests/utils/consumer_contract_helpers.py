"""Shared helpers for bounded contract tests.

This module hosts two narrowly-scoped helper groups used by bounded
contract tests:

* Consumer-contract read helpers (the original purpose of this module),
  which validate JSON instances against schema fixtures and prune
  unknown fields for tolerant consumer-side reads.
* A minimal canonical helper set for documentation/contract tests
  (``REPO_ROOT``, ``read_repo_text``, ``assert_contains_all``,
  ``assert_starts_with``) that reduces repeated repo-root and
  ``read_text`` boilerplate.

Design constraints (preserved across both helper groups):

* **Read-only:** helpers never mutate files on disk.
* **Non-inference:** helpers do not synthesize qualification,
  profitability, or readiness claims and do not interpret runtime
  behavior.
* **Non-live boundary:** these helpers are bounded contract-test
  utilities only. They do not imply live-trading readiness, broker
  execution readiness, or trader-validation evidence.
* **Assertion equivalence:** ``assert_contains_all`` and
  ``assert_starts_with`` are deterministic equivalents of expanded
  ``assert <substring> in <content>`` / ``assert content.startswith(...)``
  blocks; pass/fail outcomes are unchanged.
"""

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


REPO_ROOT: Path = Path(__file__).resolve().parents[2]
FIXTURE_DIR = Path(__file__).resolve().parents[1] / "consumer" / "consumer_fixtures"
SCHEMA_DIR = REPO_ROOT / "src" / "cilly_trading" / "contracts" / "schemas"


def read_repo_text(relative_path: str) -> str:
    """Return the UTF-8 text contents of ``relative_path`` under the repo root.

    Strictly read-only. Used by bounded contract tests to assert the
    documented evidence and claim-boundary semantics of repository
    artifacts without inferring runtime behavior.
    """

    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")


def assert_contains_all(content: str, *required_substrings: str) -> None:
    """Assert each required substring appears in ``content``.

    Each substring is checked with the ``in`` operator, preserving the
    deterministic pass/fail semantics of the equivalent expanded
    ``assert <substring> in content`` block. On failure the first
    missing substring is reported so test intent stays readable.
    """

    for substring in required_substrings:
        assert substring in content, f"Missing required substring: {substring!r}"


def assert_starts_with(content: str, prefix: str) -> None:
    """Assert ``content`` starts with ``prefix`` (deterministic)."""

    assert content.startswith(prefix), (
        f"Content does not start with required prefix: {prefix!r}"
    )

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

from __future__ import annotations

from typing import Any, Dict

import pytest

from tests.utils.schema_breaking_change_detector import (
    assert_no_breaking_changes_without_major_bump,
    detect_breaking_changes,
    extract_major_version,
)


def _base_schema() -> Dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "schema_version": {"type": "string", "enum": ["1.0.0"]},
            "signal": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "score": {"type": "number"},
                },
                "required": ["id", "score"],
                "additionalProperties": False,
            },
        },
        "required": ["schema_version", "signal"],
        "additionalProperties": False,
    }


def _breaking_removed_field_schema() -> Dict[str, Any]:
    schema = _base_schema()
    schema["properties"]["signal"]["properties"].pop("score")
    schema["properties"]["signal"]["required"] = ["id"]
    return schema


def _breaking_type_change_schema() -> Dict[str, Any]:
    schema = _base_schema()
    schema["properties"]["signal"]["properties"]["score"]["type"] = "string"
    return schema


def _breaking_requiredness_schema() -> Dict[str, Any]:
    schema = _base_schema()
    schema["properties"]["signal"]["required"] = ["id"]
    return schema


@pytest.mark.parametrize(
    "schema_factory, expected_rule, expected_field",
    [
        (_breaking_removed_field_schema, "Field removed", "$.signal.score"),
        (_breaking_type_change_schema, "Type changed", "$.signal.score"),
        (_breaking_requiredness_schema, "Requiredness changed", "$.signal.score"),
    ],
)
def test_breaking_change_requires_major_bump(schema_factory, expected_rule, expected_field) -> None:
    old_schema = _base_schema()
    new_schema = schema_factory()

    changes = detect_breaking_changes(old_schema, new_schema)

    assert changes, "Expected breaking changes to be detected"
    assert changes[0].rule == expected_rule
    assert changes[0].field_path == expected_field
    old_major = extract_major_version(old_schema)
    new_major = extract_major_version(new_schema)
    assert old_major == new_major, "Expected no major version bump in test fixture"

    with pytest.raises(AssertionError) as exc:
        assert_no_breaking_changes_without_major_bump(old_schema, new_schema)
    error_message = str(exc.value)
    assert expected_rule in error_message
    assert expected_field in error_message
    assert "Major version bump required." in error_message


def test_breaking_change_allows_major_bump() -> None:
    old_schema = _base_schema()
    new_schema = _breaking_removed_field_schema()
    new_schema["properties"]["schema_version"]["enum"] = ["2.0.0"]

    assert_no_breaking_changes_without_major_bump(old_schema, new_schema)

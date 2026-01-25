from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List


@dataclass(frozen=True)
class SchemaError:
    path: str
    message: str


def validate_json_schema(instance: Any, schema: Dict[str, Any]) -> List[SchemaError]:
    errors: List[SchemaError] = []
    _validate(instance, schema, path="$", errors=errors, root_schema=schema)
    return errors


def _validate(
    instance: Any,
    schema: Dict[str, Any],
    *,
    path: str,
    errors: List[SchemaError],
    root_schema: Dict[str, Any],
) -> None:
    if "$ref" in schema:
        ref = schema["$ref"]
        if not ref.startswith("#/"):
            errors.append(SchemaError(path, f"Unsupported $ref: {ref}"))
            return
        resolved = _resolve_ref(root_schema, ref)
        _validate(instance, resolved, path=path, errors=errors, root_schema=root_schema)
        return

    if "enum" in schema:
        if instance not in schema["enum"]:
            errors.append(SchemaError(path, f"Value {instance!r} not in enum {schema['enum']!r}"))
            return

    expected_type = schema.get("type")
    if expected_type is not None and not _type_matches(instance, expected_type):
        errors.append(
            SchemaError(
                path,
                f"Expected type {expected_type!r} but got {type(instance).__name__}",
            )
        )
        return

    if expected_type == "object":
        if not isinstance(instance, dict):
            return
        _validate_object(instance, schema, path=path, errors=errors, root_schema=root_schema)
        return

    if expected_type == "array":
        if not isinstance(instance, list):
            return
        _validate_array(instance, schema, path=path, errors=errors, root_schema=root_schema)
        return


def _validate_object(
    instance: Dict[str, Any],
    schema: Dict[str, Any],
    *,
    path: str,
    errors: List[SchemaError],
    root_schema: Dict[str, Any],
) -> None:
    required = schema.get("required", [])
    for key in required:
        if key not in instance:
            errors.append(SchemaError(path, f"Missing required property: {key}"))

    properties = schema.get("properties", {})
    additional_allowed = schema.get("additionalProperties", True)

    if additional_allowed is False:
        for key in instance.keys():
            if key not in properties:
                errors.append(SchemaError(path, f"Additional property not allowed: {key}"))

    for key, subschema in properties.items():
        if key not in instance:
            continue
        _validate(
            instance[key],
            subschema,
            path=f"{path}.{key}",
            errors=errors,
            root_schema=root_schema,
        )


def _validate_array(
    instance: List[Any],
    schema: Dict[str, Any],
    *,
    path: str,
    errors: List[SchemaError],
    root_schema: Dict[str, Any],
) -> None:
    min_items = schema.get("minItems")
    if min_items is not None and len(instance) < min_items:
        errors.append(SchemaError(path, f"Expected at least {min_items} items"))

    items_schema = schema.get("items")
    if items_schema is None:
        return
    for idx, item in enumerate(instance):
        _validate(
            item,
            items_schema,
            path=f"{path}[{idx}]",
            errors=errors,
            root_schema=root_schema,
        )


def _type_matches(value: Any, expected: Any) -> bool:
    if isinstance(expected, list):
        return any(_type_matches(value, item) for item in expected)
    if expected == "object":
        return isinstance(value, dict)
    if expected == "array":
        return isinstance(value, list)
    if expected == "string":
        return isinstance(value, str)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "boolean":
        return isinstance(value, bool)
    return False


def _resolve_ref(root_schema: Dict[str, Any], ref: str) -> Dict[str, Any]:
    parts = [part for part in ref.lstrip("#/").split("/") if part]
    resolved: Any = root_schema
    for part in parts:
        if not isinstance(resolved, dict) or part not in resolved:
            raise KeyError(f"Invalid $ref path: {ref}")
        resolved = resolved[part]
    if not isinstance(resolved, dict):
        raise KeyError(f"Invalid $ref target: {ref}")
    return resolved

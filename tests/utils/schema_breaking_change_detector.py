from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence


@dataclass(frozen=True)
class BreakingChange:
    rule: str
    field_path: str
    details: str


def detect_breaking_changes(old_schema: Dict[str, Any], new_schema: Dict[str, Any]) -> List[BreakingChange]:
    changes: List[BreakingChange] = []
    _compare_schema(old_schema, new_schema, path="$", changes=changes, root_old=old_schema, root_new=new_schema)
    return changes


def extract_major_version(schema: Dict[str, Any]) -> Optional[int]:
    version = _extract_schema_version(schema)
    if version is None:
        return None
    major_text = version.split(".", 1)[0]
    if not major_text.isdigit():
        return None
    return int(major_text)


def assert_no_breaking_changes_without_major_bump(
    old_schema: Dict[str, Any],
    new_schema: Dict[str, Any],
) -> None:
    changes = detect_breaking_changes(old_schema, new_schema)
    if not changes:
        return
    old_major = extract_major_version(old_schema)
    new_major = extract_major_version(new_schema)
    if old_major is not None and new_major is not None and new_major > old_major:
        return
    first_change = changes[0]
    message = (
        f"Breaking change detected: {first_change.rule} at {first_change.field_path}. "
        "Major version bump required."
    )
    raise AssertionError(message)


def _extract_schema_version(schema: Dict[str, Any]) -> Optional[str]:
    properties = schema.get("properties", {})
    version_schema = properties.get("schema_version")
    if not isinstance(version_schema, dict):
        return None
    enum_values = version_schema.get("enum")
    if not isinstance(enum_values, list) or not enum_values:
        return None
    version = enum_values[0]
    return version if isinstance(version, str) else None


def _compare_schema(
    old_schema: Dict[str, Any],
    new_schema: Dict[str, Any],
    *,
    path: str,
    changes: List[BreakingChange],
    root_old: Dict[str, Any],
    root_new: Dict[str, Any],
) -> None:
    old_resolved = _resolve_ref(old_schema, root_old)
    new_resolved = _resolve_ref(new_schema, root_new)

    old_type = _normalized_type(old_resolved)
    new_type = _normalized_type(new_resolved)

    if old_type is not None and new_type is not None and old_type != new_type:
        changes.append(
            BreakingChange(
                rule="Type changed",
                field_path=path,
                details=f"Expected {old_type} but got {new_type}",
            )
        )
        return

    if old_type == "object" and new_type == "object":
        _compare_object(old_resolved, new_resolved, path=path, changes=changes, root_old=root_old, root_new=root_new)
        return

    if old_type == "array" and new_type == "array":
        _compare_array(old_resolved, new_resolved, path=path, changes=changes, root_old=root_old, root_new=root_new)


def _compare_object(
    old_schema: Dict[str, Any],
    new_schema: Dict[str, Any],
    *,
    path: str,
    changes: List[BreakingChange],
    root_old: Dict[str, Any],
    root_new: Dict[str, Any],
) -> None:
    old_props = old_schema.get("properties", {})
    new_props = new_schema.get("properties", {})
    old_required = set(_as_sequence(old_schema.get("required")))
    new_required = set(_as_sequence(new_schema.get("required")))

    for key, old_prop in old_props.items():
        field_path = f"{path}.{key}"
        if key not in new_props:
            changes.append(
                BreakingChange(
                    rule="Field removed",
                    field_path=field_path,
                    details="Field no longer present in schema",
                )
            )
            continue

        new_prop = new_props[key]
        was_required = key in old_required
        is_required = key in new_required
        if was_required != is_required:
            changes.append(
                BreakingChange(
                    rule="Requiredness changed",
                    field_path=field_path,
                    details=f"Required changed from {was_required} to {is_required}",
                )
            )

        _compare_schema(
            old_prop,
            new_prop,
            path=field_path,
            changes=changes,
            root_old=root_old,
            root_new=root_new,
        )


def _compare_array(
    old_schema: Dict[str, Any],
    new_schema: Dict[str, Any],
    *,
    path: str,
    changes: List[BreakingChange],
    root_old: Dict[str, Any],
    root_new: Dict[str, Any],
) -> None:
    old_items = old_schema.get("items")
    new_items = new_schema.get("items")
    if old_items is None or new_items is None:
        return
    _compare_schema(
        old_items,
        new_items,
        path=f"{path}[]",
        changes=changes,
        root_old=root_old,
        root_new=root_new,
    )


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


def _normalized_type(schema: Dict[str, Any]) -> Optional[str]:
    schema_type = schema.get("type")
    if isinstance(schema_type, list):
        return "/".join(sorted(str(item) for item in schema_type))
    if isinstance(schema_type, str):
        return schema_type
    return None


def _as_sequence(value: Any) -> Sequence[str]:
    if isinstance(value, list):
        return [item for item in value if isinstance(item, str)]
    return []

"""Validation utilities for strategy registry inputs."""

from __future__ import annotations

import inspect
import re
from collections.abc import Callable
from typing import Any

from cilly_trading.strategies.onboarding_contract import STRATEGY_ONBOARDING_CONTRACT

_SEMVER_PATTERN = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")
_COMPARISON_GROUP_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]*$")
_BASE_METADATA_FIELD_TYPES: dict[str, type] = {
    "pack_id": str,
    "version": str,
    "deterministic_hash": str,
    "dependencies": list,
    "comparison_group": str,
    "documentation": dict,
    "test_coverage": dict,
}


class StrategyValidationError(ValueError):
    """Raised when strategy registration validation fails."""


def validate_strategy_key(key: str) -> str:
    """Validate and normalize a strategy key."""

    if not isinstance(key, str) or not key.strip():
        raise StrategyValidationError("strategy_key must be a non-empty string")
    return key.strip().upper()


def validate_strategy_metadata(metadata: dict) -> dict[str, Any]:
    """Validate strategy metadata schema and deterministic constraints."""

    if not isinstance(metadata, dict):
        raise StrategyValidationError("metadata must be a dict")

    missing_fields = [
        field
        for field in STRATEGY_ONBOARDING_CONTRACT.required_metadata_fields
        if field not in metadata
    ]
    if missing_fields:
        raise StrategyValidationError(
            f"metadata missing required fields: {', '.join(sorted(missing_fields))}"
        )

    unsupported_fields = sorted(
        set(metadata.keys()).difference(STRATEGY_ONBOARDING_CONTRACT.required_metadata_fields)
    )
    if unsupported_fields:
        raise StrategyValidationError(
            f"metadata contains unsupported fields: {', '.join(unsupported_fields)}"
        )

    for field, expected_type in _BASE_METADATA_FIELD_TYPES.items():
        value = metadata[field]
        if not isinstance(value, expected_type):
            raise StrategyValidationError(
                f"metadata field '{field}' must be of type {expected_type.__name__}"
            )
        if expected_type is str and not value.strip():
            raise StrategyValidationError(f"metadata field '{field}' must not be empty")

    pack_id = metadata["pack_id"].strip()
    version = metadata["version"].strip()
    deterministic_hash = metadata["deterministic_hash"].strip()
    comparison_group = metadata["comparison_group"].strip()

    if not _SEMVER_PATTERN.fullmatch(version):
        raise StrategyValidationError("metadata field 'version' must be valid semver")

    dependencies = metadata["dependencies"]
    if any(not isinstance(dep, str) or not dep.strip() for dep in dependencies):
        raise StrategyValidationError("metadata field 'dependencies' must contain non-empty strings")

    if dependencies != sorted(dependencies):
        raise StrategyValidationError("metadata field 'dependencies' must be sorted")

    if len(set(dependencies)) != len(dependencies):
        raise StrategyValidationError("metadata field 'dependencies' must not contain duplicates")

    if not _COMPARISON_GROUP_PATTERN.fullmatch(comparison_group):
        raise StrategyValidationError(
            "metadata field 'comparison_group' must match ^[a-z0-9][a-z0-9_-]*$"
        )

    documentation = _validate_documentation_metadata(metadata["documentation"])
    test_coverage = _validate_test_coverage_metadata(metadata["test_coverage"])

    return {
        "pack_id": pack_id,
        "version": version,
        "deterministic_hash": deterministic_hash,
        "dependencies": [dep.strip() for dep in dependencies],
        "comparison_group": comparison_group,
        "documentation": documentation,
        "test_coverage": test_coverage,
    }


def _normalize_contract_path(path: str) -> str:
    return path.strip().replace("\\", "/")


def _validate_documentation_metadata(value: dict[str, Any]) -> dict[str, str]:
    missing_fields = [
        field
        for field in STRATEGY_ONBOARDING_CONTRACT.required_documentation_fields
        if field not in value
    ]
    if missing_fields:
        raise StrategyValidationError(
            "metadata field 'documentation' missing required fields: "
            + ", ".join(sorted(missing_fields))
        )

    unsupported_fields = sorted(
        set(value.keys()).difference(STRATEGY_ONBOARDING_CONTRACT.required_documentation_fields)
    )
    if unsupported_fields:
        raise StrategyValidationError(
            "metadata field 'documentation' contains unsupported fields: "
            + ", ".join(unsupported_fields)
        )

    architecture_path = value["architecture"]
    operations_path = value["operations"]

    if not isinstance(architecture_path, str) or not architecture_path.strip():
        raise StrategyValidationError(
            "metadata field 'documentation.architecture' must be a non-empty string"
        )
    if not isinstance(operations_path, str) or not operations_path.strip():
        raise StrategyValidationError(
            "metadata field 'documentation.operations' must be a non-empty string"
        )

    architecture_path = _normalize_contract_path(architecture_path)
    operations_path = _normalize_contract_path(operations_path)

    if not architecture_path.startswith("docs/architecture/") or not architecture_path.endswith(".md"):
        raise StrategyValidationError(
            "metadata field 'documentation.architecture' must point to docs/architecture/*.md"
        )
    if not operations_path.startswith("docs/operations/") or not operations_path.endswith(".md"):
        raise StrategyValidationError(
            "metadata field 'documentation.operations' must point to docs/operations/*.md"
        )

    return {
        "architecture": architecture_path,
        "operations": operations_path,
    }


def _validate_test_coverage_metadata(value: dict[str, Any]) -> dict[str, str]:
    missing_fields = [
        field
        for field in STRATEGY_ONBOARDING_CONTRACT.required_test_coverage_fields
        if field not in value
    ]
    if missing_fields:
        raise StrategyValidationError(
            "metadata field 'test_coverage' missing required fields: "
            + ", ".join(sorted(missing_fields))
        )

    unsupported_fields = sorted(
        set(value.keys()).difference(STRATEGY_ONBOARDING_CONTRACT.required_test_coverage_fields)
    )
    if unsupported_fields:
        raise StrategyValidationError(
            "metadata field 'test_coverage' contains unsupported fields: "
            + ", ".join(unsupported_fields)
        )

    normalized_refs: dict[str, str] = {}
    for field in STRATEGY_ONBOARDING_CONTRACT.required_test_coverage_fields:
        raw_value = value[field]
        if not isinstance(raw_value, str) or not raw_value.strip():
            raise StrategyValidationError(
                f"metadata field 'test_coverage.{field}' must be a non-empty string"
            )
        normalized_value = _normalize_contract_path(raw_value)
        if not normalized_value.startswith("tests/") or not normalized_value.endswith(".py"):
            raise StrategyValidationError(
                f"metadata field 'test_coverage.{field}' must point to tests/*.py"
            )
        normalized_refs[field] = normalized_value

    if len(set(normalized_refs.values())) != len(normalized_refs):
        raise StrategyValidationError("metadata field 'test_coverage' must contain distinct test paths")

    return normalized_refs


def _validate_factory_signature(factory: Callable[..., Any]) -> None:
    signature = inspect.signature(factory)
    for parameter in signature.parameters.values():
        if parameter.kind in (
            inspect.Parameter.POSITIONAL_ONLY,
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
            inspect.Parameter.KEYWORD_ONLY,
            inspect.Parameter.VAR_POSITIONAL,
            inspect.Parameter.VAR_KEYWORD,
        ):
            raise StrategyValidationError("factory must not accept args, *args, or **kwargs")


def _is_base_strategy_instance(value: Any) -> bool:
    strategy_name = getattr(value, "name", None)
    generate_signals = getattr(value, "generate_signals", None)

    return isinstance(strategy_name, str) and bool(strategy_name.strip()) and callable(generate_signals)


def validate_strategy_factory(factory: Callable[..., Any]) -> None:
    """Validate strategy factory determinism and output contract."""

    if not callable(factory):
        raise StrategyValidationError("factory must be callable")

    _validate_factory_signature(factory)

    instance = factory()
    if not _is_base_strategy_instance(instance):
        raise StrategyValidationError("factory must return an instance of BaseStrategy")


def validate_before_registration(
    key: str,
    factory: Callable[..., Any],
    metadata: dict | None,
    registry_keys: set[str] | None = None,
) -> tuple[str, dict[str, Any]]:
    """Validate key, factory, metadata and duplicate status before registry writes."""

    normalized_key = validate_strategy_key(key)
    if registry_keys is not None and normalized_key in registry_keys:
        raise StrategyValidationError(f"strategy already registered: {normalized_key}")

    if metadata is None:
        raise StrategyValidationError("metadata is required")

    validated_metadata = validate_strategy_metadata(metadata)
    validate_strategy_factory(factory)

    return normalized_key, validated_metadata

"""Validation utilities for strategy registry inputs."""

from __future__ import annotations

import inspect
import re
from collections.abc import Callable
from typing import Any

_SEMVER_PATTERN = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")
_REQUIRED_METADATA_FIELDS: dict[str, type] = {
    "pack_id": str,
    "version": str,
    "deterministic_hash": str,
    "dependencies": list,
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

    missing_fields = [field for field in _REQUIRED_METADATA_FIELDS if field not in metadata]
    if missing_fields:
        raise StrategyValidationError(
            f"metadata missing required fields: {', '.join(sorted(missing_fields))}"
        )

    for field, expected_type in _REQUIRED_METADATA_FIELDS.items():
        value = metadata[field]
        if not isinstance(value, expected_type):
            raise StrategyValidationError(
                f"metadata field '{field}' must be of type {expected_type.__name__}"
            )
        if expected_type is str and not value.strip():
            raise StrategyValidationError(f"metadata field '{field}' must not be empty")

    if not _SEMVER_PATTERN.fullmatch(metadata["version"]):
        raise StrategyValidationError("metadata field 'version' must be valid semver")

    dependencies = metadata["dependencies"]
    if any(not isinstance(dep, str) or not dep.strip() for dep in dependencies):
        raise StrategyValidationError("metadata field 'dependencies' must contain non-empty strings")

    if dependencies != sorted(dependencies):
        raise StrategyValidationError("metadata field 'dependencies' must be sorted")

    if len(set(dependencies)) != len(dependencies):
        raise StrategyValidationError("metadata field 'dependencies' must not contain duplicates")

    return metadata


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

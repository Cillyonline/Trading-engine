from __future__ import annotations

import re

import pytest

from cilly_trading.strategies.onboarding_contract import STRATEGY_ONBOARDING_CONTRACT
from cilly_trading.strategies.validation import StrategyValidationError, validate_strategy_metadata


def _valid_metadata() -> dict:
    return {
        "pack_id": "pack-alpha",
        "version": "1.2.3",
        "deterministic_hash": "abc123",
        "dependencies": [],
        "comparison_group": "mean-reversion",
        "documentation": {
            "architecture": "docs/architecture/strategy/onboarding_contract.md",
            "operations": "docs/operations/analyst-workflow.md",
        },
        "test_coverage": {
            "contract": "tests/strategies/test_strategy_onboarding_contract.py",
            "registry": "tests/strategies/test_strategy_registry.py",
            "negative": "tests/strategies/test_strategy_validation.py",
        },
    }


def test_onboarding_contract_defines_controlled_required_fields() -> None:
    assert STRATEGY_ONBOARDING_CONTRACT.required_metadata_fields == (
        "pack_id",
        "version",
        "deterministic_hash",
        "dependencies",
        "comparison_group",
        "documentation",
        "test_coverage",
    )
    assert STRATEGY_ONBOARDING_CONTRACT.required_documentation_fields == (
        "architecture",
        "operations",
    )
    assert STRATEGY_ONBOARDING_CONTRACT.required_test_coverage_fields == (
        "contract",
        "registry",
        "negative",
    )


def test_validate_strategy_metadata_accepts_complete_onboarding_contract() -> None:
    validated = validate_strategy_metadata(_valid_metadata())

    assert validated["comparison_group"] == "mean-reversion"
    assert validated["documentation"]["architecture"] == "docs/architecture/strategy/onboarding_contract.md"
    assert validated["test_coverage"]["negative"] == "tests/strategies/test_strategy_validation.py"


@pytest.mark.parametrize(
    ("field", "value", "error"),
    [
        (
            "documentation",
            {"architecture": "docs/architecture/strategy/onboarding_contract.md"},
            "metadata field 'documentation' missing required fields: operations",
        ),
        (
            "test_coverage",
            {
                "contract": "tests/strategies/test_strategy_onboarding_contract.py",
                "registry": "tests/strategies/test_strategy_registry.py",
            },
            "metadata field 'test_coverage' missing required fields: negative",
        ),
        (
            "comparison_group",
            "MeanReversion",
            "metadata field 'comparison_group' must match ^[a-z0-9][a-z0-9_-]*$",
        ),
    ],
)
def test_validate_strategy_metadata_rejects_incomplete_contract_definitions(
    field: str,
    value: object,
    error: str,
) -> None:
    payload = _valid_metadata()
    payload[field] = value

    with pytest.raises(StrategyValidationError, match=re.escape(error)):
        validate_strategy_metadata(payload)

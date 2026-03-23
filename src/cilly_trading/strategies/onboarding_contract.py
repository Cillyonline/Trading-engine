"""Controlled onboarding contract for strategy registrations.

This module defines the reusable contract that every strategy registration must
follow. The contract is intentionally strict so that strategy expansion stays
bounded and comparable.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StrategyOnboardingContract:
    """Normative onboarding contract for strategy metadata."""

    required_metadata_fields: tuple[str, ...]
    required_documentation_fields: tuple[str, ...]
    required_test_coverage_fields: tuple[str, ...]


STRATEGY_ONBOARDING_CONTRACT = StrategyOnboardingContract(
    required_metadata_fields=(
        "pack_id",
        "version",
        "deterministic_hash",
        "dependencies",
        "comparison_group",
        "documentation",
        "test_coverage",
    ),
    required_documentation_fields=(
        "architecture",
        "operations",
    ),
    required_test_coverage_fields=(
        "contract",
        "registry",
        "negative",
    ),
)


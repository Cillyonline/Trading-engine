"""Deterministic central strategy registry.

This module is the only supported strategy loading mechanism. Strategies are
registered explicitly via :func:`register_strategy` and resolved via
:func:`create_strategy` / :func:`get_registered_strategies`.

Deterministic ordering rule:
    Registered strategies are returned sorted by stable strategy key.

Cross-strategy score comparability:
    Strategy scores are bounded to within-strategy evaluation for a single
    opportunity. Direct score comparison across strategies from different
    comparison groups is not supported. The ``comparison_group`` metadata field
    identifies which strategies share a comparison group; only strategies in
    the same comparison group may be meaningfully compared by score.

Out of scope by design:
    - dynamic plugin loading
    - reflection/module auto-discovery
    - external strategy packages
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from cilly_trading.engine.core import BaseStrategy
from cilly_trading.strategies.validation import validate_before_registration, validate_strategy_key


CROSS_STRATEGY_SCORE_NON_COMPARABILITY_NOTE = (
    "Strategy scores are bounded to within-strategy evaluation for a single opportunity. "
    "Direct score comparison across strategies from different comparison groups is not supported. "
    "The comparison_group metadata field identifies which strategies share a comparison group; "
    "only strategies within the same comparison group may be meaningfully compared by score."
)

DEFAULT_COMPARISON_GROUP = "default"
QUALIFICATION_THRESHOLD_PROFILE_DEFAULT_ID = "qualification-threshold.default.v1"

QUALIFICATION_THRESHOLD_PROFILES_BY_COMPARISON_GROUP: dict[str, dict[str, float | str]] = {
    "default": {
        "profile_id": QUALIFICATION_THRESHOLD_PROFILE_DEFAULT_ID,
        "high_aggregate": 80.0,
        "high_min_component": 70.0,
        "medium_aggregate": 60.0,
        "medium_min_component": 50.0,
    },
    "mean-reversion": {
        "profile_id": "qualification-threshold.mean-reversion.v1",
        "high_aggregate": 80.0,
        "high_min_component": 70.0,
        "medium_aggregate": 60.0,
        "medium_min_component": 50.0,
    },
    "reference-control": {
        "profile_id": "qualification-threshold.reference-control.v1",
        "high_aggregate": 79.0,
        "high_min_component": 69.0,
        "medium_aggregate": 59.0,
        "medium_min_component": 49.0,
    },
    "trend-following": {
        "profile_id": "qualification-threshold.trend-following.v1",
        "high_aggregate": 82.0,
        "high_min_component": 68.0,
        "medium_aggregate": 62.0,
        "medium_min_component": 52.0,
    },
}

QUALIFICATION_PROFILE_ROBUSTNESS_BASE_SLICES: tuple[dict[str, Any], ...] = (
    {
        "slice_id": "covered.current_evidence.v1",
        "slice_type": "covered",
        "deterministic_rank": 1,
        "description": (
            "Covered current-evidence slice resolves the qualification profile without adverse adjustments."
        ),
        "component_score_adjustments": {},
    },
    {
        "slice_id": "failure_envelope.evidence_decay.v1",
        "slice_type": "failure_envelope",
        "deterministic_rank": 2,
        "description": (
            "Failure-envelope slice degrades signal and backtest evidence by fixed bounded deltas."
        ),
        "component_score_adjustments": {
            "backtest_quality": -18.0,
            "signal_quality": -18.0,
        },
    },
    {
        "slice_id": "failure_envelope.execution_stress.v1",
        "slice_type": "failure_envelope",
        "deterministic_rank": 3,
        "description": (
            "Failure-envelope slice degrades risk and execution evidence by fixed bounded deltas."
        ),
        "component_score_adjustments": {
            "execution_readiness": -35.0,
            "risk_alignment": -40.0,
        },
    },
)

QUALIFICATION_PROFILE_ROBUSTNESS_REGIME_SLICE_BY_COMPARISON_GROUP: dict[str, dict[str, Any]] = {
    "default": {
        "slice_id": "regime_slice.default_headwind.v1",
        "slice_type": "regime_slice",
        "deterministic_rank": 4,
        "description": (
            "Default regime slice applies a bounded mixed headwind across signal, portfolio-fit, "
            "and execution evidence."
        ),
        "component_score_adjustments": {
            "execution_readiness": -8.0,
            "portfolio_fit": -10.0,
            "signal_quality": -12.0,
        },
    },
    "mean-reversion": {
        "slice_id": "regime_slice.mean_reversion_headwind.v1",
        "slice_type": "regime_slice",
        "deterministic_rank": 4,
        "description": (
            "Mean-reversion regime slice applies a bounded headwind to reversal signal, backtest, "
            "and portfolio-fit evidence."
        ),
        "component_score_adjustments": {
            "backtest_quality": -14.0,
            "portfolio_fit": -10.0,
            "signal_quality": -22.0,
        },
    },
    "reference-control": {
        "slice_id": "regime_slice.reference_control_headwind.v1",
        "slice_type": "regime_slice",
        "deterministic_rank": 4,
        "description": (
            "Reference-control regime slice applies a bounded stability check across signal, "
            "backtest, and execution evidence."
        ),
        "component_score_adjustments": {
            "backtest_quality": -10.0,
            "execution_readiness": -8.0,
            "signal_quality": -10.0,
        },
    },
    "trend-following": {
        "slice_id": "regime_slice.trend_following_headwind.v1",
        "slice_type": "regime_slice",
        "deterministic_rank": 4,
        "description": (
            "Trend-following regime slice applies a bounded chop/headwind adjustment to signal, "
            "backtest, and risk evidence."
        ),
        "component_score_adjustments": {
            "backtest_quality": -12.0,
            "risk_alignment": -8.0,
            "signal_quality": -18.0,
        },
    },
}


class StrategyNotRegisteredError(KeyError):
    """Raised when an unknown strategy key is requested."""


StrategyFactory = Callable[[], BaseStrategy]


@dataclass(frozen=True)
class RegisteredStrategy:
    """Registry entry for one strategy.

    Attributes:
        key: Stable strategy key (uppercase).
        factory: Zero-argument factory creating a strategy instance.
        metadata: Validated strategy onboarding metadata.
    """

    key: str
    factory: StrategyFactory
    metadata: dict[str, Any]


_REGISTRY: dict[str, RegisteredStrategy] = {}


def _normalize_comparison_group(comparison_group: str | None) -> str:
    return (
        comparison_group.strip()
        if isinstance(comparison_group, str) and comparison_group.strip()
        else DEFAULT_COMPARISON_GROUP
    )


def _normalize_key(strategy_key: str) -> str:
    return validate_strategy_key(strategy_key)


def register_strategy(
    strategy_key: str,
    factory: StrategyFactory,
    metadata: dict | None = None,
) -> None:
    """Register one strategy factory explicitly.

    Args:
        strategy_key: Stable strategy identifier.
        factory: Factory that returns a strategy instance.

    Raises:
        ValueError: If key/factory/metadata are invalid.
    """

    normalized_key, validated_metadata = validate_before_registration(
        strategy_key,
        factory,
        metadata,
        registry_keys=set(_REGISTRY.keys()),
    )

    _REGISTRY[normalized_key] = RegisteredStrategy(
        key=normalized_key,
        factory=factory,
        metadata=validated_metadata,
    )


def get_registered_strategies() -> list[RegisteredStrategy]:
    """Return registered strategies in deterministic order.

    Determinism is guaranteed by sorting by strategy key before returning.

    Returns:
        List of registered strategies sorted by key.
    """

    return [_REGISTRY[key] for key in sorted(_REGISTRY.keys())]


def create_strategy(strategy_key: str) -> BaseStrategy:
    """Create a strategy instance for a registered key."""

    initialize_default_registry()
    normalized_key = _normalize_key(strategy_key)
    entry = _REGISTRY.get(normalized_key)
    if entry is None:
        raise StrategyNotRegisteredError(f"strategy not registered: {normalized_key}")
    return entry.factory()


def create_registered_strategies() -> list[BaseStrategy]:
    """Create all registered strategies in deterministic order."""

    initialize_default_registry()
    return [entry.factory() for entry in get_registered_strategies()]


def get_registered_strategy_metadata() -> dict[str, dict[str, Any]]:
    """Return deterministic registry metadata keyed by strategy key."""

    initialize_default_registry()
    return {entry.key: entry.metadata for entry in get_registered_strategies()}


def reset_registry() -> None:
    """Reset registry state.

    Intended for unit tests only.
    """

    _REGISTRY.clear()


def initialize_default_registry() -> None:
    """Initialize built-in strategy registrations exactly once."""

    if _REGISTRY:
        return

    from cilly_trading.strategies.reference import ReferenceStrategy
    from cilly_trading.strategies.rsi2 import Rsi2Strategy
    from cilly_trading.strategies.turtle import TurtleStrategy

    register_strategy(
        "REFERENCE",
        lambda: ReferenceStrategy(),
        metadata={
            "pack_id": "reference-pack",
            "version": "1.0.0",
            "deterministic_hash": "reference-pack-v1-hash",
            "dependencies": [],
            "comparison_group": "reference-control",
            "documentation": {
                "architecture": "docs/architecture/strategy/onboarding_contract.md",
                "operations": "docs/operations/analyst-workflow.md",
            },
            "test_coverage": {
                "contract": "tests/strategies/test_strategy_onboarding_contract.py",
                "registry": "tests/strategies/test_strategy_registry.py",
                "negative": "tests/strategies/test_strategy_validation.py",
            },
        },
    )
    register_strategy(
        "RSI2",
        lambda: Rsi2Strategy(),
        metadata={
            "pack_id": "core-default",
            "version": "1.0.0",
            "deterministic_hash": "rsi2-default-pack-hash",
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
        },
    )
    register_strategy(
        "TURTLE",
        lambda: TurtleStrategy(),
        metadata={
            "pack_id": "core-default",
            "version": "1.0.0",
            "deterministic_hash": "turtle-default-pack-hash",
            "dependencies": [],
            "comparison_group": "trend-following",
            "documentation": {
                "architecture": "docs/architecture/strategy/onboarding_contract.md",
                "operations": "docs/operations/analyst-workflow.md",
            },
            "test_coverage": {
                "contract": "tests/strategies/test_strategy_onboarding_contract.py",
                "registry": "tests/strategies/test_strategy_registry.py",
                "negative": "tests/strategies/test_strategy_validation.py",
            },
        },
    )


def run_registry_smoke() -> list[str]:
    """Return deterministic registered strategy keys for smoke tests."""

    initialize_default_registry()
    return [entry.key for entry in get_registered_strategies()]


def resolve_qualification_threshold_profile(
    *, comparison_group: str | None
) -> dict[str, float | str]:
    """Resolve deterministic threshold profile for a comparison group."""

    normalized_group = _normalize_comparison_group(comparison_group)
    profile = QUALIFICATION_THRESHOLD_PROFILES_BY_COMPARISON_GROUP.get(normalized_group)
    if profile is None:
        profile = QUALIFICATION_THRESHOLD_PROFILES_BY_COMPARISON_GROUP[DEFAULT_COMPARISON_GROUP]
    return dict(profile)


def resolve_qualification_profile_robustness_slices(
    *, comparison_group: str | None
) -> list[dict[str, Any]]:
    """Resolve deterministic bounded robustness slices for a comparison group."""

    normalized_group = _normalize_comparison_group(comparison_group)
    regime_slice = QUALIFICATION_PROFILE_ROBUSTNESS_REGIME_SLICE_BY_COMPARISON_GROUP.get(
        normalized_group
    )
    if regime_slice is None:
        regime_slice = QUALIFICATION_PROFILE_ROBUSTNESS_REGIME_SLICE_BY_COMPARISON_GROUP[
            DEFAULT_COMPARISON_GROUP
        ]

    resolved_slices: list[dict[str, Any]] = []
    for slice_definition in (*QUALIFICATION_PROFILE_ROBUSTNESS_BASE_SLICES, regime_slice):
        adjustments = {
            str(category): float(delta)
            for category, delta in dict(
                slice_definition.get("component_score_adjustments", {})
            ).items()
        }
        resolved_slices.append(
            {
                "slice_id": str(slice_definition["slice_id"]),
                "slice_type": str(slice_definition["slice_type"]),
                "deterministic_rank": int(slice_definition["deterministic_rank"]),
                "description": str(slice_definition["description"]),
                "component_score_adjustments": dict(sorted(adjustments.items())),
            }
        )
    return sorted(
        resolved_slices,
        key=lambda item: (int(item["deterministic_rank"]), str(item["slice_id"])),
    )

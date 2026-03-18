"""Pure and deterministic exposure calculations.

This module contains only deterministic arithmetic for exposure metrics.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ExposureMetrics:
    """Computed exposure metrics for a risk request.

    Attributes:
        account_exposure: Absolute account exposure after proposal.
        account_exposure_pct: Account exposure as percentage of account equity.
        proposed_allocation_pct: Proposed position as percentage of account equity.
    """

    account_exposure: float
    account_exposure_pct: float
    proposed_allocation_pct: float


def compute_exposure_metrics(
    *,
    account_equity: float,
    current_exposure: float,
    proposed_position_size: float,
) -> ExposureMetrics:
    """Compute deterministic exposure metrics.

    Args:
        account_equity: Current account equity.
        current_exposure: Current account exposure before proposal.
        proposed_position_size: Requested position size.

    Returns:
        ExposureMetrics: Derived deterministic metrics.
    """

    absolute_equity = abs(account_equity)
    absolute_current_exposure = abs(current_exposure)
    absolute_proposed_size = abs(proposed_position_size)

    account_exposure = absolute_current_exposure + absolute_proposed_size
    if absolute_equity == 0.0:
        account_exposure_pct = float("inf")
        proposed_allocation_pct = float("inf")
    else:
        account_exposure_pct = account_exposure / absolute_equity
        proposed_allocation_pct = absolute_proposed_size / absolute_equity

    return ExposureMetrics(
        account_exposure=account_exposure,
        account_exposure_pct=account_exposure_pct,
        proposed_allocation_pct=proposed_allocation_pct,
    )

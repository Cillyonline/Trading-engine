"""Deterministic and pure risk evaluation implementation."""

from __future__ import annotations

from engine.risk_framework.allocation_rules import RiskLimits
from engine.risk_framework.contract import RiskEvaluationRequest, RiskEvaluationResponse
from engine.risk_framework.exposure_model import compute_exposure_metrics
from engine.risk_framework.kill_switch import is_kill_switch_enabled


def _safe_pct(numerator: float, denominator: float) -> float:
    """Return a deterministic percentage value."""
    if denominator == 0.0:
        return float("inf")
    return numerator / denominator


def evaluate_risk(
    request: RiskEvaluationRequest,
    *,
    limits: RiskLimits,
    strategy_exposure: float,
    symbol_exposure: float,
    config: dict[str, object] | None = None,
) -> RiskEvaluationResponse:
    """Evaluate a risk request deterministically.

    Args:
        request: Risk evaluation request contract.
        limits: Immutable risk limits used for this evaluation.
        strategy_exposure: Current absolute exposure for the request strategy.
        symbol_exposure: Current absolute exposure for the request symbol.

    Returns:
        RiskEvaluationResponse: Deterministic evaluation result.
    """

    if is_kill_switch_enabled(config=config):
        return RiskEvaluationResponse(
            approved=False,
            reason="rejected: kill_switch_enabled",
            adjusted_position_size=0.0,
            risk_score=float("inf"),
        )

    absolute_equity = abs(request.account_equity)
    absolute_proposed_size = abs(request.proposed_position_size)
    absolute_strategy_exposure = abs(strategy_exposure)
    absolute_symbol_exposure = abs(symbol_exposure)

    metrics = compute_exposure_metrics(
        account_equity=request.account_equity,
        current_exposure=request.current_exposure,
        proposed_position_size=request.proposed_position_size,
    )
    risk_score = metrics.account_exposure_pct

    if absolute_proposed_size > limits.max_position_size:
        return RiskEvaluationResponse(
            approved=False,
            reason="rejected: max_position_size_exceeded",
            adjusted_position_size=limits.max_position_size,
            risk_score=risk_score,
        )

    if metrics.account_exposure_pct > limits.max_account_exposure_pct:
        max_allowed_account = absolute_equity * limits.max_account_exposure_pct
        adjusted_position_size = max(0.0, max_allowed_account - abs(request.current_exposure))
        return RiskEvaluationResponse(
            approved=False,
            reason="rejected: max_account_exposure_pct_exceeded",
            adjusted_position_size=adjusted_position_size,
            risk_score=risk_score,
        )

    strategy_exposure_pct = _safe_pct(
        absolute_strategy_exposure + absolute_proposed_size,
        absolute_equity,
    )
    if strategy_exposure_pct > limits.max_strategy_exposure_pct:
        max_allowed_strategy = absolute_equity * limits.max_strategy_exposure_pct
        adjusted_position_size = max(0.0, max_allowed_strategy - absolute_strategy_exposure)
        return RiskEvaluationResponse(
            approved=False,
            reason="rejected: max_strategy_exposure_pct_exceeded",
            adjusted_position_size=adjusted_position_size,
            risk_score=risk_score,
        )

    symbol_exposure_pct = _safe_pct(
        absolute_symbol_exposure + absolute_proposed_size,
        absolute_equity,
    )
    if symbol_exposure_pct > limits.max_symbol_exposure_pct:
        max_allowed_symbol = absolute_equity * limits.max_symbol_exposure_pct
        adjusted_position_size = max(0.0, max_allowed_symbol - absolute_symbol_exposure)
        return RiskEvaluationResponse(
            approved=False,
            reason="rejected: max_symbol_exposure_pct_exceeded",
            adjusted_position_size=adjusted_position_size,
            risk_score=risk_score,
        )

    return RiskEvaluationResponse(
        approved=True,
        reason="approved: within_risk_limits",
        adjusted_position_size=absolute_proposed_size,
        risk_score=risk_score,
    )

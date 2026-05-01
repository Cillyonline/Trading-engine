"""Deterministic and pure risk evaluation implementation."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite

from cilly_trading.non_live_evaluation_contract import NonLiveEvaluationEvidence
from cilly_trading.risk_framework.allocation_rules import RiskLimits
from cilly_trading.risk_framework.contract import RiskEvaluationRequest, RiskEvaluationResponse
from cilly_trading.risk_framework.exposure_model import compute_exposure_metrics
from cilly_trading.risk_framework.kill_switch import is_kill_switch_enabled


def _safe_pct(numerator: float, denominator: float) -> float | None:
    """Return percentage ratio, or None when denominator is zero."""
    if denominator == 0.0:
        return None
    return numerator / denominator


@dataclass(frozen=True)
class _RuleEvidence:
    evidence: NonLiveEvaluationEvidence
    violated: bool


def _bounded_risk_required(request: RiskEvaluationRequest, limits: RiskLimits) -> bool:
    return request.require_bounded_risk_evidence or any(
        limit is not None
        for limit in (
            limits.max_trade_risk_pct,
            limits.max_strategy_risk_pct,
            limits.max_symbol_risk_pct,
            limits.max_portfolio_risk_pct,
        )
    )


def _risk_limit_notional(account_equity: float, limit_pct: float | None) -> float:
    if limit_pct is None:
        return float("inf")
    return abs(account_equity) * limit_pct


def _evidence(
    *,
    decision: str,
    scope: str,
    rule_code: str,
    reason_code: str,
    observed_value: float,
    limit_value: float,
) -> NonLiveEvaluationEvidence:
    return NonLiveEvaluationEvidence(
        decision=decision,  # type: ignore[arg-type]
        semantic="cap",
        scope=scope,  # type: ignore[arg-type]
        rule_code=rule_code,
        reason_code=reason_code,
        observed_value=observed_value,
        limit_value=limit_value,
    )


def _fail_closed_response(
    *,
    reason: str,
    risk_score: float,
    policy_evidence: tuple[NonLiveEvaluationEvidence, ...],
) -> RiskEvaluationResponse:
    return RiskEvaluationResponse(
        approved=False,
        reason=reason,
        adjusted_position_size=0.0,
        risk_score=risk_score,
        policy_evidence=policy_evidence,
    )


def _invalid_stop_loss_evidence_response() -> tuple[
    tuple[NonLiveEvaluationEvidence, ...], str, float
]:
    return (
        (
            _evidence(
                decision="reject",
                scope="trade",
                rule_code="stop_loss_evidence_valid",
                reason_code="rejected: stop_loss_evidence_invalid",
                observed_value=0.0,
                limit_value=0.0,
            ),
        ),
        "rejected: stop_loss_evidence_invalid",
        float("inf"),
    )


def _bounded_risk_inputs_are_finite(
    request: RiskEvaluationRequest,
    *,
    limits: RiskLimits,
) -> bool:
    values = (
        request.entry_price,
        request.stop_loss_price,
        request.proposed_position_size,
        request.account_equity,
        request.strategy_risk_used,
        request.symbol_risk_used,
        request.portfolio_risk_used,
        limits.max_trade_risk_pct,
        limits.max_strategy_risk_pct,
        limits.max_symbol_risk_pct,
        limits.max_portfolio_risk_pct,
    )
    return all(value is None or isfinite(value) for value in values)


def _evaluate_bounded_risk_evidence(
    request: RiskEvaluationRequest,
    *,
    limits: RiskLimits,
) -> tuple[tuple[NonLiveEvaluationEvidence, ...], str | None, float]:
    if not _bounded_risk_required(request, limits):
        return (), None, 0.0

    if request.entry_price is None or request.stop_loss_price is None:
        return (
            (
                _evidence(
                    decision="reject",
                    scope="trade",
                    rule_code="stop_loss_evidence_required",
                    reason_code="rejected: stop_loss_evidence_missing",
                    observed_value=0.0,
                    limit_value=1.0,
                ),
            ),
            "rejected: stop_loss_evidence_missing",
            float("inf"),
        )

    if not _bounded_risk_inputs_are_finite(request, limits=limits):
        return _invalid_stop_loss_evidence_response()

    entry_price = abs(request.entry_price)
    stop_loss_price = abs(request.stop_loss_price)
    stop_loss_distance = abs(entry_price - stop_loss_price)
    if entry_price == 0.0 or stop_loss_price == 0.0 or stop_loss_distance == 0.0:
        return _invalid_stop_loss_evidence_response()

    absolute_proposed_size = abs(request.proposed_position_size)
    stop_loss_risk_pct = stop_loss_distance / entry_price
    trade_risk_notional = absolute_proposed_size * stop_loss_risk_pct
    trade_risk_budget = _risk_limit_notional(
        request.account_equity,
        limits.max_trade_risk_pct,
    )
    max_stop_loss_position_size = (
        float("inf")
        if limits.max_trade_risk_pct is None
        else trade_risk_budget / stop_loss_risk_pct
    )

    rules = (
        _RuleEvidence(
            evidence=_evidence(
                decision=(
                    "reject"
                    if absolute_proposed_size > max_stop_loss_position_size
                    else "approve"
                ),
                scope="trade",
                rule_code="stop_loss_position_size",
                reason_code=(
                    "rejected: position_size_exceeds_stop_loss_budget"
                    if absolute_proposed_size > max_stop_loss_position_size
                    else "approved: within_risk_limits"
                ),
                observed_value=absolute_proposed_size,
                limit_value=max_stop_loss_position_size,
            ),
            violated=absolute_proposed_size > max_stop_loss_position_size,
        ),
        _RuleEvidence(
            evidence=_evidence(
                decision="reject" if trade_risk_notional > trade_risk_budget else "approve",
                scope="trade",
                rule_code="max_trade_risk",
                reason_code=(
                    "rejected: max_trade_risk_exceeded"
                    if trade_risk_notional > trade_risk_budget
                    else "approved: within_risk_limits"
                ),
                observed_value=trade_risk_notional,
                limit_value=trade_risk_budget,
            ),
            violated=trade_risk_notional > trade_risk_budget,
        ),
        _RuleEvidence(
            evidence=_evidence(
                decision=(
                    "reject"
                    if abs(request.strategy_risk_used) + trade_risk_notional
                    > _risk_limit_notional(request.account_equity, limits.max_strategy_risk_pct)
                    else "approve"
                ),
                scope="strategy",
                rule_code="strategy_risk_budget",
                reason_code=(
                    "rejected: strategy_risk_budget_exceeded"
                    if abs(request.strategy_risk_used) + trade_risk_notional
                    > _risk_limit_notional(request.account_equity, limits.max_strategy_risk_pct)
                    else "approved: within_risk_limits"
                ),
                observed_value=abs(request.strategy_risk_used) + trade_risk_notional,
                limit_value=_risk_limit_notional(
                    request.account_equity,
                    limits.max_strategy_risk_pct,
                ),
            ),
            violated=abs(request.strategy_risk_used) + trade_risk_notional
            > _risk_limit_notional(request.account_equity, limits.max_strategy_risk_pct),
        ),
        _RuleEvidence(
            evidence=_evidence(
                decision=(
                    "reject"
                    if abs(request.symbol_risk_used) + trade_risk_notional
                    > _risk_limit_notional(request.account_equity, limits.max_symbol_risk_pct)
                    else "approve"
                ),
                scope="symbol",
                rule_code="symbol_risk_budget",
                reason_code=(
                    "rejected: symbol_risk_budget_exceeded"
                    if abs(request.symbol_risk_used) + trade_risk_notional
                    > _risk_limit_notional(request.account_equity, limits.max_symbol_risk_pct)
                    else "approved: within_risk_limits"
                ),
                observed_value=abs(request.symbol_risk_used) + trade_risk_notional,
                limit_value=_risk_limit_notional(
                    request.account_equity,
                    limits.max_symbol_risk_pct,
                ),
            ),
            violated=abs(request.symbol_risk_used) + trade_risk_notional
            > _risk_limit_notional(request.account_equity, limits.max_symbol_risk_pct),
        ),
        _RuleEvidence(
            evidence=_evidence(
                decision=(
                    "reject"
                    if abs(request.portfolio_risk_used) + trade_risk_notional
                    > _risk_limit_notional(request.account_equity, limits.max_portfolio_risk_pct)
                    else "approve"
                ),
                scope="portfolio",
                rule_code="portfolio_risk_budget",
                reason_code=(
                    "rejected: portfolio_risk_budget_exceeded"
                    if abs(request.portfolio_risk_used) + trade_risk_notional
                    > _risk_limit_notional(request.account_equity, limits.max_portfolio_risk_pct)
                    else "approved: within_risk_limits"
                ),
                observed_value=abs(request.portfolio_risk_used) + trade_risk_notional,
                limit_value=_risk_limit_notional(
                    request.account_equity,
                    limits.max_portfolio_risk_pct,
                ),
            ),
            violated=abs(request.portfolio_risk_used) + trade_risk_notional
            > _risk_limit_notional(request.account_equity, limits.max_portfolio_risk_pct),
        ),
    )

    for rule in rules:
        if rule.violated:
            return tuple(item.evidence for item in rules), rule.evidence.reason_code, trade_risk_notional
    return tuple(item.evidence for item in rules), None, trade_risk_notional


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
            policy_evidence=(
                NonLiveEvaluationEvidence(
                    decision="reject",
                    semantic="boundary",
                    scope="runtime",
                    rule_code="kill_switch_enabled",
                    reason_code="rejected: kill_switch_enabled",
                    observed_value=1.0,
                    limit_value=0.0,
                ),
            ),
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
    policy_evidence, bounded_rejection_reason, bounded_risk_score = (
        _evaluate_bounded_risk_evidence(request, limits=limits)
    )
    if bounded_rejection_reason is not None:
        return _fail_closed_response(
            reason=bounded_rejection_reason,
            risk_score=bounded_risk_score,
            policy_evidence=policy_evidence,
        )

    if absolute_proposed_size > limits.max_position_size:
        return RiskEvaluationResponse(
            approved=False,
            reason="rejected: max_position_size_exceeded",
            adjusted_position_size=limits.max_position_size,
            risk_score=risk_score,
            policy_evidence=policy_evidence,
        )

    if metrics.account_exposure_pct > limits.max_account_exposure_pct:
        max_allowed_account = absolute_equity * limits.max_account_exposure_pct
        adjusted_position_size = max(0.0, max_allowed_account - abs(request.current_exposure))
        return RiskEvaluationResponse(
            approved=False,
            reason="rejected: max_account_exposure_pct_exceeded",
            adjusted_position_size=adjusted_position_size,
            risk_score=risk_score,
            policy_evidence=policy_evidence,
        )

    strategy_exposure_pct = _safe_pct(
        absolute_strategy_exposure + absolute_proposed_size,
        absolute_equity,
    )
    if strategy_exposure_pct is None or strategy_exposure_pct > limits.max_strategy_exposure_pct:
        max_allowed_strategy = absolute_equity * limits.max_strategy_exposure_pct
        adjusted_position_size = max(0.0, max_allowed_strategy - absolute_strategy_exposure)
        return RiskEvaluationResponse(
            approved=False,
            reason="rejected: max_strategy_exposure_pct_exceeded",
            adjusted_position_size=adjusted_position_size,
            risk_score=risk_score,
            policy_evidence=policy_evidence,
        )

    symbol_exposure_pct = _safe_pct(
        absolute_symbol_exposure + absolute_proposed_size,
        absolute_equity,
    )
    if symbol_exposure_pct is None or symbol_exposure_pct > limits.max_symbol_exposure_pct:
        max_allowed_symbol = absolute_equity * limits.max_symbol_exposure_pct
        adjusted_position_size = max(0.0, max_allowed_symbol - absolute_symbol_exposure)
        return RiskEvaluationResponse(
            approved=False,
            reason="rejected: max_symbol_exposure_pct_exceeded",
            adjusted_position_size=adjusted_position_size,
            risk_score=risk_score,
            policy_evidence=policy_evidence,
        )

    return RiskEvaluationResponse(
        approved=True,
        reason="approved: within_risk_limits",
        adjusted_position_size=absolute_proposed_size,
        risk_score=risk_score,
        policy_evidence=policy_evidence,
    )

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import pytest
from risk.contracts import RiskEvaluationRequest

from cilly_trading.engine.risk import (
    RISK_FRAMEWORK_REASON_CODES,
    RiskEvidenceDisciplineError,
    ThresholdRiskGate,
    adapt_risk_framework_response_to_risk_decision,
    evaluate_risk_framework_execution_decision,
)
from cilly_trading.non_live_evaluation_contract import (
    CANONICAL_RISK_REJECTION_REASON_CODES,
    NonLiveEvaluationEvidence,
    normalize_risk_rejection_reason_code,
    resolve_risk_rejection_reason_precedence,
)
from cilly_trading.risk_framework.allocation_rules import RiskLimits
from cilly_trading.risk_framework.contract import (
    RiskEvaluationRequest as FrameworkRiskEvaluationRequest,
    RiskEvaluationResponse as FrameworkRiskEvaluationResponse,
)


@dataclass(frozen=True)
class _LegacyRuntimeRiskResponse:
    approved: bool
    reason: str
    adjusted_position_size: float
    risk_score: float


@dataclass(frozen=True)
class _RuntimeRiskResponseWithEvidence:
    approved: bool
    reason: str
    adjusted_position_size: float
    risk_score: float
    policy_evidence: tuple[object, ...]


def _policy_evidence_or_empty(decision: object) -> tuple[object, ...]:
    evidence = getattr(decision, "policy_evidence", ())
    if evidence is None:
        return ()
    if isinstance(evidence, tuple):
        return evidence
    return tuple(evidence)


def _decision_has_policy_evidence(decision: object) -> bool:
    return hasattr(decision, "policy_evidence")


def test_threshold_risk_gate_returns_approved_for_within_threshold() -> None:
    gate = ThresholdRiskGate(max_notional_usd=1000.0)

    decision = gate.evaluate(
        RiskEvaluationRequest(
            request_id="req-1",
            strategy_id="strat-a",
            symbol="AAPL",
            notional_usd=750.0,
            metadata={},
        )
    )

    assert decision.decision == "APPROVED"


def test_threshold_risk_gate_returns_rejected_for_above_threshold() -> None:
    gate = ThresholdRiskGate(max_notional_usd=1000.0)

    decision = gate.evaluate(
        RiskEvaluationRequest(
            request_id="req-2",
            strategy_id="strat-a",
            symbol="AAPL",
            notional_usd=1500.0,
            metadata={},
        )
    )

    assert decision.decision == "REJECTED"


@pytest.mark.parametrize("max_notional", [0.0, -1.0, math.inf, math.nan])
def test_threshold_risk_gate_rejects_unbounded_threshold(max_notional: float) -> None:
    gate = ThresholdRiskGate(max_notional_usd=max_notional)

    with pytest.raises(ValueError, match="max_notional_usd"):
        gate.evaluate(
            RiskEvaluationRequest(
                request_id="req-bad-threshold",
                strategy_id="strat-a",
                symbol="AAPL",
                notional_usd=100.0,
                metadata={},
            )
        )


@pytest.mark.parametrize("notional", [-1.0, math.inf, math.nan])
def test_threshold_risk_gate_rejects_unbounded_notional(notional: float) -> None:
    gate = ThresholdRiskGate(max_notional_usd=1000.0)

    with pytest.raises(ValueError, match="notional_usd"):
        gate.evaluate(
            RiskEvaluationRequest(
                request_id="req-bad-notional",
                strategy_id="strat-a",
                symbol="AAPL",
                notional_usd=notional,
                metadata={},
            )
        )


def _framework_limits() -> RiskLimits:
    return RiskLimits(
        max_account_exposure_pct=0.80,
        max_position_size=500.0,
        max_strategy_exposure_pct=0.30,
        max_symbol_exposure_pct=0.20,
    )


def _framework_request() -> FrameworkRiskEvaluationRequest:
    return FrameworkRiskEvaluationRequest(
        strategy_id="strategy-a",
        symbol="AAPL",
        proposed_position_size=400.0,
        account_equity=2000.0,
        current_exposure=800.0,
    )


@pytest.mark.parametrize(
    ("framework_reason", "approved", "risk_score", "expected_decision", "expected_reason"),
    [
        (
            "approved: within_risk_limits",
            True,
            0.60,
            "APPROVED",
            "approved:risk_framework_within_limits",
        ),
        (
            "rejected: kill_switch_enabled",
            False,
            float("inf"),
            "REJECTED",
            "rejected:risk_framework_kill_switch_enabled",
        ),
        (
            "rejected: max_position_size_exceeded",
            False,
            0.60,
            "REJECTED",
            "rejected:risk_framework_max_position_size_exceeded",
        ),
        (
            "rejected: max_account_exposure_pct_exceeded",
            False,
            0.90,
            "REJECTED",
            "rejected:risk_framework_max_account_exposure_pct_exceeded",
        ),
        (
            "rejected: max_strategy_exposure_pct_exceeded",
            False,
            0.60,
            "REJECTED",
            "rejected:risk_framework_max_strategy_exposure_pct_exceeded",
        ),
        (
            "rejected: max_symbol_exposure_pct_exceeded",
            False,
            0.60,
            "REJECTED",
            "rejected:risk_framework_max_symbol_exposure_pct_exceeded",
        ),
    ],
)
def test_adapter_maps_risk_framework_reason_codes_deterministically(
    framework_reason: str,
    approved: bool,
    risk_score: float,
    expected_decision: str,
    expected_reason: str,
) -> None:
    decision = adapt_risk_framework_response_to_risk_decision(
        framework_request=_framework_request(),
        framework_response=FrameworkRiskEvaluationResponse(
            approved=approved,
            reason=framework_reason,
            adjusted_position_size=0.0,
            risk_score=risk_score,
        ),
        limits=_framework_limits(),
        strategy_exposure=200.0,
        symbol_exposure=100.0,
        rule_version="adapter-v1",
        evaluated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )

    assert decision.decision == expected_decision
    assert decision.reason == expected_reason
    assert decision.rule_version == "adapter-v1"
    assert decision.timestamp == datetime(2026, 1, 1, tzinfo=timezone.utc)
    if expected_decision == "APPROVED":
        assert _policy_evidence_or_empty(decision) == ()
    else:
        assert _policy_evidence_or_empty(decision)


def test_adapter_rejects_unknown_reason_code() -> None:
    with pytest.raises(ValueError, match="unsupported risk-framework reason"):
        adapt_risk_framework_response_to_risk_decision(
            framework_request=_framework_request(),
            framework_response=FrameworkRiskEvaluationResponse(
                approved=False,
                reason="rejected: unknown_rule",
                adjusted_position_size=0.0,
                risk_score=0.0,
            ),
            limits=_framework_limits(),
            strategy_exposure=0.0,
            symbol_exposure=0.0,
            rule_version="adapter-v1",
            evaluated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )


def test_adapter_handles_runtime_response_without_policy_evidence() -> None:
    decision = adapt_risk_framework_response_to_risk_decision(
        framework_request=_framework_request(),
        framework_response=_LegacyRuntimeRiskResponse(
            approved=False,
            reason="rejected: max_account_exposure_pct_exceeded",
            adjusted_position_size=0.0,
            risk_score=0.9,
        ),
        limits=_framework_limits(),
        strategy_exposure=0.0,
        symbol_exposure=0.0,
        rule_version="adapter-v1",
        evaluated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )

    assert decision.decision == "REJECTED"
    assert decision.reason == "rejected:risk_framework_max_account_exposure_pct_exceeded"
    if _decision_has_policy_evidence(decision):
        policy_evidence = _policy_evidence_or_empty(decision)
        assert len(policy_evidence) == 1
        assert policy_evidence[0].reason_code == "rejected: max_account_exposure_pct_exceeded"
        assert policy_evidence[0].scope == "portfolio"
    else:
        assert _policy_evidence_or_empty(decision) == ()


def test_adapter_rejects_contradictory_evidence_when_response_is_approved() -> None:
    with pytest.raises(
        RiskEvidenceDisciplineError,
        match="approved risk decision contains covered rejection evidence rows",
    ):
        adapt_risk_framework_response_to_risk_decision(
            framework_request=_framework_request(),
            framework_response=_RuntimeRiskResponseWithEvidence(
                approved=True,
                reason="approved: within_risk_limits",
                adjusted_position_size=400.0,
                risk_score=0.6,
                policy_evidence=(
                    NonLiveEvaluationEvidence(
                        decision="reject",
                        semantic="cap",
                        scope="trade",
                        rule_code="max_position_size",
                        reason_code="rejected: max_position_size_exceeded",
                        observed_value=600.0,
                        limit_value=500.0,
                    ),
                ),
            ),
            limits=_framework_limits(),
            strategy_exposure=200.0,
            symbol_exposure=100.0,
            rule_version="adapter-v1",
            evaluated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )


def test_adapter_rejects_contradictory_approve_evidence_when_response_is_rejected() -> None:
    with pytest.raises(
        RiskEvidenceDisciplineError,
        match="decision='approve'",
    ):
        adapt_risk_framework_response_to_risk_decision(
            framework_request=_framework_request(),
            framework_response=_RuntimeRiskResponseWithEvidence(
                approved=False,
                reason="rejected: max_position_size_exceeded",
                adjusted_position_size=500.0,
                risk_score=0.8,
                policy_evidence=(
                    {
                        "decision": "approve",
                        "scope": "trade",
                        "reason_code": "rejected: max_position_size_exceeded",
                    },
                ),
            ),
            limits=_framework_limits(),
            strategy_exposure=200.0,
            symbol_exposure=100.0,
            rule_version="adapter-v1",
            evaluated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )


def test_adapter_fails_closed_when_covered_evidence_reason_code_is_missing() -> None:
    with pytest.raises(
        RiskEvidenceDisciplineError,
        match="must include non-empty reason_code",
    ):
        adapt_risk_framework_response_to_risk_decision(
            framework_request=_framework_request(),
            framework_response=_RuntimeRiskResponseWithEvidence(
                approved=False,
                reason="rejected: max_position_size_exceeded",
                adjusted_position_size=500.0,
                risk_score=0.8,
                policy_evidence=(
                    {
                        "decision": "reject",
                        "scope": "trade",
                        "reason_code": "",
                    },
                ),
            ),
            limits=_framework_limits(),
            strategy_exposure=200.0,
            symbol_exposure=100.0,
            rule_version="adapter-v1",
            evaluated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )


def test_adapter_precedence_is_deterministic_for_multi_violation_evidence_rows() -> None:
    framework_response = _RuntimeRiskResponseWithEvidence(
        approved=False,
        reason="rejected: max_symbol_exposure_pct_exceeded",
        adjusted_position_size=200.0,
        risk_score=0.7,
        policy_evidence=(
            NonLiveEvaluationEvidence(
                decision="reject",
                semantic="cap",
                scope="portfolio",
                rule_code="max_account_exposure_pct",
                reason_code="rejected: max_account_exposure_pct_exceeded",
                observed_value=0.91,
                limit_value=0.80,
            ),
            NonLiveEvaluationEvidence(
                decision="reject",
                semantic="cap",
                scope="trade",
                rule_code="max_position_size",
                reason_code="rejected: max_position_size_exceeded",
                observed_value=900.0,
                limit_value=500.0,
            ),
        ),
    )

    first = adapt_risk_framework_response_to_risk_decision(
        framework_request=_framework_request(),
        framework_response=framework_response,
        limits=_framework_limits(),
        strategy_exposure=200.0,
        symbol_exposure=100.0,
        rule_version="adapter-v1",
        evaluated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    second = adapt_risk_framework_response_to_risk_decision(
        framework_request=_framework_request(),
        framework_response=framework_response,
        limits=_framework_limits(),
        strategy_exposure=200.0,
        symbol_exposure=100.0,
        rule_version="adapter-v1",
        evaluated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )

    assert first == second
    assert first.reason == "rejected:risk_framework_max_position_size_exceeded"


def test_canonical_rejection_reason_vocabulary_is_exposed_in_gate_map() -> None:
    mapped_rejections = tuple(
        code
        for framework_reason, code in RISK_FRAMEWORK_REASON_CODES.items()
        if framework_reason.startswith("rejected: ")
    )
    assert mapped_rejections == CANONICAL_RISK_REJECTION_REASON_CODES


def test_normalize_risk_rejection_reason_code_accepts_framework_and_canonical_values() -> None:
    assert (
        normalize_risk_rejection_reason_code("rejected: max_account_exposure_pct_exceeded")
        == "rejected:risk_framework_max_account_exposure_pct_exceeded"
    )
    assert (
        normalize_risk_rejection_reason_code(
            "rejected:risk_framework_max_account_exposure_pct_exceeded"
        )
        == "rejected:risk_framework_max_account_exposure_pct_exceeded"
    )


def test_resolve_risk_rejection_reason_precedence_is_deterministic() -> None:
    reason = resolve_risk_rejection_reason_precedence(
        [
            "rejected:risk_framework_max_symbol_exposure_pct_exceeded",
            "rejected: max_position_size_exceeded",
            "rejected:risk_framework_max_account_exposure_pct_exceeded",
        ]
    )
    assert reason == "rejected:risk_framework_max_position_size_exceeded"


def test_evaluate_risk_framework_execution_decision_is_deterministic_for_equal_inputs() -> None:
    first = evaluate_risk_framework_execution_decision(
        request_id="req-1",
        strategy_id="strategy-a",
        symbol="AAPL",
        proposed_position_size=400.0,
        account_equity=2000.0,
        current_exposure=800.0,
        strategy_exposure=200.0,
        symbol_exposure=0.0,
        limits=_framework_limits(),
        rule_version="adapter-v1",
        evaluated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    second = evaluate_risk_framework_execution_decision(
        request_id="req-1",
        strategy_id="strategy-a",
        symbol="AAPL",
        proposed_position_size=400.0,
        account_equity=2000.0,
        current_exposure=800.0,
        strategy_exposure=200.0,
        symbol_exposure=0.0,
        limits=_framework_limits(),
        rule_version="adapter-v1",
        evaluated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )

    assert first == second
    assert first.decision == "APPROVED"
    assert first.reason == "approved:risk_framework_within_limits"
    assert _policy_evidence_or_empty(first) == ()


def test_adapter_rejects_non_utc_timezone_aware_timestamp() -> None:
    with pytest.raises(ValueError, match="timezone-aware and in UTC"):
        adapt_risk_framework_response_to_risk_decision(
            framework_request=_framework_request(),
            framework_response=FrameworkRiskEvaluationResponse(
                approved=True,
                reason="approved: within_risk_limits",
                adjusted_position_size=400.0,
                risk_score=0.6,
            ),
            limits=_framework_limits(),
            strategy_exposure=200.0,
            symbol_exposure=100.0,
            rule_version="adapter-v1",
            evaluated_at=datetime(
                2026,
                1,
                1,
                tzinfo=timezone(timedelta(hours=1)),
            ),
        )


def test_evaluate_risk_framework_execution_decision_propagates_bounded_risk_evidence() -> None:
    decision = evaluate_risk_framework_execution_decision(
        request_id="req-bounded-approved",
        strategy_id="strategy-a",
        symbol="AAPL",
        proposed_position_size=400.0,
        account_equity=10_000.0,
        current_exposure=800.0,
        strategy_exposure=200.0,
        symbol_exposure=100.0,
        entry_price=100.0,
        stop_loss_price=95.0,
        strategy_risk_used=100.0,
        symbol_risk_used=50.0,
        portfolio_risk_used=200.0,
        require_bounded_risk_evidence=True,
        limits=RiskLimits(
            max_account_exposure_pct=0.80,
            max_position_size=500.0,
            max_strategy_exposure_pct=0.30,
            max_symbol_exposure_pct=0.20,
            max_trade_risk_pct=0.02,
            max_strategy_risk_pct=0.05,
            max_symbol_risk_pct=0.04,
            max_portfolio_risk_pct=0.10,
        ),
        rule_version="adapter-v1",
        evaluated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )

    policy_evidence = _policy_evidence_or_empty(decision)
    assert decision.decision == "APPROVED"
    assert decision.reason == "approved:risk_framework_within_limits"
    assert [row.rule_code for row in policy_evidence] == [
        "stop_loss_position_size",
        "max_trade_risk",
        "strategy_risk_budget",
        "symbol_risk_budget",
        "portfolio_risk_budget",
    ]
    assert {row.scope for row in policy_evidence} == {
        "trade",
        "strategy",
        "symbol",
        "portfolio",
    }


def test_evaluate_risk_framework_execution_decision_fails_closed_for_missing_bounded_evidence() -> None:
    decision = evaluate_risk_framework_execution_decision(
        request_id="req-bounded-missing",
        strategy_id="strategy-a",
        symbol="AAPL",
        proposed_position_size=400.0,
        account_equity=10_000.0,
        current_exposure=800.0,
        strategy_exposure=200.0,
        symbol_exposure=100.0,
        require_bounded_risk_evidence=True,
        limits=RiskLimits(
            max_account_exposure_pct=0.80,
            max_position_size=500.0,
            max_strategy_exposure_pct=0.30,
            max_symbol_exposure_pct=0.20,
            max_trade_risk_pct=0.02,
            max_strategy_risk_pct=0.05,
            max_symbol_risk_pct=0.04,
            max_portfolio_risk_pct=0.10,
        ),
        rule_version="adapter-v1",
        evaluated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )

    assert decision.decision == "REJECTED"
    assert decision.reason == "rejected:risk_framework_stop_loss_evidence_missing"
    assert _policy_evidence_or_empty(decision)[0].reason_code == (
        "rejected: stop_loss_evidence_missing"
    )


def test_evaluate_risk_framework_execution_decision_prefers_kill_switch_for_multi_violation() -> None:
    decision = evaluate_risk_framework_execution_decision(
        request_id="req-multi-kill-switch",
        strategy_id="strategy-a",
        symbol="AAPL",
        proposed_position_size=1000.0,
        account_equity=1000.0,
        current_exposure=900.0,
        strategy_exposure=900.0,
        symbol_exposure=900.0,
        limits=_framework_limits(),
        rule_version="adapter-v1",
        config={"risk.kill_switch.enabled": True},
        evaluated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )

    assert decision.decision == "REJECTED"
    assert decision.reason == "rejected:risk_framework_kill_switch_enabled"
    if _decision_has_policy_evidence(decision):
        policy_evidence = _policy_evidence_or_empty(decision)
        assert policy_evidence
        assert policy_evidence[0].reason_code == "rejected: kill_switch_enabled"


def test_evaluate_risk_framework_execution_decision_prefers_position_size_over_other_caps() -> None:
    decision = evaluate_risk_framework_execution_decision(
        request_id="req-multi-cap",
        strategy_id="strategy-a",
        symbol="AAPL",
        proposed_position_size=1000.0,
        account_equity=1000.0,
        current_exposure=900.0,
        strategy_exposure=900.0,
        symbol_exposure=900.0,
        limits=_framework_limits(),
        rule_version="adapter-v1",
        evaluated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )

    assert decision.decision == "REJECTED"
    assert decision.reason == "rejected:risk_framework_max_position_size_exceeded"
    if _decision_has_policy_evidence(decision):
        policy_evidence = _policy_evidence_or_empty(decision)
        assert policy_evidence
        assert policy_evidence[0].reason_code == "rejected: max_position_size_exceeded"

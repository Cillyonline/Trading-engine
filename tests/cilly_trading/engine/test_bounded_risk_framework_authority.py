"""Bounded risk-framework authority contract tests.

These tests assert the bounded non-live risk-framework authority contract
documented at
``docs/architecture/risk/bounded_risk_framework_authority_contract.md``:

* deterministic regression: identical covered inputs produce identical
  risk-boundary evaluation outputs
* fail-closed evidence discipline: missing or contradictory bounded
  risk evidence never silently degrades to APPROVED execution

This is bounded non-live technical evidence only and is not live-trading,
broker, trader-validation, or operational-readiness evidence.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

import pytest
from risk.contracts import RiskDecision, RiskEvaluationRequest

from cilly_trading.engine.risk import (
    APPROVED_RISK_FRAMEWORK_REASON_CODE,
    BOUNDED_RISK_FRAMEWORK_AUTHORITY_CONTRACT_DOC,
    BOUNDED_RISK_FRAMEWORK_AUTHORITY_ID,
    RISK_FRAMEWORK_REASON_CODES,
    RiskApprovalMissingError,
    RiskRejectedError,
    ThresholdRiskGate,
    adapt_risk_framework_response_to_risk_decision,
    enforce_approved_risk_decision,
    evaluate_risk_framework_execution_decision,
)
from cilly_trading.engine.risk.authority import (
    CANONICAL_RISK_REJECTION_REASON_CODES,
    GUARD_TRIGGER_TYPES,
    RISK_REJECTION_REASON_PRECEDENCE,
)
from cilly_trading.risk_framework.allocation_rules import RiskLimits
from cilly_trading.risk_framework.contract import (
    RiskEvaluationRequest as FrameworkRiskEvaluationRequest,
    RiskEvaluationResponse as FrameworkRiskEvaluationResponse,
)


@dataclass(frozen=True)
class _DummyRequest:
    request_id: str = "req-fc"
    strategy_id: str = "strat-a"
    symbol: str = "AAPL"
    notional_usd: float = 100.0
    metadata: dict = None  # type: ignore[assignment]

    def __post_init__(self) -> None:  # pragma: no cover - trivial
        if self.metadata is None:
            object.__setattr__(self, "metadata", {})


def _limits() -> RiskLimits:
    return RiskLimits(
        max_account_exposure_pct=0.80,
        max_position_size=500.0,
        max_strategy_exposure_pct=0.30,
        max_symbol_exposure_pct=0.20,
    )


# ---------------------------------------------------------------------------
# Canonical authority surface
# ---------------------------------------------------------------------------


def test_bounded_authority_id_is_stable_canonical_handle() -> None:
    assert BOUNDED_RISK_FRAMEWORK_AUTHORITY_ID == "risk_framework_bounded_non_live_v1"


def test_bounded_authority_doc_constant_points_at_canonical_doc() -> None:
    assert BOUNDED_RISK_FRAMEWORK_AUTHORITY_CONTRACT_DOC == (
        "docs/architecture/risk/bounded_risk_framework_authority_contract.md"
    )


def test_bounded_authority_reason_vocabulary_matches_canonical_constants() -> None:
    mapped_rejections = tuple(
        code
        for framework_reason, code in RISK_FRAMEWORK_REASON_CODES.items()
        if framework_reason.startswith("rejected: ")
    )
    assert mapped_rejections == CANONICAL_RISK_REJECTION_REASON_CODES
    assert (
        RISK_FRAMEWORK_REASON_CODES["approved: within_risk_limits"]
        == APPROVED_RISK_FRAMEWORK_REASON_CODE
    )
    assert set(RISK_REJECTION_REASON_PRECEDENCE) == set(CANONICAL_RISK_REJECTION_REASON_CODES)
    assert GUARD_TRIGGER_TYPES == frozenset(
        {"kill_switch", "drawdown", "daily_loss", "emergency"}
    )


# ---------------------------------------------------------------------------
# Deterministic regression: identical covered inputs -> identical outputs
# ---------------------------------------------------------------------------


_REGRESSION_TIMESTAMP = datetime(2026, 1, 1, tzinfo=timezone.utc)


@pytest.mark.parametrize(
    ("scenario_id", "kwargs"),
    [
        (
            "approved_within_limits",
            dict(
                request_id="req-app",
                strategy_id="strategy-a",
                symbol="AAPL",
                proposed_position_size=100.0,
                account_equity=10_000.0,
                current_exposure=0.0,
                strategy_exposure=0.0,
                symbol_exposure=0.0,
            ),
        ),
        (
            "rejected_position_size",
            dict(
                request_id="req-pos",
                strategy_id="strategy-a",
                symbol="AAPL",
                proposed_position_size=10_000.0,
                account_equity=20_000.0,
                current_exposure=0.0,
                strategy_exposure=0.0,
                symbol_exposure=0.0,
            ),
        ),
        (
            "rejected_account_exposure",
            dict(
                request_id="req-acct",
                strategy_id="strategy-a",
                symbol="AAPL",
                proposed_position_size=400.0,
                account_equity=1_000.0,
                current_exposure=900.0,
                strategy_exposure=0.0,
                symbol_exposure=0.0,
            ),
        ),
        (
            "rejected_strategy_exposure",
            dict(
                request_id="req-strat",
                strategy_id="strategy-a",
                symbol="AAPL",
                proposed_position_size=100.0,
                account_equity=10_000.0,
                current_exposure=0.0,
                strategy_exposure=4_000.0,
                symbol_exposure=0.0,
            ),
        ),
        (
            "rejected_symbol_exposure",
            dict(
                request_id="req-sym",
                strategy_id="strategy-a",
                symbol="AAPL",
                proposed_position_size=100.0,
                account_equity=10_000.0,
                current_exposure=0.0,
                strategy_exposure=0.0,
                symbol_exposure=2_500.0,
            ),
        ),
    ],
)
def test_evaluate_risk_framework_execution_decision_is_stable_for_identical_inputs(
    scenario_id: str, kwargs: dict
) -> None:
    """Deterministic regression: equal covered inputs -> equal RiskDecision."""

    decisions = [
        evaluate_risk_framework_execution_decision(
            limits=_limits(),
            rule_version="bounded-authority-v1",
            evaluated_at=_REGRESSION_TIMESTAMP,
            **kwargs,
        )
        for _ in range(3)
    ]

    assert decisions[0] == decisions[1] == decisions[2], scenario_id
    assert decisions[0].timestamp == _REGRESSION_TIMESTAMP


def test_threshold_risk_gate_is_stable_for_identical_inputs() -> None:
    gate = ThresholdRiskGate(max_notional_usd=1_000.0, rule_version="bounded-authority-v1")

    request = RiskEvaluationRequest(
        request_id="req-th",
        strategy_id="strat-a",
        symbol="AAPL",
        notional_usd=750.0,
        metadata={},
    )

    first = gate.evaluate(request)
    second = gate.evaluate(request)

    assert first.decision == second.decision == "APPROVED"
    assert first.reason == second.reason
    assert first.score == second.score
    assert first.max_allowed == second.max_allowed
    assert first.rule_version == second.rule_version == "bounded-authority-v1"


def test_multi_violation_precedence_is_deterministic_under_kill_switch() -> None:
    decision = evaluate_risk_framework_execution_decision(
        request_id="req-multi",
        strategy_id="strategy-a",
        symbol="AAPL",
        proposed_position_size=10_000.0,
        account_equity=1_000.0,
        current_exposure=900.0,
        strategy_exposure=900.0,
        symbol_exposure=900.0,
        limits=_limits(),
        rule_version="bounded-authority-v1",
        config={"risk.kill_switch.enabled": True},
        evaluated_at=_REGRESSION_TIMESTAMP,
    )

    assert decision.decision == "REJECTED"
    assert decision.reason == "rejected:risk_framework_kill_switch_enabled"


# ---------------------------------------------------------------------------
# Fail-closed bounded evidence discipline
# ---------------------------------------------------------------------------


def test_enforce_approved_risk_decision_fails_closed_when_decision_missing() -> None:
    with pytest.raises(RiskApprovalMissingError):
        enforce_approved_risk_decision(None)


def test_enforce_approved_risk_decision_fails_closed_when_rejected() -> None:
    rejected = RiskDecision(
        decision="REJECTED",
        score=1.0,
        max_allowed=0.5,
        reason="rejected:risk_framework_max_position_size_exceeded",
        timestamp=_REGRESSION_TIMESTAMP,
        rule_version="bounded-authority-v1",
    )
    with pytest.raises(RiskRejectedError):
        enforce_approved_risk_decision(rejected)


def test_adapter_fails_closed_when_approval_flag_contradicts_reason() -> None:
    """Contradictory bounded evidence (approved=True with rejected reason) fails closed."""

    framework_request = FrameworkRiskEvaluationRequest(
        strategy_id="strategy-a",
        symbol="AAPL",
        proposed_position_size=400.0,
        account_equity=2_000.0,
        current_exposure=800.0,
    )
    framework_response = FrameworkRiskEvaluationResponse(
        approved=True,  # contradicts the rejected reason below
        reason="rejected: max_position_size_exceeded",
        adjusted_position_size=0.0,
        risk_score=0.6,
    )

    with pytest.raises(ValueError, match="approval flag conflicts"):
        adapt_risk_framework_response_to_risk_decision(
            framework_request=framework_request,
            framework_response=framework_response,
            limits=_limits(),
            strategy_exposure=0.0,
            symbol_exposure=0.0,
            rule_version="bounded-authority-v1",
            evaluated_at=_REGRESSION_TIMESTAMP,
        )


def test_adapter_fails_closed_on_unknown_reason_code() -> None:
    """Incomplete bounded evidence (unknown reason code) fails closed."""

    framework_request = FrameworkRiskEvaluationRequest(
        strategy_id="strategy-a",
        symbol="AAPL",
        proposed_position_size=400.0,
        account_equity=2_000.0,
        current_exposure=800.0,
    )
    framework_response = FrameworkRiskEvaluationResponse(
        approved=False,
        reason="rejected: not_a_real_rule",
        adjusted_position_size=0.0,
        risk_score=0.0,
    )

    with pytest.raises(ValueError, match="unsupported risk-framework reason"):
        adapt_risk_framework_response_to_risk_decision(
            framework_request=framework_request,
            framework_response=framework_response,
            limits=_limits(),
            strategy_exposure=0.0,
            symbol_exposure=0.0,
            rule_version="bounded-authority-v1",
            evaluated_at=_REGRESSION_TIMESTAMP,
        )


def test_adapter_fails_closed_on_naive_timestamp() -> None:
    """Missing timezone evidence fails closed instead of silently approving."""

    framework_request = FrameworkRiskEvaluationRequest(
        strategy_id="strategy-a",
        symbol="AAPL",
        proposed_position_size=100.0,
        account_equity=10_000.0,
        current_exposure=0.0,
    )
    framework_response = FrameworkRiskEvaluationResponse(
        approved=True,
        reason="approved: within_risk_limits",
        adjusted_position_size=100.0,
        risk_score=0.01,
    )

    with pytest.raises(ValueError, match="timezone-aware"):
        adapt_risk_framework_response_to_risk_decision(
            framework_request=framework_request,
            framework_response=framework_response,
            limits=_limits(),
            strategy_exposure=0.0,
            symbol_exposure=0.0,
            rule_version="bounded-authority-v1",
            evaluated_at=datetime(2026, 1, 1),  # naive on purpose
        )


def test_threshold_gate_fails_closed_on_unbounded_threshold() -> None:
    gate = ThresholdRiskGate(max_notional_usd=0.0)
    with pytest.raises(ValueError, match="max_notional_usd"):
        gate.evaluate(
            RiskEvaluationRequest(
                request_id="req-bad",
                strategy_id="strat-a",
                symbol="AAPL",
                notional_usd=10.0,
                metadata={},
            )
        )

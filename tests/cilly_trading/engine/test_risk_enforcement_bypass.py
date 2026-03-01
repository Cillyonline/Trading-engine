from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from cilly_trading.engine.order_execution_model import (
    DeterministicExecutionConfig,
    DeterministicExecutionModel,
    Order,
    Position,
)
from cilly_trading.engine.risk import RiskApprovalMissingError, RiskRejectedError
from risk.contracts import RiskDecision


def _approved_or_rejected_decision(decision: str) -> RiskDecision:
    return RiskDecision(
        decision=decision,
        score=10.0,
        max_allowed=100.0,
        reason="risk gate test",
        timestamp=datetime.now(tz=timezone.utc),
        rule_version="test-v1",
    )


def _single_buy_order() -> Order:
    return Order(
        id="buy-1",
        side="BUY",
        quantity=Decimal("1"),
        created_snapshot_key="2024-01-01T00:00:00Z",
        sequence=1,
    )


def _execution_inputs() -> tuple[dict[str, str], Position, DeterministicExecutionConfig]:
    snapshot = {"timestamp": "2024-01-02T00:00:00Z", "open": "100"}
    position = Position(quantity=Decimal("0"), avg_price=Decimal("0"))
    config = DeterministicExecutionConfig(
        slippage_bps=10,
        commission_per_order=Decimal("1.25"),
        fill_timing="next_snapshot",
    )
    return snapshot, position, config


def test_execute_direct_call_requires_explicit_risk_approval() -> None:
    model = DeterministicExecutionModel()
    snapshot, position, config = _execution_inputs()

    with pytest.raises(RiskApprovalMissingError):
        model.execute(
            orders=[_single_buy_order()],
            snapshot=snapshot,
            position=position,
            config=config,
            risk_decision=None,
        )


def test_execute_direct_call_rejects_rejected_risk_decision() -> None:
    model = DeterministicExecutionModel()
    snapshot, position, config = _execution_inputs()

    with pytest.raises(RiskRejectedError):
        model.execute(
            orders=[_single_buy_order()],
            snapshot=snapshot,
            position=position,
            config=config,
            risk_decision=_approved_or_rejected_decision("REJECTED"),
        )


def test_execute_direct_call_allows_approved_risk_decision() -> None:
    model = DeterministicExecutionModel()
    snapshot, position, config = _execution_inputs()

    fills, updated_position = model.execute(
        orders=[_single_buy_order()],
        snapshot=snapshot,
        position=position,
        config=config,
        risk_decision=_approved_or_rejected_decision("APPROVED"),
    )

    assert len(fills) == 1
    assert updated_position.quantity == Decimal("1.00000000")

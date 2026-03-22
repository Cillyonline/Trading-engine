from __future__ import annotations

from decimal import Decimal

import pytest

from cilly_trading.engine.paper_order_lifecycle import (
    PaperOrderLifecycleRequest,
    PaperOrderLifecycleSimulator,
    PaperOrderStep,
)


def _request(**overrides: object) -> PaperOrderLifecycleRequest:
    payload: dict[str, object] = {
        "order_id": "ord-paper-1",
        "strategy_id": "strategy-paper",
        "symbol": "AAPL",
        "side": "BUY",
        "quantity": Decimal("3"),
        "created_at": "2025-01-01T09:30:00Z",
        "submitted_at": "2025-01-01T09:30:01Z",
        "sequence": 1,
        "position_id": "pos-1",
        "trade_id": "trade-1",
    }
    payload.update(overrides)
    return PaperOrderLifecycleRequest(**payload)


def test_lifecycle_transitions_are_explicit_and_deterministic() -> None:
    simulator = PaperOrderLifecycleSimulator()
    result = simulator.run(
        request=_request(),
        steps=[
            PaperOrderStep(
                occurred_at="2025-01-01T09:31:00Z",
                action="fill",
                quantity=Decimal("1"),
                price=Decimal("100"),
                commission=Decimal("0.5"),
            ),
            PaperOrderStep(
                occurred_at="2025-01-01T09:32:00Z",
                action="fill",
                quantity=Decimal("2"),
                price=Decimal("102"),
                commission=Decimal("0.5"),
            ),
        ],
    )

    assert [order.status for order in result.orders] == [
        "created",
        "submitted",
        "partially_filled",
        "filled",
    ]
    assert [event.event_type for event in result.execution_events] == [
        "created",
        "submitted",
        "partially_filled",
        "filled",
    ]
    assert result.final_order.filled_quantity == Decimal("3")


def test_representative_partial_fill_then_cancel_is_bounded_and_testable() -> None:
    simulator = PaperOrderLifecycleSimulator()
    result = simulator.run(
        request=_request(max_fill_per_step=Decimal("1")),
        steps=[
            PaperOrderStep(
                occurred_at="2025-01-01T09:31:00Z",
                action="fill",
                quantity=Decimal("2"),
                price=Decimal("100"),
                commission=Decimal("0.5"),
            ),
            PaperOrderStep(
                occurred_at="2025-01-01T09:32:00Z",
                action="cancel",
            ),
        ],
    )

    fill_event = result.execution_events[2]
    assert fill_event.event_type == "partially_filled"
    assert fill_event.execution_quantity == Decimal("1")
    assert result.final_order.status == "cancelled"
    assert result.final_order.filled_quantity == Decimal("1")


def test_invalid_transition_cancel_after_filled_is_rejected() -> None:
    simulator = PaperOrderLifecycleSimulator()

    with pytest.raises(ValueError, match="paper_order_step_after_terminal_state"):
        simulator.run(
            request=_request(quantity=Decimal("1")),
            steps=[
                PaperOrderStep(
                    occurred_at="2025-01-01T09:31:00Z",
                    action="fill",
                    quantity=Decimal("1"),
                    price=Decimal("100"),
                ),
                PaperOrderStep(
                    occurred_at="2025-01-01T09:32:00Z",
                    action="cancel",
                ),
            ],
        )


def test_invalid_transition_fill_after_cancelled_is_rejected() -> None:
    simulator = PaperOrderLifecycleSimulator()

    with pytest.raises(ValueError, match="paper_order_step_after_terminal_state"):
        simulator.run(
            request=_request(),
            steps=[
                PaperOrderStep(
                    occurred_at="2025-01-01T09:31:00Z",
                    action="cancel",
                ),
                PaperOrderStep(
                    occurred_at="2025-01-01T09:32:00Z",
                    action="fill",
                    quantity=Decimal("1"),
                    price=Decimal("100"),
                ),
            ],
        )


def test_regression_representative_flow_is_reproducible() -> None:
    simulator = PaperOrderLifecycleSimulator()
    request = _request(max_fill_per_step=Decimal("2"))
    steps = [
        PaperOrderStep(
            occurred_at="2025-01-01T09:31:00Z",
            action="fill",
            quantity=Decimal("2"),
            price=Decimal("100"),
            commission=Decimal("0.25"),
        ),
        PaperOrderStep(
            occurred_at="2025-01-01T09:32:00Z",
            action="fill",
            quantity=Decimal("2"),
            price=Decimal("101"),
            commission=Decimal("0.25"),
        ),
    ]

    first = simulator.run(request=request, steps=steps)
    second = simulator.run(request=request, steps=steps)

    assert first.orders == second.orders
    assert first.execution_events == second.execution_events

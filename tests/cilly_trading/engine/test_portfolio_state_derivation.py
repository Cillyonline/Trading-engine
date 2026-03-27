from __future__ import annotations

from decimal import Decimal

from cilly_trading.engine.portfolio import load_portfolio_state_from_simulation_repository
from cilly_trading.models import Trade


class _FakeSimulationRepository:
    def __init__(self, trades: list[Trade]) -> None:
        self._trades = trades

    def list_trades(
        self,
        *,
        strategy_id: str | None = None,
        symbol: str | None = None,
        position_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Trade]:
        items = self._trades
        if strategy_id is not None:
            items = [item for item in items if item.strategy_id == strategy_id]
        if symbol is not None:
            items = [item for item in items if item.symbol == symbol]
        if position_id is not None:
            items = [item for item in items if item.position_id == position_id]
        return items[offset : offset + limit]


def _trade(
    *,
    trade_id: str,
    position_id: str,
    strategy_id: str,
    symbol: str,
    quantity_opened: str,
    quantity_closed: str = "0",
    average_entry_price: str,
    unrealized_pnl: str | None = None,
    status: str = "open",
) -> Trade:
    closed_quantity = Decimal(quantity_closed)
    return Trade.model_validate(
        {
            "trade_id": trade_id,
            "position_id": position_id,
            "strategy_id": strategy_id,
            "symbol": symbol,
            "direction": "long",
            "status": status,
            "opened_at": "2026-03-26T09:30:00Z",
            "closed_at": "2026-03-26T16:00:00Z" if status == "closed" else None,
            "quantity_opened": Decimal(quantity_opened),
            "quantity_closed": closed_quantity,
            "average_entry_price": Decimal(average_entry_price),
            "average_exit_price": Decimal("100") if status == "closed" or closed_quantity > Decimal("0") else None,
            "exposure_notional": (
                (Decimal(quantity_opened) - closed_quantity)
                * Decimal(average_entry_price)
            ),
            "realized_pnl": Decimal("0") if status == "closed" else None,
            "unrealized_pnl": Decimal(unrealized_pnl) if unrealized_pnl is not None else None,
            "opening_order_ids": ["ord-open"],
            "closing_order_ids": ["ord-close"] if status == "closed" else [],
            "execution_event_ids": ["evt-1"],
        }
    )


def test_portfolio_state_derivation_is_deterministic_and_aggregated() -> None:
    repo = _FakeSimulationRepository(
        [
            _trade(
                trade_id="t3",
                position_id="p2",
                strategy_id="beta",
                symbol="AAPL",
                quantity_opened="1",
                average_entry_price="190",
                unrealized_pnl="2",
            ),
            _trade(
                trade_id="t2",
                position_id="p1",
                strategy_id="alpha",
                symbol="AAPL",
                quantity_opened="1",
                average_entry_price="180",
                unrealized_pnl="3",
            ),
            _trade(
                trade_id="t1",
                position_id="p1",
                strategy_id="alpha",
                symbol="AAPL",
                quantity_opened="2",
                quantity_closed="1",
                average_entry_price="200",
                unrealized_pnl="4",
            ),
            _trade(
                trade_id="t4",
                position_id="p3",
                strategy_id="gamma",
                symbol="MSFT",
                quantity_opened="2",
                quantity_closed="2",
                average_entry_price="300",
                unrealized_pnl="0",
                status="closed",
            ),
        ]
    )

    first = load_portfolio_state_from_simulation_repository(repository=repo)
    second = load_portfolio_state_from_simulation_repository(repository=repo)

    assert first == second
    assert [(item.symbol, item.strategy_id) for item in first.positions] == [
        ("AAPL", "alpha"),
        ("AAPL", "beta"),
    ]
    alpha_position = first.positions[0]
    assert alpha_position.size == 2.0
    assert alpha_position.average_price == 190.0
    assert alpha_position.unrealized_pnl == 7.0


def test_portfolio_state_derivation_returns_empty_state_when_no_open_exposure() -> None:
    repo = _FakeSimulationRepository(
        [
            _trade(
                trade_id="t-closed",
                position_id="p-closed",
                strategy_id="alpha",
                symbol="NVDA",
                quantity_opened="1",
                quantity_closed="1",
                average_entry_price="700",
                unrealized_pnl="0",
                status="closed",
            )
        ]
    )

    state = load_portfolio_state_from_simulation_repository(repository=repo)
    assert state.positions == tuple()

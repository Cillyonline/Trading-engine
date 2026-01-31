"""
Deterministic paper trading simulator for signals.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from cilly_trading.models import Signal, Trade
from cilly_trading.repositories import TradeRepository

PRICE_QUANTIZER = Decimal("0.0001")


def _to_decimal(value: float | int | str | Decimal) -> Decimal:
    return Decimal(str(value)).quantize(PRICE_QUANTIZER, rounding=ROUND_HALF_UP)


def _extract_price(signal: Signal) -> Decimal:
    if "price" in signal and signal["price"] is not None:
        return _to_decimal(signal["price"])  # type: ignore[arg-type]
    entry_zone = signal.get("entry_zone")
    if entry_zone is not None:
        return _to_decimal((entry_zone["from_"] + entry_zone["to"]) / 2)
    raise ValueError("Signal missing price and entry_zone")


def _signal_action(signal: Signal) -> str:
    action = signal.get("action")
    if isinstance(action, str) and action:
        return action.lower()
    stage = signal.get("stage")
    if stage == "entry_confirmed":
        return "entry"
    if stage == "setup":
        return "exit"
    return "entry"


def _signal_sort_key(item: Tuple[int, Signal]) -> Tuple[str, str, str, int]:
    index, signal = item
    timestamp = signal.get("timestamp") or ""
    symbol = signal.get("symbol") or ""
    action = _signal_action(signal)
    return (timestamp, symbol, action, index)


@dataclass
class PositionState:
    """Represents the deterministic position state per symbol."""

    qty: int
    avg_entry_price: Decimal
    realized_pnl: Decimal
    last_price: Decimal


@dataclass
class PositionSummary:
    """Serializable summary of a position."""

    qty: int
    avg_entry_price: float
    realized_pnl: float
    unrealized_pnl: float
    total_pnl: float


@dataclass
class SimulationResult:
    """Return structure for the paper trading simulator."""

    trades: List[Trade]
    positions: Dict[str, PositionSummary]
    pnl_by_symbol: Dict[str, Dict[str, float]]
    pnl_total: Dict[str, float]


class PaperTradingSimulator:
    """Deterministic paper trading simulator for signals.

    Args:
        trade_repository: Optional trade repository for persistence.
    """

    def __init__(self, trade_repository: Optional[TradeRepository] = None) -> None:
        self._trade_repository = trade_repository

    def run(self, signals: Sequence[Signal]) -> SimulationResult:
        """Run the deterministic simulation.

        Args:
            signals: Sequence of signals to execute.

        Returns:
            SimulationResult containing trades, positions, and PnL.
        """
        ordered_signals = [signal for _, signal in sorted(enumerate(signals), key=_signal_sort_key)]

        positions: Dict[str, PositionState] = {}
        trades: List[Trade] = []
        open_trades: Dict[str, List[Trade]] = {}

        for signal in ordered_signals:
            symbol = signal.get("symbol") or ""
            if not symbol:
                raise ValueError("Signal missing symbol")

            price = _extract_price(signal)
            timestamp = signal.get("timestamp") or ""
            action = _signal_action(signal)
            position = positions.get(symbol)
            if position is None:
                position = PositionState(qty=0, avg_entry_price=Decimal("0"), realized_pnl=Decimal("0"), last_price=price)
                positions[symbol] = position

            position.last_price = price

            if action == "entry":
                new_qty = position.qty + 1
                if new_qty == 1:
                    position.avg_entry_price = price
                else:
                    weighted_total = (position.avg_entry_price * position.qty) + price
                    position.avg_entry_price = (weighted_total / Decimal(new_qty)).quantize(
                        PRICE_QUANTIZER, rounding=ROUND_HALF_UP
                    )
                position.qty = new_qty

                trade: Trade = {
                    "symbol": symbol,
                    "strategy": signal.get("strategy") or "",
                    "stage": signal.get("stage") or "entry_confirmed",
                    "entry_price": float(price),
                    "entry_date": timestamp,
                    "reason_entry": signal.get("confirmation_rule") or "paper_trade_entry",
                    "timeframe": signal.get("timeframe") or "",
                    "market_type": signal.get("market_type") or "stock",
                    "data_source": signal.get("data_source") or "yahoo",
                }
                if self._trade_repository is not None:
                    trade_id = self._trade_repository.save_trade(trade)
                    trade["id"] = trade_id

                trades.append(trade)
                open_trades.setdefault(symbol, []).append(trade)
                continue

            if action == "exit":
                if position.qty <= 0:
                    continue
                position.qty -= 1

                if open_trades.get(symbol):
                    open_trade = open_trades[symbol].pop(0)
                    entry_price_value = open_trade.get("entry_price") or 0
                    entry_price_decimal = _to_decimal(entry_price_value)
                    pnl = (price - entry_price_decimal).quantize(PRICE_QUANTIZER, rounding=ROUND_HALF_UP)
                    position.realized_pnl = (position.realized_pnl + pnl).quantize(
                        PRICE_QUANTIZER, rounding=ROUND_HALF_UP
                    )
                    open_trade["exit_price"] = float(price)
                    open_trade["exit_date"] = timestamp
                    open_trade["reason_exit"] = "paper_trade_exit"
                    if self._trade_repository is not None and "id" in open_trade:
                        update_exit = getattr(self._trade_repository, "update_trade_exit", None)
                        if update_exit is None:
                            raise AttributeError("Trade repository missing update_trade_exit")
                        update_exit(open_trade["id"], float(price), timestamp, "paper_trade_exit")

                if position.qty == 0:
                    position.avg_entry_price = Decimal("0")

        positions_summary: Dict[str, PositionSummary] = {}
        pnl_by_symbol: Dict[str, Dict[str, float]] = {}
        total_realized = Decimal("0")
        total_unrealized = Decimal("0")

        for symbol, position in sorted(positions.items()):
            unrealized = Decimal("0")
            if position.qty > 0:
                unrealized = (position.last_price - position.avg_entry_price) * Decimal(position.qty)
                unrealized = unrealized.quantize(PRICE_QUANTIZER, rounding=ROUND_HALF_UP)
            realized = position.realized_pnl.quantize(PRICE_QUANTIZER, rounding=ROUND_HALF_UP)
            total = (realized + unrealized).quantize(PRICE_QUANTIZER, rounding=ROUND_HALF_UP)

            positions_summary[symbol] = PositionSummary(
                qty=position.qty,
                avg_entry_price=float(position.avg_entry_price),
                realized_pnl=float(realized),
                unrealized_pnl=float(unrealized),
                total_pnl=float(total),
            )
            pnl_by_symbol[symbol] = {
                "realized": float(realized),
                "unrealized": float(unrealized),
                "total": float(total),
            }
            total_realized += realized
            total_unrealized += unrealized

        pnl_total = {
            "realized": float(total_realized.quantize(PRICE_QUANTIZER, rounding=ROUND_HALF_UP)),
            "unrealized": float(total_unrealized.quantize(PRICE_QUANTIZER, rounding=ROUND_HALF_UP)),
            "total": float(
                (total_realized + total_unrealized).quantize(PRICE_QUANTIZER, rounding=ROUND_HALF_UP)
            ),
        }

        return SimulationResult(
            trades=trades,
            positions=positions_summary,
            pnl_by_symbol=pnl_by_symbol,
            pnl_total=pnl_total,
        )


__all__ = ["PaperTradingSimulator", "PositionSummary", "SimulationResult"]

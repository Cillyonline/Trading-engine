from __future__ import annotations

from collections import defaultdict, deque
from typing import Any, Deque, Mapping, Sequence


def _signal_action(signal: Mapping[str, object]) -> str:
    action = signal.get("action")
    if isinstance(action, str) and action:
        return action.lower()
    return "entry"


def _signal_sort_key(item: tuple[int, Mapping[str, object]]) -> tuple[str, str, str, int]:
    index, signal = item
    timestamp = str(signal.get("timestamp") or "")
    symbol = str(signal.get("symbol") or "")
    action = _signal_action(signal)
    return (timestamp, symbol, action, index)


def _signal_reason(signal: Mapping[str, object]) -> str:
    reasons = signal.get("reasons")
    if isinstance(reasons, list) and reasons:
        first_reason = reasons[0]
        if isinstance(first_reason, Mapping):
            reason_id = first_reason.get("reason_id")
            if isinstance(reason_id, str) and reason_id:
                return reason_id

    confirmation_rule = signal.get("confirmation_rule")
    if isinstance(confirmation_rule, str) and confirmation_rule:
        return confirmation_rule

    return "unknown"


def _signal_key(signal: Mapping[str, object]) -> tuple[str, str, str, str, str, str, str]:
    return (
        str(signal.get("strategy") or ""),
        str(signal.get("symbol") or ""),
        str(signal.get("timestamp") or ""),
        _signal_reason(signal),
        str(signal.get("timeframe") or ""),
        str(signal.get("market_type") or "stock"),
        str(signal.get("data_source") or "yahoo"),
    )


def _trade_key(trade: Mapping[str, object]) -> tuple[str, str, str, str, str, str, str]:
    return (
        str(trade.get("strategy") or ""),
        str(trade.get("symbol") or ""),
        str(trade.get("entry_date") or ""),
        str(trade.get("reason_entry") or ""),
        str(trade.get("timeframe") or ""),
        str(trade.get("market_type") or "stock"),
        str(trade.get("data_source") or "yahoo"),
    )


def _trade_sort_key(item: tuple[int, Mapping[str, object]]) -> tuple[str, str, str, str, int]:
    index, trade = item
    return (
        str(trade.get("exit_date") or ""),
        str(trade.get("entry_date") or ""),
        str(trade.get("symbol") or ""),
        str(trade.get("strategy") or ""),
        index,
    )


def build_trade_attribution(
    *,
    trades: Sequence[Mapping[str, object]],
    signals: Sequence[Mapping[str, object]],
) -> dict[str, object]:
    """Build deterministic attribution linking each trade to its originating signal."""
    signal_queues: dict[tuple[str, str, str, str, str, str, str], Deque[Mapping[str, object]]] = defaultdict(deque)

    ordered_signals = [signal for _, signal in sorted(enumerate(signals), key=_signal_sort_key)]
    for signal in ordered_signals:
        if _signal_action(signal) != "entry":
            continue
        signal_queues[_signal_key(signal)].append(signal)

    ordered_trades = [trade for _, trade in sorted(enumerate(trades), key=_trade_sort_key)]
    attributions: list[dict[str, object]] = []

    for trade in ordered_trades:
        symbol = str(trade.get("symbol") or "")
        if symbol == "__SUMMARY__":
            continue
        entry_timestamp = trade.get("entry_date")
        exit_timestamp = trade.get("exit_date")
        entry_price = trade.get("entry_price")
        exit_price = trade.get("exit_price")
        if not isinstance(entry_timestamp, str) or not isinstance(exit_timestamp, str):
            continue
        if entry_price is None or exit_price is None:
            continue

        key = _trade_key(trade)
        matched_signal = signal_queues[key].popleft() if signal_queues[key] else None
        if matched_signal is None:
            raise ValueError(f"no originating signal found for trade key: {key!r}")

        attribution: dict[str, object] = {
            "trade_ref": {
                "symbol": symbol,
                "strategy_id": str(trade.get("strategy") or ""),
                "entry_timestamp": entry_timestamp,
                "exit_timestamp": exit_timestamp,
            },
            "strategy_id": str(matched_signal.get("strategy") or ""),
            "originating_signal": {
                "signal_id": str(matched_signal.get("signal_id") or ""),
                "timestamp": str(matched_signal.get("timestamp") or ""),
                "reason": _signal_reason(matched_signal),
            },
            "market_context": {
                "timeframe": str(matched_signal.get("timeframe") or ""),
                "market_type": str(matched_signal.get("market_type") or "stock"),
                "data_source": str(matched_signal.get("data_source") or "yahoo"),
            },
        }
        attributions.append(attribution)

    return {
        "artifact": "trade_attribution",
        "artifact_version": "1",
        "attributions": attributions,
    }


__all__ = ["build_trade_attribution"]

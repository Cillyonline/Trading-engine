"""Backtest execution contract and deterministic run configuration."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Literal, Mapping, Sequence

from risk.contracts import RiskDecision, RiskEvaluationRequest, RiskGate

from cilly_trading.engine.pipeline.orchestrator import (
    DeterministicExecutionConfig,
    ExecutionEvent,
    Order,
    Position,
    run_pipeline,
)
from cilly_trading.engine.strategy_lifecycle.model import StrategyLifecycleState

SUPPORTED_RUN_CONTRACT_VERSION = "1.0.0"
DEFAULT_ACTION_TO_SIDE: dict[str, Literal["BUY", "SELL"]] = {"BUY": "BUY", "SELL": "SELL"}


@dataclass(frozen=True)
class BacktestSignalTranslationConfig:
    """Explicit rules for translating signals into simulated market orders."""

    signal_collection_field: str = "signals"
    signal_id_field: str = "signal_id"
    action_field: str = "action"
    quantity_field: str = "quantity"
    symbol_field: str = "symbol"
    action_to_side: Mapping[str, Literal["BUY", "SELL"]] = field(
        default_factory=lambda: dict(DEFAULT_ACTION_TO_SIDE)
    )

    def __post_init__(self) -> None:
        for value in (
            self.signal_collection_field,
            self.signal_id_field,
            self.action_field,
            self.quantity_field,
            self.symbol_field,
        ):
            if not isinstance(value, str) or not value.strip():
                raise ValueError("Signal translation field names must be non-empty strings")

        normalized: dict[str, Literal["BUY", "SELL"]] = {}
        for action, side in self.action_to_side.items():
            normalized_action = str(action).strip().upper()
            if side not in {"BUY", "SELL"}:
                raise ValueError("Signal action mappings must resolve to BUY or SELL")
            if not normalized_action:
                raise ValueError("Signal action mapping keys must be non-empty")
            normalized[normalized_action] = side

        if not normalized:
            raise ValueError("Signal action mapping must not be empty")

        object.__setattr__(self, "action_to_side", normalized)

    def to_payload(self) -> dict[str, Any]:
        return {
            "signal_collection_field": self.signal_collection_field,
            "signal_id_field": self.signal_id_field,
            "action_field": self.action_field,
            "quantity_field": self.quantity_field,
            "symbol_field": self.symbol_field,
            "action_to_side": dict(sorted(self.action_to_side.items())),
        }


@dataclass(frozen=True)
class BacktestExecutionAssumptions:
    """Explicit deterministic assumptions for backtest order execution."""

    fill_model: Literal["deterministic_market"] = "deterministic_market"
    fill_timing: Literal["next_snapshot", "same_snapshot"] = "next_snapshot"
    price_source: Literal["open_then_price"] = "open_then_price"
    slippage_bps: int = 0
    commission_per_order: Decimal = Decimal("0")
    partial_fills_allowed: bool = False

    def __post_init__(self) -> None:
        if self.slippage_bps < 0:
            raise ValueError("Execution assumption slippage_bps must be >= 0")
        if self.commission_per_order < Decimal("0"):
            raise ValueError("Execution assumption commission_per_order must be >= 0")
        if self.partial_fills_allowed:
            raise ValueError("Execution assumption partial_fills_allowed must be false")

    def to_execution_config(self) -> DeterministicExecutionConfig:
        return DeterministicExecutionConfig(
            slippage_bps=self.slippage_bps,
            commission_per_order=self.commission_per_order,
            fill_timing=self.fill_timing,
        )

    def to_payload(self) -> dict[str, Any]:
        return {
            "fill_model": self.fill_model,
            "fill_timing": self.fill_timing,
            "price_source": self.price_source,
            "slippage_bps": self.slippage_bps,
            "commission_per_order": str(self.commission_per_order),
            "partial_fills_allowed": self.partial_fills_allowed,
        }


@dataclass(frozen=True)
class BacktestRunContract:
    """Backtest run contract with explicit reproducibility metadata."""

    contract_version: str = SUPPORTED_RUN_CONTRACT_VERSION
    signal_translation: BacktestSignalTranslationConfig = field(
        default_factory=BacktestSignalTranslationConfig
    )
    execution_assumptions: BacktestExecutionAssumptions = field(
        default_factory=BacktestExecutionAssumptions
    )

    def __post_init__(self) -> None:
        if self.contract_version != SUPPORTED_RUN_CONTRACT_VERSION:
            raise ValueError(
                f"Unsupported backtest contract_version: {self.contract_version}"
            )

    def to_payload(
        self,
        *,
        run_id: str,
        strategy_name: str,
        strategy_params: Mapping[str, Any],
        engine_name: str,
        engine_version: str | None,
    ) -> dict[str, Any]:
        return {
            "contract_version": self.contract_version,
            "signal_translation": self.signal_translation.to_payload(),
            "execution_assumptions": self.execution_assumptions.to_payload(),
            "reproducibility_metadata": {
                "run_id": run_id,
                "strategy_name": strategy_name,
                "strategy_params": dict(strategy_params),
                "engine_name": engine_name,
                "engine_version": engine_version,
            },
        }


@dataclass(frozen=True)
class BacktestExecutionFlowResult:
    """Deterministic simulated flow result for a run contract."""

    orders: List[Order]
    fills: List[ExecutionEvent]
    positions: List[Position]


def resolve_snapshot_key(snapshot: Mapping[str, Any]) -> str:
    """Resolve deterministic snapshot key used for sequencing and fills."""

    if snapshot.get("timestamp") is not None:
        return str(snapshot["timestamp"])
    if snapshot.get("snapshot_key") is not None:
        return str(snapshot["snapshot_key"])
    if snapshot.get("id") is not None:
        return str(snapshot["id"])
    raise ValueError("Snapshot must contain one of: timestamp, snapshot_key, id")


def sort_snapshots(snapshots: Sequence[Mapping[str, Any]]) -> List[dict[str, Any]]:
    """Sort snapshots deterministically by key and id."""

    sortable: list[tuple[tuple[str, str], dict[str, Any]]] = []
    for snapshot in snapshots:
        normalized = dict(snapshot)
        sortable.append(
            (
                (resolve_snapshot_key(normalized), str(normalized.get("id", ""))),
                normalized,
            )
        )
    sortable.sort(key=lambda item: item[0])
    return [item[1] for item in sortable]


def translate_signals_to_orders(
    *,
    ordered_snapshots: Sequence[Mapping[str, Any]],
    run_id: str,
    strategy_name: str,
    signal_translation: BacktestSignalTranslationConfig,
) -> List[Order]:
    """Translate snapshot signals into deterministic market orders."""

    orders: list[Order] = []
    sequence = 1
    for snapshot in ordered_snapshots:
        snapshot_key = resolve_snapshot_key(snapshot)
        raw_signals = snapshot.get(signal_translation.signal_collection_field, [])
        if raw_signals in (None, []):
            continue
        if not isinstance(raw_signals, Sequence) or isinstance(raw_signals, (str, bytes)):
            raise ValueError("Snapshot signals must be a sequence")

        normalized_signals = sorted(
            (signal for signal in raw_signals),
            key=lambda signal: (
                str(signal.get(signal_translation.signal_id_field, "")),
                str(signal.get(signal_translation.symbol_field, "")),
            ),
        )
        for signal in normalized_signals:
            if not isinstance(signal, Mapping):
                raise ValueError("Each signal must be a mapping")
            signal_id = signal.get(signal_translation.signal_id_field)
            if not isinstance(signal_id, str) or not signal_id.strip():
                raise ValueError("Signal must define a non-empty signal_id")
            raw_action = signal.get(signal_translation.action_field)
            if not isinstance(raw_action, str):
                raise ValueError("Signal must define an action string")
            action = raw_action.strip().upper()
            side = signal_translation.action_to_side.get(action)
            if side is None:
                raise ValueError(f"Unsupported signal action: {action}")

            symbol_value = signal.get(signal_translation.symbol_field, snapshot.get("symbol"))
            if not isinstance(symbol_value, str) or not symbol_value.strip():
                raise ValueError("Signal must define a non-empty symbol")
            symbol = symbol_value.strip().upper()

            quantity_value = signal.get(signal_translation.quantity_field)
            try:
                quantity = Decimal(str(quantity_value))
            except Exception as exc:  # pragma: no cover - defensive parsing
                raise ValueError("Signal quantity must be decimal-compatible") from exc
            if quantity <= Decimal("0"):
                raise ValueError("Signal quantity must be > 0")

            order = Order(
                order_id=f"{run_id}:{signal_id}:{sequence}",
                strategy_id=strategy_name,
                symbol=symbol,
                sequence=sequence,
                side=side,
                order_type="market",
                time_in_force="day",
                status="created",
                quantity=quantity,
                created_at=snapshot_key,
                position_id=f"{run_id}:{symbol}:position",
                trade_id=f"{run_id}:{symbol}:trade",
            )
            orders.append(order)
            sequence += 1

    return orders


def simulate_execution_flow(
    *,
    snapshots: Sequence[Mapping[str, Any]],
    run_id: str,
    strategy_name: str,
    run_contract: BacktestRunContract,
) -> BacktestExecutionFlowResult:
    """Run deterministic signal->order->fill->position backtest flow."""

    ordered_snapshots = sort_snapshots(snapshots)
    orders = translate_signals_to_orders(
        ordered_snapshots=ordered_snapshots,
        run_id=run_id,
        strategy_name=strategy_name,
        signal_translation=run_contract.signal_translation,
    )
    execution_config = run_contract.execution_assumptions.to_execution_config()
    lifecycle_store = _ProductionLifecycleStore()
    risk_gate = _ApprovedRiskGate()

    symbol_positions: dict[str, Position] = {}
    symbol_pending_orders: dict[str, list[Order]] = {}
    for order in orders:
        symbol_pending_orders.setdefault(order.symbol, []).append(order)
        symbol_positions.setdefault(order.symbol, _initial_position(run_id, strategy_name, order.symbol))

    fills: list[ExecutionEvent] = []
    for snapshot in ordered_snapshots:
        snapshot_symbol = snapshot.get("symbol")
        candidate_symbols: list[str]
        if isinstance(snapshot_symbol, str) and snapshot_symbol.strip():
            candidate_symbols = [snapshot_symbol.strip().upper()]
        else:
            candidate_symbols = sorted(symbol_pending_orders.keys())

        for symbol in candidate_symbols:
            pending_orders = symbol_pending_orders.get(symbol, [])
            if not pending_orders:
                continue

            current_position = symbol_positions[symbol]
            pipeline_result = run_pipeline(
                {"orders": pending_orders, "snapshot": snapshot},
                risk_gate=risk_gate,
                lifecycle_store=lifecycle_store,
                risk_request=_risk_request(run_id=run_id, strategy_name=strategy_name, symbol=symbol),
                position=current_position,
                execution_config=execution_config,
            )
            snapshot_fills = pipeline_result.fills
            if not snapshot_fills:
                continue

            symbol_positions[symbol] = pipeline_result.position
            filled_order_ids = {fill.order_id for fill in snapshot_fills}
            symbol_pending_orders[symbol] = [
                order for order in pending_orders if order.order_id not in filled_order_ids
            ]
            fills.extend(snapshot_fills)

    positions = [symbol_positions[symbol] for symbol in sorted(symbol_positions.keys())]
    return BacktestExecutionFlowResult(orders=orders, fills=fills, positions=positions)


def _initial_position(run_id: str, strategy_name: str, symbol: str) -> Position:
    return Position(
        position_id=f"{run_id}:{symbol}:position",
        strategy_id=strategy_name,
        symbol=symbol,
        direction="long",
        status="flat",
        opened_at="backtest-start",
        quantity_opened=Decimal("0"),
        quantity_closed=Decimal("0"),
        net_quantity=Decimal("0"),
        average_entry_price=Decimal("0"),
        order_ids=[],
        execution_event_ids=[],
        trade_ids=[],
    )


def _risk_request(*, run_id: str, strategy_name: str, symbol: str) -> RiskEvaluationRequest:
    return RiskEvaluationRequest(
        request_id=f"{run_id}:{strategy_name}:{symbol}:risk",
        strategy_id=strategy_name,
        symbol=symbol,
        notional_usd=0.0,
        metadata={"source": "backtest_execution_contract"},
    )


class _ApprovedRiskGate(RiskGate):
    def evaluate(self, request: RiskEvaluationRequest) -> RiskDecision:
        return RiskDecision(
            decision="APPROVED",
            score=0.0,
            max_allowed=0.0,
            reason="deterministic_backtest",
            timestamp=datetime(1970, 1, 1, tzinfo=timezone.utc),
            rule_version="deterministic-backtest-v1",
        )


class _ProductionLifecycleStore:
    def get_state(self, strategy_id: str) -> StrategyLifecycleState:
        return StrategyLifecycleState.PRODUCTION

    def set_state(self, strategy_id: str, new_state: StrategyLifecycleState) -> None:
        return None


def serialize_orders(orders: Sequence[Order]) -> list[dict[str, Any]]:
    return [order.model_dump(mode="json") for order in orders]


def serialize_fills(fills: Sequence[ExecutionEvent]) -> list[dict[str, Any]]:
    return [fill.model_dump(mode="json") for fill in fills]


def serialize_positions(positions: Sequence[Position]) -> list[dict[str, Any]]:
    return [position.model_dump(mode="json") for position in positions]

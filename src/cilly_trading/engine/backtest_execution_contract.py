"""Backtest execution contract and deterministic run configuration."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Literal, Mapping, Sequence

from risk.contracts import RiskDecision, RiskEvaluationRequest, RiskGate

from cilly_trading.metrics import compute_backtest_metrics
from cilly_trading.engine.pipeline.orchestrator import (
    DeterministicExecutionConfig,
    ExecutionEvent,
    Order,
    Position,
    run_pipeline,
)
from cilly_trading.engine.strategy_lifecycle.model import StrategyLifecycleState

SUPPORTED_RUN_CONTRACT_VERSION = "1.0.0"
BASELINE_VERSION = "1.0.0"
REALISM_BOUNDARY_VERSION = "1.0.0"
DEFAULT_ACTION_TO_SIDE: dict[str, Literal["BUY", "SELL"]] = {"BUY": "BUY", "SELL": "SELL"}
MAX_SLIPPAGE_BPS = 250
MAX_COMMISSION_PER_ORDER = Decimal("25")
DEFAULT_STARTING_EQUITY = Decimal("100000")


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
        if self.fill_model != "deterministic_market":
            raise ValueError("Execution assumption fill_model must be deterministic_market")
        if self.fill_timing not in {"next_snapshot", "same_snapshot"}:
            raise ValueError("Execution assumption fill_timing is unsupported")
        if self.price_source != "open_then_price":
            raise ValueError("Execution assumption price_source must be open_then_price")
        if not isinstance(self.partial_fills_allowed, bool):
            raise ValueError("Execution assumption partial_fills_allowed must be a boolean")
        if self.partial_fills_allowed:
            raise ValueError("Execution assumption partial_fills_allowed must be false")

        if isinstance(self.slippage_bps, bool) or not isinstance(self.slippage_bps, int):
            raise ValueError("Execution assumption slippage_bps must be an integer")
        if self.slippage_bps < 0:
            raise ValueError("Execution assumption slippage_bps must be >= 0")
        if self.slippage_bps > MAX_SLIPPAGE_BPS:
            raise ValueError(f"Execution assumption slippage_bps must be <= {MAX_SLIPPAGE_BPS}")

        normalized_commission = self._normalize_commission(self.commission_per_order)
        if normalized_commission < Decimal("0"):
            raise ValueError("Execution assumption commission_per_order must be >= 0")
        if normalized_commission > MAX_COMMISSION_PER_ORDER:
            raise ValueError(
                f"Execution assumption commission_per_order must be <= {MAX_COMMISSION_PER_ORDER}"
            )
        object.__setattr__(self, "commission_per_order", normalized_commission)

    @staticmethod
    def _normalize_commission(value: Decimal | int | float | str) -> Decimal:
        try:
            normalized = Decimal(str(value))
        except (InvalidOperation, ValueError, TypeError) as exc:
            raise ValueError("Execution assumption commission_per_order must be decimal-compatible") from exc
        if not normalized.is_finite():
            raise ValueError("Execution assumption commission_per_order must be finite")
        return normalized

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


def build_backtest_realism_boundary(
    *,
    execution_assumptions: BacktestExecutionAssumptions,
) -> dict[str, Any]:
    """Build explicit modeled vs unmodeled realism disclosures for reporting."""

    return {
        "boundary_version": REALISM_BOUNDARY_VERSION,
        "modeled_assumptions": {
            "fees": {
                "commission_model": "fixed_per_filled_order",
                "commission_per_order": str(execution_assumptions.commission_per_order),
            },
            "slippage": {
                "slippage_bps": execution_assumptions.slippage_bps,
                "slippage_model": "fixed_basis_points_by_side",
            },
            "fills": {
                "fill_model": execution_assumptions.fill_model,
                "fill_timing": execution_assumptions.fill_timing,
                "partial_fills_allowed": execution_assumptions.partial_fills_allowed,
                "price_source": execution_assumptions.price_source,
            },
        },
        "unmodeled_assumptions": {
            "market_hours": (
                "Not modeled. Snapshot timestamps are replayed as provided; exchange sessions, "
                "holidays, halts, auctions, and after-hours restrictions are excluded."
            ),
            "broker_behavior": (
                "Not modeled. Routing, venue selection, rejects, cancels, and broker-specific "
                "policies are excluded."
            ),
            "liquidity_and_microstructure": (
                "Not modeled. Order-book depth, queue position, fill probability, latency, and "
                "market impact are excluded."
            ),
        },
        "evidence_boundary": {
            "supported_interpretation": [
                "Deterministic replay of supplied snapshots under the declared fill, slippage, and fee assumptions.",
                "Cost-aware metrics bounded to fixed commission and fixed basis-point slippage.",
            ],
            "unsupported_claims": [
                "broker execution realism",
                "market-hours compliance realism",
                "liquidity or market microstructure realism",
                "live-trading readiness or approval",
                "future profitability or out-of-sample robustness",
            ],
            "qualification_constraint": (
                "Backtest evidence is bounded and must not be used alone for qualification, "
                "trader approval, or live-trading decisions."
            ),
            "decision_use_constraint": (
                "Qualification and decision documents must treat this artifact as bounded "
                "backtest evidence only."
            ),
        },
    }


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


def build_cost_slippage_metrics_baseline(
    *,
    ordered_snapshots: Sequence[Mapping[str, Any]],
    fills: Sequence[ExecutionEvent],
    execution_assumptions: BacktestExecutionAssumptions,
) -> dict[str, Any]:
    """Build deterministic cost-aware vs cost-free baseline outputs."""

    snapshot_rows = [dict(snapshot) for snapshot in ordered_snapshots]
    if not snapshot_rows:
        return {
            "baseline_version": BASELINE_VERSION,
            "assumptions": execution_assumptions.to_payload(),
            "summary": {
                "starting_equity": float(DEFAULT_STARTING_EQUITY),
                "ending_equity_cost_free": float(DEFAULT_STARTING_EQUITY),
                "ending_equity_cost_aware": float(DEFAULT_STARTING_EQUITY),
                "total_transaction_cost": 0.0,
                "total_commission": 0.0,
                "total_slippage_cost": 0.0,
                "fill_count": 0,
            },
            "equity_curve": {
                "cost_free": [],
                "cost_aware": [],
            },
            "metrics": {
                "cost_free": compute_backtest_metrics(
                    summary={
                        "start_equity": float(DEFAULT_STARTING_EQUITY),
                        "end_equity": float(DEFAULT_STARTING_EQUITY),
                    },
                    equity_curve=[],
                    trades=[],
                ),
                "cost_aware": compute_backtest_metrics(
                    summary={
                        "start_equity": float(DEFAULT_STARTING_EQUITY),
                        "end_equity": float(DEFAULT_STARTING_EQUITY),
                    },
                    equity_curve=[],
                    trades=[],
                ),
                "deltas": {},
            },
            "trades": [],
        }

    fills_by_snapshot: dict[str, list[ExecutionEvent]] = {}
    for fill in fills:
        fills_by_snapshot.setdefault(fill.occurred_at, []).append(fill)
    for key in fills_by_snapshot:
        fills_by_snapshot[key] = sorted(
            fills_by_snapshot[key],
            key=lambda event: (event.sequence, event.order_id, event.event_id),
        )

    cash_cost_free = DEFAULT_STARTING_EQUITY
    cash_cost_aware = DEFAULT_STARTING_EQUITY
    net_quantity = Decimal("0")
    total_commission = Decimal("0")
    total_slippage_cost = Decimal("0")

    cost_free_curve: list[dict[str, Any]] = []
    cost_aware_curve: list[dict[str, Any]] = []

    for index, snapshot in enumerate(snapshot_rows):
        snapshot_key = resolve_snapshot_key(snapshot)
        reference_price = _snapshot_fill_reference_price(snapshot)
        snapshot_fills = fills_by_snapshot.get(snapshot_key, [])
        if snapshot_fills and reference_price is None:
            raise ValueError("Snapshot must contain either 'open' or 'price'")

        for fill in snapshot_fills:
            if fill.execution_quantity is None or fill.execution_price is None:
                continue
            quantity = fill.execution_quantity
            execution_price = fill.execution_price
            commission = fill.commission if fill.commission is not None else Decimal("0")

            reference_notional = reference_price * quantity
            execution_notional = execution_price * quantity

            total_commission += commission
            total_slippage_cost += abs(execution_price - reference_price) * quantity

            if fill.side == "BUY":
                cash_cost_free -= reference_notional
                cash_cost_aware -= execution_notional + commission
                net_quantity += quantity
            else:
                cash_cost_free += reference_notional
                cash_cost_aware += execution_notional - commission
                net_quantity -= quantity

        if reference_price is None:
            if net_quantity != Decimal("0"):
                raise ValueError("Snapshot must contain either 'open' or 'price' when position is open")
            mark_to_market_notional = Decimal("0")
        else:
            mark_to_market_notional = net_quantity * reference_price
        equity_cost_free = cash_cost_free + mark_to_market_notional
        equity_cost_aware = cash_cost_aware + mark_to_market_notional

        point_timestamp = snapshot.get("timestamp", index)
        cost_free_curve.append(
            {
                "timestamp": point_timestamp,
                "equity": _round_money(equity_cost_free),
            }
        )
        cost_aware_curve.append(
            {
                "timestamp": point_timestamp,
                "equity": _round_money(equity_cost_aware),
            }
        )

    start_equity = _round_money(DEFAULT_STARTING_EQUITY)
    end_equity_cost_free = cost_free_curve[-1]["equity"]
    end_equity_cost_aware = cost_aware_curve[-1]["equity"]

    summary_cost_free = {
        "start_equity": start_equity,
        "end_equity": end_equity_cost_free,
    }
    summary_cost_aware = {
        "start_equity": start_equity,
        "end_equity": end_equity_cost_aware,
    }

    metrics_cost_free = compute_backtest_metrics(
        summary=summary_cost_free,
        equity_curve=cost_free_curve,
        trades=[],
    )
    metrics_cost_aware = compute_backtest_metrics(
        summary=summary_cost_aware,
        equity_curve=cost_aware_curve,
        trades=[],
    )

    deltas: dict[str, float | None] = {}
    for key, value in metrics_cost_aware.items():
        cost_free_value = metrics_cost_free.get(key)
        if isinstance(value, (int, float)) and isinstance(cost_free_value, (int, float)):
            deltas[key] = _round_metric(float(value) - float(cost_free_value))
        else:
            deltas[key] = None

    total_transaction_cost = total_commission + total_slippage_cost
    return {
        "baseline_version": BASELINE_VERSION,
        "assumptions": execution_assumptions.to_payload(),
        "summary": {
            "starting_equity": start_equity,
            "ending_equity_cost_free": end_equity_cost_free,
            "ending_equity_cost_aware": end_equity_cost_aware,
            "total_transaction_cost": _round_money(total_transaction_cost),
            "total_commission": _round_money(total_commission),
            "total_slippage_cost": _round_money(total_slippage_cost),
            "fill_count": len(fills),
        },
        "equity_curve": {
            "cost_free": cost_free_curve,
            "cost_aware": cost_aware_curve,
        },
        "metrics": {
            "cost_free": metrics_cost_free,
            "cost_aware": metrics_cost_aware,
            "deltas": deltas,
        },
        "trades": [],
    }


def _snapshot_fill_reference_price(snapshot: Mapping[str, Any]) -> Decimal | None:
    if snapshot.get("open") is not None:
        return Decimal(str(snapshot["open"]))
    if snapshot.get("price") is not None:
        return Decimal(str(snapshot["price"]))
    return None


def _round_money(value: Decimal) -> float:
    return float(value.quantize(Decimal("0.01")))


def _round_metric(value: float) -> float:
    return float(Decimal(str(value)).quantize(Decimal("0.000000000001")))

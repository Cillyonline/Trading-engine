"""Backtest execution contract and deterministic run configuration."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from math import isfinite
from typing import Any, Dict, List, Literal, Mapping, Sequence

from risk.contracts import RiskDecision, RiskEvaluationRequest, RiskGate

from cilly_trading.metrics import compute_backtest_metrics
from cilly_trading.models import compute_execution_event_id
from cilly_trading.engine.pipeline.orchestrator import (
    DeterministicExecutionConfig,
    ExecutionEvent,
    Order,
    Position,
    run_pipeline,
)
from cilly_trading.engine.slippage import StochasticSlippageModel
from cilly_trading.engine.strategy_lifecycle.model import StrategyLifecycleState

SUPPORTED_RUN_CONTRACT_VERSION = "1.0.0"
BASELINE_VERSION = "1.0.0"
REALISM_BOUNDARY_VERSION = "1.0.0"
REALISM_SENSITIVITY_MATRIX_VERSION = "1.0.0"
DEFAULT_ACTION_TO_SIDE: dict[str, Literal["BUY", "SELL"]] = {"BUY": "BUY", "SELL": "SELL"}
MAX_SLIPPAGE_BPS = 250
MAX_COMMISSION_PER_ORDER = Decimal("25")
DEFAULT_STARTING_EQUITY = Decimal("100000")
BACKTEST_RISK_EVIDENCE_VERSION = "1.0.0"
BACKTEST_RISK_RULE_VERSION = "deterministic-backtest-risk-v1"
BACKTEST_RISK_DECISION_TIMESTAMP = datetime(1970, 1, 1, tzinfo=timezone.utc)
REALISM_PROFILE_BASELINE_ID = "configured_baseline"
REALISM_PROFILE_COST_FREE_ID = "cost_free_reference"
REALISM_PROFILE_COST_STRESS_ID = "bounded_cost_stress"
REALISM_PROFILE_COST_STRESS_SLIPPAGE_BPS = 25
REALISM_PROFILE_COST_STRESS_COMMISSION_PER_ORDER = Decimal("2.50")


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
    stochastic_slippage_model: StochasticSlippageModel | None = field(
        default=None, compare=False, hash=False
    )

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

        if self.stochastic_slippage_model is not None and not isinstance(
            self.stochastic_slippage_model, StochasticSlippageModel
        ):
            raise ValueError(
                "Execution assumption stochastic_slippage_model must be a StochasticSlippageModel instance or None"
            )

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
            stochastic_slippage_model=self.stochastic_slippage_model,
        )

    def to_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "fill_model": self.fill_model,
            "fill_timing": self.fill_timing,
            "price_source": self.price_source,
            "slippage_bps": self.slippage_bps,
            "commission_per_order": str(self.commission_per_order),
            "partial_fills_allowed": self.partial_fills_allowed,
        }
        if self.stochastic_slippage_model is not None:
            payload["stochastic_slippage_model"] = self.stochastic_slippage_model.to_payload()
        return payload


@dataclass(frozen=True)
class BacktestRiskEvidenceConfig:
    """Deterministic risk-evidence fields required for signal-derived orders."""

    evidence_field: str = "risk_evidence"
    decision_field: str = "decision"
    score_field: str = "score"
    max_allowed_field: str = "max_allowed"
    reason_field: str = "reason"
    rule_version_field: str = "rule_version"

    def __post_init__(self) -> None:
        for value in (
            self.evidence_field,
            self.decision_field,
            self.score_field,
            self.max_allowed_field,
            self.reason_field,
            self.rule_version_field,
        ):
            if not isinstance(value, str) or not value.strip():
                raise ValueError("Risk evidence field names must be non-empty strings")

    def to_payload(self) -> dict[str, Any]:
        return {
            "risk_evidence_version": BACKTEST_RISK_EVIDENCE_VERSION,
            "required": True,
            "evidence_field": self.evidence_field,
            "decision_field": self.decision_field,
            "score_field": self.score_field,
            "max_allowed_field": self.max_allowed_field,
            "reason_field": self.reason_field,
            "rule_version_field": self.rule_version_field,
            "missing_evidence_policy": "reject_order",
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
    risk_evidence: BacktestRiskEvidenceConfig = field(
        default_factory=BacktestRiskEvidenceConfig
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
            "risk_evidence": self.risk_evidence.to_payload(),
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
    risk_decisions: List[dict[str, Any]]
    rejected_orders: List[Order]
    rejection_events: List[ExecutionEvent]


def build_backtest_realism_boundary(
    *,
    execution_assumptions: BacktestExecutionAssumptions,
) -> dict[str, Any]:
    """Build explicit modeled vs unmodeled realism disclosures for reporting."""

    return {
        "boundary_version": REALISM_BOUNDARY_VERSION,
        "modeled_assumptions": {
            "bounded_risk_decisions": {
                "risk_evidence_version": BACKTEST_RISK_EVIDENCE_VERSION,
                "evidence_source": "signal_risk_evidence",
                "missing_evidence_policy": "deterministic_order_rejection",
                "broker_risk_behavior": "not_modeled",
            },
            "fees": {
                "commission_model": "fixed_per_filled_order",
                "commission_per_order": str(execution_assumptions.commission_per_order),
            },
            "slippage": {
                "slippage_bps": execution_assumptions.slippage_bps,
                "slippage_model": (
                    "stochastic"
                    if execution_assumptions.stochastic_slippage_model is not None
                    else "fixed_basis_points_by_side"
                ),
                **(
                    {
                        "stochastic_slippage_model": execution_assumptions.stochastic_slippage_model.to_payload()
                    }
                    if execution_assumptions.stochastic_slippage_model is not None
                    else {}
                ),
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
                "Not modeled. Routing, venue selection, broker rejects, cancels, and "
                "broker-specific policies are excluded. Backtest risk rejections are "
                "deterministic artifact evidence only and are not broker behavior."
            ),
            "liquidity_and_microstructure": (
                "Not modeled. Order-book depth, queue position, fill probability, latency, and "
                "market impact are excluded."
            ),
        },
        "evidence_boundary": {
            "supported_interpretation": [
                "Deterministic replay of supplied snapshots under the declared fill, slippage, and fee assumptions.",
                "Deterministic bounded risk decisions for signal-derived orders when required risk evidence is present or missing.",
                "Cost-aware metrics bounded to fixed commission and fixed basis-point slippage.",
            ],
            "unsupported_claims": [
                "broker execution realism",
                "broker reject realism",
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


def _translate_signals_to_order_plans(
    *,
    ordered_snapshots: Sequence[Mapping[str, Any]],
    run_id: str,
    strategy_name: str,
    signal_translation: BacktestSignalTranslationConfig,
    risk_evidence_config: BacktestRiskEvidenceConfig,
) -> tuple[List[Order], dict[str, Mapping[str, Any] | None]]:
    orders: list[Order] = []
    risk_evidence_by_order_id: dict[str, Mapping[str, Any] | None] = {}
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
            raw_risk_evidence = signal.get(risk_evidence_config.evidence_field)
            risk_evidence_by_order_id[order.order_id] = (
                raw_risk_evidence if isinstance(raw_risk_evidence, Mapping) else None
            )
            orders.append(order)
            sequence += 1

    return orders, risk_evidence_by_order_id


def simulate_execution_flow(
    *,
    snapshots: Sequence[Mapping[str, Any]],
    run_id: str,
    strategy_name: str,
    run_contract: BacktestRunContract,
) -> BacktestExecutionFlowResult:
    """Run deterministic signal->order->fill->position backtest flow."""

    ordered_snapshots = sort_snapshots(snapshots)
    orders, risk_evidence_by_order_id = _translate_signals_to_order_plans(
        ordered_snapshots=ordered_snapshots,
        run_id=run_id,
        strategy_name=strategy_name,
        signal_translation=run_contract.signal_translation,
        risk_evidence_config=run_contract.risk_evidence,
    )
    execution_config = run_contract.execution_assumptions.to_execution_config()
    lifecycle_store = _ProductionLifecycleStore()
    risk_gate = _DeterministicBacktestRiskGate(
        risk_evidence_by_order_id=risk_evidence_by_order_id,
        risk_evidence_config=run_contract.risk_evidence,
    )

    symbol_positions: dict[str, Position] = {}
    symbol_pending_orders: dict[str, list[Order]] = {}
    for order in orders:
        symbol_pending_orders.setdefault(order.symbol, []).append(order)
        symbol_positions.setdefault(order.symbol, _initial_position(run_id, strategy_name, order.symbol))

    fills: list[ExecutionEvent] = []
    risk_decisions: list[dict[str, Any]] = []
    risk_decision_by_order_id: dict[str, RiskDecision] = {}
    rejected_orders: list[Order] = []
    rejection_events: list[ExecutionEvent] = []
    for snapshot in ordered_snapshots:
        snapshot_key = resolve_snapshot_key(snapshot)
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
            remaining_orders: list[Order] = []
            for order in pending_orders:
                risk_request = _risk_request(
                    run_id=run_id,
                    strategy_name=strategy_name,
                    symbol=symbol,
                    order=order,
                )
                risk_decision = risk_decision_by_order_id.get(order.order_id)
                if risk_decision is None:
                    risk_decision = risk_gate.evaluate(risk_request)
                    risk_decision_by_order_id[order.order_id] = risk_decision
                    risk_decisions.append(
                        risk_gate.build_decision_record(
                            request=risk_request,
                            order=order,
                            snapshot_key=snapshot_key,
                            decision=risk_decision,
                        )
                    )

                if risk_decision.decision != "APPROVED":
                    rejected_order = _mark_order_rejected(order)
                    rejected_orders.append(rejected_order)
                    rejection_events.append(
                        _build_rejection_event(
                            order=rejected_order,
                            snapshot_key=snapshot_key,
                            sequence=len(rejection_events) + 1,
                        )
                    )
                    continue

                if not _order_ready_for_snapshot(
                    order=order,
                    snapshot_key=snapshot_key,
                    fill_timing=run_contract.execution_assumptions.fill_timing,
                ):
                    remaining_orders.append(order)
                    continue

                pipeline_result = run_pipeline(
                    {"orders": [order], "snapshot": snapshot},
                    risk_gate=risk_gate,
                    lifecycle_store=lifecycle_store,
                    risk_request=risk_request,
                    position=current_position,
                    execution_config=execution_config,
                )

                if pipeline_result.status == "rejected":
                    rejected_order = _mark_order_rejected(order)
                    rejected_orders.append(rejected_order)
                    rejection_events.append(
                        _build_rejection_event(
                            order=rejected_order,
                            snapshot_key=snapshot_key,
                            sequence=len(rejection_events) + 1,
                        )
                    )
                    continue

                snapshot_fills = pipeline_result.fills
                if snapshot_fills:
                    current_position = pipeline_result.position
                    fills.extend(snapshot_fills)
                    continue

                remaining_orders.append(order)

            symbol_positions[symbol] = current_position
            symbol_pending_orders[symbol] = remaining_orders

    positions = [symbol_positions[symbol] for symbol in sorted(symbol_positions.keys())]
    return BacktestExecutionFlowResult(
        orders=orders,
        fills=fills,
        positions=positions,
        risk_decisions=sorted(
            risk_decisions,
            key=lambda record: (
                str(record["snapshot_key"]),
                str(record["order_id"]),
                str(record["request_id"]),
            ),
        ),
        rejected_orders=sorted(rejected_orders, key=lambda order: order.order_id),
        rejection_events=sorted(
            rejection_events,
            key=lambda event: (event.occurred_at, event.sequence, event.order_id),
        ),
    )


def _order_ready_for_snapshot(
    *,
    order: Order,
    snapshot_key: str,
    fill_timing: Literal["next_snapshot", "same_snapshot"],
) -> bool:
    if fill_timing == "same_snapshot":
        return order.created_at <= snapshot_key
    return order.created_at < snapshot_key


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


def _risk_request(
    *,
    run_id: str,
    strategy_name: str,
    symbol: str,
    order: Order,
) -> RiskEvaluationRequest:
    return RiskEvaluationRequest(
        request_id=f"{run_id}:{order.order_id}:risk",
        strategy_id=strategy_name,
        symbol=symbol,
        notional_usd=float(order.quantity),
        metadata={
            "source": "backtest_execution_contract",
            "order_id": order.order_id,
            "guard_type": "emergency",
        },
    )


class _DeterministicBacktestRiskGate(RiskGate):
    def __init__(
        self,
        *,
        risk_evidence_by_order_id: Mapping[str, Mapping[str, Any] | None],
        risk_evidence_config: BacktestRiskEvidenceConfig,
    ) -> None:
        self._risk_evidence_by_order_id = dict(risk_evidence_by_order_id)
        self._risk_evidence_config = risk_evidence_config
        self._evidence_status_by_request_id: dict[str, str] = {}

    def evaluate(self, request: RiskEvaluationRequest) -> RiskDecision:
        order_id = request.metadata.get("order_id", "")
        evidence = self._risk_evidence_by_order_id.get(order_id)
        if evidence is None:
            self._evidence_status_by_request_id[request.request_id] = "missing_required_risk_evidence"
            return RiskDecision(
                decision="REJECTED",
                score=0.0,
                max_allowed=0.0,
                reason="missing_required_risk_evidence",
                timestamp=BACKTEST_RISK_DECISION_TIMESTAMP,
                rule_version=BACKTEST_RISK_RULE_VERSION,
            )

        config = self._risk_evidence_config
        try:
            raw_decision = evidence[config.decision_field]
            score = float(evidence[config.score_field])
            max_allowed = float(evidence[config.max_allowed_field])
            reason = str(evidence[config.reason_field]).strip()
            rule_version = str(evidence[config.rule_version_field]).strip()
        except (KeyError, TypeError, ValueError) as exc:
            self._evidence_status_by_request_id[request.request_id] = "invalid_required_risk_evidence"
            return RiskDecision(
                decision="REJECTED",
                score=0.0,
                max_allowed=0.0,
                reason=f"invalid_required_risk_evidence:{type(exc).__name__}",
                timestamp=BACKTEST_RISK_DECISION_TIMESTAMP,
                rule_version=BACKTEST_RISK_RULE_VERSION,
            )

        if not isfinite(score) or not isfinite(max_allowed):
            self._evidence_status_by_request_id[request.request_id] = "invalid_required_risk_evidence"
            return RiskDecision(
                decision="REJECTED",
                score=0.0,
                max_allowed=0.0,
                reason="invalid_required_risk_evidence:non_finite_score_or_max_allowed",
                timestamp=BACKTEST_RISK_DECISION_TIMESTAMP,
                rule_version=BACKTEST_RISK_RULE_VERSION,
            )

        decision = str(raw_decision).strip().upper()
        if decision not in {"APPROVED", "REJECTED"}:
            self._evidence_status_by_request_id[request.request_id] = "invalid_required_risk_evidence"
            return RiskDecision(
                decision="REJECTED",
                score=score,
                max_allowed=max_allowed,
                reason="invalid_required_risk_evidence:unsupported_decision",
                timestamp=BACKTEST_RISK_DECISION_TIMESTAMP,
                rule_version=BACKTEST_RISK_RULE_VERSION,
            )
        if not reason or not rule_version:
            self._evidence_status_by_request_id[request.request_id] = "invalid_required_risk_evidence"
            return RiskDecision(
                decision="REJECTED",
                score=score,
                max_allowed=max_allowed,
                reason="invalid_required_risk_evidence:empty_reason_or_rule_version",
                timestamp=BACKTEST_RISK_DECISION_TIMESTAMP,
                rule_version=BACKTEST_RISK_RULE_VERSION,
            )

        self._evidence_status_by_request_id[request.request_id] = "present"
        return RiskDecision(
            decision=decision,  # type: ignore[arg-type]
            score=score,
            max_allowed=max_allowed,
            reason=reason,
            timestamp=BACKTEST_RISK_DECISION_TIMESTAMP,
            rule_version=rule_version,
        )

    def build_decision_record(
        self,
        *,
        request: RiskEvaluationRequest,
        order: Order,
        snapshot_key: str,
        decision: RiskDecision,
    ) -> dict[str, Any]:
        return {
            "risk_evidence_version": BACKTEST_RISK_EVIDENCE_VERSION,
            "request_id": request.request_id,
            "order_id": order.order_id,
            "symbol": order.symbol,
            "side": order.side,
            "snapshot_key": snapshot_key,
            "evidence_status": self._evidence_status_by_request_id.get(
                request.request_id,
                "unknown",
            ),
            "decision": decision.decision,
            "score": decision.score,
            "max_allowed": decision.max_allowed,
            "reason": decision.reason,
            "timestamp": decision.timestamp.isoformat().replace("+00:00", "Z"),
            "rule_version": decision.rule_version,
        }


def _mark_order_rejected(order: Order) -> Order:
    return Order.model_validate({**order.model_dump(mode="python"), "status": "rejected"})


def _build_rejection_event(
    *,
    order: Order,
    snapshot_key: str,
    sequence: int,
) -> ExecutionEvent:
    return ExecutionEvent(
        event_id=compute_execution_event_id(
            order_id=order.order_id,
            event_type="rejected",
            occurred_at=snapshot_key,
            sequence=sequence,
        ),
        order_id=order.order_id,
        strategy_id=order.strategy_id,
        symbol=order.symbol,
        side=order.side,
        event_type="rejected",
        occurred_at=snapshot_key,
        sequence=sequence,
        position_id=order.position_id,
        trade_id=order.trade_id,
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


def build_realism_sensitivity_matrix(
    *,
    ordered_snapshots: Sequence[Mapping[str, Any]],
    run_id: str,
    strategy_name: str,
    run_contract: BacktestRunContract,
) -> dict[str, Any]:
    """Build deterministic bounded realism sensitivity metrics from one snapshot set."""

    profile_definitions = _build_realism_profile_assumptions(
        execution_assumptions=run_contract.execution_assumptions
    )

    baseline_summary: Mapping[str, Any] | None = None
    baseline_metrics: Mapping[str, Any] | None = None
    profiles: list[dict[str, Any]] = []
    for profile_id, profile_name, profile_description, profile_assumptions in profile_definitions:
        profile_contract = BacktestRunContract(
            contract_version=run_contract.contract_version,
            signal_translation=run_contract.signal_translation,
            execution_assumptions=profile_assumptions,
        )
        profile_flow = simulate_execution_flow(
            snapshots=ordered_snapshots,
            run_id=run_id,
            strategy_name=strategy_name,
            run_contract=profile_contract,
        )
        profile_baseline = build_cost_slippage_metrics_baseline(
            ordered_snapshots=ordered_snapshots,
            fills=profile_flow.fills,
            execution_assumptions=profile_assumptions,
        )
        profile_summary = dict(profile_baseline["summary"])
        profile_metrics = dict(profile_baseline["metrics"]["cost_aware"])
        if profile_id == REALISM_PROFILE_BASELINE_ID:
            baseline_summary = profile_summary
            baseline_metrics = profile_metrics

        profiles.append(
            {
                "profile_id": profile_id,
                "profile_name": profile_name,
                "profile_description": profile_description,
                "assumptions": profile_assumptions.to_payload(),
                "summary": profile_summary,
                "metrics": profile_metrics,
            }
        )

    if baseline_summary is None or baseline_metrics is None:
        raise ValueError("Configured baseline realism profile is required")

    for profile in profiles:
        profile["delta_vs_baseline"] = {
            "summary": _build_numeric_delta_map(
                current=profile["summary"],
                baseline=baseline_summary,
            ),
            "metrics": _build_numeric_delta_map(
                current=profile["metrics"],
                baseline=baseline_metrics,
            ),
        }

    return {
        "matrix_version": REALISM_SENSITIVITY_MATRIX_VERSION,
        "deterministic": True,
        "baseline_profile_id": REALISM_PROFILE_BASELINE_ID,
        "profile_order": [profile["profile_id"] for profile in profiles],
        "profiles": profiles,
    }


def _build_realism_profile_assumptions(
    *,
    execution_assumptions: BacktestExecutionAssumptions,
) -> tuple[
    tuple[str, str, str, BacktestExecutionAssumptions],
    tuple[str, str, str, BacktestExecutionAssumptions],
    tuple[str, str, str, BacktestExecutionAssumptions],
]:
    fill_timing = execution_assumptions.fill_timing
    stress_slippage_bps = max(
        execution_assumptions.slippage_bps,
        REALISM_PROFILE_COST_STRESS_SLIPPAGE_BPS,
    )
    stress_commission = max(
        execution_assumptions.commission_per_order,
        REALISM_PROFILE_COST_STRESS_COMMISSION_PER_ORDER,
    )
    return (
        (
            REALISM_PROFILE_BASELINE_ID,
            "Configured baseline",
            "Run-config execution assumptions without sensitivity overrides.",
            execution_assumptions,
        ),
        (
            REALISM_PROFILE_COST_FREE_ID,
            "Cost-free reference",
            "Deterministic reference with zero slippage and zero commission.",
            BacktestExecutionAssumptions(
                fill_timing=fill_timing,
                slippage_bps=0,
                commission_per_order=Decimal("0"),
            ),
        ),
        (
            REALISM_PROFILE_COST_STRESS_ID,
            "Bounded cost stress",
            "Deterministic bounded stress with elevated fixed slippage and commission.",
            BacktestExecutionAssumptions(
                fill_timing=fill_timing,
                slippage_bps=stress_slippage_bps,
                commission_per_order=stress_commission,
            ),
        ),
    )


def _build_numeric_delta_map(
    *,
    current: Mapping[str, Any],
    baseline: Mapping[str, Any],
) -> dict[str, float | None]:
    deltas: dict[str, float | None] = {}
    ordered_keys = sorted(set(current.keys()) | set(baseline.keys()))
    for key in ordered_keys:
        current_value = current.get(key)
        baseline_value = baseline.get(key)
        if isinstance(current_value, (int, float)) and isinstance(baseline_value, (int, float)):
            deltas[key] = _round_metric(float(current_value) - float(baseline_value))
        else:
            deltas[key] = None
    return deltas


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

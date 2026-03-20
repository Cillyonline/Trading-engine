"""
Central data models for the Cilly Trading Engine.
"""

from __future__ import annotations

import hashlib
import json
from decimal import Decimal
from typing import Any, Dict, List, Literal, Mapping, Optional, TypedDict, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


Stage = Literal["setup", "entry_confirmed"]
MarketType = Literal["stock", "crypto"]
Direction = Literal["long"]
DataSource = Literal["yahoo", "binance"]
ReasonType = Literal[
    "INDICATOR_THRESHOLD",
    "INDICATOR_CROSSOVER",
    "PATTERN_MATCH",
    "STATE_TRANSITION",
]
DataType = Literal["INDICATOR_VALUE", "PRICE_VALUE", "BAR_VALUE", "STATE_VALUE"]

CoreDirection = Literal["long"]
OrderSide = Literal["BUY", "SELL"]
OrderType = Literal["market"]
TimeInForce = Literal["day", "gtc"]
OrderStatus = Literal["created", "submitted", "partially_filled", "filled", "cancelled", "rejected"]
PositionStatus = Literal["flat", "open", "closed"]
TradeStatus = Literal["open", "closed"]
ExecutionEventType = Literal["created", "submitted", "partially_filled", "filled", "cancelled", "rejected"]


TRADING_CORE_MODEL_VERSION = "1.0.0"

TRADING_CORE_ENTITIES: Dict[str, Dict[str, str]] = {
    "Order": {
        "authority": "authoritative",
        "responsibility": "A trading instruction and its bounded lifecycle state.",
    },
    "ExecutionEvent": {
        "authority": "authoritative",
        "responsibility": "An immutable execution-side lifecycle fact linked to exactly one order.",
    },
    "Position": {
        "authority": "derived",
        "responsibility": "Deterministic aggregate exposure state derived from execution events.",
    },
    "Trade": {
        "authority": "derived",
        "responsibility": "Deterministic lifecycle summary assembled from orders and execution events.",
    },
}

TRADING_CORE_RELATIONSHIPS: tuple[dict[str, str], ...] = (
    {
        "from_entity": "Order",
        "to_entity": "ExecutionEvent",
        "cardinality": "1:n",
        "link_field": "order_id",
        "description": "ExecutionEvent.order_id references Order.order_id.",
    },
    {
        "from_entity": "Position",
        "to_entity": "Order",
        "cardinality": "1:n",
        "link_field": "position_id",
        "description": "Order.position_id references Position.position_id when the order affects the position.",
    },
    {
        "from_entity": "Trade",
        "to_entity": "Position",
        "cardinality": "n:1",
        "link_field": "position_id",
        "description": "Trade.position_id references the derived position the trade belongs to.",
    },
    {
        "from_entity": "Trade",
        "to_entity": "ExecutionEvent",
        "cardinality": "1:n",
        "link_field": "execution_event_ids",
        "description": "Trade.execution_event_ids records the execution events that formed the trade lifecycle.",
    },
)


class EntryZone(TypedDict):
    from_: float
    to: float


class RuleRef(TypedDict):
    rule_id: str
    rule_version: str


ReasonValue = Union[float, int, str, bool]


class DataRef(TypedDict):
    data_type: DataType
    data_id: str
    value: ReasonValue
    timestamp: str


class SignalReason(TypedDict):
    """Order by (ordering_key asc, reason_id asc) for canonical sequences."""

    reason_id: str
    reason_type: ReasonType
    signal_id: str
    rule_ref: RuleRef
    data_refs: List[DataRef]
    ordering_key: int


class Signal(TypedDict, total=False):
    """Unified signal model for the existing MVP surface."""

    signal_id: str
    analysis_run_id: str
    ingestion_run_id: str
    symbol: str
    strategy: str
    direction: Direction
    score: float
    timestamp: str
    stage: Stage
    entry_zone: Optional[EntryZone]
    confirmation_rule: str
    timeframe: str
    market_type: MarketType
    data_source: DataSource
    reasons: Optional[List[SignalReason]]


class PersistedTradePayload(TypedDict, total=False):
    """Legacy persisted trade payload used by current paper-trading surfaces."""

    id: int
    symbol: str
    strategy: str
    stage: Stage
    entry_price: Optional[float]
    entry_date: Optional[str]
    exit_price: Optional[float]
    exit_date: Optional[str]
    reason_entry: str
    reason_exit: Optional[str]
    notes: Optional[str]
    timeframe: str
    market_type: MarketType
    data_source: DataSource


def _normalize_assets(value: Any) -> list[str]:
    if not isinstance(value, (list, tuple)):
        raise TypeError("assets must be a list or tuple")

    normalized = []
    for item in value:
        if not isinstance(item, str):
            raise TypeError("assets list items must be strings")
        normalized.append(item.strip().upper())

    return sorted(normalized)


def _normalize_decimal(value: Decimal) -> str:
    normalized = format(value.normalize(), "f")
    if "." in normalized:
        normalized = normalized.rstrip("0").rstrip(".")
    if normalized in {"", "-0"}:
        return "0"
    return normalized


def _normalize_identifier_list(value: Any) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, (list, tuple)):
        raise TypeError("identifier collections must be a list or tuple")

    normalized: list[str] = []
    for item in value:
        if not isinstance(item, str):
            raise TypeError("identifier collections must contain strings")
        identifier = item.strip()
        if not identifier:
            raise ValueError("identifier collections must not contain empty strings")
        normalized.append(identifier)

    if len(set(normalized)) != len(normalized):
        raise ValueError("identifier collections must not contain duplicates")

    return sorted(normalized)


def _normalize_canonical_value(value: Any, *, key: Optional[str] = None) -> Any:
    if isinstance(value, float):
        raise TypeError("floats are not supported in canonical_json")

    if isinstance(value, Decimal):
        return _normalize_decimal(value)

    if value is None or isinstance(value, (bool, int, str)):
        return value

    if isinstance(value, TradingCoreBase):
        return value.to_canonical_payload()

    if isinstance(value, Mapping):
        normalized_dict: Dict[str, Any] = {}
        for raw_key, raw_value in value.items():
            if not isinstance(raw_key, str):
                raise TypeError("dict keys must be strings")
            normalized_dict[raw_key] = _normalize_canonical_value(raw_value, key=raw_key)
        return normalized_dict

    if isinstance(value, (list, tuple)):
        if key == "assets":
            return _normalize_assets(value)
        return [_normalize_canonical_value(item) for item in value]

    raise TypeError(f"unsupported type for canonical_json: {type(value).__name__}")


def canonical_json(obj: Any) -> str:
    """Create a deterministic JSON representation of the provided object."""

    normalized = _normalize_canonical_value(obj)
    return json.dumps(
        normalized,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def sha256_hex(text: str) -> str:
    """Return a SHA-256 hex digest for the provided text."""

    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class TradingCoreBase(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    def to_canonical_payload(self) -> dict[str, Any]:
        payload = self.model_dump(mode="python")
        return {
            key: _normalize_canonical_value(value, key=key)
            for key, value in payload.items()
        }

    def to_canonical_json(self) -> str:
        return canonical_json(self.to_canonical_payload())


class CanonicalOrder(TradingCoreBase):
    order_id: str = Field(min_length=1)
    strategy_id: str = Field(min_length=1)
    symbol: str = Field(min_length=1)
    sequence: int = Field(ge=1)
    side: OrderSide
    order_type: OrderType
    time_in_force: TimeInForce
    status: OrderStatus
    quantity: Decimal = Field(gt=Decimal("0"))
    filled_quantity: Decimal = Field(default=Decimal("0"), ge=Decimal("0"))
    created_at: str = Field(min_length=1)
    submitted_at: Optional[str] = None
    average_fill_price: Optional[Decimal] = Field(default=None, gt=Decimal("0"))
    last_execution_event_id: Optional[str] = Field(default=None, min_length=1)
    position_id: Optional[str] = Field(default=None, min_length=1)
    trade_id: Optional[str] = Field(default=None, min_length=1)

    @model_validator(mode="after")
    def _validate_lifecycle(self) -> "CanonicalOrder":
        if self.filled_quantity > self.quantity:
            raise ValueError("filled_quantity must not exceed quantity")

        if self.status in {"partially_filled", "filled"}:
            if self.average_fill_price is None:
                raise ValueError("average_fill_price is required for filled orders")
            if self.last_execution_event_id is None:
                raise ValueError("last_execution_event_id is required for filled orders")
        elif self.filled_quantity != Decimal("0"):
            raise ValueError("filled_quantity must be zero unless status is partially_filled or filled")

        if self.status == "filled" and self.filled_quantity != self.quantity:
            raise ValueError("filled orders must have filled_quantity equal to quantity")

        if self.status == "partially_filled" and self.filled_quantity >= self.quantity:
            raise ValueError("partially_filled orders must have filled_quantity less than quantity")

        return self


class CanonicalExecutionEvent(TradingCoreBase):
    event_id: str = Field(min_length=1)
    order_id: str = Field(min_length=1)
    strategy_id: str = Field(min_length=1)
    symbol: str = Field(min_length=1)
    side: OrderSide
    event_type: ExecutionEventType
    occurred_at: str = Field(min_length=1)
    sequence: int = Field(ge=1)
    execution_quantity: Optional[Decimal] = Field(default=None, gt=Decimal("0"))
    execution_price: Optional[Decimal] = Field(default=None, gt=Decimal("0"))
    commission: Optional[Decimal] = Field(default=None, ge=Decimal("0"))
    position_id: Optional[str] = Field(default=None, min_length=1)
    trade_id: Optional[str] = Field(default=None, min_length=1)

    @model_validator(mode="after")
    def _validate_event_shape(self) -> "CanonicalExecutionEvent":
        requires_fill_payload = self.event_type in {"partially_filled", "filled"}
        if requires_fill_payload:
            if self.execution_quantity is None:
                raise ValueError("execution_quantity is required for fill events")
            if self.execution_price is None:
                raise ValueError("execution_price is required for fill events")
            if self.commission is None:
                raise ValueError("commission is required for fill events")
        elif any(
            value is not None
            for value in (self.execution_quantity, self.execution_price, self.commission)
        ):
            raise ValueError("non-fill events must not define execution payload fields")

        return self


class CanonicalPosition(TradingCoreBase):
    position_id: str = Field(min_length=1)
    strategy_id: str = Field(min_length=1)
    symbol: str = Field(min_length=1)
    direction: CoreDirection
    status: PositionStatus
    opened_at: str = Field(min_length=1)
    closed_at: Optional[str] = None
    quantity_opened: Decimal = Field(ge=Decimal("0"))
    quantity_closed: Decimal = Field(default=Decimal("0"), ge=Decimal("0"))
    net_quantity: Decimal
    average_entry_price: Decimal = Field(ge=Decimal("0"))
    average_exit_price: Optional[Decimal] = Field(default=None, gt=Decimal("0"))
    realized_pnl: Optional[Decimal] = None
    order_ids: List[str] = Field(default_factory=list)
    execution_event_ids: List[str] = Field(default_factory=list)
    trade_ids: List[str] = Field(default_factory=list)

    @field_validator("order_ids", "execution_event_ids", "trade_ids", mode="before")
    @classmethod
    def _normalize_id_fields(cls, value: Any) -> list[str]:
        return _normalize_identifier_list(value)

    @model_validator(mode="after")
    def _validate_position_state(self) -> "CanonicalPosition":
        expected_net = self.quantity_opened - self.quantity_closed
        if self.net_quantity != expected_net:
            raise ValueError("net_quantity must equal quantity_opened minus quantity_closed")
        if self.quantity_closed > self.quantity_opened:
            raise ValueError("quantity_closed must not exceed quantity_opened")

        if self.status == "flat":
            if any(
                value != Decimal("0")
                for value in (
                    self.quantity_opened,
                    self.quantity_closed,
                    self.net_quantity,
                    self.average_entry_price,
                )
            ):
                raise ValueError("flat positions must have zero quantities and zero average_entry_price")
            if self.closed_at is not None:
                raise ValueError("flat positions must not define closed_at")
        elif self.status == "open":
            if self.net_quantity <= Decimal("0"):
                raise ValueError("open positions must have positive net_quantity")
            if self.closed_at is not None:
                raise ValueError("open positions must not define closed_at")
        elif self.status == "closed":
            if self.net_quantity != Decimal("0"):
                raise ValueError("closed positions must have zero net_quantity")
            if self.closed_at is None:
                raise ValueError("closed positions must define closed_at")
            if self.realized_pnl is None:
                raise ValueError("closed positions must define realized_pnl")
            if self.quantity_opened != self.quantity_closed:
                raise ValueError("closed positions must have quantity_closed equal to quantity_opened")

        if self.quantity_closed > Decimal("0") and self.average_exit_price is None:
            raise ValueError("average_exit_price is required when quantity_closed is positive")

        return self


class CanonicalTrade(TradingCoreBase):
    trade_id: str = Field(min_length=1)
    position_id: str = Field(min_length=1)
    strategy_id: str = Field(min_length=1)
    symbol: str = Field(min_length=1)
    direction: CoreDirection
    status: TradeStatus
    opened_at: str = Field(min_length=1)
    closed_at: Optional[str] = None
    quantity_opened: Decimal = Field(gt=Decimal("0"))
    quantity_closed: Decimal = Field(default=Decimal("0"), ge=Decimal("0"))
    average_entry_price: Decimal = Field(gt=Decimal("0"))
    average_exit_price: Optional[Decimal] = Field(default=None, gt=Decimal("0"))
    realized_pnl: Optional[Decimal] = None
    opening_order_ids: List[str] = Field(default_factory=list)
    closing_order_ids: List[str] = Field(default_factory=list)
    execution_event_ids: List[str] = Field(default_factory=list)

    @field_validator("opening_order_ids", "closing_order_ids", "execution_event_ids", mode="before")
    @classmethod
    def _normalize_id_lists(cls, value: Any) -> list[str]:
        return _normalize_identifier_list(value)

    @model_validator(mode="after")
    def _validate_trade_state(self) -> "CanonicalTrade":
        if self.quantity_closed > self.quantity_opened:
            raise ValueError("quantity_closed must not exceed quantity_opened")

        if self.status == "open":
            if self.quantity_closed >= self.quantity_opened:
                raise ValueError("open trades must retain positive remaining quantity")
            if self.closed_at is not None:
                raise ValueError("open trades must not define closed_at")
        elif self.status == "closed":
            if self.quantity_closed != self.quantity_opened:
                raise ValueError("closed trades must have quantity_closed equal to quantity_opened")
            if self.closed_at is None:
                raise ValueError("closed trades must define closed_at")
            if self.average_exit_price is None:
                raise ValueError("closed trades must define average_exit_price")
            if self.realized_pnl is None:
                raise ValueError("closed trades must define realized_pnl")

        if self.quantity_closed > Decimal("0") and self.average_exit_price is None:
            raise ValueError("average_exit_price is required when quantity_closed is positive")

        return self


Order = CanonicalOrder
Position = CanonicalPosition
ExecutionEvent = CanonicalExecutionEvent
Trade = CanonicalTrade

TRADING_CORE_MODEL_TYPES: Dict[str, type[TradingCoreBase]] = {
    "order": Order,
    "position": Position,
    "execution_event": ExecutionEvent,
    "trade": Trade,
}


def _signal_identity_payload(signal: Mapping[str, Any]) -> Dict[str, Any]:
    payload: Dict[str, Any] = {}
    for key in (
        "symbol",
        "strategy",
        "timestamp",
        "timeframe",
        "market_type",
        "data_source",
        "direction",
        "stage",
        "assets",
    ):
        if key in signal:
            payload[key] = signal[key]
    return payload


def compute_signal_id(signal: Mapping[str, Any]) -> str:
    """Compute a deterministic signal ID."""

    return sha256_hex(canonical_json(_signal_identity_payload(signal)))


def compute_signal_reason_id(
    *,
    signal_id: str,
    reason_type: ReasonType,
    rule_ref: RuleRef,
    data_refs: List[DataRef],
) -> str:
    canonical_data_refs = sorted(
        data_refs,
        key=lambda data_ref: (
            data_ref["data_type"],
            data_ref["data_id"],
            data_ref["timestamp"],
            str(data_ref["value"]),
        ),
    )
    payload = {
        "signal_id": signal_id,
        "reason_type": reason_type,
        "rule_id": rule_ref["rule_id"],
        "rule_version": rule_ref["rule_version"],
        "data_refs": canonical_data_refs,
    }
    serialized = json.dumps(
        payload,
        separators=(",", ":"),
        sort_keys=True,
        ensure_ascii=False,
    )
    digest = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
    return f"sr_{digest}"


def compute_execution_event_id(
    *,
    order_id: str,
    event_type: ExecutionEventType,
    occurred_at: str,
    sequence: int,
) -> str:
    payload = {
        "order_id": order_id,
        "event_type": event_type,
        "occurred_at": occurred_at,
        "sequence": sequence,
    }
    return f"evt_{sha256_hex(canonical_json(payload))}"


def validate_trading_core_entity(entity_name: str, payload: Mapping[str, Any]) -> TradingCoreBase:
    model_type = TRADING_CORE_MODEL_TYPES.get(entity_name)
    if model_type is None:
        raise ValueError(f"unsupported trading core entity: {entity_name}")
    return model_type.model_validate(payload)


def serialize_trading_core_entity(entity: TradingCoreBase) -> str:
    return entity.to_canonical_json()


def validate_trading_core_relationships(
    *,
    trade: CanonicalTrade,
    position: CanonicalPosition,
    orders: List[CanonicalOrder],
    execution_events: List[CanonicalExecutionEvent],
) -> None:
    order_ids = {order.order_id for order in orders}
    event_ids = {event.event_id for event in execution_events}

    if trade.position_id != position.position_id:
        raise ValueError("trade.position_id must match position.position_id")

    if not set(trade.opening_order_ids).issubset(order_ids):
        raise ValueError("trade opening_order_ids must reference known orders")

    if not set(trade.closing_order_ids).issubset(order_ids):
        raise ValueError("trade closing_order_ids must reference known orders")

    if not set(trade.execution_event_ids).issubset(event_ids):
        raise ValueError("trade execution_event_ids must reference known execution events")

    if not set(position.order_ids).issubset(order_ids):
        raise ValueError("position order_ids must reference known orders")

    if not set(position.execution_event_ids).issubset(event_ids):
        raise ValueError("position execution_event_ids must reference known execution events")

    if trade.trade_id not in position.trade_ids:
        raise ValueError("position.trade_ids must include trade.trade_id")

    for order in orders:
        if order.position_id is not None and order.position_id != position.position_id:
            raise ValueError("order.position_id must match position.position_id")
        if order.trade_id is not None and order.trade_id != trade.trade_id:
            raise ValueError("order.trade_id must match trade.trade_id")

    for event in execution_events:
        if event.order_id not in order_ids:
            raise ValueError("execution_event.order_id must reference a known order")
        if event.position_id is not None and event.position_id != position.position_id:
            raise ValueError("execution_event.position_id must match position.position_id")
        if event.trade_id is not None and event.trade_id != trade.trade_id:
            raise ValueError("execution_event.trade_id must match trade.trade_id")


class EntryZoneDTO(BaseModel):
    from_: float = Field(..., alias="from_")
    to: float

    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class SignalReadItemDTO(BaseModel):
    symbol: str
    strategy: str
    direction: Direction
    score: float
    created_at: str
    stage: Stage
    entry_zone: Optional[EntryZoneDTO] = None
    confirmation_rule: Optional[str] = None
    timeframe: str
    market_type: MarketType
    data_source: DataSource

    model_config = ConfigDict(extra="forbid")


class SignalReadResponseDTO(BaseModel):
    items: List[SignalReadItemDTO]
    limit: int
    offset: int
    total: int

    model_config = ConfigDict(extra="forbid")

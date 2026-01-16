"""
Zentrale Datenmodelle für die Cilly Trading Engine.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List, Literal, Mapping, Optional, TypedDict, Union

from pydantic import BaseModel, ConfigDict, Field


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
    """
    Einheitliches Signalmodell gemäß MVP-Spezifikation.
    """
    symbol: str
    strategy: str
    direction: Direction
    score: float
    timestamp: str      # ISO-String
    stage: Stage        # "setup" | "entry_confirmed"
    entry_zone: Optional[EntryZone]
    confirmation_rule: str
    timeframe: str      # z. B. "D1"
    market_type: MarketType
    data_source: DataSource
    reasons: Optional[List[SignalReason]]


class Trade(TypedDict, total=False):
    """
    Minimales Trade-Modell für Papertrading und spätere Backtests.
    """
    id: int              # wird von DB vergeben
    symbol: str
    strategy: str
    stage: Stage
    entry_price: Optional[float]
    entry_date: Optional[str]   # ISO-String
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


def _normalize_canonical_value(value: Any, *, key: Optional[str] = None) -> Any:
    if isinstance(value, float):
        raise TypeError("floats are not supported in canonical_json")

    if value is None or isinstance(value, (bool, int, str)):
        return value

    if isinstance(value, dict):
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
    """Create a deterministic JSON representation of the provided object.

    Args:
        obj: Object to serialize into deterministic JSON.

    Returns:
        Canonical JSON string.
    """
    normalized = _normalize_canonical_value(obj)
    return json.dumps(
        normalized,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def sha256_hex(text: str) -> str:
    """Return a SHA-256 hex digest for the provided text.

    Args:
        text: String to hash.

    Returns:
        SHA-256 hex digest.
    """
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


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
    """Compute a deterministic signal ID.

    Args:
        signal: Signal payload used to compute the ID.

    Returns:
        Deterministic signal ID.
    """
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

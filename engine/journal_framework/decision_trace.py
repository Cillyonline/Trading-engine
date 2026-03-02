"""Deterministic decision trace primitives and generation logic."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from types import MappingProxyType
from typing import Any, Mapping



def _deep_freeze(value: Any) -> Any:
    """Create an immutable representation for nested containers.

    Args:
        value: Arbitrary JSON-compatible or container value.

    Returns:
        Immutable representation of input value.
    """

    if isinstance(value, Mapping):
        frozen = {key: _deep_freeze(value[key]) for key in sorted(value)}
        return MappingProxyType(frozen)
    if isinstance(value, list):
        return tuple(_deep_freeze(item) for item in value)
    if isinstance(value, tuple):
        return tuple(_deep_freeze(item) for item in value)
    return value


@dataclass(frozen=True)
class PortfolioDecisionSnapshot:
    """Immutable snapshot of strategy decision inputs.

    Attributes:
        strategy_id: Stable strategy identifier.
        symbol: Traded symbol.
        signal: Strategy signal label.
        confidence: Optional confidence scalar.
        allocation: Optional target allocation scalar.
        inputs: Deterministic input values used for the decision.
    """

    strategy_id: str
    symbol: str
    signal: str
    confidence: float | None
    allocation: float | None
    inputs: Mapping[str, Any]

    def __post_init__(self) -> None:
        object.__setattr__(self, "inputs", _deep_freeze(self.inputs))


@dataclass(frozen=True)
class DecisionTrace:
    """Immutable deterministic trace of a portfolio decision.

    Attributes:
        trace_id: SHA256 digest of canonical trace input.
        snapshot: Decision snapshot captured at decision time.
        decision_context: Additional deterministic context payload.
    """

    trace_id: str
    snapshot: PortfolioDecisionSnapshot
    decision_context: Mapping[str, Any]

    def __post_init__(self) -> None:
        object.__setattr__(self, "decision_context", _deep_freeze(self.decision_context))



def _canonicalize(value: Any) -> Any:
    """Convert nested structures into deterministically serializable values.

    Args:
        value: Arbitrary JSON-compatible or container value.

    Returns:
        Canonical representation with sorted mapping keys.
    """

    if isinstance(value, Mapping):
        return {key: _canonicalize(value[key]) for key in sorted(value)}
    if isinstance(value, tuple):
        return [_canonicalize(item) for item in value]
    if isinstance(value, list):
        return [_canonicalize(item) for item in value]
    return value



def generate_decision_trace(
    snapshot: PortfolioDecisionSnapshot,
    decision_context: Mapping[str, Any] | None = None,
) -> DecisionTrace:
    """Create a deterministic, side-effect free decision trace.

    Args:
        snapshot: Immutable strategy decision snapshot.
        decision_context: Optional deterministic context values.

    Returns:
        DecisionTrace with deterministic SHA256 trace id.
    """

    context_payload: Mapping[str, Any] = _deep_freeze(decision_context or {})
    payload = {
        "snapshot": {
            "strategy_id": snapshot.strategy_id,
            "symbol": snapshot.symbol,
            "signal": snapshot.signal,
            "confidence": snapshot.confidence,
            "allocation": snapshot.allocation,
            "inputs": _canonicalize(snapshot.inputs),
        },
        "decision_context": _canonicalize(context_payload),
    }
    serialized = json.dumps(payload, separators=(",", ":"), sort_keys=True, ensure_ascii=True)
    trace_id = sha256(serialized.encode("utf-8")).hexdigest()
    return DecisionTrace(trace_id=trace_id, snapshot=snapshot, decision_context=context_payload)

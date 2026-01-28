"""Guardrails for Phase-6 deterministic, read-only market data adapters."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

FORBIDDEN_TOKENS = (
    "engine.execution",
    "engine.orders",
    "engine.broker",
    "engine.strategy",
    "place_order",
    "submit_order",
    "execute_order",
    "websocket",
    "websockets",
    "subscribe",
    "listener",
    "async def",
    "await ",
    "asyncio",
    "time.time",
    "time.time_ns",
    "time.perf_counter",
    "time.sleep",
    "datetime.now",
    "datetime.utcnow",
)


@dataclass(frozen=True)
class GuardrailViolation:
    token: str
    message: str


class GuardrailError(RuntimeError):
    """Raised when a Phase-6 guardrail is violated."""


def find_forbidden_tokens(source: str, tokens: Iterable[str] = FORBIDDEN_TOKENS) -> list[GuardrailViolation]:
    """Return forbidden token matches found in the provided source."""

    violations: list[GuardrailViolation] = []
    for token in tokens:
        if token in source:
            violations.append(
                GuardrailViolation(
                    token=token,
                    message=f"Forbidden token detected: {token}",
                )
            )
    return violations


def assert_no_forbidden_references(source: str, *, origin: str) -> None:
    """Raise if forbidden tokens appear in the provided source."""

    violations = find_forbidden_tokens(source)
    if violations:
        messages = ", ".join(v.token for v in violations)
        raise GuardrailError(f"Guardrail violation in {origin}: {messages}")


def assert_adapter_guardrails(adapter_path: Path) -> None:
    """Enforce Phase-6 guardrails for adapter implementations."""

    source = adapter_path.read_text(encoding="utf-8")
    assert_no_forbidden_references(source, origin=str(adapter_path))

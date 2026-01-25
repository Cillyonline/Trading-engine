from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Iterable, List, Sequence


PRECISION_PLACES = 4
PRECISION_EPSILON = Decimal("1e-9")


@dataclass(frozen=True)
class NumericViolation:
    path: str
    value: float
    rounded: str
    delta: str


def _decimal_quantize(value: float) -> tuple[Decimal, Decimal]:
    raw = Decimal(str(value))
    quantum = Decimal(f"1.{('0' * PRECISION_PLACES)}")
    rounded = raw.quantize(quantum, rounding=ROUND_HALF_UP)
    return raw, rounded


def _format_path(path: Sequence[str | int]) -> str:
    rendered: List[str] = []
    for part in path:
        if isinstance(part, int):
            rendered.append(f"[{part}]")
        else:
            rendered.append(f".{part}" if rendered else str(part))
    return "".join(rendered)


def _collect_paths(value: Any, *, prefix: Sequence[str | int] = ()) -> Iterable[tuple[Sequence[str | int], Any]]:
    if isinstance(value, dict):
        for key, child in value.items():
            yield from _collect_paths(child, prefix=(*prefix, key))
        return
    if isinstance(value, list):
        for idx, child in enumerate(value):
            yield from _collect_paths(child, prefix=(*prefix, idx))
        return
    yield prefix, value


def find_numeric_precision_violations(payload: Any) -> List[NumericViolation]:
    violations: List[NumericViolation] = []
    for path, value in _collect_paths(payload):
        if isinstance(value, bool):
            continue
        if isinstance(value, float):
            raw, rounded = _decimal_quantize(value)
            delta = abs(raw - rounded)
            if delta > PRECISION_EPSILON:
                violations.append(
                    NumericViolation(
                        path=_format_path(path),
                        value=value,
                        rounded=str(rounded),
                        delta=str(delta),
                    )
                )
    return violations

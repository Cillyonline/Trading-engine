from __future__ import annotations

from decimal import Decimal, ROUND_HALF_EVEN
import json
from pathlib import Path
from typing import Any, Mapping


METRICS_ARTIFACT_FILENAME = "metrics-result.json"
METRICS_SCHEMA_VERSION = "1.0.0"
METRIC_KEYS = (
    "total_return",
    "cagr",
    "max_drawdown",
    "sharpe_ratio",
    "win_rate",
    "profit_factor",
)
_QUANT = Decimal("0.000000000001")


def _normalize_float(value: float) -> float:
    rounded = float(Decimal(str(value)).quantize(_QUANT, rounding=ROUND_HALF_EVEN))
    if rounded == 0.0:
        return 0.0
    return rounded


def _normalize_for_json(value: Any) -> Any:
    if isinstance(value, bool) or value is None or isinstance(value, str):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return _normalize_float(value)
    if isinstance(value, Mapping):
        return {str(key): _normalize_for_json(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_normalize_for_json(item) for item in value]
    if isinstance(value, tuple):
        return [_normalize_for_json(item) for item in value]
    return value


def canonical_json_bytes(obj: Any) -> bytes:
    normalized = _normalize_for_json(obj)
    serialized = json.dumps(
        normalized,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )
    return (serialized + "\n").encode("utf-8")


def build_metrics_artifact(metrics: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": METRICS_SCHEMA_VERSION,
        **{key: metrics.get(key) for key in METRIC_KEYS},
    }


def write_metrics_artifact(metrics: Mapping[str, Any], output_dir: str | Path) -> Path:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    artifact = build_metrics_artifact(metrics)
    artifact_path = output_path / METRICS_ARTIFACT_FILENAME
    artifact_path.write_bytes(canonical_json_bytes(artifact))
    return artifact_path

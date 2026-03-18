from __future__ import annotations

import hashlib
import json
from decimal import Decimal, ROUND_HALF_EVEN
from pathlib import Path
from typing import Any, Mapping

_QUANT = Decimal("0.000000000001")
_ZERO = Decimal("0")


def _to_decimal(value: object) -> Decimal | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, Decimal):
        number = value
    elif isinstance(value, (int, float, str)):
        try:
            number = Decimal(str(value))
        except Exception:
            return None
    else:
        return None

    if not number.is_finite():
        return None
    return number


def _round_12(value: Decimal) -> Decimal:
    rounded = value.quantize(_QUANT, rounding=ROUND_HALF_EVEN)
    if rounded == _ZERO:
        return _ZERO
    return rounded


def _to_float(value: Decimal | None) -> float | None:
    if value is None:
        return None
    return float(_round_12(value))


def _trade_sort_key(item: tuple[int, Mapping[str, object]]) -> tuple[str, str, str, str, str, int]:
    index, trade = item
    return (
        str(trade.get("exit_timestamp") or ""),
        str(trade.get("entry_timestamp") or ""),
        str(trade.get("symbol") or ""),
        str(trade.get("strategy_id") or ""),
        str(trade.get("trade_id") or ""),
        index,
    )


def _ordered_trades(payload: Mapping[str, Any]) -> list[Mapping[str, object]]:
    trades_raw = payload.get("trades")
    if not isinstance(trades_raw, list):
        return []
    ordered = sorted(
        [(index, trade) for index, trade in enumerate(trades_raw) if isinstance(trade, Mapping)],
        key=_trade_sort_key,
    )
    return [trade for _, trade in ordered]


def build_equity_curve_from_trade_ledger(payload: Mapping[str, Any]) -> dict[str, object]:
    ordered_trades = _ordered_trades(payload)

    curve_points: list[dict[str, object]] = []
    equity = _ZERO

    for trade in ordered_trades:
        pnl = _to_decimal(trade.get("pnl"))
        if pnl is None:
            continue

        equity += pnl
        curve_points.append(
            {
                "timestamp": str(trade.get("exit_timestamp") or ""),
                "equity": _to_float(equity),
            }
        )

    if not curve_points:
        return {
            "artifact": "equity_curve",
            "artifact_version": "1",
            "equity_curve": [],
            "drawdown_stats": {
                "max_drawdown": None,
                "recovery_time_steps": None,
                "drawdown_distribution": [],
            },
        }

    peak_equity = _to_decimal(curve_points[0]["equity"]) or _ZERO
    peak_timestamp = str(curve_points[0]["timestamp"])
    trough_equity = peak_equity
    trough_timestamp = peak_timestamp
    trough_index = 0
    in_drawdown = False

    max_drawdown = _ZERO
    best_recovery_steps: int | None = None
    drawdown_distribution: list[dict[str, object]] = []

    for index, point in enumerate(curve_points):
        equity_value = _to_decimal(point["equity"])
        if equity_value is None:
            continue
        timestamp = str(point["timestamp"])

        if equity_value > peak_equity:
            if in_drawdown:
                recovery_steps = index - trough_index
                drawdown_distribution.append(
                    {
                        "peak_timestamp": peak_timestamp,
                        "trough_timestamp": trough_timestamp,
                        "recovery_timestamp": timestamp,
                        "drawdown": _to_float(
                            ((peak_equity - trough_equity) / abs(peak_equity)) if peak_equity != _ZERO else _ZERO
                        ),
                        "recovery_time_steps": recovery_steps,
                    }
                )
                if best_recovery_steps is None or recovery_steps < best_recovery_steps:
                    best_recovery_steps = recovery_steps
                in_drawdown = False

            peak_equity = equity_value
            peak_timestamp = timestamp
            trough_equity = equity_value
            trough_timestamp = timestamp
            trough_index = index
            continue

        drawdown = ((peak_equity - equity_value) / abs(peak_equity)) if peak_equity != _ZERO else _ZERO
        if drawdown > max_drawdown:
            max_drawdown = drawdown

        if equity_value < peak_equity:
            if not in_drawdown:
                in_drawdown = True
                trough_equity = equity_value
                trough_timestamp = timestamp
                trough_index = index
            elif equity_value < trough_equity:
                trough_equity = equity_value
                trough_timestamp = timestamp
                trough_index = index

    if in_drawdown:
        drawdown_distribution.append(
            {
                "peak_timestamp": peak_timestamp,
                "trough_timestamp": trough_timestamp,
                "recovery_timestamp": None,
                "drawdown": _to_float(((peak_equity - trough_equity) / abs(peak_equity)) if peak_equity != _ZERO else _ZERO),
                "recovery_time_steps": None,
            }
        )

    return {
        "artifact": "equity_curve",
        "artifact_version": "1",
        "equity_curve": curve_points,
        "drawdown_stats": {
            "max_drawdown": _to_float(max_drawdown),
            "recovery_time_steps": best_recovery_steps,
            "drawdown_distribution": drawdown_distribution,
        },
    }


def canonical_equity_curve_json_bytes(payload: Mapping[str, Any]) -> bytes:
    rendered = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    return (rendered + "\n").encode("utf-8")


def write_equity_curve_artifact(output_dir: Path, payload: Mapping[str, Any]) -> tuple[Path, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    artifact_path = output_dir / "equity-curve.json"

    canonical_bytes = canonical_equity_curve_json_bytes(payload)
    artifact_path.write_bytes(canonical_bytes)

    sha_value = hashlib.sha256(canonical_bytes).hexdigest()
    (output_dir / "equity-curve.sha256").write_text(f"{sha_value}\n", encoding="utf-8")
    return artifact_path, sha_value


def load_equity_curve_artifact(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("equity curve payload must be an object")

    equity_curve = payload.get("equity_curve")
    if not isinstance(equity_curve, list):
        raise ValueError("equity curve missing equity_curve list")

    drawdown_stats = payload.get("drawdown_stats")
    if not isinstance(drawdown_stats, dict):
        raise ValueError("equity curve missing drawdown_stats object")

    if "max_drawdown" not in drawdown_stats:
        raise ValueError("equity curve drawdown_stats missing max_drawdown")
    if "recovery_time_steps" not in drawdown_stats:
        raise ValueError("equity curve drawdown_stats missing recovery_time_steps")
    distribution = drawdown_stats.get("drawdown_distribution")
    if not isinstance(distribution, list):
        raise ValueError("equity curve drawdown_stats missing drawdown_distribution list")

    return payload


__all__ = [
    "build_equity_curve_from_trade_ledger",
    "canonical_equity_curve_json_bytes",
    "write_equity_curve_artifact",
    "load_equity_curve_artifact",
]

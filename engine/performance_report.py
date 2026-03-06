from __future__ import annotations

import hashlib
import json
from decimal import Decimal, ROUND_HALF_EVEN
from pathlib import Path
from typing import Any, Mapping, Sequence

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


def build_performance_report_from_trade_ledger(payload: Mapping[str, Any]) -> dict[str, object]:
    """Build deterministic performance report from a post-trade ledger payload."""
    ordered_trades = _ordered_trades(payload)

    strategy_stats: dict[str, dict[str, Decimal | int]] = {}
    total_pnl = _ZERO
    total_holding_seconds = _ZERO
    wins = 0
    losses = 0
    breakeven = 0

    for trade in ordered_trades:
        strategy_id = str(trade.get("strategy_id") or "")
        pnl = _to_decimal(trade.get("pnl"))
        if pnl is None:
            continue

        holding_time_raw = _to_decimal(trade.get("holding_time"))
        holding_time = holding_time_raw if holding_time_raw is not None else _ZERO

        strategy = strategy_stats.setdefault(
            strategy_id,
            {
                "trade_count": 0,
                "total_pnl": _ZERO,
                "wins": 0,
            },
        )

        strategy["trade_count"] = int(strategy["trade_count"]) + 1
        strategy["total_pnl"] = (strategy["total_pnl"] if isinstance(strategy["total_pnl"], Decimal) else _ZERO) + pnl
        if pnl > _ZERO:
            strategy["wins"] = int(strategy["wins"]) + 1
            wins += 1
        elif pnl < _ZERO:
            losses += 1
        else:
            breakeven += 1

        total_pnl += pnl
        total_holding_seconds += holding_time

    total_trades = wins + losses + breakeven
    strategy_count = len(strategy_stats)

    strategy_comparison_raw: list[dict[str, object]] = []
    for strategy_id, values in strategy_stats.items():
        trade_count = int(values["trade_count"])
        strategy_total_pnl = values["total_pnl"] if isinstance(values["total_pnl"], Decimal) else _ZERO
        strategy_wins = int(values["wins"])

        average_pnl = (strategy_total_pnl / Decimal(trade_count)) if trade_count > 0 else None
        win_rate = (Decimal(strategy_wins) / Decimal(trade_count)) if trade_count > 0 else None

        strategy_comparison_raw.append(
            {
                "strategy_id": strategy_id,
                "trade_count": trade_count,
                "total_pnl": _to_float(strategy_total_pnl),
                "average_pnl": _to_float(average_pnl),
                "win_rate": _to_float(win_rate),
            }
        )

    strategy_comparison = sorted(
        strategy_comparison_raw,
        key=lambda item: (
            -float(item["total_pnl"] if item["total_pnl"] is not None else 0.0),
            str(item["strategy_id"]),
        ),
    )

    average_pnl_per_trade = (total_pnl / Decimal(total_trades)) if total_trades > 0 else None
    overall_win_rate = (Decimal(wins) / Decimal(total_trades)) if total_trades > 0 else None
    average_holding_time = (total_holding_seconds / Decimal(total_trades)) if total_trades > 0 else None

    best_strategy_id = strategy_comparison[0]["strategy_id"] if strategy_comparison else None
    worst_strategy_id = strategy_comparison[-1]["strategy_id"] if strategy_comparison else None

    risk_adjusted_metrics_raw = payload.get("risk_adjusted_metrics")
    risk_adjusted_metrics = risk_adjusted_metrics_raw if isinstance(risk_adjusted_metrics_raw, Mapping) else None

    return {
        "artifact": "performance_report",
        "artifact_version": "1",
        "performance_summary": {
            "total_trades": total_trades,
            "strategies_analyzed": strategy_count,
            "total_pnl": _to_float(total_pnl),
            "winning_trades": wins,
            "losing_trades": losses,
            "breakeven_trades": breakeven,
        },
        "strategy_comparison": strategy_comparison,
        "key_metrics_overview": {
            "overall_win_rate": _to_float(overall_win_rate),
            "average_pnl_per_trade": _to_float(average_pnl_per_trade),
            "average_holding_time_seconds": _to_float(average_holding_time),
            "best_strategy_id": best_strategy_id,
            "worst_strategy_id": worst_strategy_id,
            "risk_adjusted_metrics": risk_adjusted_metrics,
        },
    }


def canonical_performance_report_json_bytes(payload: Mapping[str, Any]) -> bytes:
    rendered = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    return (rendered + "\n").encode("utf-8")


def write_performance_report_artifact(output_dir: Path, payload: Mapping[str, Any]) -> tuple[Path, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    artifact_path = output_dir / "performance-report.json"

    canonical_bytes = canonical_performance_report_json_bytes(payload)
    artifact_path.write_bytes(canonical_bytes)

    sha_value = hashlib.sha256(canonical_bytes).hexdigest()
    (output_dir / "performance-report.sha256").write_text(f"{sha_value}\n", encoding="utf-8")
    return artifact_path, sha_value


def load_performance_report_artifact(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("performance report payload must be an object")

    summary = payload.get("performance_summary")
    if not isinstance(summary, dict):
        raise ValueError("performance report missing performance_summary object")

    strategy_comparison = payload.get("strategy_comparison")
    if not isinstance(strategy_comparison, list):
        raise ValueError("performance report missing strategy_comparison list")

    for row in strategy_comparison:
        if not isinstance(row, dict):
            raise ValueError("strategy comparison entry must be an object")
        required = {"strategy_id", "trade_count", "total_pnl", "average_pnl", "win_rate"}
        missing = required.difference(row.keys())
        if missing:
            raise ValueError(f"strategy comparison entry missing fields: {sorted(missing)}")

    key_metrics = payload.get("key_metrics_overview")
    if not isinstance(key_metrics, dict):
        raise ValueError("performance report missing key_metrics_overview object")

    return payload


__all__ = [
    "build_performance_report_from_trade_ledger",
    "canonical_performance_report_json_bytes",
    "write_performance_report_artifact",
    "load_performance_report_artifact",
]

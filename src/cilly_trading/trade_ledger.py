from __future__ import annotations

import hashlib
import json
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any, Mapping, Sequence

from cilly_trading.performance_report import (
    build_performance_report_from_trade_ledger,
    write_performance_report_artifact,
)
from cilly_trading.equity_curve import build_equity_curve_from_trade_ledger, write_equity_curve_artifact
from cilly_trading.risk_adjusted_metrics import compute_risk_adjusted_metrics_from_trade_ledger
from cilly_trading.trade_attribution import build_trade_attribution

_PRICE_QUANTIZER = Decimal("0.0001")


def _to_decimal(value: object) -> Decimal:
    if isinstance(value, Decimal):
        number = value
    elif isinstance(value, (int, float, str)):
        number = Decimal(str(value))
    else:
        raise ValueError(f"unsupported numeric value: {value!r}")
    return number.quantize(_PRICE_QUANTIZER, rounding=ROUND_HALF_UP)


def _to_utc_datetime(timestamp: str) -> datetime:
    # Simulator timestamps are ISO-8601 with trailing Z.
    return datetime.fromisoformat(timestamp.replace("Z", "+00:00"))


def _format_decimal(value: Decimal) -> str:
    return str(value.quantize(_PRICE_QUANTIZER, rounding=ROUND_HALF_UP))


def _build_trade_id(
    *,
    strategy_id: str,
    symbol: str,
    entry_timestamp: str,
    exit_timestamp: str,
    entry_price: str,
    exit_price: str,
    quantity: str,
) -> str:
    digest_input = "|".join(
        [
            strategy_id,
            symbol,
            entry_timestamp,
            exit_timestamp,
            entry_price,
            exit_price,
            quantity,
        ]
    )
    digest = hashlib.sha256(digest_input.encode("utf-8")).hexdigest()[:16]
    return f"trade-{digest}"


def build_trade_ledger_from_paper_trades(
    trades: Sequence[Mapping[str, object]],
    *,
    signals: Sequence[Mapping[str, object]] | None = None,
) -> dict[str, object]:
    """Build canonical deterministic ledger from paper-trading trades."""
    ledger_trades: list[dict[str, object]] = []

    for index, trade in enumerate(trades):
        symbol = str(trade.get("symbol") or "")
        if symbol == "__SUMMARY__":
            continue

        entry_timestamp = trade.get("entry_date")
        exit_timestamp = trade.get("exit_date")
        entry_price_raw = trade.get("entry_price")
        exit_price_raw = trade.get("exit_price")

        if not isinstance(entry_timestamp, str) or not isinstance(exit_timestamp, str):
            continue

        if entry_price_raw is None or exit_price_raw is None:
            continue

        quantity_raw = trade.get("quantity", 1)
        quantity_decimal = _to_decimal(quantity_raw)
        entry_price_decimal = _to_decimal(entry_price_raw)
        exit_price_decimal = _to_decimal(exit_price_raw)

        pnl = (exit_price_decimal - entry_price_decimal) * quantity_decimal
        pnl = pnl.quantize(_PRICE_QUANTIZER, rounding=ROUND_HALF_UP)

        holding_seconds = int((_to_utc_datetime(exit_timestamp) - _to_utc_datetime(entry_timestamp)).total_seconds())

        strategy_id = str(trade.get("strategy") or "")
        quantity_value = _format_decimal(quantity_decimal)
        entry_price_value = _format_decimal(entry_price_decimal)
        exit_price_value = _format_decimal(exit_price_decimal)

        ledger_trades.append(
            {
                "_index": index,
                "trade_id": _build_trade_id(
                    strategy_id=strategy_id,
                    symbol=symbol,
                    entry_timestamp=entry_timestamp,
                    exit_timestamp=exit_timestamp,
                    entry_price=entry_price_value,
                    exit_price=exit_price_value,
                    quantity=quantity_value,
                ),
                "strategy_id": strategy_id,
                "symbol": symbol,
                "entry_timestamp": entry_timestamp,
                "exit_timestamp": exit_timestamp,
                "entry_price": entry_price_value,
                "exit_price": exit_price_value,
                "quantity": quantity_value,
                "pnl": _format_decimal(pnl),
                "holding_time": holding_seconds,
            }
        )

    ledger_trades_sorted = sorted(
        ledger_trades,
        key=lambda item: (
            str(item["exit_timestamp"]),
            str(item["entry_timestamp"]),
            str(item["symbol"]),
            str(item["strategy_id"]),
            int(item["_index"]),
        ),
    )

    canonical_trades: list[dict[str, object]] = []
    for item in ledger_trades_sorted:
        canonical_trades.append(
            {
                "trade_id": item["trade_id"],
                "strategy_id": item["strategy_id"],
                "symbol": item["symbol"],
                "entry_timestamp": item["entry_timestamp"],
                "exit_timestamp": item["exit_timestamp"],
                "entry_price": item["entry_price"],
                "exit_price": item["exit_price"],
                "quantity": item["quantity"],
                "pnl": item["pnl"],
                "holding_time": item["holding_time"],
            }
        )

    payload: dict[str, object] = {
        "artifact": "trade_ledger",
        "artifact_version": "1",
        "trades": canonical_trades,
    }
    payload["risk_adjusted_metrics"] = compute_risk_adjusted_metrics_from_trade_ledger(payload)
    payload["performance_report"] = build_performance_report_from_trade_ledger(payload)
    payload["equity_curve_analysis"] = build_equity_curve_from_trade_ledger(payload)
    if signals is not None:
        attribution_payload = build_trade_attribution(trades=trades, signals=signals)
        payload["attributions"] = attribution_payload["attributions"]
    return payload


def canonical_trade_ledger_json_bytes(payload: Mapping[str, Any]) -> bytes:
    rendered = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return (rendered + "\n").encode("utf-8")


def write_trade_ledger_artifact(output_dir: Path, payload: Mapping[str, Any]) -> tuple[Path, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    artifact_path = output_dir / "trade-ledger.json"
    canonical_bytes = canonical_trade_ledger_json_bytes(payload)
    artifact_path.write_bytes(canonical_bytes)

    sha_value = hashlib.sha256(canonical_bytes).hexdigest()
    (output_dir / "trade-ledger.sha256").write_text(f"{sha_value}\n", encoding="utf-8")

    performance_report = payload.get("performance_report")
    if isinstance(performance_report, Mapping):
        write_performance_report_artifact(output_dir, performance_report)

    equity_curve_analysis = payload.get("equity_curve_analysis")
    if isinstance(equity_curve_analysis, Mapping):
        write_equity_curve_artifact(output_dir, equity_curve_analysis)

    return artifact_path, sha_value


def load_trade_ledger_artifact(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("trade ledger payload must be an object")

    trades = payload.get("trades")
    if not isinstance(trades, list):
        raise ValueError("trade ledger payload missing trades list")

    required_fields = {
        "trade_id",
        "strategy_id",
        "symbol",
        "entry_timestamp",
        "exit_timestamp",
        "entry_price",
        "exit_price",
        "quantity",
        "pnl",
        "holding_time",
    }
    for trade in trades:
        if not isinstance(trade, dict):
            raise ValueError("trade ledger trade entry must be an object")
        missing = required_fields.difference(trade.keys())
        if missing:
            raise ValueError(f"trade ledger entry missing fields: {sorted(missing)}")

    attributions = payload.get("attributions")
    if attributions is not None:
        if not isinstance(attributions, list):
            raise ValueError("trade ledger attributions must be a list")
        for attribution in attributions:
            if not isinstance(attribution, dict):
                raise ValueError("trade ledger attribution entry must be an object")
            for field in ("trade_ref", "strategy_id", "originating_signal", "market_context"):
                if field not in attribution:
                    raise ValueError(f"trade ledger attribution missing field: {field}")

    risk_adjusted_metrics = payload.get("risk_adjusted_metrics")
    if risk_adjusted_metrics is not None:
        if not isinstance(risk_adjusted_metrics, dict):
            raise ValueError("trade ledger risk_adjusted_metrics must be an object when present")
        required_metric_fields = {
            "sharpe_ratio",
            "sortino_ratio",
            "calmar_ratio",
            "profit_factor",
            "win_rate",
        }
        missing_metric_fields = required_metric_fields.difference(risk_adjusted_metrics.keys())
        if missing_metric_fields:
            raise ValueError(f"trade ledger risk_adjusted_metrics missing fields: {sorted(missing_metric_fields)}")
        for metric_name in required_metric_fields:
            metric_value = risk_adjusted_metrics.get(metric_name)
            if metric_value is not None and not isinstance(metric_value, (int, float)):
                raise ValueError(f"trade ledger risk_adjusted_metrics field {metric_name} must be numeric or null")

    performance_report = payload.get("performance_report")
    if performance_report is not None:
        if not isinstance(performance_report, dict):
            raise ValueError("trade ledger performance_report must be an object when present")
        for field in ("artifact", "artifact_version", "performance_summary", "strategy_comparison", "key_metrics_overview"):
            if field not in performance_report:
                raise ValueError(f"trade ledger performance_report missing field: {field}")

    equity_curve_analysis = payload.get("equity_curve_analysis")
    if equity_curve_analysis is not None:
        if not isinstance(equity_curve_analysis, dict):
            raise ValueError("trade ledger equity_curve_analysis must be an object when present")
        for field in ("artifact", "artifact_version", "equity_curve", "drawdown_stats"):
            if field not in equity_curve_analysis:
                raise ValueError(f"trade ledger equity_curve_analysis missing field: {field}")

    return payload


__all__ = [
    "build_trade_ledger_from_paper_trades",
    "canonical_trade_ledger_json_bytes",
    "write_trade_ledger_artifact",
    "load_trade_ledger_artifact",
]

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
import importlib.util
from pathlib import Path
import sys
from typing import Any, Literal

import pandas as pd
import pytest
from risk.contracts import RiskDecision, RiskEvaluationRequest, RiskGate

from cilly_trading.engine.core import EngineConfig, run_watchlist_analysis
from cilly_trading.engine.logging import (
    emit_structured_engine_log,
    reset_engine_logging_for_tests,
)
from cilly_trading.engine.metrics import (
    ENGINE_METRIC_NAMES,
    get_engine_metrics_snapshot,
    reset_engine_metrics_registry,
)
from cilly_trading.engine.pipeline.orchestrator import run_pipeline
from cilly_trading.engine.strategy_lifecycle.model import StrategyLifecycleState


def _load_provider_module():
    root = Path(__file__).resolve().parents[2]
    module_path = root / "src" / "cilly_trading" / "engine" / "data" / "market_data_provider.py"
    spec = importlib.util.spec_from_file_location("market_data_provider_contract_metrics", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load market_data_provider module")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


_provider_module = _load_provider_module()
Candle = _provider_module.Candle
MarketDataProviderRegistry = _provider_module.MarketDataProviderRegistry
MarketDataRequest = _provider_module.MarketDataRequest


@pytest.fixture(autouse=True)
def _reset_runtime_metrics() -> None:
    reset_engine_metrics_registry()
    reset_engine_logging_for_tests()


@dataclass
class _SignalRepo:
    saved: list[dict[str, Any]] | None = None

    def save_signals(self, signals: list[dict[str, Any]]) -> None:
        self.saved = list(signals)


class _LineageRepo:
    def save_lineage(self, ctx: Any) -> None:
        return None


class _SingleSignalStrategy:
    name = "GENERIC"

    def generate_signals(self, df: pd.DataFrame, config: dict[str, Any]) -> list[dict[str, Any]]:
        return [{"stage": "setup", "score": 1}]


@dataclass(frozen=True)
class _Order:
    id: str
    side: Literal["BUY", "SELL"]
    quantity: Decimal
    created_snapshot_key: str
    sequence: int


@dataclass(frozen=True)
class _Position:
    quantity: Decimal
    avg_price: Decimal


@dataclass(frozen=True)
class _ExecutionConfig:
    slippage_bps: int
    commission_per_order: Decimal
    price_scale: Decimal = Decimal("0.00000001")
    money_scale: Decimal = Decimal("0.01")
    quantity_scale: Decimal = Decimal("0.00000001")
    fill_timing: Literal["next_snapshot", "same_snapshot"] = "next_snapshot"


class _RejectedRiskGate(RiskGate):
    def evaluate(self, request: RiskEvaluationRequest) -> RiskDecision:
        return RiskDecision(
            decision="REJECTED",
            score=1000.0,
            max_allowed=100.0,
            reason="blocked",
            timestamp=datetime(2025, 1, 1, tzinfo=timezone.utc),
            rule_version="test-v1",
        )


class _ProductionLifecycleStore:
    def get_state(self, strategy_id: str) -> StrategyLifecycleState:
        return StrategyLifecycleState.PRODUCTION

    def set_state(self, strategy_id: str, new_state: StrategyLifecycleState) -> None:
        return None


class _AlwaysFailProvider:
    def iter_candles(self, request: MarketDataRequest):
        raise RuntimeError("primary failed")


class _SingleCandleProvider:
    def __init__(self, candle: Candle) -> None:
        self._candle = candle

    def iter_candles(self, request: MarketDataRequest):
        return iter((self._candle,))


def test_metric_counter_increment_is_deterministic() -> None:
    emit_structured_engine_log("analysis_run.started")
    emit_structured_engine_log("signal.generated")
    emit_structured_engine_log("signal.generated")
    emit_structured_engine_log("order_submission.attempt")
    emit_structured_engine_log("order_submission.attempt")
    emit_structured_engine_log("guard.triggered")
    emit_structured_engine_log("provider_failover.attempt_failed")
    emit_structured_engine_log("provider_failover.attempt_failed")
    emit_structured_engine_log("provider_failover.exhausted")
    emit_structured_engine_log("provider_failover.recovered")

    assert get_engine_metrics_snapshot() == {
        "analysis_runs": 1,
        "signals_generated": 2,
        "orders_submitted": 2,
        "guard_triggers": 1,
        "provider_failovers": 2,
    }


def test_metric_values_are_reproducible_across_identical_runs() -> None:
    def _run_once() -> dict[str, int]:
        reset_engine_metrics_registry()
        reset_engine_logging_for_tests()
        for event_name in (
            "analysis_run.started",
            "signal.generated",
            "signal.generated",
            "order_submission.attempt",
            "guard.triggered",
            "provider_failover.attempt_failed",
            "provider_failover.exhausted",
        ):
            emit_structured_engine_log(event_name)
        return get_engine_metrics_snapshot()

    first = _run_once()
    second = _run_once()

    assert first == second


def test_exhausted_failover_path_increments_provider_failovers_deterministically() -> None:
    def _run_once() -> dict[str, int]:
        reset_engine_metrics_registry()
        reset_engine_logging_for_tests()
        emit_structured_engine_log("provider_failover.exhausted")
        emit_structured_engine_log("provider_failover.exhausted")
        return get_engine_metrics_snapshot()

    first = _run_once()
    second = _run_once()

    assert first == second
    assert first["provider_failovers"] == 2


def test_recovered_failover_runtime_path_counts_single_sequence() -> None:
    registry = MarketDataProviderRegistry()
    registry.register(name="primary", provider=_AlwaysFailProvider(), priority=1)
    registry.register(
        name="fallback",
        provider=_SingleCandleProvider(
            Candle(
                timestamp=datetime(2025, 1, 1, tzinfo=timezone.utc),
                symbol="AAPL",
                timeframe="1D",
                open=Decimal("1"),
                high=Decimal("1"),
                low=Decimal("1"),
                close=Decimal("1"),
                volume=Decimal("1"),
            )
        ),
        priority=2,
    )

    tuple(registry.iter_candles_with_failover(MarketDataRequest(symbol="AAPL", timeframe="1D")))

    assert get_engine_metrics_snapshot()["provider_failovers"] == 1


def test_exhausted_failover_runtime_path_does_not_double_count_sequence() -> None:
    registry = MarketDataProviderRegistry()
    registry.register(name="primary", provider=_AlwaysFailProvider(), priority=1)
    registry.register(name="backup", provider=_AlwaysFailProvider(), priority=2)

    with pytest.raises(_provider_module.ProviderFailoverExhaustedError):
        tuple(registry.iter_candles_with_failover(MarketDataRequest(symbol="AAPL", timeframe="1D")))

    assert get_engine_metrics_snapshot()["provider_failovers"] == 1


def test_runtime_event_metric_coverage() -> None:
    def _df(*args: Any, **kwargs: Any) -> pd.DataFrame:
        return pd.DataFrame(
            [
                {
                    "timestamp": "2025-01-01T00:00:00Z",
                    "open": 100,
                    "high": 101,
                    "low": 99,
                    "close": 100,
                    "volume": 10,
                }
            ]
        )

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr("cilly_trading.engine.core.load_ohlcv", _df)
    try:
        run_watchlist_analysis(
            symbols=["AAPL"],
            strategies=[_SingleSignalStrategy()],
            engine_config=EngineConfig(external_data_enabled=True),
            strategy_configs={},
            signal_repo=_SignalRepo(),
            ingestion_run_id="ingest-1",
            snapshot_id="snapshot-1",
            lineage_repo=_LineageRepo(),
        )

        run_pipeline(
            signal={
                "orders": [
                    _Order(
                        id="ord-1",
                        side="BUY",
                        quantity=Decimal("1"),
                        created_snapshot_key="2025-01-01T00:00:00Z",
                        sequence=1,
                    )
                ],
                "snapshot": {"timestamp": "2025-01-02T00:00:00Z", "open": "100"},
            },
            risk_gate=_RejectedRiskGate(),
            lifecycle_store=_ProductionLifecycleStore(),
            risk_request=RiskEvaluationRequest(
                request_id="req-1",
                strategy_id="strategy-a",
                symbol="AAPL",
                notional_usd=1000.0,
                metadata={},
            ),
            position=_Position(quantity=Decimal("0"), avg_price=Decimal("0")),
            execution_config=_ExecutionConfig(
                slippage_bps=10,
                commission_per_order=Decimal("1.25"),
            ),
        )

        registry = MarketDataProviderRegistry()
        registry.register(name="primary", provider=_AlwaysFailProvider(), priority=1)
        registry.register(
            name="fallback",
            provider=_SingleCandleProvider(
                Candle(
                    timestamp=datetime(2025, 1, 1, tzinfo=timezone.utc),
                    symbol="AAPL",
                    timeframe="1D",
                    open=Decimal("1"),
                    high=Decimal("1"),
                    low=Decimal("1"),
                    close=Decimal("1"),
                    volume=Decimal("1"),
                )
            ),
            priority=2,
        )
        tuple(
            registry.iter_candles_with_failover(
                MarketDataRequest(symbol="AAPL", timeframe="1D")
            )
        )
    finally:
        monkeypatch.undo()

    snapshot = get_engine_metrics_snapshot()

    assert set(snapshot.keys()) == set(ENGINE_METRIC_NAMES)
    assert snapshot["analysis_runs"] == 1
    assert snapshot["signals_generated"] == 1
    assert snapshot["orders_submitted"] == 1
    assert snapshot["guard_triggers"] == 1
    assert snapshot["provider_failovers"] == 1

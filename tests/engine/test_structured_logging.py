from __future__ import annotations

import json
import importlib.util
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Literal
from pathlib import Path
import sys
from typing import Any

import pandas as pd
import pytest
from risk.contracts import RiskDecision, RiskEvaluationRequest, RiskGate

from cilly_trading.engine.core import EngineConfig, run_watchlist_analysis
from cilly_trading.engine.logging import (
    InMemoryEngineLogSink,
    configure_engine_log_emitter,
    emit_structured_engine_log,
    reset_engine_logging_for_tests,
)
from cilly_trading.engine.pipeline.orchestrator import run_pipeline
from cilly_trading.engine.strategy_lifecycle.model import StrategyLifecycleState


def _load_provider_module():
    root = Path(__file__).resolve().parents[2]
    module_path = root / "src" / "cilly_trading" / "engine" / "data" / "market_data_provider.py"
    spec = importlib.util.spec_from_file_location("market_data_provider_contract_logging", module_path)
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
def _reset_structured_logging() -> None:
    reset_engine_logging_for_tests()


def _parse_lines(lines: tuple[str, ...]) -> list[dict[str, Any]]:
    return [json.loads(line) for line in lines]


def test_structured_log_schema_is_deterministic_json() -> None:
    sink = InMemoryEngineLogSink()
    configure_engine_log_emitter(sink.write)

    emit_structured_engine_log(
        "analysis_run.started",
        payload={"analysis_run_id": "run-1", "symbols": ["AAPL"]},
    )

    assert len(sink.lines) == 1
    event = json.loads(sink.lines[0])
    assert event == {
        "component": "engine",
        "event": "analysis_run.started",
        "event_index": 0,
        "level": "INFO",
        "payload": {"analysis_run_id": "run-1", "symbols": ["AAPL"]},
        "schema_version": "cilly.engine.log.v1",
    }


def test_structured_log_order_is_deterministic_across_identical_runs() -> None:
    def _emit_sequence() -> tuple[str, ...]:
        reset_engine_logging_for_tests()
        sink = InMemoryEngineLogSink()
        configure_engine_log_emitter(sink.write)
        emit_structured_engine_log("analysis_run.started", payload={"analysis_run_id": "run-1"})
        emit_structured_engine_log("signal.generated", payload={"signal_id": "sig-1"})
        emit_structured_engine_log("analysis_run.completed", payload={"analysis_run_id": "run-1"})
        return sink.lines

    first = _emit_sequence()
    second = _emit_sequence()

    assert first == second
    assert [event["event_index"] for event in _parse_lines(first)] == [0, 1, 2]


@dataclass
class _SignalRepo:
    saved: list[dict[str, Any]] | None = None

    def save_signals(self, signals: list[dict[str, Any]]) -> None:
        self.saved = list(signals)


class _FailingSignalRepo:
    def save_signals(self, signals: list[dict[str, Any]]) -> None:
        raise RuntimeError("persist failed")


class _LineageRepo:
    def save_lineage(self, ctx: Any) -> None:
        return None


class _SingleSignalStrategy:
    name = "GENERIC"

    def generate_signals(self, df: pd.DataFrame, config: dict[str, Any]) -> list[dict[str, Any]]:
        return [{"stage": "setup", "score": 42}]


class _ProductionLifecycleStore:
    def get_state(self, strategy_id: str) -> StrategyLifecycleState:
        return StrategyLifecycleState.PRODUCTION

    def set_state(self, strategy_id: str, new_state: StrategyLifecycleState) -> None:
        return None


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


class _StaticDecisionRiskGate(RiskGate):
    def __init__(self, decision: str) -> None:
        self._decision = decision

    def evaluate(self, request: RiskEvaluationRequest) -> RiskDecision:
        return RiskDecision(
            decision=self._decision,
            score=10.0,
            max_allowed=100.0,
            reason="test",
            timestamp=datetime(2025, 1, 1, tzinfo=timezone.utc),
            rule_version="test-v1",
        )


class _AlwaysFailProvider:
    def iter_candles(self, request: MarketDataRequest):
        raise RuntimeError("primary failed")


class _SingleCandleProvider:
    def __init__(self, candle: Candle) -> None:
        self._candle = candle

    def iter_candles(self, request: MarketDataRequest):
        return iter((self._candle,))


def test_core_engine_events_emit_structured_logs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sink = InMemoryEngineLogSink()
    configure_engine_log_emitter(sink.write)

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

    monkeypatch.setattr("cilly_trading.engine.core.load_ohlcv", _df)

    repo = _SignalRepo()
    run_watchlist_analysis(
        symbols=["AAPL"],
        strategies=[_SingleSignalStrategy()],
        engine_config=EngineConfig(external_data_enabled=True),
        strategy_configs={},
        signal_repo=repo,
        ingestion_run_id="ingest-1",
        snapshot_id="snapshot-1",
        lineage_repo=_LineageRepo(),
    )

    risk_request = RiskEvaluationRequest(
        request_id="req-1",
        strategy_id="strategy-a",
        symbol="AAPL",
        notional_usd=100.0,
        metadata={},
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
        risk_gate=_StaticDecisionRiskGate("APPROVED"),
        lifecycle_store=_ProductionLifecycleStore(),
        risk_request=risk_request,
        position=_Position(quantity=Decimal("0"), avg_price=Decimal("0")),
        execution_config=_ExecutionConfig(
            slippage_bps=10,
            commission_per_order=Decimal("1.25"),
        ),
    )
    run_pipeline(
        signal={"orders": [], "snapshot": {"timestamp": "2025-01-02T00:00:00Z", "open": "100"}},
        risk_gate=_StaticDecisionRiskGate("REJECTED"),
        lifecycle_store=_ProductionLifecycleStore(),
        risk_request=risk_request,
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
    tuple(registry.iter_candles_with_failover(MarketDataRequest(symbol="AAPL", timeframe="1D")))

    emitted_names = [event["event"] for event in _parse_lines(sink.lines)]
    assert "analysis_run.started" in emitted_names
    assert "signal.generated" in emitted_names
    assert "analysis_run.completed" in emitted_names
    assert "order_submission.attempt" in emitted_names
    assert "order_submission.executed" in emitted_names
    assert "guard.triggered" in emitted_names
    assert "provider_failover.attempt_failed" in emitted_names
    assert "provider_failover.recovered" in emitted_names


def test_structured_logs_are_observable_without_explicit_emitter(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.INFO, logger="cilly_trading.engine.logging.structured")

    emit_structured_engine_log(
        "analysis_run.started",
        payload={"analysis_run_id": "run-default-emitter"},
    )

    matching = [
        record.getMessage()
        for record in caplog.records
        if record.name == "cilly_trading.engine.logging.structured"
    ]
    assert len(matching) == 1
    parsed = json.loads(matching[0])
    assert parsed["event"] == "analysis_run.started"
    assert parsed["event_index"] == 0
    assert parsed["payload"]["analysis_run_id"] == "run-default-emitter"


def test_analysis_run_completed_status_reflects_signal_persistence_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sink = InMemoryEngineLogSink()
    configure_engine_log_emitter(sink.write)

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

    monkeypatch.setattr("cilly_trading.engine.core.load_ohlcv", _df)

    run_watchlist_analysis(
        symbols=["AAPL"],
        strategies=[_SingleSignalStrategy()],
        engine_config=EngineConfig(external_data_enabled=True),
        strategy_configs={},
        signal_repo=_FailingSignalRepo(),
        ingestion_run_id="ingest-fail-1",
        snapshot_id="snapshot-fail-1",
        lineage_repo=_LineageRepo(),
    )

    completed_events = [
        event
        for event in _parse_lines(sink.lines)
        if event["event"] == "analysis_run.completed"
    ]
    assert len(completed_events) == 1
    assert completed_events[0]["payload"]["status"] == "signal_persistence_failed"
    assert completed_events[0]["payload"]["status"] != "signals_persisted"

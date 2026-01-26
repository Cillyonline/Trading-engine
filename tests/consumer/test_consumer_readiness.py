from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from tests.utils.consumer_contract_helpers import (
    assert_consumer_can_read_v0_from_v1_output,
    deserialize_tolerant,
    load_fixture,
    load_schema,
)


@dataclass(frozen=True)
class ConsumerEntryZone:
    from_: float
    to: float


@dataclass(frozen=True)
class ConsumerReason:
    reason_id: str
    reason_type: str
    signal_id: str
    ordering_key: int


@dataclass(frozen=True)
class ConsumerSignal:
    signal_id: str
    ingestion_run_id: str
    symbol: str
    strategy: str
    direction: str
    score: float
    timestamp: str
    stage: str
    timeframe: str
    market_type: str
    data_source: str
    reasons: List[ConsumerReason]
    confirmation_rule: Optional[str] = None
    entry_zone: Optional[ConsumerEntryZone] = None


@dataclass(frozen=True)
class ConsumerOutput:
    schema_version: str
    analysis_run_id: str
    ingestion_run_id: str
    symbol: str
    strategy: str
    signals: List[ConsumerSignal]


def _parse_reason(data: Dict[str, Any]) -> ConsumerReason:
    return ConsumerReason(
        reason_id=data["reason_id"],
        reason_type=data["reason_type"],
        signal_id=data["signal_id"],
        ordering_key=int(data["ordering_key"]),
    )


def _parse_signal(data: Dict[str, Any]) -> ConsumerSignal:
    entry_zone_data = data.get("entry_zone")
    entry_zone = None
    if isinstance(entry_zone_data, dict):
        entry_zone = ConsumerEntryZone(
            from_=float(entry_zone_data["from_"]),
            to=float(entry_zone_data["to"]),
        )
    reasons = [_parse_reason(reason) for reason in data["reasons"]]
    return ConsumerSignal(
        signal_id=data["signal_id"],
        ingestion_run_id=data["ingestion_run_id"],
        symbol=data["symbol"],
        strategy=data["strategy"],
        direction=data["direction"],
        score=float(data["score"]),
        timestamp=data["timestamp"],
        stage=data["stage"],
        timeframe=data["timeframe"],
        market_type=data["market_type"],
        data_source=data["data_source"],
        reasons=reasons,
        confirmation_rule=data.get("confirmation_rule"),
        entry_zone=entry_zone,
    )


def _parse_output(data: Dict[str, Any]) -> ConsumerOutput:
    signals = [_parse_signal(signal) for signal in data["signals"]]
    return ConsumerOutput(
        schema_version=data["schema_version"],
        analysis_run_id=data["analysis_run_id"],
        ingestion_run_id=data["ingestion_run_id"],
        symbol=data["symbol"],
        strategy=data["strategy"],
        signals=signals,
    )


def test_consumer_can_read_v1_output_with_v0_expectations() -> None:
    fixture = load_fixture("signal-output.v1.json")
    payload = assert_consumer_can_read_v0_from_v1_output(fixture)

    output = _parse_output(payload)

    assert "producer_metadata" not in payload
    assert "future_note" not in payload["signals"][0]
    assert output.signals[0].confirmation_rule == "rsi_cross"
    assert output.signals[1].confirmation_rule is None
    assert output.signals[1].entry_zone is None
    assert output.signals[0].entry_zone is not None


def test_consumer_schema_rejects_missing_required_fields() -> None:
    fixture = load_fixture("signal-output.v1.missing-required.json")
    schema_v0 = load_schema("signal-output.schema.v0.json")
    schema_v0["properties"]["schema_version"]["enum"] = ["0.9.0", "1.0.0"]
    result = deserialize_tolerant(fixture, schema_v0)

    messages = [error.message for error in result.errors]
    assert any("Missing required property: score" in message for message in messages)

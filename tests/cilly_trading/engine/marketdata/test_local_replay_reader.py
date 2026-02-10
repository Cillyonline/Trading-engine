from __future__ import annotations

from pathlib import Path

import pytest

from cilly_trading.engine.marketdata.adapter.impl.local_replay_reader import (
    LocalReplayConfig,
    LocalReplayMarketDataReader,
)
from cilly_trading.engine.marketdata.guardrails.adapter_guardrails import (
    GuardrailError,
    assert_no_forbidden_references,
)
from cilly_trading.engine.marketdata.models.market_data_models import MarketDataRequest

FIXTURE_PATH = Path(__file__).with_name("replay_sample.csv")


def test_guardrails_reject_forbidden_tokens() -> None:
    with pytest.raises(GuardrailError):
        assert_no_forbidden_references("time.time()", origin="unit-test")


def test_deterministic_reads_match_across_calls() -> None:
    config = LocalReplayConfig(dataset_path=FIXTURE_PATH, format="csv", delay_steps=0)
    reader = LocalReplayMarketDataReader(config)
    request = MarketDataRequest(symbol="AAPL", timeframe="D1")

    first = reader.get_bars(request)
    second = reader.get_bars(request)

    assert first == second
    assert first.metadata.audit_id == second.metadata.audit_id


def test_delay_steps_are_deterministic() -> None:
    config = LocalReplayConfig(dataset_path=FIXTURE_PATH, format="csv", delay_steps=1)
    reader = LocalReplayMarketDataReader(config)
    request = MarketDataRequest(symbol="AAPL", timeframe="D1")

    batch = reader.get_bars(request)

    assert batch.metadata.delay_steps == 1
    assert batch.metadata.row_count == 2
    assert [bar.timestamp for bar in batch.bars] == [
        "2024-01-01T00:00:00Z",
        "2024-01-02T00:00:00Z",
    ]


def test_limit_is_applied_deterministically() -> None:
    config = LocalReplayConfig(dataset_path=FIXTURE_PATH, format="csv", delay_steps=0)
    reader = LocalReplayMarketDataReader(config)
    request = MarketDataRequest(symbol="AAPL", timeframe="D1", limit=1)

    batch = reader.get_bars(request)

    assert batch.metadata.row_count == 1
    assert batch.bars[0].timestamp == "2024-01-01T00:00:00Z"

def test_adapter_source_passes_guardrails() -> None:
    adapter_path = (
        Path(__file__).resolve().parents[4]
        / "src"
        / "cilly_trading"
        / "engine"
        / "marketdata"
        / "adapter"
        / "impl"
        / "local_replay_reader.py"
    )
    source = adapter_path.read_text(encoding="utf-8")
    assert_no_forbidden_references(source, origin=str(adapter_path))


def test_audit_id_is_path_independent(tmp_path: Path) -> None:
    first_copy = tmp_path / "one" / "replay_sample.csv"
    second_copy = tmp_path / "two" / "replay_sample.csv"
    first_copy.parent.mkdir(parents=True, exist_ok=True)
    second_copy.parent.mkdir(parents=True, exist_ok=True)
    sample_bytes = FIXTURE_PATH.read_bytes()
    first_copy.write_bytes(sample_bytes)
    second_copy.write_bytes(sample_bytes)

    config_one = LocalReplayConfig(dataset_path=first_copy, format="csv", delay_steps=0)
    config_two = LocalReplayConfig(dataset_path=second_copy, format="csv", delay_steps=0)

    reader_one = LocalReplayMarketDataReader(config_one)
    reader_two = LocalReplayMarketDataReader(config_two)

    assert reader_one.get_bars(MarketDataRequest(symbol="AAPL", timeframe="D1")).metadata.audit_id == (
        reader_two.get_bars(MarketDataRequest(symbol="AAPL", timeframe="D1")).metadata.audit_id
    )

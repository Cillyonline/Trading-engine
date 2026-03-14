from __future__ import annotations

import pytest
from pydantic import ValidationError

from api.chart_contract import (
    PHASE_39_CHART_SCHEMA_VERSION,
    build_analysis_run_chart_contract,
    build_signal_log_chart_contract,
    build_watchlist_execution_chart_contract,
    validate_runtime_chart_contract,
)


def test_analysis_run_chart_contract_is_snapshot_bound_and_deterministic() -> None:
    payload = {
        "analysis_run_id": "run-001",
        "ingestion_run_id": "11111111-1111-4111-8111-111111111111",
        "symbol": "AAPL",
        "strategy": "RSI2",
        "signals": [
            {
                "symbol": "AAPL",
                "strategy": "RSI2",
                "score": 42.5,
                "timestamp": "2025-01-02T00:00:00+00:00",
                "stage": "setup",
                "timeframe": "D1",
                "market_type": "stock",
                "data_source": "yahoo",
                "confirmation_rule": "RSI below 10",
                "entry_zone": {"from_": 178.5, "to": 182.0},
            },
            {
                "symbol": "AAPL",
                "strategy": "RSI2",
                "score": 55.0,
                "timestamp": "2025-01-03T00:00:00+00:00",
                "stage": "confirm",
                "timeframe": "D1",
                "market_type": "stock",
                "data_source": "yahoo",
            },
        ],
    }

    contract = build_analysis_run_chart_contract(payload)

    assert contract.model_dump(mode="json") == {
        "schema_version": PHASE_39_CHART_SCHEMA_VERSION,
        "contract_scope": "runtime_visual_analysis",
        "constraints": {
            "snapshot_first": True,
            "live_data_allowed": False,
            "market_data_product": False,
            "chart_route_added": False,
        },
        "source": {
            "source_type": "analysis_run",
            "endpoint": "/analysis/run",
            "reuse": "existing_runtime_api",
            "authority": "authoritative",
            "snapshot_binding": "explicit_ingestion_run_id",
            "order_basis": "response_order",
        },
        "context": {
            "runtime_surface": "/ui",
            "analysis_run_id": "run-001",
            "ingestion_run_id": "11111111-1111-4111-8111-111111111111",
            "watchlist_id": None,
            "watchlist_name": None,
            "symbol": "AAPL",
            "strategy": "RSI2",
            "market_type": None,
        },
        "points": [
            {
                "sequence": 1,
                "symbol": "AAPL",
                "strategy": "RSI2",
                "stage": "setup",
                "score": 42.5,
                "signal_strength": None,
                "rank": None,
                "recorded_at": "2025-01-02T00:00:00+00:00",
                "timeframe": "D1",
                "market_type": "stock",
                "data_source": "yahoo",
                "confirmation_rule": "RSI below 10",
                "entry_zone": {"from_": 178.5, "to": 182.0},
                "setups": [],
            },
            {
                "sequence": 2,
                "symbol": "AAPL",
                "strategy": "RSI2",
                "stage": "confirm",
                "score": 55.0,
                "signal_strength": None,
                "rank": None,
                "recorded_at": "2025-01-03T00:00:00+00:00",
                "timeframe": "D1",
                "market_type": "stock",
                "data_source": "yahoo",
                "confirmation_rule": None,
                "entry_zone": None,
                "setups": [],
            },
        ],
        "failures": [],
    }

    validated = validate_runtime_chart_contract(contract.model_dump(mode="json"))
    assert validated == contract


def test_watchlist_execution_chart_contract_carries_ranked_results_and_failures() -> None:
    payload = {
        "analysis_run_id": "watchlist-run-001",
        "ingestion_run_id": "22222222-2222-4222-8222-222222222222",
        "watchlist_id": "ranked-tech",
        "watchlist_name": "Ranked Tech",
        "market_type": "stock",
        "ranked_results": [
            {
                "rank": 1,
                "symbol": "NVDA",
                "score": 91.0,
                "signal_strength": 0.88,
                "setups": [
                    {
                        "strategy": "TURTLE",
                        "score": 91.0,
                        "signal_strength": 0.88,
                        "stage": "setup",
                        "timeframe": "D1",
                        "market_type": "stock",
                        "confirmation_rule": "Breakout confirmed",
                    }
                ],
            }
        ],
        "failures": [
            {
                "symbol": "MSFT",
                "code": "snapshot_data_invalid",
                "detail": "snapshot data unavailable or invalid for symbol",
            }
        ],
    }

    contract = build_watchlist_execution_chart_contract(payload)

    assert contract.source.source_type == "watchlist_execution"
    assert contract.source.endpoint == "/watchlists/{watchlist_id}/execute"
    assert contract.source.authority == "authoritative"
    assert contract.source.snapshot_binding == "explicit_ingestion_run_id"
    assert contract.source.order_basis == "rank_ascending"
    assert contract.context.ingestion_run_id == "22222222-2222-4222-8222-222222222222"
    assert contract.context.watchlist_id == "ranked-tech"
    assert contract.context.watchlist_name == "Ranked Tech"
    assert contract.points[0].rank == 1
    assert contract.points[0].market_type == "stock"
    assert contract.points[0].setups[0].strategy == "TURTLE"
    assert contract.points[0].setups[0].confirmation_rule == "Breakout confirmed"
    assert contract.failures[0].model_dump() == {
        "symbol": "MSFT",
        "code": "snapshot_data_invalid",
        "detail": "snapshot data unavailable or invalid for symbol",
    }
    assert contract.constraints.model_dump() == {
        "snapshot_first": True,
        "live_data_allowed": False,
        "market_data_product": False,
        "chart_route_added": False,
    }


def test_signal_log_chart_contract_is_explicitly_fallback_only() -> None:
    payload = {
        "items": [
            {
                "symbol": "AAPL",
                "strategy": "RSI2",
                "direction": "long",
                "score": 42.5,
                "created_at": "2025-01-04T00:00:00+00:00",
                "stage": "setup",
                "timeframe": "D1",
                "market_type": "stock",
                "data_source": "yahoo",
            }
        ],
        "limit": 20,
        "offset": 0,
        "total": 1,
    }

    contract = build_signal_log_chart_contract(payload)

    assert contract.source.source_type == "signal_log"
    assert contract.source.endpoint == "/signals"
    assert contract.source.authority == "fallback_only"
    assert contract.source.snapshot_binding == "not_available_in_source"
    assert contract.context.ingestion_run_id is None
    assert contract.points[0].recorded_at == "2025-01-04T00:00:00+00:00"
    assert contract.points[0].score == 42.5


def test_analysis_run_chart_contract_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        build_analysis_run_chart_contract(
            {
                "analysis_run_id": "run-001",
                "ingestion_run_id": "11111111-1111-4111-8111-111111111111",
                "symbol": "AAPL",
                "strategy": "RSI2",
                "signals": [],
                "unexpected": "value",
            }
        )

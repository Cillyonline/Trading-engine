"""Contract tests for P56: bounded signal-quality validation."""

from __future__ import annotations

from pathlib import Path

from api.services.analysis_service import build_ranked_symbol_results


REPO_ROOT = Path(__file__).resolve().parents[1]
CONTRACT_DOC = REPO_ROOT / "docs" / "governance" / "signal-quality-bounded-contract.md"


def _signal(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "symbol": "AAPL",
        "strategy": "RSI2",
        "stage": "setup",
        "score": 50.0,
        "signal_strength": 0.5,
        "timeframe": "D1",
        "market_type": "stock",
    }
    base.update(overrides)
    return base


def test_p56_ranking_is_deterministic_for_defined_fixture_ordering() -> None:
    signals = [
        _signal(symbol="BBB", score=60.0, signal_strength=0.4),
        _signal(symbol="AAA", score=60.0, signal_strength=0.7),
        _signal(symbol="AAC", score=60.0, signal_strength=0.7),
        _signal(symbol="DDD", score=95.0, signal_strength=0.2),
        _signal(symbol="EEE", score=20.0, signal_strength=0.9),
    ]

    ranked = build_ranked_symbol_results(signals, min_score=30.0)
    assert [item.symbol for item in ranked] == ["DDD", "AAA", "AAC", "BBB"]


def test_p56_ranking_is_stable_for_permuted_input_fixture() -> None:
    fixture_a = [
        _signal(symbol="BBB", score=60.0, signal_strength=0.4),
        _signal(symbol="AAA", score=60.0, signal_strength=0.7),
        _signal(symbol="AAC", score=60.0, signal_strength=0.7),
        _signal(symbol="DDD", score=95.0, signal_strength=0.2),
    ]
    fixture_b = list(reversed(fixture_a))

    ranked_a = build_ranked_symbol_results(fixture_a, min_score=30.0)
    ranked_b = build_ranked_symbol_results(fixture_b, min_score=30.0)

    assert [item.symbol for item in ranked_a] == [item.symbol for item in ranked_b]
    assert [item.score for item in ranked_a] == [item.score for item in ranked_b]
    assert [item.signal_strength for item in ranked_a] == [item.signal_strength for item in ranked_b]


def test_p56_selectivity_respects_min_score_boundary_for_supported_numeric_scores() -> None:
    signals = [
        _signal(symbol="A", score=44.9),
        _signal(symbol="B", score=45.0),
        _signal(symbol="C", score=80.0),
    ]

    ranked = build_ranked_symbol_results(signals, min_score=45.0)

    assert [item.symbol for item in ranked] == ["C", "B"]


def test_p56_weak_or_low_information_cases_are_bounded_where_supported() -> None:
    signals = [
        _signal(symbol="", score=99.0, signal_strength=1.0),
        _signal(symbol="NO_SETUP", stage="entry", score=99.0, signal_strength=1.0),
        _signal(symbol="NO_SCORE", score=None, signal_strength=0.4),
        _signal(symbol="TEXT_SCORE", score="n/a", signal_strength=0.4),
        _signal(symbol="VALID", score=55.0, signal_strength=0.2),
    ]

    ranked = build_ranked_symbol_results(signals, min_score=30.0)

    assert [item.symbol for item in ranked] == ["VALID"]


def test_p56_contract_doc_is_bounded_and_no_trader_readiness_claim() -> None:
    content = CONTRACT_DOC.read_text(encoding="utf-8")

    assert content.startswith("# P56 Signal Quality - Bounded Validation Contract")
    assert "Deterministic ranking behavior under defined fixtures" in content
    assert "Selectivity boundary for low-information candidates" in content
    assert "Stability boundary under equivalent fixture content" in content
    assert "Classification: technically good, traderically weak" in content
    assert "does not claim trader readiness" in content
    assert "no live-trading readiness, execution approval, or profitability guarantee" in content

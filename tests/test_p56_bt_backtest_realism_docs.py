"""Contract tests for P56-BT bounded backtest realism assumptions."""

from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
CONTRACT_DOC = REPO_ROOT / "docs" / "testing" / "backtesting" / "p56_bounded_backtest_realism_assumptions.md"


def test_p56_bt_doc_explicitly_documents_current_assumptions() -> None:
    content = CONTRACT_DOC.read_text(encoding="utf-8")

    assert content.startswith("# P56-BT Bounded Backtest Realism Assumptions")
    assert "Current Implemented Assumptions (Validated)" in content
    assert "Fill model is fixed to `deterministic_market`." in content
    assert "Price source is fixed to `open_then_price`" in content
    assert "Commission model is fixed per filled order (`commission_per_order`)." in content
    assert "Trader validation status for this implementation remains `trader_validation_not_started`." in content


def test_p56_bt_doc_explicitly_states_realism_gaps_and_unsupported_claims() -> None:
    content = CONTRACT_DOC.read_text(encoding="utf-8")

    assert "Explicit Realism Gaps (Not Modeled)" in content
    assert "Market hours/session calendars" in content
    assert "Broker routing" in content
    assert "Order-book depth, queue position" in content
    assert "Unsupported claims:" in content
    assert "live-trading readiness or approval" in content
    assert "trader validation or trader approval" in content
    assert "future profitability or out-of-sample robustness" in content


def test_p56_bt_doc_status_wording_is_evidence_bounded() -> None:
    content = CONTRACT_DOC.read_text(encoding="utf-8")

    assert "Status Wording" in content
    assert "Classification: technically good, traderically weak." in content
    assert "deterministic and test-validated for implemented assumptions" in content
    assert "key market-realism dimensions are intentionally unmodeled" in content
    assert "trader validation status remains `trader_validation_not_started`" in content

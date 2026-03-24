from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_backtest_cli_doc_defines_reproducible_evidence_fields() -> None:
    content = (REPO_ROOT / "docs" / "testing" / "backtesting" / "backtest_cli.md").read_text(
        encoding="utf-8"
    )

    assert "## Reproducible Evidence Fields" in content
    assert "`run.run_id`" in content
    assert "`run_config.execution_assumptions`" in content
    assert "`run_config.reproducibility_metadata`" in content
    assert "`metrics_baseline.assumptions`" in content
    assert "MUST match" in content


def test_backtest_cli_doc_defines_trader_interpretation_boundary() -> None:
    content = (REPO_ROOT / "docs" / "testing" / "backtesting" / "backtest_cli.md").read_text(
        encoding="utf-8"
    )

    assert "## Trader Interpretation Boundary" in content
    assert "does **not** prove" in content
    assert "Live trading readiness." in content
    assert "Future performance" in content

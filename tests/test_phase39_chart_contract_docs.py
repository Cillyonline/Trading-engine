from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_runtime_chart_data_contract_doc_covers_route_reuse_and_boundaries() -> None:
    content = (
        REPO_ROOT / "docs" / "api" / "runtime_chart_data_contract.md"
    ).read_text(encoding="utf-8")

    assert content.startswith("# Runtime Chart Data Contract")
    assert "/analysis/run" in content
    assert "/watchlists/{watchlist_id}/execute" in content
    assert "/signals" in content
    assert "No new chart-specific route is introduced in Phase 39." in content
    assert "snapshot-first" in content
    assert "market-data product" in content
    assert "fallback-only" in content


def test_runtime_chart_data_contract_doc_closes_example_json_before_sections() -> None:
    content = (
        REPO_ROOT / "docs" / "api" / "runtime_chart_data_contract.md"
    ).read_text(encoding="utf-8")

    assert content.count("```json") == 1
    assert content.count("```") == 2
    assert (
        "}\n```\n\n"
        "The example above is illustrative only. The following sections remain normative contract guidance.\n\n"
        "## Consumer Expectations"
    ) in content
    assert content.index("## Consumer Expectations") < content.index("## Explicit Non-Goals")


def test_phase39_ui_doc_points_to_runtime_chart_data_contract() -> None:
    content = (
        REPO_ROOT / "docs" / "ui" / "phase-39-charting-contract.md"
    ).read_text(encoding="utf-8")

    assert "docs/api/runtime_chart_data_contract.md" in content
    assert "existing runtime API routes" in content
    assert "fallback-only" in content


def test_docs_index_links_runtime_chart_data_contract() -> None:
    content = (REPO_ROOT / "docs" / "index.md").read_text(encoding="utf-8")

    assert "api/runtime_chart_data_contract.md" in content

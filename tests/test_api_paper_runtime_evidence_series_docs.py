from __future__ import annotations


def test_paper_runtime_evidence_series_docs_state_inspection_only_boundary(
    read_repo_doc,
    doc_assert_contains_all,
) -> None:
    content = read_repo_doc("docs/api/paper_runtime_evidence_series.md")

    doc_assert_contains_all(
        content,
        "GET /paper/runtime/evidence-series",
        "read-only inspection endpoint",
        "does not trigger paper-runtime runs",
        "scripts/run_daily_bounded_paper_runtime.py",
        "not_configured",
        "missing",
        "empty",
        "available",
        "does not imply trader validation",
        "live-trading readiness",
        "broker readiness",
        "profitability",
    )

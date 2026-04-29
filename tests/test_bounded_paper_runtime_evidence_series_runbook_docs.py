from __future__ import annotations


RUNBOOK = "docs/operations/runtime/bounded-paper-runtime-evidence-series-runbook.md"
DOCS_INDEX = "docs/index.md"
EVIDENCE_TABLE_HEADER = (
    "| Run | UTC timestamp | Operator | Exit code | Classification |"
    " Ingestion run ID | Analysis run ID | Eligible | Skipped |"
    " Reconciliation ok | Mismatches | Docker ps | Health | Summary file |"
    " Local operator log | Notes |"
)
EVIDENCE_TABLE_SEPARATOR = (
    "| --- | --- | --- | --- | --- | --- | --- | ---: | ---: | --- | ---: |"
    " --- | --- | --- | --- | --- |"
)


def _assert_all_fenced_code_blocks_are_closed(content: str) -> None:
    fence_count = sum(1 for line in content.splitlines() if line.startswith("```"))
    assert fence_count > 0
    assert fence_count % 2 == 0


def test_bounded_paper_runtime_evidence_series_runbook_defines_manual_process(
    read_repo_doc,
    doc_assert_contains_all,
) -> None:
    content = read_repo_doc(RUNBOOK)

    doc_assert_contains_all(
        content,
        "# Bounded Paper Runtime Evidence-Series Runbook",
        "manual operator procedure",
        "20 to 30 manually executed bounded paper-runtime runs",
        "## Before Each Run",
        "## Run Command",
        "## After Each Run",
        "## Per-Run Record Format",
        "## Evidence Table Template",
        "## Classification Rules",
        "## Non-Live Boundary",
        "docker compose --env-file /root/Trading-engine/.env",
        "run_daily_bounded_paper_runtime.py",
        "--db-path /data/db/cilly_trading.db",
        "--base-url http://127.0.0.1:8000",
        "curl -sS http://127.0.0.1:18000/health",
        "runs/operator-logs/bounded-paper-runtime-evidence-series",
    )


def test_bounded_paper_runtime_evidence_series_runbook_has_valid_markdown_structure(
    read_repo_doc,
    doc_assert_contains_all,
) -> None:
    content = read_repo_doc(RUNBOOK)

    _assert_all_fenced_code_blocks_are_closed(content)
    doc_assert_contains_all(
        content,
        "## Before Each Run",
        "## Run Command",
        "## After Each Run",
        "## Evidence Table Template",
        "## Classification Rules",
        "## Non-Live Boundary",
        "## References",
        EVIDENCE_TABLE_HEADER,
        EVIDENCE_TABLE_SEPARATOR,
    )


def test_bounded_paper_runtime_evidence_series_runbook_preserves_boundaries(
    read_repo_doc,
    doc_assert_contains_all,
) -> None:
    content = read_repo_doc(RUNBOOK)

    doc_assert_contains_all(
        content,
        "does not automate the runner",
        "does not trigger paper-runtime runs from a browser",
        "does not change runtime behavior",
        "does not modify paper execution behavior",
        "does not change signal generation",
        "does not change risk logic",
        "does not change thresholds",
        "does not change data ingestion",
        "no live orders are placed",
        "no broker APIs are called",
        "no real capital is at risk",
        "no live-trading-readiness claim is made",
        "no broker-readiness claim is made",
        "no production-readiness claim is made",
        "no operational-readiness claim is made",
        "no trader-validation claim is made",
        "no profitability claim is made",
    )


def test_bounded_paper_runtime_evidence_series_runbook_defines_classification_and_same_day_warning(
    read_repo_doc,
    doc_assert_contains_all,
) -> None:
    content = read_repo_doc(RUNBOOK)

    doc_assert_contains_all(
        content,
        "Fresh daily runs are traderically more meaningful",
        "Repeated same-day runs",
        "must not be interpreted as independent market evidence",
        "`healthy`",
        "`no_eligible`",
        "`degraded`",
        "do not rerun solely to force eligible activity",
        "stop continuation claims",
    )


def test_bounded_paper_runtime_evidence_series_runbook_renders_references_as_markdown_list(
    read_repo_doc,
    doc_assert_contains_all,
) -> None:
    content = read_repo_doc(RUNBOOK)

    doc_assert_contains_all(
        content,
        "## References",
        "- `docs/operations/runtime/p63-daily-bounded-paper-runtime-workflow.md`",
        "- `docs/operations/runtime/p64-one-command-bounded-daily-paper-runtime-runner.md`",
        "- `docs/operations/runtime/bounded-paper-runtime-evidence-series-summarizer.md`",
    )


def test_docs_index_links_bounded_paper_runtime_evidence_series_runbook(
    read_repo_doc,
    doc_assert_contains_all,
) -> None:
    content = read_repo_doc(DOCS_INDEX)

    doc_assert_contains_all(
        content,
        "operations/runtime/bounded-paper-runtime-evidence-series-runbook.md",
        "Bounded paper runtime evidence-series runbook",
    )

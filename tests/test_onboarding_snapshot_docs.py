from __future__ import annotations

from tests.utils.consumer_contract_helpers import (
    assert_contains_all,
    read_repo_text,
)


REPO_SNAPSHOT_DOC = "docs/getting-started/repo-snapshot.md"
RUNBOOK_DOC = "docs/operations/runbook.md"


def test_repo_snapshot_reflects_current_bounded_evidence_without_readiness_inference() -> None:
    content = read_repo_text(REPO_SNAPSHOT_DOC)

    assert_contains_all(
        content,
        "bounded backtest evidence contracts and tests",
        "bounded portfolio and paper inspection read surfaces",
        "bounded daily paper-runtime workflow and one-command runner documentation",
        "Phase 25",
        "Phase 26",
        "These surfaces do not imply live-trading readiness, broker readiness, production",
    )


def test_repo_snapshot_removes_stale_absence_claims_for_bounded_surfaces() -> None:
    content = read_repo_text(REPO_SNAPSHOT_DOC)

    stale_claims = [
        "Backtesting frameworks.",
        "Portfolio management.",
        "There is no CLI entrypoint documented",
        "no owner-facing run command",
    ]
    for stale_claim in stale_claims:
        assert stale_claim not in content


def test_runbook_points_paper_runtime_to_bounded_ops_p63_p64_contracts() -> None:
    content = read_repo_text(RUNBOOK_DOC)

    assert_contains_all(
        content,
        "OPS-P64 daily runner",
        "scripts/run_daily_bounded_paper_runtime.py",
        "runtime/p63-daily-bounded-paper-runtime-workflow.md",
        "runtime/p64-one-command-bounded-daily-paper-runtime-runner.md",
        "This command remains bounded and non-live.",
    )
    assert "no owner-facing run command is defined here" not in content

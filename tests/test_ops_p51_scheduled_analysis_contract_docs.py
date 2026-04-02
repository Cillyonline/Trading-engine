from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def _read(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")


def test_ops_p51_usage_contract_defines_one_authoritative_scheduled_analysis_contract() -> None:
    content = _read("docs/operations/api/usage_contract.md")

    assert "## Canonical Scheduled Analysis and Watchlist Execution Contract" in content
    assert (
        "This section is the single authoritative server-side contract for scheduled analysis "
        "in this repository."
    ) in content
    assert "Scheduled analysis is **snapshot-only**." in content
    assert "`POST /analysis/run`" in content
    assert "`POST /watchlists/{watchlist_id}/execute`" in content
    assert 'implicit "latest snapshot" mode' in content
    assert "live-data fallback" in content


def test_ops_p51_usage_contract_distinguishes_empty_results_symbol_failures_and_snapshot_failures() -> None:
    content = _read("docs/operations/api/usage_contract.md")

    assert "### Scheduled outcome classification" in content
    assert "`200 OK` from `POST /analysis/run` with `signals: []`" in content
    assert (
        "`200 OK` from `POST /watchlists/{watchlist_id}/execute` with `ranked_results: []` "
        "and `failures: []`"
    ) in content
    assert (
        "`200 OK` from `POST /watchlists/{watchlist_id}/execute` with one or more `failures` items"
    ) in content
    assert "`invalid_ingestion_run_id`, `ingestion_run_not_found`, `ingestion_run_not_ready`, or `snapshot_data_invalid`" in content
    assert "The scheduled run did not produce authoritative analysis output" in content


def test_ops_p51_docs_and_existing_endpoint_tests_align_to_same_operator_contract() -> None:
    usage = _read("docs/operations/api/usage_contract.md")
    snapshot_runtime = _read("docs/operations/runtime/snapshot_runtime.md")
    manual_analysis_tests = _read("tests/test_api_manual_analysis_trigger.py")
    snapshot_first_tests = _read("tests/test_api_snapshot_first_enforcement.py")
    watchlist_tests = _read("tests/test_api_watchlists.py")

    assert (
        "The repository's implemented persistence path stores request and result payloads keyed by "
        "`analysis_run_id` for both `POST /analysis/run` and "
        "`POST /watchlists/{watchlist_id}/execute`."
    ) in usage
    assert "def test_manual_analysis_idempotent" in manual_analysis_tests
    assert 'assert second_body["analysis_run_id"] == expected_run_id' in manual_analysis_tests
    assert 'assert response.json()["detail"] == "snapshot_data_invalid"' in snapshot_first_tests
    assert "def test_watchlist_execute_returns_empty_results_when_no_signals" in watchlist_tests
    assert 'assert response.json()["ranked_results"] == []' in watchlist_tests
    assert "def test_watchlist_execute_isolates_partial_symbol_failures" in watchlist_tests
    assert '"code": "snapshot_data_invalid"' in watchlist_tests
    assert "The repository now includes one bounded in-process scheduled analysis runner" in snapshot_runtime
    assert "`created_at DESC`" in snapshot_runtime
    assert "`ingestion_run_id ASC`" in snapshot_runtime
    assert "Only one scheduled execution loop may be active per server process." in snapshot_runtime
    assert "`runs/analysis_run_evidence/<YYYY-Www>/<analysis_run_id>/`" in usage
    assert "`analysis-run-evidence.json`" in usage
    assert "`operator-review.json`" in usage
    assert "`comparison_key`" in usage
    assert "`review_week`" in usage
    assert "Weekly review is supported by scanning one ISO-week bucket at a time" in usage
    assert "## Scheduled Evidence Artifacts" in snapshot_runtime
    assert "`CILLY_ANALYSIS_EVIDENCE_DIR`" in snapshot_runtime
    assert "`analysis-run-evidence.sha256`" in snapshot_runtime
    assert "`operator-review.sha256`" in snapshot_runtime
    assert "deterministic weekly review buckets and bounded operator review artifacts" in snapshot_runtime

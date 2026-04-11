"""Contract tests for OPS-P52: bounded signal-to-paper execution policy."""

from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]

POLICY_DOC_PATH = (
    "docs/operations/runtime/signal_to_paper_execution_policy.md"
)


def _read(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# AC1: One bounded signal-to-paper execution policy exists
# ---------------------------------------------------------------------------


def test_ops_p52_one_bounded_policy_exists_with_required_header() -> None:
    content = _read(POLICY_DOC_PATH)

    assert content.startswith(
        "# Bounded Signal-to-Paper Execution Policy Contract (OPS-P52)"
    )
    assert "single authoritative bounded policy" in content
    assert "signal may become a paper trade" in content


def test_ops_p52_policy_is_non_live_and_bounded() -> None:
    content = _read(POLICY_DOC_PATH)

    assert "## Non-Live Boundary" in content
    assert "No live orders are placed." in content
    assert "No broker APIs are called." in content
    assert "No real capital is at risk." in content
    assert "does not constitute live trading" in content
    assert (
        "Passing this policy gate does not imply live-trading readiness"
    ) in content


def test_ops_p52_policy_defines_ordered_evaluation_sequence() -> None:
    content = _read(POLICY_DOC_PATH)

    assert "## Policy Overview" in content
    assert "Eligibility check" in content
    assert "Score threshold check" in content
    assert "Duplicate-entry check" in content
    assert "Cooldown check" in content
    assert "Exposure check" in content


# ---------------------------------------------------------------------------
# AC2: Eligibility, skip, and reject rules are explicit
# ---------------------------------------------------------------------------


def test_ops_p52_eligibility_rules_define_required_signal_fields() -> None:
    content = _read(POLICY_DOC_PATH)

    assert "## Eligibility Rules" in content
    assert "| `symbol` |" in content
    assert "| `strategy` |" in content
    assert "| `direction` |" in content
    assert "| `score` |" in content
    assert "| `timestamp` |" in content
    assert "| `stage` |" in content
    assert "`reject:invalid_signal_fields`" in content


def test_ops_p52_timestamp_requirement_matches_iso8601_only_implementation_claim() -> None:
    content = _read(POLICY_DOC_PATH)

    assert "| `timestamp` | Parseable ISO-8601 datetime string. |" in content
    assert "Unix epoch milliseconds" not in content


def test_ops_p52_skip_and_reject_outcomes_are_explicit_with_codes() -> None:
    content = _read(POLICY_DOC_PATH)

    assert "## Eligibility, Skip, and Reject Outcome Summary" in content
    assert "| Outcome | Code | Trigger |" in content
    assert "| Eligible | `eligible` |" in content
    assert "| Skip | `skip:score_below_threshold` |" in content
    assert "| Skip | `skip:duplicate_entry` |" in content
    assert "| Skip | `skip:cooldown_active` |" in content
    assert "| Reject | `reject:invalid_signal_fields` |" in content
    assert "| Reject | `reject:position_size_exceeds_limit` |" in content
    assert "| Reject | `reject:total_exposure_exceeds_limit` |" in content
    assert "| Reject | `reject:concurrent_position_limit_exceeded` |" in content


def test_ops_p52_skip_and_reject_semantics_are_distinguished() -> None:
    content = _read(POLICY_DOC_PATH)

    assert "**Skip** outcomes" in content
    assert "**Reject** outcomes" in content
    assert "silently bypassed" in content
    assert "hard policy violation" in content
    assert "must be logged" in content


# ---------------------------------------------------------------------------
# AC3: Duplicate-entry and cooldown rules are explicit
# ---------------------------------------------------------------------------


def test_ops_p52_duplicate_entry_prevention_is_explicit() -> None:
    content = _read(POLICY_DOC_PATH)

    assert "## Duplicate-Entry Prevention" in content
    assert "`(symbol, strategy, direction)`" in content
    assert "`skip:duplicate_entry`" in content
    assert "canonical execution repository state" in content
    assert "paper_state_authority.py" in content
    assert "Only one active issue should be executing per `(symbol, strategy)` scope" in content


def test_ops_p52_cooldown_rules_are_explicit() -> None:
    content = _read(POLICY_DOC_PATH)

    assert "## Cooldown Rules" in content
    assert "`24 hours`" in content
    assert "`(symbol, strategy)` pair" in content
    assert "`skip:cooldown_active`" in content
    assert "cooldown timer starts at the timestamp of the last accepted entry" in content


# ---------------------------------------------------------------------------
# AC4: Exposure limits are explicit
# ---------------------------------------------------------------------------


def test_ops_p52_exposure_limits_are_explicit_with_defaults() -> None:
    content = _read(POLICY_DOC_PATH)

    assert "## Exposure and Position Limits" in content
    assert "### Per-position exposure limit" in content
    assert "### Global exposure limit" in content
    assert "### Concurrent position limit" in content
    assert "`max_position_pct = 0.10`" in content
    assert "`max_total_exposure_pct = 0.80`" in content
    assert "`max_concurrent_positions = 10`" in content
    assert "`reject:position_size_exceeds_limit`" in content
    assert "`reject:total_exposure_exceeds_limit`" in content
    assert "`reject:concurrent_position_limit_exceeded`" in content


def test_ops_p52_score_threshold_rules_are_explicit() -> None:
    content = _read(POLICY_DOC_PATH)

    assert "## Score Threshold Rules" in content
    assert "`60.0`" in content
    assert "`[0.0, 100.0]`" in content
    assert "`skip:score_below_threshold`" in content
    assert "does not imply broker execution readiness" in content
    assert "docs/governance/score-semantics-cross-strategy.md" in content


# ---------------------------------------------------------------------------
# AC5: Contract remains non-live and bounded
# ---------------------------------------------------------------------------


def test_ops_p52_policy_application_boundary_is_non_live() -> None:
    content = _read(POLICY_DOC_PATH)

    assert "## Policy Application Boundary" in content
    assert "bounded paper simulation boundary" in content
    assert "does not apply to backtesting, live trading, or broker execution" in content
    assert "intentionally non-live" in content
    assert "live-trading readiness or broker execution approval" in content


def test_ops_p52_out_of_scope_reminder_names_excluded_items() -> None:
    content = _read(POLICY_DOC_PATH)

    assert "## Out-of-Scope Reminder" in content
    assert "live order routing" in content
    assert "broker APIs" in content
    assert "portfolio optimization engines" in content
    assert "broad strategy redesign" in content

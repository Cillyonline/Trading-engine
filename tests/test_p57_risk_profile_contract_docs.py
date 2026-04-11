from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
POLICY_DOC_PATH = "docs/operations/runtime/signal_to_paper_execution_policy.md"


def _read(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")


def test_p57_risk_profile_contract_is_documented_with_validation_boundary() -> None:
    content = _read(POLICY_DOC_PATH)

    assert "## Paper Execution Risk Profile Contract (P57-RISK)" in content
    assert "paper_execution_risk_profile.py" in content
    assert "paper-execution-risk-profile-v1" in content
    assert "validates all bounded profile inputs fail-closed" in content
    assert "Invalid values raise explicit errors" in content


def test_p57_docs_state_what_is_not_claimed_and_no_p56_duplication() -> None:
    content = _read(POLICY_DOC_PATH)

    assert "Not claimed by this contract" in content
    assert "live-trading readiness" in content
    assert "broker integration readiness" in content
    assert "production-readiness approval" in content
    assert "does not duplicate the existing P56 adverse-scenario" in content

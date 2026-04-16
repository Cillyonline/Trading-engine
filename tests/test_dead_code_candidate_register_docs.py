from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
REGISTER_PATH = REPO_ROOT / "docs" / "architecture" / "reports" / "dead_code_candidate_register.md"


def test_register_contains_required_sections_and_closed_code_fences() -> None:
    content = REGISTER_PATH.read_text(encoding="utf-8")

    assert "# Dead-Code Candidate Register" in content
    assert "## Candidate Register" in content
    assert "## Reference Check Evidence" in content
    assert "Per-Candidate Verification Dimensions" in content
    assert "Remediation Eligibility Summary" in content
    assert content.count("~~~powershell") == 1
    assert content.count("~~~") == 2


def test_register_includes_required_candidates_and_no_removal_scope() -> None:
    content = REGISTER_PATH.read_text(encoding="utf-8")

    assert "`pr_issue_935.md`" in content
    assert "`tests/.tmp_issue955_broader_output.txt`" in content
    assert "`tests/.tmp_issue955_targeted_output.txt`" in content
    assert "`tests/issue955_review_package.txt`" in content
    assert "No deletion or functional code change is performed by this register issue #945." in content

from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
RELEASE_CONTRACT_PATH = (
    REPO_ROOT / "docs" / "releases" / "release_governance_contract.md"
)


def test_release_governance_contract_defines_bounded_server_ready_stage() -> None:
    content = RELEASE_CONTRACT_PATH.read_text(encoding="utf-8")

    assert content.startswith("# Release Governance Contract - Server-Ready Stage")
    assert "## 1. Purpose and Stage Boundary" in content
    assert "deterministic local operation and staging-first server deployment validation" in content
    assert "does not grant production approval" in content
    assert "does not declare live-trading readiness" in content


def test_release_governance_contract_defines_versioning_and_tag_expectations() -> None:
    content = RELEASE_CONTRACT_PATH.read_text(encoding="utf-8")

    assert "## 2. Versioning Rules for This Stage" in content
    assert "Semantic versioning (`MAJOR.MINOR.PATCH`)" in content
    assert "Exactly one authoritative engine version exists per release" in content
    assert "The authoritative release version is the tagged version, not an untagged branch head." in content

    assert "## 3. Release-Tag Expectations" in content
    assert "exactly one immutable git tag in the format `vX.Y.Z`" in content
    assert "Moving or deleting an existing release tag is forbidden." in content
    assert "force-retagging is forbidden" in content


def test_release_governance_contract_defines_feature_flag_and_rollback_boundaries() -> None:
    content = RELEASE_CONTRACT_PATH.read_text(encoding="utf-8")

    assert "## 4. Feature-Flag Boundaries (Covered Deployment Modes)" in content
    assert "deterministic local mode" in content
    assert "staging-first server mode" in content
    assert "Flags must not be used to enable live order routing" in content
    assert "A feature flag is not a scope override" in content

    assert "## 5. Rollback Discipline for Bounded Operational Recovery" in content
    assert "disable only the failing stage-scoped flag" in content
    assert "rollback to a last-known-good release tag" in content
    assert "run version verification, smoke run, and staging validation checks" in content
    assert "Record every rollback decision" in content


def test_release_governance_contract_explicitly_bounds_non_goals() -> None:
    content = RELEASE_CONTRACT_PATH.read_text(encoding="utf-8")

    assert "## 7. Explicit Non-Goals" in content
    assert "- live trading rollout" in content
    assert "- broker integrations" in content
    assert "- CI platform redesign" in content
    assert "- strategy logic expansion" in content
    assert "- UI redesign" in content
    assert "- production high-availability approval" in content

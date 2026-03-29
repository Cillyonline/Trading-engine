from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_configuration_boundary_declares_ops_p46_server_contract_scope() -> None:
    content = (
        REPO_ROOT / "docs" / "architecture" / "configuration_boundary.md"
    ).read_text(encoding="utf-8")

    assert "## OPS-P46 Bounded Server Environment and Filesystem Contract" in content
    assert "first-paper server environment contract" in content
    assert ".env.example" in content
    assert "docker/staging/docker-compose.staging.yml" in content
    assert "Conditional provider secret requirements" in content


def test_configuration_boundary_defines_required_env_and_path_alignment_rules() -> None:
    content = (
        REPO_ROOT / "docs" / "architecture" / "configuration_boundary.md"
    ).read_text(encoding="utf-8")

    assert "One bounded server environment contract exists and is authoritative" in content
    assert "Compose, docs, and env guidance must define the same path values." in content
    assert "Persistence expectations must explicitly distinguish restart/redeploy" in content

from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_staging_topology_doc_defines_single_canonical_topology() -> None:
    content = (
        REPO_ROOT / "docs" / "operations" / "runtime" / "staging-first-deployment-topology.md"
    ).read_text(encoding="utf-8")

    assert content.startswith("# Staging-First Deployment Topology and Runtime Contract")
    assert "## Canonical Topology Claim" in content
    assert "Exactly one canonical staging-first topology is valid in this stage" in content
    assert "No alternative equal-status topology is defined for this stage." in content
    assert "`docker/staging/docker-compose.staging.yml`" in content
    assert "one `api` service process (`uvicorn api.main:app`)" in content
    assert "one local SQLite persistence volume mounted at `/data`" in content


def test_staging_topology_doc_defines_runtime_environment_and_boundary_non_goals() -> None:
    content = (
        REPO_ROOT / "docs" / "operations" / "runtime" / "staging-first-deployment-topology.md"
    ).read_text(encoding="utf-8")

    assert "## Runtime Contract and Service Boundary" in content
    assert "Required runtime services in this topology:" in content
    assert "Operating assumptions:" in content
    assert "## Environment Boundary" in content
    assert "must not be mixed" in content
    assert "production-like scope" in content
    assert "## Persistence, Logging, and Health Expectations" in content
    assert "## Non-Goals and Excluded Runtime Modes" in content
    assert "- live trading" in content
    assert "- broker integrations" in content
    assert "- production high availability" in content
    assert "- any runtime mode that places live market orders" in content


def test_docs_index_links_staging_first_topology_contract() -> None:
    content = (REPO_ROOT / "docs" / "index.md").read_text(encoding="utf-8")

    assert "operations/runtime/staging-first-deployment-topology.md" in content

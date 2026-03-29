from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def _assert_fence_closes_to_transition(
    content: str,
    *,
    block_marker: str,
    expected_transition: str,
) -> None:
    marker_index = content.index(block_marker)

    opening_index = content.rfind("\n```", 0, marker_index)
    if opening_index == -1:
        opening_index = content.rfind("```", 0, marker_index)
    else:
        opening_index += 1
    assert opening_index != -1

    opening_line_end = content.find("\n", opening_index)
    if opening_line_end == -1:
        opening_line_end = len(content)
    opening_line = content[opening_index:opening_line_end]
    assert opening_line.startswith("```")

    search_from = opening_line_end
    closing_line_start = -1
    while True:
        candidate = content.find("\n```", search_from)
        if candidate == -1:
            break
        line_start = candidate + 1
        line_end = content.find("\n", line_start)
        if line_end == -1:
            line_end = len(content)
        if content[line_start:line_end] == "```":
            closing_line_start = line_start
            break
        search_from = line_end

    assert closing_line_start != -1
    assert opening_index < marker_index < closing_line_start

    transition_index = content.index(expected_transition)
    assert transition_index > closing_line_start
    assert not (opening_index < transition_index < closing_line_start)


def test_staging_topology_doc_defines_single_canonical_topology() -> None:
    content = (
        REPO_ROOT / "docs" / "operations" / "runtime" / "staging-first-deployment-topology.md"
    ).read_text(encoding="utf-8")

    assert content.startswith("# Staging-First Deployment Topology and Runtime Contract")
    assert "## Canonical Topology Claim" in content
    assert "Exactly one canonical staging-first topology is valid in this stage" in content
    assert "No alternative equal-status topology is defined for this stage." in content
    assert "`docker/staging/docker-compose.staging.yml`" in content
    assert "## Canonical First-Deployment Install Path" in content
    assert "Docker/Compose is the canonical and only first-clean-server install path in" in content
    assert "Canonical install/runbook authority:" in content
    assert "`docs/operations/runtime/staging-server-deployment.md`" in content
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
    assert (
        "        [SQLite persistence at /data]\n```\n\n"
        "## Runtime Contract and Service Boundary"
    ) in content
    _assert_fence_closes_to_transition(
        content,
        block_marker="[Operator client or bounded automation]",
        expected_transition="## Runtime Contract and Service Boundary",
    )
    _assert_fence_closes_to_transition(
        content,
        block_marker="[Operator client or bounded automation]",
        expected_transition="## Environment Boundary",
    )
    _assert_fence_closes_to_transition(
        content,
        block_marker="[Operator client or bounded automation]",
        expected_transition="## Persistence, Logging, and Health Expectations",
    )
    _assert_fence_closes_to_transition(
        content,
        block_marker="[Operator client or bounded automation]",
        expected_transition="## Non-Goals and Excluded Runtime Modes",
    )
    _assert_fence_closes_to_transition(
        content,
        block_marker="[Operator client or bounded automation]",
        expected_transition="## Install-Ready Versus Later Scope",
    )
    _assert_fence_closes_to_transition(
        content,
        block_marker="[Operator client or bounded automation]",
        expected_transition="## Validation and Verification Path",
    )
    _assert_fence_closes_to_transition(
        content,
        block_marker="[Operator client or bounded automation]",
        expected_transition="## Related References",
    )


def test_docs_index_links_staging_first_topology_contract() -> None:
    content = (REPO_ROOT / "docs" / "index.md").read_text(encoding="utf-8")

    assert "operations/runtime/staging-first-deployment-topology.md" in content
    assert "Canonical first-clean-server install contract:" in content
    assert "Docker/Compose (`docker compose -f docker/staging/docker-compose.staging.yml up -d --build`) is the only canonical first-clean-server startup path." in content
    assert "Local development setup guides are non-canonical for first-clean-server installation." in content


def test_getting_started_marks_local_setup_non_canonical_for_first_clean_server() -> None:
    content = (
        REPO_ROOT / "docs" / "getting-started" / "getting-started.md"
    ).read_text(encoding="utf-8")

    assert "This guide is not the canonical first-clean-server install contract." in content
    assert "docs/operations/runtime/staging-server-deployment.md" in content
    assert "Canonical for local development setup only." in content
    assert "Non-canonical for first-clean-server install/startup." in content

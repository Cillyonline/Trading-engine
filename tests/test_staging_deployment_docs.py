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


def test_staging_topology_doc_references_canonical_staging_artifacts() -> None:
    content = (
        REPO_ROOT / "docs" / "operations" / "runtime" / "staging-server-deployment.md"
    ).read_text(encoding="utf-8")

    assert content.lstrip().startswith("# Staging Server Deployment and Runtime Validation")
    assert "docker/staging/Dockerfile" in content
    assert "docker/staging/docker-compose.staging.yml" in content
    assert "python scripts/validate_staging_deployment.py" in content
    assert "STAGING_VALIDATE:SUCCESS" in content
    assert "/health/engine" in content
    assert "/health/data" in content
    assert "/health/guards" in content
    assert "docker compose -f docker/staging/docker-compose.staging.yml restart api" in content
    assert "## Canonical First-Deployment Install Path" in content
    assert "## Reproducible Build and Deploy Path" in content
    assert "## Health and Readiness Checks" in content
    assert "## Logging and Observability Expectations" in content
    assert "## Restart-Safe Runtime Behavior" in content
    assert "## Storage and Persistence Expectations" in content
    assert "## Bounded Staging Validation" in content
    assert "## Acceptance-Gate Alignment" in content
    assert "`server-ready (staging)`" in content
    assert "`paper-install-ready`" in content
    assert "EVIDENCE_STAGING_VALIDATION_LOG" in content
    assert "## Test Gate" in content


def test_staging_topology_doc_declares_single_canonical_first_deployment_path() -> None:
    content = (
        REPO_ROOT / "docs" / "operations" / "runtime" / "staging-server-deployment.md"
    ).read_text(encoding="utf-8")

    assert "The canonical first-deployment install path in this repository is:" in content
    assert "docker compose -f docker/staging/docker-compose.staging.yml up -d --build" in content
    assert "Legacy `requirements.txt` installation is non-canonical" in content
    assert (
        "docker compose -f docker/staging/docker-compose.staging.yml up -d --build\n```\n\n"
        "Reproducibility constraints in this path:"
    ) in content
    assert (
        "curl -sS -H \"X-Cilly-Role: read_only\" http://127.0.0.1:18000/health/guards\n```\n\n"
        "Readiness expectations:"
    ) in content
    assert (
        "python scripts/validate_staging_deployment.py\n```\n\n"
        "Validation stages:"
    ) in content
    _assert_fence_closes_to_transition(
        content,
        block_marker="docker compose -f docker/staging/docker-compose.staging.yml config",
        expected_transition="Reproducibility constraints in this path:",
    )
    _assert_fence_closes_to_transition(
        content,
        block_marker="docker compose -f docker/staging/docker-compose.staging.yml config",
        expected_transition="## Health and Readiness Checks",
    )
    _assert_fence_closes_to_transition(
        content,
        block_marker="curl -sS -H \"X-Cilly-Role: read_only\" http://127.0.0.1:18000/health",
        expected_transition="Readiness expectations:",
    )
    _assert_fence_closes_to_transition(
        content,
        block_marker="docker compose -f docker/staging/docker-compose.staging.yml logs -f api",
        expected_transition="## Restart-Safe Runtime Behavior",
    )
    _assert_fence_closes_to_transition(
        content,
        block_marker="docker compose -f docker/staging/docker-compose.staging.yml restart api",
        expected_transition="Expected result:",
    )
    _assert_fence_closes_to_transition(
        content,
        block_marker="docker compose -f docker/staging/docker-compose.staging.yml restart api",
        expected_transition="## Storage and Persistence Expectations",
    )
    _assert_fence_closes_to_transition(
        content,
        block_marker="docker compose -f docker/staging/docker-compose.staging.yml down -v",
        expected_transition="## Bounded Staging Validation",
    )
    _assert_fence_closes_to_transition(
        content,
        block_marker="python scripts/validate_staging_deployment.py",
        expected_transition="Validation stages:",
    )
    _assert_fence_closes_to_transition(
        content,
        block_marker="python scripts/validate_staging_deployment.py",
        expected_transition="## Test Gate",
    )

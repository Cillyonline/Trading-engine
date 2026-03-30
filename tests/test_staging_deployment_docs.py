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
    assert ".env.example" in content
    assert "python scripts/validate_staging_deployment.py" in content
    assert "STAGING_VALIDATE:SUCCESS" in content
    assert "/health/engine" in content
    assert "/health/data" in content
    assert "/health/guards" in content
    assert "--env-file .env -f docker/staging/docker-compose.staging.yml restart api" in content
    assert "## Canonical First-Clean-Server Install Contract" in content
    assert "## Host Prerequisites and Package Contract" in content
    assert "## Required Directories and Persistence Paths" in content
    assert "## Required Environment Variables (Bounded First Deploy / Paper Mode)" in content
    assert "## Ownership and Permission Expectations" in content
    assert "## Exact Startup Commands" in content
    assert "## Exact Smoke Commands" in content
    assert "## Logging and Observability Expectations" in content
    assert "## Exact Restart Validation Commands" in content
    assert "## Storage and Persistence Expectations" in content
    assert "## Bounded Staging Validation" in content
    assert "## Conflicting Guidance Handling" in content
    assert "## Acceptance-Gate Alignment" in content
    assert "`server-ready (staging)`" in content
    assert "`paper-install-ready`" in content
    assert "EVIDENCE_STAGING_VALIDATION_LOG" in content
    assert "## Test Gate" in content
    assert "## Access and Trust Boundary (Staging Paper)" in content
    assert "Default access posture for staging paper operation is localhost-only" in content
    assert "public authentication model" in content
    assert "Public or internet-exposed access without an external trust boundary is" in content
    assert "explicitly disallowed." in content


def test_staging_topology_doc_declares_single_canonical_first_deployment_path() -> None:
    content = (
        REPO_ROOT / "docs" / "operations" / "runtime" / "staging-server-deployment.md"
    ).read_text(encoding="utf-8")

    assert "Docker/Compose is the canonical and only first-clean-server install path" in content
    assert "The canonical first-clean-server startup command is:" in content
    assert "docker compose --env-file .env -f docker/staging/docker-compose.staging.yml up -d --build" in content
    assert "Legacy `requirements.txt` installation is non-canonical" in content
    assert "Required on host:" in content
    assert "Docker Engine" in content
    assert "Docker Compose v2 plugin" in content
    assert "Optional on host:" in content
    assert "`uv` (not required for first-clean-server startup/smoke/restart validation" in content
    assert "Required runtime environment variables for bounded first deployment:" in content
    assert "- `PYTHONPATH=/app/src`" in content
    assert "- `CILLY_DB_PATH=/data/db/cilly_trading.db`" in content
    assert "- `CILLY_LOG_LEVEL=INFO`" in content
    assert "- `CILLY_LOG_FORMAT=json`" in content
    assert "- `CILLY_STAGING_DB_DIR`" in content
    assert "- `CILLY_STAGING_ARTIFACT_DIR`" in content
    assert "- `CILLY_STAGING_JOURNAL_DIR`" in content
    assert "- `CILLY_STAGING_LOG_DIR`" in content
    assert "- `CILLY_STAGING_RUNTIME_STATE_DIR`" in content
    assert "Conditional provider secret requirements are explicit:" in content
    assert "Remote access boundary:" in content
    assert "Remote access is out of default staging scope" in content
    assert "Any local-run or local development installation guidance is non-canonical for" in content
    assert (
        "docker compose --env-file .env -f docker/staging/docker-compose.staging.yml up -d --build\n```\n\n"
        "Reproducibility constraints in this path:"
    ) in content
    assert (
        "curl -sS -H \"X-Cilly-Role: read_only\" http://127.0.0.1:18000/health/guards\n```\n\n"
        "Readiness expectations:"
    ) in content
    assert "`ready: true` as the canonical bounded" in content
    assert "`runtime_status` or" in content
    assert (
        "python scripts/validate_staging_deployment.py\n```\n\n"
        "The validation script uses `.env` by default"
    ) in content
    assert "uses `.env` by default for all compose calls" in content
    _assert_fence_closes_to_transition(
        content,
        block_marker="docker compose --env-file .env -f docker/staging/docker-compose.staging.yml config",
        expected_transition="Reproducibility constraints in this path:",
    )
    _assert_fence_closes_to_transition(
        content,
        block_marker="docker compose --env-file .env -f docker/staging/docker-compose.staging.yml config",
        expected_transition="## Exact Smoke Commands",
    )
    _assert_fence_closes_to_transition(
        content,
        block_marker="curl -sS -H \"X-Cilly-Role: read_only\" http://127.0.0.1:18000/health",
        expected_transition="Readiness expectations:",
    )
    _assert_fence_closes_to_transition(
        content,
        block_marker="docker compose --env-file .env -f docker/staging/docker-compose.staging.yml logs -f api",
        expected_transition="## Exact Restart Validation Commands",
    )
    _assert_fence_closes_to_transition(
        content,
        block_marker="docker compose --env-file .env -f docker/staging/docker-compose.staging.yml restart api",
        expected_transition="Expected result:",
    )
    _assert_fence_closes_to_transition(
        content,
        block_marker="docker compose --env-file .env -f docker/staging/docker-compose.staging.yml restart api",
        expected_transition="## Storage and Persistence Expectations",
    )
    _assert_fence_closes_to_transition(
        content,
        block_marker="docker compose --env-file .env -f docker/staging/docker-compose.staging.yml down --remove-orphans",
        expected_transition="## Bounded Staging Validation",
    )
    _assert_fence_closes_to_transition(
        content,
        block_marker="```bash\npython scripts/validate_staging_deployment.py",
        expected_transition="Validation stages:",
    )
    _assert_fence_closes_to_transition(
        content,
        block_marker="```bash\npython scripts/validate_staging_deployment.py",
        expected_transition="## Test Gate",
    )

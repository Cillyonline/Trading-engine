from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def _read(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")


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

    transition_index = content.find(expected_transition, closing_line_start + 1)
    assert transition_index != -1
    assert transition_index > closing_line_start
    assert not (opening_index < transition_index < closing_line_start)


def test_ops_p46_docs_define_localhost_only_and_non_public_role_header_boundary() -> None:
    staging_doc = _read("docs/operations/runtime/staging-server-deployment.md")
    usage_doc = _read("docs/operations/api/usage_contract.md")
    gate_doc = _read("docs/operations/runtime/paper-deployment-acceptance-gate.md")

    assert "localhost-only" in staging_doc
    assert "localhost-only" in usage_doc.lower() or "localhost-only" in gate_doc.lower()

    expected_phrase = "public authentication model"
    assert expected_phrase in staging_doc
    assert expected_phrase in usage_doc
    assert expected_phrase in gate_doc


def test_ops_p46_docs_bound_remote_access_and_disallow_public_exposure() -> None:
    staging_doc = _read("docs/operations/runtime/staging-server-deployment.md")
    usage_doc = _read("docs/operations/api/usage_contract.md")
    gate_doc = _read("docs/operations/runtime/paper-deployment-acceptance-gate.md")

    assert "Remote access is out of default staging scope" in staging_doc
    assert "Remote access is not part of the default API usage contract" in usage_doc
    assert "Remote access is outside default staging scope" in gate_doc

    disallow_phrase = "without an external trust boundary"
    assert disallow_phrase in staging_doc
    assert disallow_phrase in usage_doc
    assert disallow_phrase in gate_doc


def test_usage_contract_examples_have_closed_fences_and_valid_section_transitions() -> None:
    content = _read("docs/operations/api/usage_contract.md")

    assert "### Canonical request body" in content
    assert "Canonical request example:" in content
    assert "Request boundary notes:" in content
    assert "### Canonical success response body" in content
    assert "Canonical success response example:" in content
    assert "### Canonical failure semantics" in content
    assert "**Response:**" in content
    assert "---\n\n## POST /watchlists" in content

    fence_count = sum(1 for line in content.splitlines() if line.startswith("```"))
    assert fence_count % 2 == 0

    _assert_fence_closes_to_transition(
        content,
        block_marker='"strategy_config": {',
        expected_transition="Request boundary notes:",
    )
    _assert_fence_closes_to_transition(
        content,
        block_marker='"analysis_run_id": "e1f2d3c4-1111-2222-3333-444455556666"',
        expected_transition="### Canonical failure semantics",
    )
    assert (
        "Canonical request example:\n\n```json\n{\n"
        in content
    )
    assert (
        "}\n```\n\nRequest boundary notes:"
        in content
    )
    assert (
        "Canonical success response example:\n\n```json\n{\n"
        in content
    )
    assert (
        "}\n```\n\n### Canonical failure semantics"
        in content
    )
    assert (
        "### Example\n\n**Request:**\n\n```bash\n"
        "curl -s -X POST http://localhost:8000/analysis/run \\\n"
        in content
    )
    assert (
        "  }'\n```\n\n**Response:**\n\n```json\n{\n"
        '  "analysis_run_id": "e1f2d3c4-1111-2222-3333-444455556666",\n'
        in content
    )
    assert (
        '  "signals": []\n}\n```\n\n---\n\n## POST /watchlists'
        in content
    )

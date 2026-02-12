from __future__ import annotations

from pathlib import Path

import api


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_public_import_surface_is_explicit_and_frozen() -> None:
    assert hasattr(api, "__all__")
    assert api.__all__ == ("app",)
    assert hasattr(api, "app")


def test_public_api_documentation_sections_exist() -> None:
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    boundary_doc = REPO_ROOT / "docs" / "api" / "public_api_boundary.md"

    assert "## Public API" in readme
    assert "docs/api/public_api_boundary.md" in readme

    assert boundary_doc.exists()
    content = boundary_doc.read_text(encoding="utf-8")
    assert content.startswith("# Public API Boundary")

"""Import and boundary tests for portfolio framework modules."""

from __future__ import annotations

import ast
from pathlib import Path


MODULES = [
    "engine.portfolio_framework",
    "engine.portfolio_framework.contract",
    "engine.portfolio_framework.exposure_aggregator",
]

FORBIDDEN_PREFIXES = (
    "engine.execution",
    "engine.orchestrator",
    "engine.broker",
)


def test_import_portfolio_framework_modules() -> None:
    """Each portfolio framework module should import without side effects."""
    for module_name in MODULES:
        __import__(module_name)


def _imported_module_names(node: ast.AST) -> list[str]:
    """Return normalized imported module names for import nodes."""
    if isinstance(node, ast.Import):
        return [alias.name for alias in node.names]
    if isinstance(node, ast.ImportFrom):
        return [node.module] if node.module else []
    return []


def test_portfolio_framework_import_boundary() -> None:
    """Portfolio framework package must not import forbidden runtime packages."""
    root = Path(__file__).resolve().parents[2]
    package_dir = root / "engine" / "portfolio_framework"

    for path in package_dir.glob("*.py"):
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
        for node in ast.walk(tree):
            for module_name in _imported_module_names(node):
                assert not module_name.startswith(FORBIDDEN_PREFIXES), (
                    f"Forbidden import '{module_name}' found in {path}"
                )

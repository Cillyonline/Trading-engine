"""Import and boundary tests for portfolio framework modules."""

from __future__ import annotations

import ast
from pathlib import Path


MODULES = [
    "cilly_trading.portfolio_framework",
    "cilly_trading.portfolio_framework.capital_allocation_policy",
    "cilly_trading.portfolio_framework.contract",
    "cilly_trading.portfolio_framework.exposure_aggregator",
    "cilly_trading.portfolio_framework.guardrails",
]

FORBIDDEN_PREFIXES = (
    "cilly_trading.execution",
    "cilly_trading.orchestrator",
    "cilly_trading.broker",
)


DYNAMIC_IMPORT_FUNCTIONS = {
    "importlib.import_module",
    "__import__",
}


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


def _dynamic_import_target(node: ast.AST) -> str | None:
    """Return dynamic import target when found, else None."""
    if not isinstance(node, ast.Call):
        return None

    if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
        callable_name = f"{node.func.value.id}.{node.func.attr}"
    elif isinstance(node.func, ast.Name):
        callable_name = node.func.id
    else:
        return None

    if callable_name not in DYNAMIC_IMPORT_FUNCTIONS:
        return None

    if not node.args or not isinstance(node.args[0], ast.Constant):
        return None
    if not isinstance(node.args[0].value, str):
        return None

    return node.args[0].value


def test_portfolio_framework_import_boundary() -> None:
    """Portfolio framework package must not import forbidden runtime packages."""
    root = Path(__file__).resolve().parents[2]
    package_dir = root / "src" / "cilly_trading" / "portfolio_framework"

    for path in package_dir.glob("*.py"):
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
        for node in ast.walk(tree):
            for module_name in _imported_module_names(node):
                assert not module_name.startswith(FORBIDDEN_PREFIXES), (
                    f"Forbidden import '{module_name}' found in {path}"
                )

            dynamic_target = _dynamic_import_target(node)
            if dynamic_target is not None:
                assert not dynamic_target.startswith(FORBIDDEN_PREFIXES), (
                    f"Forbidden dynamic import '{dynamic_target}' found in {path}"
                )

"""Import and architecture boundary tests for risk framework skeleton modules."""

from __future__ import annotations

import ast
from pathlib import Path


MODULES = [
    "cilly_trading.risk_framework",
    "cilly_trading.risk_framework.contract",
    "cilly_trading.risk_framework.risk_evaluator",
    "cilly_trading.risk_framework.exposure_model",
    "cilly_trading.risk_framework.allocation_rules",
    "cilly_trading.risk_framework.kill_switch",
]

FORBIDDEN_PREFIXES = (
    "cilly_trading.execution",
    "cilly_trading.orchestrator",
)


def test_import_risk_framework_modules() -> None:
    """Each risk framework module should import without raising exceptions."""
    for module_name in MODULES:
        __import__(module_name)


def _imported_module_names(node: ast.AST) -> list[str]:
    """Return normalized imported module names for import nodes."""
    if isinstance(node, ast.Import):
        return [alias.name for alias in node.names]
    if isinstance(node, ast.ImportFrom):
        return [node.module] if node.module else []
    return []


def test_risk_framework_import_boundary() -> None:
    """Risk framework package must not import execution or orchestrator packages."""
    root = Path(__file__).resolve().parents[2]
    package_dir = root / "src" / "cilly_trading" / "risk_framework"

    for path in package_dir.glob("*.py"):
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
        for node in ast.walk(tree):
            for module_name in _imported_module_names(node):
                assert not module_name.startswith(FORBIDDEN_PREFIXES), (
                    f"Forbidden import '{module_name}' found in {path}"
                )

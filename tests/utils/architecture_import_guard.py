from __future__ import annotations

import ast
from pathlib import Path


FORBIDDEN_IMPORT_ROOTS = (
    "cilly_trading.engine.order_execution_model",
)
OPTIONAL_FORBIDDEN_IMPORT_ROOTS = (
    "cilly_trading.engine.execution",
)
ALLOWED_IMPORTER_RELATIVE_PATH = Path("src/cilly_trading/engine/pipeline/orchestrator.py")


def collect_forbidden_execution_import_violations(repo_root: Path) -> list[str]:
    """Collect forbidden execution import violations outside the orchestrator module."""
    repo_root = repo_root.resolve()
    forbidden_roots = _resolve_forbidden_import_roots(repo_root)
    allowed_importer = (repo_root / ALLOWED_IMPORTER_RELATIVE_PATH).resolve()
    violations: list[str] = []

    for path in _iter_python_files(repo_root):
        if path.resolve() == allowed_importer:
            continue

        source = path.read_text(encoding="utf-8-sig")
        tree = ast.parse(source, filename=str(path))

        for import_name in _iter_static_imports(tree):
            if _matches_forbidden_root(import_name, forbidden_roots):
                relative_path = _to_project_relative_posix(path, repo_root)
                violations.append(f"{relative_path}: static import {import_name}")

        for module_name in _iter_dynamic_import_calls(tree):
            if _matches_forbidden_root(module_name, forbidden_roots):
                relative_path = _to_project_relative_posix(path, repo_root)
                violations.append(f"{relative_path}: dynamic import {module_name}")

    return sorted(set(violations))


def _resolve_forbidden_import_roots(repo_root: Path) -> tuple[str, ...]:
    forbidden_roots = list(FORBIDDEN_IMPORT_ROOTS)

    for module_path in OPTIONAL_FORBIDDEN_IMPORT_ROOTS:
        if _module_exists(repo_root, module_path):
            forbidden_roots.append(module_path)

    return tuple(forbidden_roots)


def _to_project_relative_posix(path: Path, project_root: Path) -> str:
    return Path(path).resolve().relative_to(project_root.resolve()).as_posix()


def _iter_python_files(repo_root: Path) -> list[Path]:
    python_files: list[Path] = []
    for scope in ("src", "tests"):
        scope_root = repo_root / scope
        if not scope_root.exists():
            continue
        python_files.extend(scope_root.rglob("*.py"))
    return python_files


def _iter_static_imports(tree: ast.AST) -> list[str]:
    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.module is not None:
                imports.append(node.module)
    return imports


def _iter_dynamic_import_calls(tree: ast.AST) -> list[str]:
    dynamic_imports: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue

        if _is_importlib_import_module_call(node) and node.args:
            module_name = _extract_str_literal(node.args[0])
            if module_name is not None:
                dynamic_imports.append(module_name)

        if _is_builtin_import_call(node) and node.args:
            module_name = _extract_str_literal(node.args[0])
            if module_name is not None:
                dynamic_imports.append(module_name)

    return dynamic_imports


def _is_importlib_import_module_call(node: ast.Call) -> bool:
    if isinstance(node.func, ast.Attribute):
        return (
            isinstance(node.func.value, ast.Name)
            and node.func.value.id == "importlib"
            and node.func.attr == "import_module"
        )
    if isinstance(node.func, ast.Name):
        return node.func.id == "import_module"
    return False


def _is_builtin_import_call(node: ast.Call) -> bool:
    return isinstance(node.func, ast.Name) and node.func.id == "__import__"


def _extract_str_literal(node: ast.AST) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _matches_forbidden_root(import_name: str, forbidden_roots: tuple[str, ...]) -> bool:
    return any(
        import_name == root or import_name.startswith(f"{root}.")
        for root in forbidden_roots
    )


def _module_exists(repo_root: Path, module_path: str) -> bool:
    module_file = repo_root / "src" / Path(*module_path.split("."))
    return module_file.with_suffix(".py").exists() or module_file.is_dir()

from __future__ import annotations

from pathlib import Path


FORBIDDEN_DIRECT_IMPORT = (
    "from cilly_trading.engine.order_execution_model import " + "_execute_order"
)


def test_private_execution_entrypoint_only_imported_by_orchestrator() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    allowed = {repo_root / "src/cilly_trading/engine/pipeline/orchestrator.py"}
    violations: list[str] = []

    search_roots = [repo_root / "src", repo_root / "tests"]
    for root in search_roots:
        for path in root.rglob("*.py"):
            if path in allowed:
                continue
            text = path.read_text(encoding="utf-8")
            if FORBIDDEN_DIRECT_IMPORT in text:
                violations.append(str(path.relative_to(repo_root)))

    assert not violations, (
        "Forbidden direct _execute_order imports outside orchestrator: "
        + ", ".join(sorted(violations))
    )

from __future__ import annotations

from pathlib import Path

from tests.utils.architecture_import_guard import (
    collect_forbidden_execution_import_violations,
)


def test_execution_imports_are_restricted_to_orchestrator() -> None:
    repo_root = Path(__file__).resolve().parents[3]

    violations = collect_forbidden_execution_import_violations(repo_root)

    assert not violations, (
        "Forbidden execution imports outside orchestrator:\n"
        + "\n".join(f"- {violation}" for violation in violations)
    )


def test_execution_import_guard_detects_static_and_dynamic_violations(tmp_path: Path) -> None:
    src_dir = tmp_path / "src"

    static_violation_file = src_dir / "static_violation.py"
    static_violation_file.parent.mkdir(parents=True, exist_ok=True)
    static_violation_file.write_text(
        "import cilly_trading.engine.order_execution_model\n",
        encoding="utf-8",
    )

    dynamic_violation_file = src_dir / "dynamic_violation.py"
    dynamic_violation_file.write_text(
        "import importlib\n"
        "mod = importlib.import_module('cilly_trading.engine.order_execution_model')\n",
        encoding="utf-8",
    )

    orchestrator_file = src_dir / "cilly_trading/engine/pipeline/orchestrator.py"
    orchestrator_file.parent.mkdir(parents=True, exist_ok=True)
    orchestrator_file.write_text(
        "import cilly_trading.engine.order_execution_model\n",
        encoding="utf-8",
    )

    violations = collect_forbidden_execution_import_violations(tmp_path)

    assert violations
    assert any(
        "src/static_violation.py: static import cilly_trading.engine.order_execution_model" in violation
        for violation in violations
    )
    assert any(
        "src/dynamic_violation.py: dynamic import cilly_trading.engine.order_execution_model" in violation
        for violation in violations
    )
    assert not any("orchestrator.py" in violation for violation in violations)

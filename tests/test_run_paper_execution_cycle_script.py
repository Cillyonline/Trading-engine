from __future__ import annotations

import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from cilly_trading.engine.paper_execution_risk_profile import (
    PAPER_EXECUTION_RISK_PROFILE_CONTRACT_ID,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_script_module():
    module_path = REPO_ROOT / "scripts" / "run_paper_execution_cycle.py"
    spec = importlib.util.spec_from_file_location(
        "test_run_paper_execution_cycle_script_module",
        module_path,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load run_paper_execution_cycle.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_run_paper_execution_cycle_includes_canonical_risk_profile(
    tmp_path: Path,
) -> None:
    module = _load_script_module()

    db_path = tmp_path / "paper_execution.db"
    evidence_dir = tmp_path / "evidence"

    exit_code = module.run_paper_execution_cycle(
        db_path=str(db_path),
        evidence_dir=str(evidence_dir),
        signal_limit=10,
        ran_at=datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
    )
    assert exit_code == module.EXIT_CYCLE_NO_ELIGIBLE

    evidence_files = sorted(evidence_dir.glob("paper-execution-no-eligible-*.json"))
    assert len(evidence_files) == 1

    payload = json.loads(evidence_files[0].read_text(encoding="utf-8"))
    assert payload["risk_profile"]["contract_id"] == PAPER_EXECUTION_RISK_PROFILE_CONTRACT_ID

from __future__ import annotations

import sys
from pathlib import Path


def pytest_load_initial_conftests(early_config, parser, args) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    src_path = repo_root / "src"

    src_str = str(src_path)
    root_str = str(repo_root)

    # Ensure src is first
    if src_str in sys.path:
        sys.path.remove(src_str)
    sys.path.insert(0, src_str)

    # Ensure repo root does not shadow src/api
    if root_str in sys.path:
        sys.path.remove(root_str)
        sys.path.append(root_str)

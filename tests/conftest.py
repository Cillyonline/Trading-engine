from __future__ import annotations

import sys
from pathlib import Path


def pytest_load_initial_conftests(early_config, parser, args) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    src_path = repo_root / "src"
    cwd = Path.cwd().resolve()

    src_str = str(src_path)
    root_str = str(repo_root)
    cwd_str = str(cwd)

    # Put src first
    if src_str in sys.path:
        sys.path.remove(src_str)
    sys.path.insert(0, src_str)

    # Move any repo-root equivalents behind src (including '' / '.' / cwd)
    for entry in ("", ".", cwd_str, root_str):
        while entry in sys.path:
            sys.path.remove(entry)
        sys.path.append(entry)

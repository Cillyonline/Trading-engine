from __future__ import annotations

import importlib
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = (REPO_ROOT / "src").resolve()
CWD = Path.cwd().resolve()


def _norm(p: str) -> str:
    try:
        return str(Path(p).resolve()).rstrip("\\/").lower()
    except Exception:
        return str(p).rstrip("\\/").lower()


repo_norm = _norm(str(REPO_ROOT))
src_norm = _norm(str(SRC_PATH))
cwd_norm = _norm(str(CWD))

# Put src first and remove repo-root/cwd variants to avoid shadowing repo-root api/
new_path: list[str] = [str(SRC_PATH)]
for p in sys.path:
    if not p or p == ".":
        continue
    np = _norm(p)
    if np in (repo_norm, cwd_norm):
        continue
    if np == src_norm:
        continue
    new_path.append(p)

sys.path[:] = new_path

# Clear any cached wrong 'api' modules so they re-resolve from src/
for name in list(sys.modules.keys()):
    if name == "api" or name.startswith("api."):
        del sys.modules[name]

# Lock correct resolution early (must resolve from src/)
importlib.import_module("api.main")

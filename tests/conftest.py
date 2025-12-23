from __future__ import annotations

import sys
from pathlib import Path

# Ensure src/ layout is importable when running tests locally or in CI.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_PATH))

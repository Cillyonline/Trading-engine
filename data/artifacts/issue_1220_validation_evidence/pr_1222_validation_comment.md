## #1220 validation evidence update

No implementation changes were made for this validation pass.

### Focused tests
Command:
```powershell
python -m pytest tests/scripts/test_export_historical_snapshots.py -q
```
Output:
```text
................................................                         [100%]
48 passed in 5.40s
```

### Full repository pytest on PR branch
Command:
```powershell
$env:PYTHONIOENCODING='utf-8'; $env:PYTHONUTF8='1'; python -X utf8 -m pytest -q
```
Result:
```text
36 failed, 1609 passed, 1 skipped, 1 warning in 149.29s (0:02:29)
```

### Baseline comparison against origin/main
Same command was run in a clean detached worktree at `origin/main` (`7a84d6f`).
Result:
```text
36 failed, 1577 passed, 1 skipped, 1 warning in 215.93s (0:03:35)
```

The failed-test set is identical between PR branch and `origin/main`; current-only failures: none; main-only failures: none.
Full pytest outputs and per-test classification are preserved here:
https://gist.github.com/Cillyonline/d2ba642b6e7d0772a2f1967836e8484a

### Failure classification
All 36 failures are classified as `pre-existing unrelated` because the exact same failed-test set occurs on current `origin/main` before the PR changes. None are classified as `caused by #1220`. None require an implementation change in this PR.

### yfinance rate-limit limitation
The live smoke export command completed, but yfinance returned `YFRateLimitError('Too Many Requests. Rate limited. Try after a while.')` for all six required symbols (`AAPL`, `COST`, `GS`, `MSFT`, `NVDA`, `WMT`), so the live artifact contained zero snapshots. The generated zero-snapshot annotated artifact was still accepted by the backtest CLI with exit code 0.

### Synthetic blocker-parity smoke
Command:
```powershell
python - <<'PY'
import importlib.util
import json
from pathlib import Path
spec = importlib.util.spec_from_file_location('export_historical_snapshots', Path('scripts/export_historical_snapshots.py'))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
summary = mod.build_turtle_research_summary({
    'AAPL_2024-01-02': {'symbol': 'AAPL', 'signal_produced': True, 'stage': 'setup', 'score': 58.0, 'score_blocked': True, 'risk_blocked': False, 'is_entry_candidate': False},
    'GS_2024-01-02': {'symbol': 'GS', 'signal_produced': True, 'stage': 'entry_confirmed', 'score': 80.0, 'score_blocked': False, 'risk_blocked': True, 'is_entry_candidate': False},
})
print(json.dumps(summary['totals'], sort_keys=True))
print(json.dumps(summary['by_symbol'], sort_keys=True))
PY
```
Output:
```text
{"entry_candidates": 0, "entry_confirmed_count": 1, "exit_count": 0, "risk_blocked_count": 1, "score_blocked_count": 1, "setup_count": 1, "signals_produced": 2, "total_bars": 2}
{"AAPL": {"entry_candidates": 0, "risk_blocked_count": 0, "score_blocked_count": 1, "score_buckets": {"50-55": 0, "55-60": 1, "60-65": 0, "65-70": 0, "70+": 0, "<50": 0}, "score_max": 58.0, "score_mean": 58.0, "score_min": 58.0, "signals_produced": 1, "stages": {"entry_confirmed": 0, "exit": 0, "setup": 1}, "total_bars": 1}, "GS": {"entry_candidates": 0, "risk_blocked_count": 1, "score_blocked_count": 0, "score_buckets": {"50-55": 0, "55-60": 0, "60-65": 0, "65-70": 0, "70+": 1, "<50": 0}, "score_max": 80.0, "score_mean": 80.0, "score_min": 80.0, "signals_produced": 1, "stages": {"entry_confirmed": 1, "exit": 0, "setup": 0}, "total_bars": 1}}
```

### Scope confirmation
No strategy/risk/paper/live/broker/roadmap/governance/dashboard files were changed. Modified files remain limited to:
- `scripts/export_historical_snapshots.py`
- `tests/scripts/test_export_historical_snapshots.py`

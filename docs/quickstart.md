# Quickstart - Cilly Trading Engine

## 1. Prerequisites
- Python 3.12+
- Git installed

## 2. Clone the Repository
```bash
git clone <repo-url>
cd Trading-engine
```

## 3. Create Virtual Environment

### PowerShell (Windows)
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
python -m pip install -e ".[test]"
```

### Bash (macOS/Linux)
```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -e ".[test]"
```

The canonical dependency install path is the repository `pyproject.toml` via
`python -m pip install -e ".[test]"`.

## 4. Run Deterministic Smoke Test

### PowerShell
```powershell
$env:PYTHONPATH = "src"
python -c "from cilly_trading.smoke_run import run_smoke_run; raise SystemExit(run_smoke_run())"
```

### Bash
```bash
PYTHONPATH=src python -c 'from cilly_trading.smoke_run import run_smoke_run; raise SystemExit(run_smoke_run())'
```

## 5. Expected Output (Exact)
```text
SMOKE_RUN:START
SMOKE_RUN:FIXTURES_OK
SMOKE_RUN:CHECKS_OK
SMOKE_RUN:END
```

Exit code must be 0.
Any deviation indicates a broken environment.

## 6. Start the Local API

Run this from the repository root after the virtual environment is active.

### PowerShell (Windows)
```powershell
$env:PYTHONPATH = "src"
uvicorn api.main:app --reload
```

### Bash (macOS/Linux)
```bash
PYTHONPATH=src uvicorn api.main:app --reload
```

This is the canonical local startup path documented in `docs/local_run.md`.

## 7. Verify Local Health

In a second terminal:

### PowerShell (Windows)
```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
```

### Bash (macOS/Linux)
```bash
curl http://127.0.0.1:8000/health
```

Expected output:

```json
{"status":"ok"}
```

## 8. Stop or Reset

- Stop the running API with `Ctrl+C` in the terminal where `uvicorn` is running.
- For a full local reset, see `docs/local_run.md` and `docs/GETTING_STARTED.md`.

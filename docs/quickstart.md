# Quickstart – Cilly Trading Engine

## 1. Prerequisites
- Python 3.10+
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
python -m pip install -r requirements.txt
```

### Bash (macOS/Linux)
```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -r requirements.txt
```

This repository includes `requirements.txt`, so install dependencies with that file.

## 4. Run Deterministic Smoke Test

### PowerShell
```powershell
$env:PYTHONPATH="src"
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

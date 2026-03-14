# Getting Started (Owner)

## A. Purpose
This guide provides the single authoritative path for owners to start and access the application locally. Follow the steps in order to verify the API is running and then stop/reset it cleanly.

## B. Prerequisites
- Python 3.12+
- `pip`

## C. Single Authoritative Start Method (canonical)
From the repository root, run exactly:

### Bash (macOS/Linux)

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[test]"
PYTHONPATH=src uvicorn api.main:app --reload
```

### PowerShell (Windows)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[test]"
$env:PYTHONPATH = "src"
uvicorn api.main:app --reload
```

The install step is canonical because it comes from the repository-controlled
`pyproject.toml`. It replaces older requirements-file-based instructions.

## D. Secondary / utility entrypoints (not canonical)
- `PYTHONPATH=src python -m api.main`
- `docker compose up --build`

Use these only as alternatives. The canonical owner startup path is Section C.

## E. Single Access Endpoint
Use this endpoint to access the running application:

- http://127.0.0.1:8000/health

## F. Success Indicator
The application is running when the endpoint returns exactly:

```json
{"status":"ok"}
```

## G. Clean Stop Procedure
1. In the terminal where `uvicorn` is running, press `Ctrl+C` once.
2. Wait until shutdown completes and the terminal prompt returns.
3. Optional confirmation:

### Bash (macOS/Linux)

```bash
curl --fail http://127.0.0.1:8000/health
```

### PowerShell (Windows)

```powershell
try {
  Invoke-WebRequest http://127.0.0.1:8000/health -ErrorAction Stop | Out-Null
  throw "API still running"
} catch {
  if ($_.Exception.Message -eq "API still running") { throw }
}
```

After stopping `uvicorn`, the command exits non-zero because the endpoint is unreachable.

## H. Reset Local Runtime State
Run from repository root (local development only):

### Bash (macOS/Linux)

```bash
rm -f cilly_trading.db
```

### PowerShell (Windows)

```powershell
Remove-Item .\cilly_trading.db -ErrorAction SilentlyContinue
```

On next API start, SQLite tables are recreated automatically.

## I. Troubleshooting
- If `uvicorn: command not found` appears, activate the virtual environment again:

  Bash (macOS/Linux):
  ```bash
  source .venv/bin/activate
  ```

  PowerShell (Windows):
  ```powershell
  .\.venv\Scripts\Activate.ps1
  ```

- If `/health` does not respond, confirm the start command is running exactly as documented:

  Bash (macOS/Linux):
  ```bash
  PYTHONPATH=src uvicorn api.main:app --reload
  ```

  PowerShell (Windows):
  ```powershell
  $env:PYTHONPATH = "src"
  uvicorn api.main:app --reload
  ```

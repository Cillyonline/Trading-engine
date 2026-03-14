# Local Development: Run & Analyze

This document defines the canonical local run path for both PowerShell on
Windows and Bash on macOS/Linux. The PowerShell commands below are first-class
instructions, not translations of the Bash path.

## TL;DR Quick Start (fresh local setup)

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

In a second terminal:

### Bash (macOS/Linux)

```bash
curl http://127.0.0.1:8000/health
```

### PowerShell (Windows)

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
```

Expected output:

```json
{"status":"ok"}
```

## Prerequisites

- Python 3.12+
- `pip`

## Canonical local setup path

The canonical local dependency install path is the repository `pyproject.toml`:

### Bash (macOS/Linux)

```bash
python -m pip install -e ".[test]"
```

### PowerShell (Windows)

```powershell
python -m pip install -e ".[test]"
```

Run it from the repository root after activating your virtual environment. This
installs the project and the repo-defined test extra from files that are
versioned in this repository.

## Canonical startup path

The canonical local startup path is:

### Bash (macOS/Linux)

```bash
PYTHONPATH=src uvicorn api.main:app --reload
```

### PowerShell (Windows)

```powershell
$env:PYTHONPATH = "src"
uvicorn api.main:app --reload
```

Run it from the repository root after venv activation and dependency install.

## Canonical configuration boundary

The authoritative configuration contract for local runtime, environment, and
strategy-related inputs is `docs/architecture/configuration_boundary.md`.

For local runs, that contract currently spans:

- process environment inputs such as `CILLY_LOG_LEVEL`
- process-wide runtime constants such as `SIGNALS_READ_MAX_LIMIT`
- request-scoped API inputs such as `market_type`, `lookback_days`, and
  `strategy_config`
- strategy-schema defaults and validation rules in
  `src/cilly_trading/strategies/config_schema.py`

This document describes how to start the app locally. It is not the authority
for configuration precedence or validation ownership.

## Secondary / utility entrypoints (not canonical)

- `PYTHONPATH=src python -m api.main` (starts same FastAPI app via module `__main__` block)
- `docker compose up --build` (containerized local run)
- `PYTHONPATH=src python -m cilly_trading.engine.deterministic_run --fixtures-dir fixtures/deterministic-analysis --output tests/output/deterministic-analysis.json` (deterministic offline utility run)

There is no installed top-level project CLI command (for example `cilly-trading ...`).

## Step-by-step (fresh clone -> analysis request -> persisted signals)

1) **Create and activate a virtual environment**

### Bash (macOS/Linux)

```bash
python -m venv .venv
source .venv/bin/activate
```

### PowerShell (Windows)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2) **Install dependencies**

### Bash (macOS/Linux)

```bash
python -m pip install -e ".[test]"
```

### PowerShell (Windows)

```powershell
python -m pip install -e ".[test]"
```

3) **Start the API (terminal A)**

### Bash (macOS/Linux)

```bash
PYTHONPATH=src uvicorn api.main:app --reload
```

### PowerShell (Windows)

```powershell
$env:PYTHONPATH = "src"
uvicorn api.main:app --reload
```

4) **Verify API health (terminal B)**

### Bash (macOS/Linux)

```bash
curl http://127.0.0.1:8000/health
```

### PowerShell (Windows)

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
```

Expected output:

```json
{"status":"ok"}
```

5) **Create a demo snapshot and capture `ingestion_run_id` (terminal B)**

### Bash (macOS/Linux)

```bash
SNAPSHOT_ID=$(python scripts/create_demo_snapshot.py | awk -F'= ' '/ingestion_run_id/{print $2}')
echo "$SNAPSHOT_ID"
```

### PowerShell (Windows)

```powershell
$snapshotOutput = python scripts/create_demo_snapshot.py
$SNAPSHOT_ID = ($snapshotOutput | Select-String "ingestion_run_id = ").ToString().Split("= ")[1].Trim()
$SNAPSHOT_ID
```

Expected behavior:
- command prints a UUID value
- this value is required by snapshot-only analysis endpoints

6) **Trigger strategy analysis using the created snapshot (terminal B)**

### Bash (macOS/Linux)

```bash
curl -X POST "http://127.0.0.1:8000/strategy/analyze" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -d "{
    \"ingestion_run_id\": \"$SNAPSHOT_ID\",
    \"symbol\": \"AAPL\",
    \"strategy\": \"RSI2\",
    \"market_type\": \"stock\",
    \"lookback_days\": 200
  }"
```

### PowerShell (Windows)

```powershell
$body = @{
  ingestion_run_id = $SNAPSHOT_ID
  symbol = "AAPL"
  strategy = "RSI2"
  market_type = "stock"
  lookback_days = 200
} | ConvertTo-Json

Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8000/strategy/analyze" `
  -ContentType "application/json" `
  -Body $body
```

Expected output shape:

```json
{
  "symbol": "AAPL",
  "strategy": "RSI2",
  "signals": []
}
```

(`signals` may be empty or contain one/more signal objects depending on snapshot data.)

7) **Verify persisted signals (terminal B)**

### Bash (macOS/Linux)

```bash
curl -X GET "http://127.0.0.1:8000/signals?strategy=RSI2&ingestion_run_id=$SNAPSHOT_ID&limit=10" \
  -H "Accept: application/json"
```

### PowerShell (Windows)

```powershell
Invoke-RestMethod `
  -Method Get `
  -Uri "http://127.0.0.1:8000/signals?strategy=RSI2&ingestion_run_id=$SNAPSHOT_ID&limit=10" `
  -Headers @{ Accept = "application/json" }
```

Expected output shape:

```json
{
  "items": [],
  "limit": 10,
  "offset": 0,
  "total": 0
}
```

## Stop / Reset

### Stop API
In terminal A (where `uvicorn` runs), press `Ctrl+C` once.

Optional verification:

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

This returns non-zero after successful stop.

### Reset local DB (non-Docker)

### Bash (macOS/Linux)

```bash
rm -f cilly_trading.db
```

### PowerShell (Windows)

```powershell
Remove-Item .\cilly_trading.db -ErrorAction SilentlyContinue
```

Then restart API with the canonical startup command.

### Reset local DB (Docker)

```bash
docker compose down -v
```

Safety note: reset deletes local signals, analysis runs, ingestion runs, and snapshot rows.

### Optional shell cleanup after stopping

If you want to clear the local shell session variable used by the canonical
startup path:

### Bash (macOS/Linux)

```bash
unset PYTHONPATH
```

### PowerShell (Windows)

```powershell
Remove-Item Env:PYTHONPATH -ErrorAction SilentlyContinue
```

## Common setup errors & fixes

1) **Missing snapshot reference (422)**
- Symptom: `{"detail":"ingestion_run_not_found"}` or `{"detail":"ingestion_run_not_ready"}`
- Fix: run `python scripts/create_demo_snapshot.py`, capture `ingestion_run_id`, and reuse it in the request.

2) **Unknown strategy (400)**
- Symptom: `{"detail":"Unknown strategy: <strategy>"}`
- Fix: use supported strategies: `RSI2` or `TURTLE`.

3) **Missing required field (422)**
- Symptom: `422 Unprocessable Entity` with missing field details.
- Fix: provide required request fields, including `ingestion_run_id` for snapshot-only analysis endpoints.

4) **invalid_ingestion_run_id (422)**
- Symptom: `{"detail":"invalid_ingestion_run_id"}`
- Fix: provide a valid UUIDv4 string.

## Run tests (optional)

### Bash (macOS/Linux)

```bash
python -m pytest -q
```

### PowerShell (Windows)

```powershell
python -m pytest -q
```

See `docs/testing.md` for the canonical test setup and command, and see
`docs/architecture/configuration_boundary.md` for the canonical configuration
contract used by follow-up runtime-boundary work.

# Getting Started (Owner)

## A. Purpose
This guide provides the single authoritative path for owners to start and access the application locally. Follow the steps in order to verify the API is running and then stop/reset it cleanly.

## B. Prerequisites
- Python 3.10+
- `pip`

## C. Single Authoritative Start Method (canonical)
From the repository root, run exactly:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
PYTHONPATH=src uvicorn api.main:app --reload
```

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

```bash
curl --fail http://127.0.0.1:8000/health
```

After stopping `uvicorn`, the command exits non-zero because the endpoint is unreachable.

## H. Reset Local Runtime State
Run from repository root (local development only):

```bash
rm -f cilly_trading.db
```

On next API start, SQLite tables are recreated automatically.

## I. Troubleshooting
- If `uvicorn: command not found` appears, activate the virtual environment again:

  ```bash
  source .venv/bin/activate
  ```

- If `/health` does not respond, confirm the start command is running exactly as documented:

  ```bash
  PYTHONPATH=src uvicorn api.main:app --reload
  ```

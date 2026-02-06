# Getting Started (Owner)

## A. Purpose
This guide provides the single authoritative path for owners to start and access the application locally. Follow the steps in order to verify the API is running and then stop it cleanly.

## B. Prerequisites
- Python 3.10+
- `pip`

## C. Single Authoritative Start Method
From the repository root, run exactly:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
PYTHONPATH=src uvicorn api.main:app --reload
```

## D. Single Access Endpoint
Use this endpoint to access the running application:

- http://127.0.0.1:8000/health

## E. Success Indicator
The application is running when the endpoint returns exactly:

```json
{"status":"ok"}
```

## F. Clean Stop Procedure
1. In the terminal where `uvicorn` is running, press `Ctrl+C` once.
2. Wait until the shutdown completes and the terminal prompt returns.
3. Optional confirmation:

```bash
curl http://127.0.0.1:8000/health
After stopping uvicorn, the endpoint is no longer reachable.

## G. Troubleshooting
- If `uvicorn: command not found` appears, activate the virtual environment again:

  ```bash
  source .venv/bin/activate
  ```

- If `/health` does not respond, confirm the start command is running exactly as documented:

  ```bash
  PYTHONPATH=src uvicorn api.main:app --reload
  ```

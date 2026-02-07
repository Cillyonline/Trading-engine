# Owner Runbook: Start / Stop / Logs / Reset Cheatsheet

## Purpose & Safety Notes
This runbook gives owners a short, safe checklist to run, stop, monitor, and reset the local system.

- Use this checklist exactly as written.
- Perform these steps only in your local environment.
- Keep commands and outputs visible while you operate.

## Canonical startup path (owner default)
Run from the repository root:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
PYTHONPATH=src uvicorn api.main:app --reload
```

What happens: FastAPI starts locally on port `8000`, and SQLite tables are initialized in `cilly_trading.db`.

Expected success signal (run in a second terminal):

```bash
curl http://127.0.0.1:8000/health
```

Expected response:

```json
{"status":"ok"}
```

## Secondary / utility entrypoints (not the default owner path)
- Module start (same API app, without typing the uvicorn target):
  ```bash
  PYTHONPATH=src python -m api.main
  ```
- Docker Compose start:
  ```bash
  docker compose up --build
  ```

These are valid utility paths, but the canonical owner path is `PYTHONPATH=src uvicorn api.main:app --reload`.

## Stop
Action (terminal where the server is running):
- Press `Ctrl+C` once.

Expected success signal (from another terminal):

```bash
curl --fail http://127.0.0.1:8000/health
```

The command exits non-zero because the service is no longer reachable.

## Logs
Action:
- Read the terminal where `uvicorn` runs; runtime logs are written there.

Optional follow mode:

```bash
PYTHONPATH=src uvicorn api.main:app --reload 2>&1 | tee local-api.log
```

What happens: logs stream to terminal and also to `local-api.log`.

## Reset / Cleanup
> ⚠ WARNING — LOCAL DEVELOPMENT ONLY
>
> NEVER run this on production or shared systems.

Action:

```bash
rm -f cilly_trading.db
```

What happens: Local runtime state is cleared for a fresh local start.

Expected success signal:
- `cilly_trading.db` is removed.
- After the next API start, `cilly_trading.db` is created again.

## Troubleshooting
- If start fails, rerun the canonical startup command and read the first error line.
- If `/health` fails while server is running, confirm the process uses `127.0.0.1:8000`.
- If logs look empty, ensure you are looking at the terminal where `uvicorn` is running.
- If reset appears ineffective, stop the API first, run `rm -f cilly_trading.db`, then start again.

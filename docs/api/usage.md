# API Usage – Local Testing

## 1. What this document covers

- Start the FastAPI app locally
- Verify OpenAPI and Swagger UI
- Run read-only test calls
- Interpret common HTTP status codes

## 2. Start the API (uvicorn)

### PowerShell (Windows)

Set `PYTHONPATH` for PowerShell and start uvicorn with reload:

```powershell
$env:PYTHONPATH="src"
uvicorn api.main:app --reload
```

### Bash (macOS/Linux)

```bash
PYTHONPATH=src uvicorn api.main:app --reload
```

Expected startup line (approx.):

```text
Uvicorn running on http://127.0.0.1:8000
```

## 3. Open Swagger UI and OpenAPI

- Swagger UI: http://127.0.0.1:8000/docs
- OpenAPI JSON: http://127.0.0.1:8000/openapi.json

`/docs` is the interactive UI for trying endpoints manually. `/openapi.json` is the machine-readable API specification.

## 4. Read-only example calls

Use only `GET` requests for local, non-mutating checks.

### Example 1 (curl)

```bash
curl http://127.0.0.1:8000/openapi.json
```

### Example 2 (Swagger UI)

1. Open http://127.0.0.1:8000/docs.
2. Select any `GET` endpoint from the list.
3. Click **Try it out**.
4. Click **Execute**.
5. Observe the HTTP status (`200` or `422`, depending on required parameters).

### Example 3 (Swagger UI with optional query parameters)

1. In Swagger UI, choose a `GET` endpoint that supports optional query parameters.
2. Enter one or more optional query parameter values.
3. Click **Execute**.
4. Observe the returned JSON payload.

## 5. Expected HTTP status codes

- `200 OK`: Request succeeded.
- `404 Not Found`: Path does not exist.
- `422 Unprocessable Entity`: Validation failed (for example, missing or invalid query parameters).
- `500 Internal Server Error`: Server-side bug; capture API logs for diagnosis.

## 6. Stop the server

Press `Ctrl+C` in the terminal where uvicorn is running.

# Local Development: Run & Test

## Prerequisites

- Python 3.10+
- `pip`

## Local setup

```bash
python -m venv .venv
```

```bash
source .venv/bin/activate
```

```bash
pip install -r requirements.txt
```

## Run the engine

No CLI entrypoint yet; see Issue #15.

## Run the API

```bash
uvicorn api.main:app --reload
```

```bash
curl http://127.0.0.1:8000/health
```

## Run the API with Docker

```bash
docker compose up --build
```

```bash
curl http://127.0.0.1:8000/health
```

SQLite persistence is handled via a named Docker volume. Stopping and starting
the container will keep the data:

```bash
docker compose down
docker compose up
```

To reset the local SQLite database, remove the volume:

```bash
docker compose down -v
```

## Run tests

```bash
python -m pytest
```

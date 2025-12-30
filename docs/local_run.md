# Local Development: Run & Test

## Prerequisites

- Python 3.10+
- `pip`

## Local setup

```bash
python -m venv .venv
source .venv/bin/activate
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

## Acceptance criteria

docker compose up starts the API successfully

SQLite data persists after container restart

No runtime behavior changes beyond containerization

Documentation clearly explains local Docker run

## Test requirements

No tests required (container/docs change only)

However, validate basic run path:

```bash
docker compose up --build
```

```bash
curl http://127.0.0.1:8000/health
```

restart: docker compose down then docker compose up

DB file should exist in volume-mounted working dir (/data/cilly_trading.db)

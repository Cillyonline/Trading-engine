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

## Run tests

```bash
python -m pytest
```

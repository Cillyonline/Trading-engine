FROM python:3.12.8-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN python -m pip install -U pip uv

COPY pyproject.toml uv.lock README.md ./
COPY src ./src
COPY scripts ./scripts

RUN uv sync --frozen --no-dev
RUN mkdir -p /data/db /data/artifacts /data/logs /data/runtime-state /app/runs/phase6

ENV PATH="/app/.venv/bin:${PATH}" \
    PYTHONPATH="/app/src" \
    CILLY_DB_PATH="/data/db/cilly_trading.db"

WORKDIR /data

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 CMD python -c "import json, urllib.request; request = urllib.request.Request('http://127.0.0.1:8000/health/engine', headers={'X-Cilly-Role': 'read_only'}); payload = json.load(urllib.request.urlopen(request, timeout=3)); raise SystemExit(0 if payload.get('ready') else 1)"

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]

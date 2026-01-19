# Exploration Guide: Cilly Trading Engine MVP v1.1 (Snapshot-First)

This guide documents **current behavior only**. It is written for a single technical user exploring the MVP locally in VS Code. It assumes you will run the API and issue HTTP requests from a terminal. All analysis is snapshot-first and deterministic when using the API endpoints described below.

---

## 1. What This Product Is (Today)

**What the MVP actually does**

- Provides a FastAPI service with analysis endpoints that **only** run against existing snapshot data in SQLite. The API enforces snapshot readiness before analysis and always uses the snapshot-only execution path. 【F:api/main.py†L620-L898】【F:docs/api/usage_contract.md†L9-L49】
- Runs two implemented strategies: `RSI2` and `TURTLE`. 【F:api/main.py†L287-L295】【F:docs/api/usage_contract.md†L70-L73】
- Stores generated signals and manual analysis runs in SQLite (`cilly_trading.db`). 【F:src/cilly_trading/db/init_db.py†L10-L77】【F:api/main.py†L770-L855】
- Exposes read endpoints for stored signals (`GET /signals`) and screener results (`GET /screener/v2/results`). 【F:api/main.py†L468-L615】

**What it explicitly does NOT do yet**

- It does **not** ingest snapshots. Snapshot ingestion is out-of-band; the repository only reads snapshots already present in the database. 【F:docs/analyst-workflow.md†L15-L23】【F:docs/api/usage_contract.md†L21-L32】
- It does **not** run live data pulls when using the API. All API analysis is snapshot-only; live/external data is only used by engine calls outside the API. 【F:docs/api/usage_contract.md†L13-L52】【F:src/cilly_trading/engine/data.py†L96-L207】
- It does **not** support live trading, broker integrations, backtesting, or AI-based decision logic. 【F:docs/analyst-workflow.md†L56-L56】

---

## 2. Core Mental Model

### Snapshot-first execution

- Every analysis request must reference an existing `ingestion_run_id`. The API validates the ID and checks that snapshot rows exist for every requested symbol and timeframe (D1). 【F:docs/analyst-workflow.md†L24-L30】【F:api/main.py†L314-L344】
- When the API runs analysis, it forces `snapshot_only=True`, so data is loaded **only** from `ohlcv_snapshots`. 【F:docs/analyst-workflow.md†L31-L41】【F:api/main.py†L359-L366】

### Determinism vs non-determinism

- **Deterministic path (API):** The API uses snapshot-only analysis, so the same snapshot produces the same signals. 【F:docs/analyst-workflow.md†L31-L50】【F:docs/api/usage_contract.md†L43-L49】
- **Non-deterministic path (engine only):** Direct engine calls with `snapshot_only=False` can pull live data from Yahoo Finance or Binance via `yfinance`/`ccxt`, which varies over time. This is **not** the API path. 【F:docs/api/usage_contract.md†L49-L52】【F:src/cilly_trading/engine/data.py†L96-L207】

### Why snapshots exist and what problem they solve

- Snapshots create a fixed, immutable dataset so analysis runs can be repeated and compared without data drift. Immutability is enforced by SQLite triggers that block updates/deletes on `ohlcv_snapshots`. 【F:docs/analyst-workflow.md†L20-L23】【F:src/cilly_trading/db/init_db.py†L156-L195】

---

## 3. Where Data Comes From

### Yahoo / external sources

- The engine **can** load live stock data from Yahoo Finance and crypto data from Binance via `yfinance` and `ccxt`. This happens only in non-snapshot engine calls. 【F:src/cilly_trading/engine/data.py†L96-L207】

### Why live data is NOT used by the API

- The API endpoints enforce snapshot-only execution and require `ingestion_run_id`. Live data is not consulted when using `/strategy/analyze`, `/analysis/run`, or `/screener/basic`. 【F:docs/api/usage_contract.md†L13-L49】【F:api/main.py†L620-L898】

### What “out-of-band ingestion” means in practice

- This repository does **not** create `ingestion_runs` or populate `ohlcv_snapshots`. Those rows must be inserted externally. The API only reads what already exists in the SQLite database. 【F:docs/analyst-workflow.md†L15-L23】【F:docs/api/usage_contract.md†L21-L32】

---

## 4. How to Use the Product (Step-by-Step)

### Local setup assumptions

- You are running locally in VS Code with a Python 3.10+ environment.
- The SQLite database file is `cilly_trading.db` in the project root. 【F:src/cilly_trading/db/init_db.py†L1-L23】
- Snapshot data (`ingestion_runs` and `ohlcv_snapshots`) already exists in that database (inserted out-of-band). 【F:docs/analyst-workflow.md†L15-L30】

### Step 1 — Start the API

From the VS Code terminal:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
PYTHONPATH=src uvicorn api.main:app --reload
```

The API defaults to `http://127.0.0.1:8000`. 【F:docs/local_run.md†L7-L31】

### Step 2 — Confirm the API is running

```bash
curl http://127.0.0.1:8000/health
```

Expected:

```json
{"status":"ok"}
```

【F:api/main.py†L292-L312】

### Step 3 — Confirm you have a valid snapshot ID

You **must** supply a valid UUIDv4 `ingestion_run_id` that exists in `ingestion_runs` and has at least one `ohlcv_snapshots` row for each requested symbol/timeframe. If either check fails, the API returns `422` with an error code. 【F:docs/api/usage_contract.md†L34-L63】【F:api/main.py†L304-L344】

Practical check (from a VS Code terminal):

```bash
sqlite3 cilly_trading.db "SELECT ingestion_run_id, timeframe, created_at FROM ingestion_runs ORDER BY created_at DESC LIMIT 5;"
```

```bash
sqlite3 cilly_trading.db "SELECT symbol, timeframe, COUNT(*) FROM ohlcv_snapshots WHERE ingestion_run_id='<YOUR_ID>' GROUP BY symbol, timeframe;"
```

> Use the `ingestion_run_id` that has rows for your target symbols and timeframe `D1`.

### Step 4 — Trigger analysis for a single symbol

#### Option A: `/strategy/analyze` (single strategy, optional presets)

```bash
curl -X POST "http://127.0.0.1:8000/strategy/analyze" \
  -H "Content-Type: application/json" \
  -d '{
    "ingestion_run_id": "<YOUR_INGESTION_RUN_ID>",
    "symbol": "AAPL",
    "strategy": "RSI2",
    "market_type": "stock",
    "lookback_days": 200
  }'
```

- Required inputs: `ingestion_run_id`, `symbol`, `strategy`, `market_type` (`stock` or `crypto`), `lookback_days` (30–1000). 【F:api/main.py†L56-L118】
- This endpoint runs **one strategy** for one symbol and returns signals directly. 【F:api/main.py†L620-L769】

#### Option B: `/analysis/run` (manual analysis with deterministic run ID)

```bash
curl -X POST "http://127.0.0.1:8000/analysis/run" \
  -H "Content-Type: application/json" \
  -d '{
    "ingestion_run_id": "<YOUR_INGESTION_RUN_ID>",
    "symbol": "AAPL",
    "strategy": "TURTLE",
    "market_type": "stock",
    "lookback_days": 200
  }'
```

- The API computes a deterministic `analysis_run_id` based on the request payload. Repeating the same request returns the same stored result. 【F:api/main.py†L770-L855】

### Step 5 — Run the basic screener

```bash
curl -X POST "http://127.0.0.1:8000/screener/basic" \
  -H "Content-Type: application/json" \
  -d '{
    "ingestion_run_id": "<YOUR_INGESTION_RUN_ID>",
    "market_type": "stock",
    "lookback_days": 200,
    "min_score": 30.0
  }'
```

- If `symbols` is omitted, the screener uses a default watchlist (stocks: `AAPL`, `MSFT`, `NVDA`, `META`, `TSLA`; crypto: `BTC/USDT`, `ETH/USDT`, `SOL/USDT`, `BNB/USDT`, `XRP/USDT`). 【F:api/main.py†L860-L883】
- The response groups setup signals by symbol and filters by `min_score`. 【F:api/main.py†L884-L980】

### Step 6 — Read stored signals

```bash
curl -X GET "http://127.0.0.1:8000/signals?strategy=RSI2&limit=10" \
  -H "Accept: application/json"
```

- Use filters (`symbol`, `strategy`, `preset`, `from`/`to`) and pagination (`limit`, `offset`) to inspect stored results. 【F:api/main.py†L341-L615】

---

## 5. Understanding the Results

### What signals mean

Signals are structured outputs produced by strategies and stored in SQLite. Each signal includes fields like `stage` (`setup` or `entry_confirmed`), `score` (0–100), and `confirmation_rule`. 【F:src/cilly_trading/models.py†L33-L73】【F:src/cilly_trading/strategies/turtle.py†L1-L134】

- `RSI2` produces **setup** signals when the last bar’s RSI is oversold enough. 【F:src/cilly_trading/strategies/rsi2.py†L1-L114】
- `TURTLE` produces **setup** or **entry_confirmed** signals depending on whether the last close is near or above the breakout level. 【F:src/cilly_trading/strategies/turtle.py†L1-L134】

### What empty results mean

Empty results are valid and common. They mean **no signal conditions were met** for the given symbol and snapshot. Strategies only emit signals when their rules are triggered on the latest bar. 【F:src/cilly_trading/strategies/rsi2.py†L69-L114】【F:src/cilly_trading/strategies/turtle.py†L62-L134】

### Difference between “no signal” and “skipped strategy”

- **No signal:** The strategy ran successfully but returned an empty list because conditions were not met. 【F:src/cilly_trading/strategies/rsi2.py†L69-L114】
- **Skipped strategy:** The strategy config was invalid (wrong type, out-of-range values, or alias conflicts). The engine logs an error and skips that strategy, producing no signals while still returning `200 OK`. 【F:docs/api/usage_contract.md†L85-L107】【F:docs/strategy-configs.md†L9-L44】

### Common valid outcomes

- `signals: []` on `/strategy/analyze` or `/analysis/run` means “no signal.” 【F:api/main.py†L747-L768】【F:api/main.py†L820-L855】
- `/screener/basic` may return an empty `symbols` list if no setups meet the `min_score` threshold. 【F:api/main.py†L884-L980】

---

## 6. Exploration Playbook (Several Days)

### Day 1 — Verify snapshot readiness and baseline runs

- Identify a valid `ingestion_run_id` and confirm symbols/timeframe coverage in SQLite. 【F:docs/api/usage_contract.md†L34-L39】
- Run `/strategy/analyze` for one symbol and one strategy to confirm the snapshot path works. 【F:api/main.py†L620-L769】
- Run `/analysis/run` for the same inputs and confirm the `analysis_run_id` stays the same on repeat. 【F:api/main.py†L770-L855】

### Day 2 — Expand symbols and compare strategies

- Pick 3–5 symbols that exist in your snapshot and run:
  - `RSI2` vs `TURTLE` on the same symbol.
  - `stock` vs `crypto` symbols (if both are in the snapshot). 【F:api/main.py†L620-L769】
- Use `/signals` to confirm signals are persisted and filter by strategy. 【F:api/main.py†L341-L615】

### Day 3 — Screener behavior and threshold sensitivity

- Run `/screener/basic` with default watchlists and adjust `min_score` to see how results change. 【F:api/main.py†L860-L980】
- Record which symbols appear as setups at different thresholds. 【F:api/main.py†L884-L980】

### What NOT to change during exploration

- Do **not** modify snapshot data during exploration; snapshot immutability is part of the deterministic model. 【F:src/cilly_trading/db/init_db.py†L182-L195】
- Do **not** bypass API endpoints with direct engine calls if you want deterministic results. 【F:docs/analyst-workflow.md†L53-L56】

---

## 7. How to Judge Success or Failure

### Signals of success

- The API accepts valid `ingestion_run_id` values and returns `200 OK` for analysis endpoints. 【F:api/main.py†L620-L898】
- Repeating the same `/analysis/run` request returns the same `analysis_run_id` and the same result. 【F:api/main.py†L770-L855】
- Signals are persisted and can be retrieved via `/signals`. 【F:api/main.py†L468-L615】

### Signals of concern

- `422 ingestion_run_not_found` or `422 ingestion_run_not_ready` indicates missing or incomplete snapshot data. 【F:docs/api/usage_contract.md†L54-L63】
- `422 snapshot_data_invalid` indicates snapshot rows exist but fail validation. 【F:docs/api/usage_contract.md†L63-L63】【F:src/cilly_trading/engine/data.py†L120-L175】
- `200 OK` with **consistently empty** results across multiple symbols may mean snapshot data is too sparse for the strategies’ requirements. 【F:src/cilly_trading/strategies/turtle.py†L72-L96】

### When exploration should stop

- If you cannot obtain a valid snapshot (`ingestion_runs` + `ohlcv_snapshots`) that passes readiness checks, exploration cannot proceed because the API will not run analysis. 【F:docs/api/usage_contract.md†L34-L63】【F:api/main.py†L304-L344】
- If repeated, valid runs return no signals across multiple symbols and strategies, you likely lack sufficient snapshot coverage or the market conditions don’t match current strategy rules. 【F:src/cilly_trading/strategies/rsi2.py†L69-L114】【F:src/cilly_trading/strategies/turtle.py†L72-L134】

---

## 8. How to Capture Learnings

### What to write down

- The `ingestion_run_id` used, symbols tested, and endpoints called. 【F:docs/api/usage_contract.md†L34-L39】【F:api/main.py†L620-L898】
- Strategy config changes (if any), including exact parameters and whether they caused skips. 【F:docs/strategy-configs.md†L9-L44】【F:docs/api/usage_contract.md†L85-L107】
- Observed outputs: number of signals, stages, and scores from `/strategy/analyze`, `/analysis/run`, and `/screener/basic`. 【F:api/main.py†L620-L980】

### What decisions should be supported by evidence

- Whether snapshot coverage is sufficient to evaluate the strategies (check symbol/timeframe coverage and signal output rates). 【F:docs/api/usage_contract.md†L34-L39】【F:api/main.py†L884-L980】
- Whether deterministic behavior holds (repeat `/analysis/run` with identical input and verify results are the same). 【F:api/main.py†L770-L855】

### What questions remain open after exploration

- If you see empty results, determine whether they are due to market conditions or insufficient snapshot history (e.g., Turtle requires enough lookback bars for a breakout window). 【F:src/cilly_trading/strategies/turtle.py†L72-L96】
- If a strategy was skipped, confirm the exact config key/type conflict that caused it. 【F:docs/strategy-configs.md†L9-L44】

---

## Appendix: Required Inputs by Endpoint (Snapshot-Only)

- `POST /strategy/analyze`: `ingestion_run_id`, `symbol`, `strategy`, `market_type`, `lookback_days` (30–1000). 【F:api/main.py†L56-L118】
- `POST /analysis/run`: `ingestion_run_id`, `symbol`, `strategy`, `market_type`, `lookback_days` (30–1000). 【F:api/main.py†L120-L154】
- `POST /screener/basic`: `ingestion_run_id`, `market_type`, `lookback_days` (30–1000), `min_score` (0–100). 【F:api/main.py†L156-L193】

If you follow the steps above, you can explore the MVP’s current behavior without modifying runtime code or adding new features.

# Exploration Guide: Cilly Trading Engine MVP v1.1 (Snapshot-First)

This guide documents **current behavior only**. It is written for a single technical user exploring the MVP locally in VS Code. It assumes you will run the API and issue HTTP requests from a terminal. All analysis is snapshot-first and deterministic when using the API endpoints described below.

---

## 1. What This Product Is (Today)

**What the MVP actually does**

- Provides a FastAPI service with analysis endpoints that **only** run against existing snapshot data in SQLite. The API enforces snapshot readiness before analysis and always uses the snapshot-only execution path. ã€F:api/main.pyâ€ L620-L898ã€‘ã€F:docs/operations/api/usage_contract.mdâ€ L9-L49ã€‘
- Runs two implemented strategies: `RSI2` and `TURTLE`. ã€F:api/main.pyâ€ L287-L295ã€‘ã€F:docs/operations/api/usage_contract.mdâ€ L70-L73ã€‘
- Stores generated signals and manual analysis runs in SQLite (`cilly_trading.db`). ã€F:src/cilly_trading/db/init_db.pyâ€ L10-L77ã€‘ã€F:api/main.pyâ€ L770-L855ã€‘
- Exposes read endpoints for stored signals (`GET /signals`) and screener results (`GET /screener/v2/results`). ã€F:api/main.pyâ€ L468-L615ã€‘

**What it explicitly does NOT do yet**

- It does **not** ingest snapshots. Snapshot ingestion is out-of-band; the repository only reads snapshots already present in the database. ã€F:docs/operations/analyst-workflow.mdâ€ L15-L23ã€‘ã€F:docs/operations/api/usage_contract.mdâ€ L21-L32ã€‘
- It does **not** run live data pulls when using the API. All API analysis is snapshot-only; live/external data is only used by engine calls outside the API. ã€F:docs/operations/api/usage_contract.mdâ€ L13-L52ã€‘ã€F:src/cilly_trading/engine/data.pyâ€ L96-L207ã€‘
- It does **not** support live trading, broker integrations, backtesting, or AI-based decision logic. ã€F:docs/operations/analyst-workflow.mdâ€ L56-L56ã€‘

---

## 2. Core Mental Model

### Snapshot-first execution

- Every analysis request must reference an existing `ingestion_run_id`. The API validates the ID and checks that snapshot rows exist for every requested symbol and timeframe (D1). ã€F:docs/operations/analyst-workflow.mdâ€ L24-L30ã€‘ã€F:api/main.pyâ€ L314-L344ã€‘
- When the API runs analysis, it forces `snapshot_only=True`, so data is loaded **only** from `ohlcv_snapshots`. ã€F:docs/operations/analyst-workflow.mdâ€ L31-L41ã€‘ã€F:api/main.pyâ€ L359-L366ã€‘

### Determinism vs non-determinism

- **Deterministic path (API):** The API uses snapshot-only analysis, so the same snapshot produces the same signals. ã€F:docs/operations/analyst-workflow.mdâ€ L31-L50ã€‘ã€F:docs/operations/api/usage_contract.mdâ€ L43-L49ã€‘
- **Non-deterministic path (engine only):** Direct engine calls with `snapshot_only=False` can pull live data from Yahoo Finance or Binance via `yfinance`/`ccxt`, which varies over time. This is **not** the API path. ã€F:docs/operations/api/usage_contract.mdâ€ L49-L52ã€‘ã€F:src/cilly_trading/engine/data.pyâ€ L96-L207ã€‘

### Why snapshots exist and what problem they solve

- Snapshots create a fixed, immutable dataset so analysis runs can be repeated and compared without data drift. Immutability is enforced by SQLite triggers that block updates/deletes on `ohlcv_snapshots`. ã€F:docs/operations/analyst-workflow.mdâ€ L20-L23ã€‘ã€F:src/cilly_trading/db/init_db.pyâ€ L156-L195ã€‘

---

## 3. Where Data Comes From

### Yahoo / external sources

- The engine **can** load live stock data from Yahoo Finance and crypto data from Binance via `yfinance` and `ccxt`. This happens only in non-snapshot engine calls. ã€F:src/cilly_trading/engine/data.pyâ€ L96-L207ã€‘

### Why live data is NOT used by the API

- The API endpoints enforce snapshot-only execution and require `ingestion_run_id`. Live data is not consulted when using `/strategy/analyze`, `/analysis/run`, or `/screener/basic`. ã€F:docs/operations/api/usage_contract.mdâ€ L13-L49ã€‘ã€F:api/main.pyâ€ L620-L898ã€‘

### What â€œout-of-band ingestionâ€ means in practice

- This repository does **not** create `ingestion_runs` or populate `ohlcv_snapshots`. Those rows must be inserted externally. The API only reads what already exists in the SQLite database. ã€F:docs/operations/analyst-workflow.mdâ€ L15-L23ã€‘ã€F:docs/operations/api/usage_contract.mdâ€ L21-L32ã€‘

---

## 4. How to Use the Product (Step-by-Step)

### Local setup assumptions

- You are running locally in VS Code with a Python 3.12+ environment.
- The SQLite database file is `cilly_trading.db` in the project root. ã€F:src/cilly_trading/db/init_db.pyâ€ L1-L23ã€‘
- Snapshot data (`ingestion_runs` and `ohlcv_snapshots`) already exists in that database (inserted out-of-band). ã€F:docs/operations/analyst-workflow.mdâ€ L15-L30ã€‘

### Step 1 - Start the API

From the VS Code terminal:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[test]"
PYTHONPATH=src uvicorn api.main:app --reload
```

The API defaults to `http://127.0.0.1:8000`. ã€F:docs/getting-started/local-run.mdâ€ L7-L31ã€‘

### Step 2 - Confirm the API is running

```bash
curl http://127.0.0.1:8000/health
```

Expected:

```json
{"status":"ok"}
```

ã€F:api/main.pyâ€ L292-L312ã€‘

### Step 3 - Confirm you have a valid snapshot ID

You **must** supply a valid UUIDv4 `ingestion_run_id` that exists in `ingestion_runs` and has at least one `ohlcv_snapshots` row for each requested symbol/timeframe. If either check fails, the API returns `422` with an error code. ã€F:docs/operations/api/usage_contract.mdâ€ L34-L63ã€‘ã€F:api/main.pyâ€ L304-L344ã€‘

Practical check (from a VS Code terminal):

```bash
sqlite3 cilly_trading.db "SELECT ingestion_run_id, timeframe, created_at FROM ingestion_runs ORDER BY created_at DESC LIMIT 5;"
sqlite3 cilly_trading.db "SELECT symbol, timeframe, COUNT(*) FROM ohlcv_snapshots WHERE ingestion_run_id='<YOUR_ID>' GROUP BY symbol, timeframe;"
```

> Use the `ingestion_run_id` that has rows for your target symbols and timeframe `D1`.

### Step 4 - Trigger analysis for a single symbol

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

- Required inputs: `ingestion_run_id`, `symbol`, `strategy`, `market_type` (`stock` or `crypto`), `lookback_days` (30-1000). ã€F:api/main.pyâ€ L56-L118ã€‘
- This endpoint runs **one strategy** for one symbol and returns signals directly. ã€F:api/main.pyâ€ L620-L769ã€‘

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

- The API computes a deterministic `analysis_run_id` based on the request payload. Repeating the same request returns the same stored result. ã€F:api/main.pyâ€ L770-L855ã€‘

### Step 5 - Run the basic screener

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

- If `symbols` is omitted, the screener uses a default watchlist (stocks: `AAPL`, `MSFT`, `NVDA`, `META`, `TSLA`; crypto: `BTC/USDT`, `ETH/USDT`, `SOL/USDT`, `BNB/USDT`, `XRP/USDT`). ã€F:api/main.pyâ€ L860-L883ã€‘
- The response groups setup signals by symbol and filters by `min_score`. ã€F:api/main.pyâ€ L884-L980ã€‘

### Step 6 - Read stored signals

```bash
curl -X GET "http://127.0.0.1:8000/signals?strategy=RSI2&limit=10" \
  -H "Accept: application/json"
```

- Use filters (`symbol`, `strategy`, `timeframe`, `from`/`to`) and pagination (`limit`, `offset`) to inspect stored results. ã€F:api/main.pyâ€ L341-L615ã€‘

---
## 5. Understanding the Results

### What signals mean

Signals are structured outputs produced by strategies and stored in SQLite. Each signal includes fields like `stage` (`setup` or `entry_confirmed`), `score` (0â€“100), and `confirmation_rule`. ã€F:src/cilly_trading/models.pyâ€ L33-L73ã€‘ã€F:src/cilly_trading/strategies/turtle.pyâ€ L1-L134ã€‘

- `RSI2` produces **setup** signals when the last barâ€™s RSI is oversold enough. ã€F:src/cilly_trading/strategies/rsi2.pyâ€ L1-L114ã€‘
- `TURTLE` produces **setup** or **entry_confirmed** signals depending on whether the last close is near or above the breakout level. ã€F:src/cilly_trading/strategies/turtle.pyâ€ L1-L134ã€‘

### What empty results mean

Empty results are valid and common. They mean **no signal conditions were met** for the given symbol and snapshot. Strategies only emit signals when their rules are triggered on the latest bar. ã€F:src/cilly_trading/strategies/rsi2.pyâ€ L69-L114ã€‘ã€F:src/cilly_trading/strategies/turtle.pyâ€ L62-L134ã€‘

### Difference between â€œno signalâ€ and â€œskipped strategyâ€

- **No signal:** The strategy ran successfully but returned an empty list because conditions were not met. ã€F:src/cilly_trading/strategies/rsi2.pyâ€ L69-L114ã€‘
- **Skipped strategy:** The strategy config was invalid (wrong type, out-of-range values, or alias conflicts). The engine logs an error and skips that strategy, producing no signals while still returning `200 OK`. ã€F:docs/operations/api/usage_contract.mdâ€ L85-L107ã€‘ã€F:docs/architecture/strategy-configs.mdâ€ L9-L44ã€‘

### Common valid outcomes

- `signals: []` on `/strategy/analyze` or `/analysis/run` means â€œno signal.â€ ã€F:api/main.pyâ€ L747-L768ã€‘ã€F:api/main.pyâ€ L820-L855ã€‘
- `/screener/basic` may return an empty `symbols` list if no setups meet the `min_score` threshold. ã€F:api/main.pyâ€ L884-L980ã€‘

---

## 6. Exploration Playbook (Several Days)

### Day 1 â€” Verify snapshot readiness and baseline runs

- Identify a valid `ingestion_run_id` and confirm symbols/timeframe coverage in SQLite. ã€F:docs/operations/api/usage_contract.mdâ€ L34-L39ã€‘
- Run `/strategy/analyze` for one symbol and one strategy to confirm the snapshot path works. ã€F:api/main.pyâ€ L620-L769ã€‘
- Run `/analysis/run` for the same inputs and confirm the `analysis_run_id` stays the same on repeat. ã€F:api/main.pyâ€ L770-L855ã€‘

### Day 2 â€” Expand symbols and compare strategies

- Pick 3â€“5 symbols that exist in your snapshot and run:
  - `RSI2` vs `TURTLE` on the same symbol.
  - `stock` vs `crypto` symbols (if both are in the snapshot). ã€F:api/main.pyâ€ L620-L769ã€‘
- Use `/signals` to confirm signals are persisted and filter by strategy. ã€F:api/main.pyâ€ L341-L615ã€‘

### Day 3 â€” Screener behavior and threshold sensitivity

- Run `/screener/basic` with default watchlists and adjust `min_score` to see how results change. ã€F:api/main.pyâ€ L860-L980ã€‘
- Record which symbols appear as setups at different thresholds. ã€F:api/main.pyâ€ L884-L980ã€‘

### What NOT to change during exploration

- Do **not** modify snapshot data during exploration; snapshot immutability is part of the deterministic model. ã€F:src/cilly_trading/db/init_db.pyâ€ L182-L195ã€‘
- Do **not** bypass API endpoints with direct engine calls if you want deterministic results. ã€F:docs/operations/analyst-workflow.mdâ€ L53-L56ã€‘

---

## 7. How to Judge Success or Failure

### Signals of success

- The API accepts valid `ingestion_run_id` values and returns `200 OK` for analysis endpoints. ã€F:api/main.pyâ€ L620-L898ã€‘
- Repeating the same `/analysis/run` request returns the same `analysis_run_id` and the same result. ã€F:api/main.pyâ€ L770-L855ã€‘
- Signals are persisted and can be retrieved via `/signals`. ã€F:api/main.pyâ€ L468-L615ã€‘

### Signals of concern

- `422 ingestion_run_not_found` or `422 ingestion_run_not_ready` indicates missing or incomplete snapshot data. ã€F:docs/operations/api/usage_contract.mdâ€ L54-L63ã€‘
- `422 snapshot_data_invalid` indicates snapshot rows exist but fail validation. ã€F:docs/operations/api/usage_contract.mdâ€ L63-L63ã€‘ã€F:src/cilly_trading/engine/data.pyâ€ L120-L175ã€‘
- `200 OK` with **consistently empty** results across multiple symbols may mean snapshot data is too sparse for the strategiesâ€™ requirements. ã€F:src/cilly_trading/strategies/turtle.pyâ€ L72-L96ã€‘

### When exploration should stop

- If you cannot obtain a valid snapshot (`ingestion_runs` + `ohlcv_snapshots`) that passes readiness checks, exploration cannot proceed because the API will not run analysis. ã€F:docs/operations/api/usage_contract.mdâ€ L34-L63ã€‘ã€F:api/main.pyâ€ L304-L344ã€‘
- If repeated, valid runs return no signals across multiple symbols and strategies, you likely lack sufficient snapshot coverage or the market conditions donâ€™t match current strategy rules. ã€F:src/cilly_trading/strategies/rsi2.pyâ€ L69-L114ã€‘ã€F:src/cilly_trading/strategies/turtle.pyâ€ L72-L134ã€‘

---

## 8. How to Capture Learnings

### What to write down

- The `ingestion_run_id` used, symbols tested, and endpoints called. ã€F:docs/operations/api/usage_contract.mdâ€ L34-L39ã€‘ã€F:api/main.pyâ€ L620-L898ã€‘
- Strategy config changes (if any), including exact parameters and whether they caused skips. ã€F:docs/architecture/strategy-configs.mdâ€ L9-L44ã€‘ã€F:docs/operations/api/usage_contract.mdâ€ L85-L107ã€‘
- Observed outputs: number of signals, stages, and scores from `/strategy/analyze`, `/analysis/run`, and `/screener/basic`. ã€F:api/main.pyâ€ L620-L980ã€‘

### What decisions should be supported by evidence

- Whether snapshot coverage is sufficient to evaluate the strategies (check symbol/timeframe coverage and signal output rates). ã€F:docs/operations/api/usage_contract.mdâ€ L34-L39ã€‘ã€F:api/main.pyâ€ L884-L980ã€‘
- Whether deterministic behavior holds (repeat `/analysis/run` with identical input and verify results are the same). ã€F:api/main.pyâ€ L770-L855ã€‘

### What questions remain open after exploration

- If you see empty results, determine whether they are due to market conditions or insufficient snapshot history (e.g., Turtle requires enough lookback bars for a breakout window). ã€F:src/cilly_trading/strategies/turtle.pyâ€ L72-L96ã€‘
- If a strategy was skipped, confirm the exact config key/type conflict that caused it. ã€F:docs/architecture/strategy-configs.mdâ€ L9-L44ã€‘

---

## Appendix: Required Inputs by Endpoint (Snapshot-Only)

- `POST /strategy/analyze`: `ingestion_run_id`, `symbol`, `strategy`, `market_type`, `lookback_days` (30â€“1000). ã€F:api/main.pyâ€ L56-L118ã€‘
- `POST /analysis/run`: `ingestion_run_id`, `symbol`, `strategy`, `market_type`, `lookback_days` (30â€“1000). ã€F:api/main.pyâ€ L120-L154ã€‘
- `POST /screener/basic`: `ingestion_run_id`, `market_type`, `lookback_days` (30â€“1000), `min_score` (0â€“100). ã€F:api/main.pyâ€ L156-L193ã€‘

If you follow the steps above, you can explore the MVPâ€™s current behavior without modifying runtime code or adding new features.


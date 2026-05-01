# Trade Journal API

The journal API allows manual paper trades to be logged, exited, and analyzed alongside screener signals.

## Authorization

All endpoints use the `X-Cilly-Role` header.

- `operator`: create trades and log exits
- `read_only`: list, filter, analyze, and export trades

---

## Trades

### `POST /journal/trades`

Logs a manually executed trade entry. The optional `signal_id` links the trade to a screener signal.

Request body:

```json
{
  "symbol": "AAPL",
  "strategy": "RSI2",
  "stage": "entry_confirmed",
  "timeframe": "D1",
  "market_type": "stock",
  "data_source": "yahoo",
  "reason_entry": "RSI2 oversold, close above prior high",
  "entry_price": 174.50,
  "entry_date": "2026-04-28",
  "signal_id": "35f95b8f...",
  "notes": "Half position, waiting for confirmation"
}
```

Field rules:

- `symbol`, `strategy`, `timeframe`, `reason_entry` — required, non-empty
- `stage` — `"setup"` or `"entry_confirmed"` (default: `"entry_confirmed"`)
- `market_type` — `"stock"` or `"crypto"` (default: `"stock"`)
- `data_source` — `"yahoo"` or `"binance"` (default: `"yahoo"`)
- `entry_price`, `entry_date`, `signal_id`, `notes` — optional
- Unknown fields are rejected

Returns `201 Created` with the full trade record including `id`, `status: "open"`, and `pnl_pct: null`.

---

### `PUT /journal/trades/{trade_id}/exit`

Logs the exit for an open trade.

Request body:

```json
{
  "exit_price": 181.20,
  "exit_date": "2026-05-02",
  "reason_exit": "Target reached, RSI2 overbought"
}
```

- Returns `404` if the trade does not exist
- Returns `409` if the trade already has an exit
- Returns the updated trade with `status: "closed"` and `pnl_pct` calculated

`pnl_pct` is computed as `(exit_price - entry_price) / entry_price * 100`, rounded to 4 decimal places.

---

### `GET /journal/trades`

Lists trades with optional filters.

Query parameters:

| Parameter | Type | Description |
|-----------|------|-------------|
| `symbol` | string | Filter by exact symbol |
| `strategy` | string | Filter by exact strategy name |
| `signal_id` | string | Filter by linked signal ID |
| `status` | `open` \| `closed` | Filter by trade status |
| `limit` | integer 1–500 | Max results (default: 50) |

Response:

```json
{
  "items": [
    {
      "id": 1,
      "symbol": "AAPL",
      "strategy": "RSI2",
      "stage": "entry_confirmed",
      "entry_price": 174.50,
      "entry_date": "2026-04-28",
      "exit_price": 181.20,
      "exit_date": "2026-05-02",
      "pnl_pct": 3.8394,
      "status": "closed",
      "reason_entry": "RSI2 oversold, close above prior high",
      "reason_exit": "Target reached, RSI2 overbought",
      "signal_id": "35f95b8f...",
      "notes": null,
      "timeframe": "D1",
      "market_type": "stock",
      "data_source": "yahoo"
    }
  ],
  "total": 1
}
```

---

### `GET /journal/trades/export`

Downloads all matching trades as a CSV file (`trades.csv`).

Accepts the same query parameters as `GET /journal/trades` (max `limit`: 5000).

Response: `text/csv` with `Content-Disposition: attachment; filename=trades.csv`.

---

## Performance

### `GET /journal/performance`

Returns aggregated performance metrics across all logged trades, broken down by strategy and symbol.

Query parameters: `symbol`, `strategy`, `limit` (1–1000, default: 500).

Response:

```json
{
  "metrics": {
    "total_trades": 12,
    "open_trades": 3,
    "closed_trades": 9,
    "winning_trades": 6,
    "win_rate_pct": 66.67,
    "avg_pnl_pct": 2.14,
    "total_pnl_pct": 19.26,
    "best_trade_pnl_pct": 8.52,
    "worst_trade_pnl_pct": -3.10
  },
  "by_strategy": [
    { "key": "RSI2", "metrics": { "..." : "..." } }
  ],
  "by_symbol": [
    { "key": "AAPL", "metrics": { "..." : "..." } }
  ]
}
```

Metric rules:

- All metric fields are `null` when no closed trades exist in the group
- `by_strategy` and `by_symbol` are sorted by `closed_trades` descending

---

### `GET /journal/signals/{signal_id}/performance`

Returns all trades linked to a specific screener signal with aggregated metrics.

- Returns `404` if no trades are found for the given `signal_id`

Response shape is the same as `GET /journal/performance` metrics block, plus a `trades` array.

---

### `GET /journal/performance/export`

Downloads the aggregated performance summary as a CSV file (`performance.csv`).

Accepts `symbol` and `strategy` query parameters.

Rows: one for `overall`, then one per strategy, then one per symbol — each with all metric columns.

Response: `text/csv` with `Content-Disposition: attachment; filename=performance.csv`.

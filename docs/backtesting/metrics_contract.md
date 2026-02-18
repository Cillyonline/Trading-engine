# Backtest Metrics Contract

## 1. Purpose & Scope
This document defines the deterministic contract for backtest metrics output.

In scope:
- Canonical metric categories: return, risk, and trade-level metrics.
- Deterministic computation rules, including explicit formulas and edge-case handling.
- A normative JSON Schema for output validation.
- Artifact invariants for required deterministic inputs from Phase 22 artifacts.
- Specification-level tests for schema conformance and determinism.

Out of scope:
- Strategy ranking.
- Optimization loops.
- Strategy parameter search.
- ML-based evaluation.

## 2. Inputs (Phase 22 deterministic artifacts)
The metrics computation consumes deterministic artifacts produced by Phase 22.

Required inputs:
1. `summary` artifact
   - `start_equity` (number, account currency)
   - `end_equity` (number, account currency)
   - Optional deterministic run metadata (only forwarded if present)

2. `equity_curve` artifact
   - Ordered or orderable points containing:
     - `timestamp` (ISO 8601, UTC)
     - `equity` (number, account currency)

3. `trades` artifact
   - Trade records containing at minimum:
     - `trade_id` (string or integer convertible to canonical string)
     - `exit_ts` (ISO 8601, UTC)
     - `pnl` (number, account currency)

If `equity_curve` is unavailable, risk metrics defined in this contract MUST be `null`.
If `trades` is unavailable, trade-level metrics defined in this contract MUST be `null`.

## 3. Artifact Invariants
The following invariants MUST hold for inputs before metrics computation:

1. Time format and timezone
   - All timestamps MUST be ISO 8601 with explicit `Z` suffix (UTC).
   - Any non-UTC timestamp MUST be rejected before computation.

2. Currency and units
   - Monetary values MUST be in account currency.
   - Percentage metrics MUST be decimal fractions (`0.12` = `12%`).

3. Canonical ordering
   - Equity points MUST be sorted by `(timestamp)` ascending.
   - Trades MUST be sorted by `(exit_ts, trade_id)` ascending.
   - If multiple records share the same sort key, original artifact order MUST NOT be used; tie-break resolution MUST be deterministic by canonical string comparison of `trade_id`.

4. Numeric domain
   - Inputs used for numeric computation MUST be finite JSON numbers.
   - NaN and Infinity are invalid in inputs and MUST be rejected.

5. Deterministic preprocessing
   - No interpolation, resampling, or inferred sampling frequency is allowed.
   - Missing required input fields MUST fail upstream artifact validation; this contract does not infer defaults.

## 4. Deterministic Computation Rules (Global)
1. Computation order
   - Apply canonical sorting first.
   - Compute return metrics.
   - Compute risk metrics.
   - Compute trade-level metrics.

2. Precision and output representation
   - Internal arithmetic uses exact deterministic language/runtime numeric semantics.
   - Final JSON output MUST serialize numbers without rounding beyond runtime numeric value.
   - No presentation rounding is allowed in contract output.

3. Null handling
   - Output MUST NOT contain NaN or Infinity.
   - If a metric is undefined by rule, output `null`.
   - Undefined metric conditions are explicitly listed per metric.

4. Time and frequency assumptions
   - This contract makes no implied sampling-frequency assumptions.
   - Volatility-derived metrics (e.g., Sharpe) are out of scope unless sampling frequency is explicitly provided by input artifacts; when absent they are omitted from this schema.

5. Deterministic median for even counts
   - For even `N`, median is `(x[N/2 - 1] + x[N/2]) / 2` after ascending sort of values.

## 5. Metric Definitions

### 5.1 Return Metrics
All monetary values are in account currency.

1. `start_equity`
   - Formula: value from `summary.start_equity`.

2. `end_equity`
   - Formula: value from `summary.end_equity`.

3. `net_profit`
   - Formula: `end_equity - start_equity`.

4. `net_profit_pct`
   - Formula: `net_profit / start_equity`.
   - Edge case: if `start_equity == 0`, `net_profit_pct = null`.

5. `cagr`
   - Formula (only when deterministic year span is derivable):
     - `years = (t_end - t_start) / 31557600` seconds
     - `cagr = (end_equity / start_equity)^(1 / years) - 1`
   - Required conditions:
     - Deterministic `t_start` and `t_end` provided by artifacts.
     - `years > 0`.
     - `start_equity > 0`.
     - `end_equity >= 0`.
   - Edge case: if any required condition is not met, `cagr = null`.

### 5.2 Risk Metrics
Risk metrics require `equity_curve`.

Let equity points after canonical sort be `E = [e_0, e_1, ..., e_n]`.
Define running peak `p_t = max(e_0..e_t)`.

1. `max_drawdown_abs`
   - Per-point drawdown: `dd_abs_t = p_t - e_t`.
   - Formula: `max_drawdown_abs = max(dd_abs_t)` for all points.
   - Edge case: if no equity points exist, `max_drawdown_abs = null`.

2. `max_drawdown_pct`
   - Per-point drawdown percent:
     - if `p_t > 0`: `dd_pct_t = (p_t - e_t) / p_t`
     - if `p_t == 0`: `dd_pct_t = null` for that point
   - Formula: maximum of non-null `dd_pct_t` values.
   - Edge cases:
     - if no equity points exist, `max_drawdown_pct = null`.
     - if all `dd_pct_t` are null (all peaks are zero), `max_drawdown_pct = null`.

### 5.3 Trade-level Metrics
Trade-level metrics require `trades`.

Let trade pnls after canonical sort be `P = [p_1, ..., p_n]`.
Define:
- wins: `W = {p_i | p_i > 0}`
- losses: `L = {p_i | p_i < 0}`

1. `trade_count`
   - Formula: number of trades, `n`.

2. `win_rate`
   - Formula: `|W| / n`.
   - Edge case: if `n == 0`, `win_rate = null`.

3. `avg_trade_pnl`
   - Formula: `sum(P) / n`.
   - Edge case: if `n == 0`, `avg_trade_pnl = null`.

4. `median_trade_pnl`
   - Formula: deterministic median of sorted `P` ascending.
   - Edge case: if `n == 0`, `median_trade_pnl = null`.

5. `profit_factor`
   - Formula: `sum(W) / abs(sum(L))`.
   - Deterministic zero-loss rule:
     - if `sum(L) == 0` and `sum(W) > 0`, `profit_factor = null`.
     - if `sum(L) == 0` and `sum(W) == 0`, `profit_factor = null`.

6. `expectancy`
   - Definitions:
     - `avg_win = sum(W) / |W|` if `|W| > 0`, else `0`
     - `avg_loss = sum(L) / |L|` if `|L| > 0`, else `0`
     - `win_rate` as above
   - Formula: `expectancy = (win_rate * avg_win) - ((1 - win_rate) * abs(avg_loss))`
   - Edge case: if `n == 0`, `expectancy = null`.

## 6. Output Schema (JSON Schema)
Draft version: **JSON Schema Draft 2020-12**.

Policy:
- Top-level `additionalProperties` is `false`.
- `schema_version` and `metrics` are required.
- `metadata` is optional and may be included only when source artifacts provide deterministic metadata.

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://example.org/schemas/backtest-metrics-contract.schema.json",
  "title": "Backtest Metrics Contract",
  "type": "object",
  "additionalProperties": false,
  "required": ["schema_version", "metrics"],
  "properties": {
    "schema_version": {
      "type": "string",
      "const": "1.0.0"
    },
    "metadata": {
      "type": "object",
      "additionalProperties": false,
      "properties": {
        "run_id": { "type": "string" },
        "generated_at": {
          "type": "string",
          "format": "date-time"
        }
      },
      "required": [],
      "description": "Optional; include only if deterministically provided by input artifacts."
    },
    "metrics": {
      "type": "object",
      "additionalProperties": false,
      "required": ["returns", "risk", "trade_level"],
      "properties": {
        "returns": {
          "type": "object",
          "additionalProperties": false,
          "required": [
            "start_equity",
            "end_equity",
            "net_profit",
            "net_profit_pct",
            "cagr"
          ],
          "properties": {
            "start_equity": { "type": "number" },
            "end_equity": { "type": "number" },
            "net_profit": { "type": "number" },
            "net_profit_pct": { "type": ["number", "null"] },
            "cagr": { "type": ["number", "null"] }
          }
        },
        "risk": {
          "type": "object",
          "additionalProperties": false,
          "required": ["max_drawdown_abs", "max_drawdown_pct"],
          "properties": {
            "max_drawdown_abs": { "type": ["number", "null"] },
            "max_drawdown_pct": { "type": ["number", "null"] }
          }
        },
        "trade_level": {
          "type": "object",
          "additionalProperties": false,
          "required": [
            "trade_count",
            "win_rate",
            "avg_trade_pnl",
            "median_trade_pnl",
            "profit_factor",
            "expectancy"
          ],
          "properties": {
            "trade_count": { "type": ["integer", "null"], "minimum": 0 },
            "win_rate": { "type": ["number", "null"] },
            "avg_trade_pnl": { "type": ["number", "null"] },
            "median_trade_pnl": { "type": ["number", "null"] },
            "profit_factor": { "type": ["number", "null"] },
            "expectancy": { "type": ["number", "null"] }
          }
        }
      }
    }
  }
}
```

Example output (conforming):

```json
{
  "schema_version": "1.0.0",
  "metadata": {
    "run_id": "bt-2026-01-15-0001",
    "generated_at": "2026-01-15T12:00:00Z"
  },
  "metrics": {
    "returns": {
      "start_equity": 10000.0,
      "end_equity": 11250.0,
      "net_profit": 1250.0,
      "net_profit_pct": 0.125,
      "cagr": null
    },
    "risk": {
      "max_drawdown_abs": 420.0,
      "max_drawdown_pct": 0.03733333333333333
    },
    "trade_level": {
      "trade_count": 10,
      "win_rate": 0.6,
      "avg_trade_pnl": 125.0,
      "median_trade_pnl": 80.0,
      "profit_factor": 1.8,
      "expectancy": 125.0
    }
  }
}
```

## 7. Determinism & Validation Tests (Specification)
1. Schema validation test
   - Given a produced metrics artifact, validate against the JSON Schema in Section 6.
   - Test passes only when validation succeeds with no additional properties and all required fields present.

2. Determinism assertion test
   - Given identical input artifacts (`summary`, `equity_curve`, `trades`), run metrics computation at least twice.
   - Canonicalize each output JSON before byte comparison using all rules below:
     1. UTF-8 encoding.
     2. Object keys sorted lexicographically at every level.
     3. Arrays preserved in contract-defined canonical order.
     4. Numbers serialized with stable runtime JSON formatting (no locale dependence, no scientific notation rewriting between runs).
     5. No trailing whitespace, newline normalization to `\n`.
   - Test passes only when canonicalized byte streams are identical.

3. Undefined/edge-case conformance test set
   - `start_equity == 0` => `net_profit_pct = null`.
   - Empty equity series => risk metrics are `null`.
   - Peak equity always `0` => `max_drawdown_pct = null`.
   - `trade_count == 0` => `win_rate`, `avg_trade_pnl`, `median_trade_pnl`, `profit_factor`, `expectancy` are `null` and `trade_count = 0`.
   - `sum_losses == 0` => `profit_factor = null`.
   - No output field contains NaN/Infinity.

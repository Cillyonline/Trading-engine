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
The metrics computation MUST consume deterministic artifacts produced by Phase 22.

Required inputs:
1. `summary` artifact
   - `start_equity` (number, account currency)
   - `end_equity` (number, account currency)
   - Deterministic run metadata fields are permitted only if present in Phase 22 artifacts and copied without transformation.

2. `equity_curve` artifact
   - Ordered or orderable points containing:
     - `timestamp` (ISO 8601, UTC, `Z` suffix)
     - `equity` (number, account currency)

3. `trades` artifact
   - Trade records containing at minimum:
     - `trade_id` (string or integer converted to canonical string)
     - `exit_ts` (ISO 8601, UTC, `Z` suffix)
     - `pnl` (number, account currency)

Object-presence rule:
- `metrics.returns` MUST always exist.
- `metrics.risk` MUST always exist.
- `metrics.trade_level` MUST always exist.

Missing-input rule:
- If `equity_curve` is unavailable, all `metrics.risk.*` fields MUST be `null`.
- If `trades` is unavailable, `metrics.trade_level.trade_count` MUST be `0`, and `win_rate`, `avg_trade_pnl`, `median_trade_pnl`, `profit_factor`, and `expectancy` MUST be `null`.

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
   - If multiple records share the same sort key, tie-break resolution MUST be deterministic by canonical string comparison of `trade_id`.

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
   - Numeric type for all computed metrics MUST be IEEE-754 double precision.
   - All metric values in JSON MUST be serialized as JSON numbers and MUST NOT be serialized as JSON strings.
   - All division results MUST use round-half-to-even to 12 fractional digits before serialization.
   - Canonical JSON number formatting MUST follow all rules below:
     1. Exponent notation is forbidden.
     2. Decimal representation only.
     3. Trailing decimal point is forbidden.
     4. Trailing zeros after decimal point are forbidden.
     5. At least one digit before decimal point is required.
     6. `-0` is forbidden and MUST serialize as `0`.

3. Null handling
   - Output MUST NOT contain NaN or Infinity.
   - If a metric is undefined by rule, output `null`.
   - Undefined metric conditions are explicitly listed per metric.

4. Time and frequency assumptions
   - This contract makes no implied sampling-frequency assumptions.
   - Volatility-derived metrics (for example Sharpe) are out of scope unless sampling frequency is explicitly provided by input artifacts; absent explicit sampling frequency, such metrics MUST be omitted.

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
   - Deterministic time source:
     - `t_start` MUST be the first `equity_curve.timestamp` after canonical sort.
     - `t_end` MUST be the last `equity_curve.timestamp` after canonical sort.
   - Formula:
     - `years = (t_end - t_start) / 31557600` seconds
     - `cagr = (end_equity / start_equity)^(1 / years) - 1`
   - Required conditions:
     - `equity_curve` is available.
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
   - Edge case: if no equity points exist or `equity_curve` is unavailable, `max_drawdown_abs = null`.

2. `max_drawdown_pct`
   - Per-point drawdown percent:
     - if `p_t > 0`: `dd_pct_t = (p_t - e_t) / p_t`
     - if `p_t == 0`: `dd_pct_t = null` for that point
   - Formula: maximum of non-null `dd_pct_t` values.
   - Edge cases:
     - if no equity points exist or `equity_curve` is unavailable, `max_drawdown_pct = null`.
     - if all `dd_pct_t` are null (all peaks are zero), `max_drawdown_pct = null`.

### 5.3 Trade-level Metrics
Trade-level metrics require `trades`.

Let trade pnls after canonical sort be `P = [p_1, ..., p_n]`.
Define:
- wins: `W = {p_i | p_i > 0}`
- losses: `L = {p_i | p_i < 0}`

Unavailable-trades rule:
- If `trades` is unavailable, `trade_count` MUST be `0`.
- If `trades` is unavailable, `win_rate`, `avg_trade_pnl`, `median_trade_pnl`, `profit_factor`, and `expectancy` MUST be `null`.

1. `trade_count`
   - Formula: number of trades, `n`.
   - Edge case: if `trades` is unavailable, `trade_count = 0`.

2. `win_rate`
   - Formula: `|W| / n`.
   - Edge case: if `n == 0` or `trades` is unavailable, `win_rate = null`.

3. `avg_trade_pnl`
   - Formula: `sum(P) / n`.
   - Edge case: if `n == 0` or `trades` is unavailable, `avg_trade_pnl = null`.

4. `median_trade_pnl`
   - Formula: deterministic median of sorted `P` ascending.
   - Edge case: if `n == 0` or `trades` is unavailable, `median_trade_pnl = null`.

5. `profit_factor`
   - Formula: `sum(W) / abs(sum(L))`.
   - Deterministic zero-loss rule:
     - if `sum(L) == 0` and `sum(W) > 0`, `profit_factor = null`.
     - if `sum(L) == 0` and `sum(W) == 0`, `profit_factor = null`.
   - Edge case: if `trades` is unavailable, `profit_factor = null`.

6. `expectancy`
   - Definitions:
     - `avg_win = sum(W) / |W|` if `|W| > 0`, else `0`
     - `avg_loss = sum(L) / |L|` if `|L| > 0`, else `0`
     - `win_rate` as above
   - Formula: `expectancy = (win_rate * avg_win) - ((1 - win_rate) * abs(avg_loss))`
   - Edge case: if `n == 0` or `trades` is unavailable, `expectancy = null`.

## 6. Output Schema (JSON Schema)
Draft version: **JSON Schema Draft 2020-12**.

Policy:
- Top-level `additionalProperties` is `false`.
- `schema_version` and `metrics` are required.
- `metadata` is optional and is allowed only if deterministically provided by input artifacts.
- `metrics.returns`, `metrics.risk`, and `metrics.trade_level` are required objects and MUST always be present.

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
      "required": []
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
            "trade_count": { "type": "integer", "minimum": 0 },
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
      "start_equity": 10000,
      "end_equity": 11250,
      "net_profit": 1250,
      "net_profit_pct": 0.125,
      "cagr": null
    },
    "risk": {
      "max_drawdown_abs": null,
      "max_drawdown_pct": null
    },
    "trade_level": {
      "trade_count": 0,
      "win_rate": null,
      "avg_trade_pnl": null,
      "median_trade_pnl": null,
      "profit_factor": null,
      "expectancy": null
    }
  }
}
```

## 7. Determinism & Validation Tests (Specification)
1. Schema validation test
   - Given a produced metrics artifact, validate against the JSON Schema in Section 6.
   - Test passes only when validation succeeds with no additional properties and all required fields present.
   - Test passes only when `metrics.returns`, `metrics.risk`, and `metrics.trade_level` exist.

2. Determinism assertion test
   - Given identical input artifacts (`summary`, `equity_curve`, `trades`), run metrics computation at least twice.
   - Canonicalize each output JSON before byte comparison using all rules below:
     1. UTF-8 encoding.
     2. Object keys sorted lexicographically at every level.
     3. Arrays preserved in contract-defined canonical order.
     4. Numbers serialized as canonical decimal JSON numbers with no exponent notation.
     5. No trailing decimal point.
     6. No trailing zeros after decimal point.
     7. At least one digit before decimal point.
     8. `-0` normalized to `0`.
     9. Division results rounded with round-half-to-even to 12 fractional digits before serialization.
     10. No trailing whitespace; newline normalization to `\n`.
   - Test passes only when canonicalized byte streams are identical.

3. Undefined/edge-case conformance test set
   - `start_equity == 0` => `net_profit_pct = null`.
   - `equity_curve` unavailable => `risk.max_drawdown_abs = null` and `risk.max_drawdown_pct = null`.
   - `equity_curve` unavailable => `cagr = null`.
   - Empty equity series => risk metrics are `null`.
   - Peak equity always `0` => `max_drawdown_pct = null`.
   - `trades` unavailable => `trade_count = 0` and `win_rate`, `avg_trade_pnl`, `median_trade_pnl`, `profit_factor`, `expectancy` are `null`.
   - `trade_count == 0` => `win_rate`, `avg_trade_pnl`, `median_trade_pnl`, `profit_factor`, `expectancy` are `null` and `trade_count = 0`.
   - `sum_losses == 0` => `profit_factor = null`.
   - No output field contains NaN/Infinity.
```

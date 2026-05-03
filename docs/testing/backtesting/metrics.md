# 1. Purpose

This document defines the deterministic evaluation contract for backtesting metrics.

All metrics are pure functions of input artifacts.

No randomness is allowed.

No time-dependent behavior is allowed.

Identical input artifacts SHALL produce identical metric values and identical output artifact bytes.

# 2. Input Artifacts

The evaluation input consists of three artifacts:

- `summary`: scalar run metadata required by metric definitions.
- `equity_curve`: ordered equity observations with timestamped equity values.
- `trades`: closed-trade records with realized `pnl` and trade identifiers.

For issue `#728`, backtest artifacts now include deterministic baseline artifacts directly:

- `summary` (cost-aware baseline): `start_equity`, `end_equity`.
- `equity_curve` (cost-aware baseline): canonical timestamp/equity series.
- `trades`: deterministic closed-trade summaries for the covered round-trip path.
- `metrics_baseline`: deterministic comparison object with:
  - `assumptions` (explicit cost/slippage assumptions from run config),
  - `summary` (starting/ending equity, total commission, total slippage cost, total transaction cost, fill count),
  - `equity_curve.cost_free` and `equity_curve.cost_aware`,
  - `metrics.cost_free`, `metrics.cost_aware`, and `metrics.deltas`,
  - `trades` (cost-aware closed-trade summaries used by the trader-facing artifact path).

## Canonical Ordering Rules

The evaluator SHALL operate on canonicalized sequences:

1. `equity_curve` sorted by `timestamp` ascending.
2. `trades` sorted by `(exit_ts, trade_id)` ascending.

Deterministic tie-breaking rules:

- For equal `timestamp` values in `equity_curve`, records SHALL be ordered by a stable, deterministic secondary key agreed by schema (if present); if no secondary key exists, the original artifact order SHALL be preserved as a stable order.
- For equal `(exit_ts, trade_id)` in `trades`, records SHALL be ordered by a stable, deterministic secondary key agreed by schema (if present); if no secondary key exists, the original artifact order SHALL be preserved as a stable order.

## Numeric Domain Constraints

All numeric values SHALL use IEEE-754 double-precision semantics.

All numeric values SHALL be finite.

`NaN`, `+Infinity`, and `-Infinity` are invalid and SHALL cause evaluation failure.

# 3. Determinism Invariants

The evaluator SHALL satisfy the following invariants:

- No randomness.
- No system time access.
- No locale-dependent formatting.
- Round-half-to-even at 12 fractional digits for emitted metric numbers.
- `-0` normalized to `0`.
- Deterministic JSON key ordering.
- UTF-8 encoding.
- JSON serialization with `allow_nan = False`.
- Stable JSON separators `(",", ":")`.

`canonical_json_bytes` behavior is defined as follows:

1. Input is a validated metrics result object conforming to Section 5.
2. Keys are serialized in lexicographic order.
3. Numbers are normalized under the numeric invariants in this section.
4. Serialization uses UTF-8, `allow_nan = False`, and separators `(",", ":")` with no additional whitespace.
5. Output is the exact byte sequence used for artifact persistence and hashing.

# 4. Mathematical Metric Definitions

Let `E = [(t_0, e_0), (t_1, e_1), ..., (t_n, e_n)]` be the canonical `equity_curve` with strictly non-decreasing timestamps after ordering rules are applied. Let `T` be the canonical `trades` sequence.

## 4.1 Total Return

\[
\mathrm{total\_return} = \frac{\mathrm{end\_equity} - \mathrm{start\_equity}}{\mathrm{start\_equity}}
\]

where:

- `start_equity = e_0`
- `end_equity = e_n`

Edge case:

- If `start_equity = 0`, `total_return = null`.

## 4.2 CAGR

\[
\mathrm{cagr} = \left(\frac{\mathrm{end\_equity}}{\mathrm{start\_equity}}\right)^{1/\mathrm{years}} - 1
\]

\[
\mathrm{years} = \frac{t_{\mathrm{end}} - t_{\mathrm{start}}}{365.25 \times 24 \times 60 \times 60}
\]

where:

- `t_start = t_0`
- `t_end = t_n`
- `start_equity = e_0`
- `end_equity = e_n`

Edge cases:

- If fewer than 2 equity points exist, `cagr = null`.
- If `start_equity <= 0`, `cagr = null`.
- If `years <= 0`, `cagr = null`.

## 4.3 Maximum Drawdown

Define peak recursion:

\[
\mathrm{peak}_0 = e_0
\]

\[
\mathrm{peak}_t = \max(\mathrm{peak}_{t-1}, e_t), \quad t \ge 1
\]

Point drawdown:

\[
\mathrm{dd}_t = \frac{\mathrm{peak}_t - e_t}{\mathrm{peak}_t}
\]

Maximum drawdown:

\[
\mathrm{max\_drawdown} = \max_t(\mathrm{dd}_t)
\]

Edge cases:

- If fewer than 2 equity points exist, `max_drawdown = null`.
- If no positive peak exists (`\forall t: \mathrm{peak}_t \le 0`), `max_drawdown = null`.

## 4.4 Sharpe Ratio (Deterministic, Non-Annualized)

For `t = 1..n`, define period return:

\[
r_t = \frac{e_t - e_{t-1}}{e_{t-1}}
\]

Let `R = [r_1, ..., r_n]`.

\[
\mu = \mathrm{mean}(R)
\]

\[
\sigma = \sqrt{\frac{1}{N-1}\sum_{i=1}^{N}(r_i - \mu)^2}
\]

\[
\mathrm{sharpe\_ratio} = \frac{\mu}{\sigma}
\]

where `N = |R|` and `\sigma` is the sample standard deviation (`N-1` denominator).

Edge cases:

- If fewer than 2 returns exist (`N < 2`), `sharpe_ratio = null`.
- If `\sigma = 0`, `sharpe_ratio = null`.

No annualization factor is applied.

## 4.5 Calmar Ratio

\[
\mathrm{calmar\_ratio} = \frac{\mathrm{cagr}}{|\mathrm{max\_drawdown}|}
\]

Edge cases:

- If `cagr = null`, `calmar_ratio = null`.
- If `max_drawdown = null`, `calmar_ratio = null`.
- If `max_drawdown = 0`, `calmar_ratio = null` (division by zero avoided).

## 4.6 Sortino Ratio (Deterministic, Non-Annualized)

Uses the same period-return series `R = [r_1, ..., r_n]` defined in 4.4, with MAR = 0.

Define the downside-deviation series:

\[
d_i = \min(r_i, 0), \quad i = 1..N
\]

\[
\sigma_d = \sqrt{\frac{1}{N-1}\sum_{i=1}^{N} d_i^2}
\]

\[
\mathrm{sortino\_ratio} = \frac{\mu}{\sigma_d}
\]

where `\mu` is the mean return (same as Sharpe, Section 4.4) and `\sigma_d` is the sample downside deviation (`N-1` denominator, consistent with Sharpe).

Edge cases:

- If fewer than 2 returns exist (`N < 2`), `sortino_ratio = null`.
- If `\sigma_d = 0` (no negative returns or flat series), `sortino_ratio = null`.

No annualization factor is applied. Supply `periods_per_year` to the metric function to obtain an annualized ratio.

## 4.7 Win Rate

\[
\mathrm{win\_rate} = \frac{\#(\mathrm{pnl} > 0)}{\mathrm{total\_trades}}
\]

where `total_trades = |T|`.

Edge case:

- If `total_trades = 0`, `win_rate = null`.

## 4.8 Profit Factor

\[
\mathrm{profit\_factor} = \frac{\sum \mathrm{positive\_pnls}}{\sum |\mathrm{negative\_pnls}|}
\]

where:

- `positive_pnls = {p \in pnl(T) \mid p > 0}`
- `negative_pnls = {p \in pnl(T) \mid p < 0}`

Edge case:

- If `gross_loss = \sum |\mathrm{negative\_pnls}| = 0`, `profit_factor = null`.

# 5. Artifact Specification

The output artifact is `metrics-result.json` with exact structure:

```json
{
  "schema_version": "1.0.0",
  "total_return": number|null,
  "cagr": number|null,
  "max_drawdown": number|null,
  "sharpe_ratio": number|null,
  "sortino_ratio": number|null,
  "calmar_ratio": number|null,
  "win_rate": number|null,
  "profit_factor": number|null
}
```

The fenced JSON example above is complete and closed before the following normative constraints.

Normative constraints:

- Keys SHALL be sorted lexicographically in serialized output.
- No additional properties are allowed.
- Floating-point values SHALL be emitted as canonical decimal JSON numbers.
- Repeated runs over identical input artifacts SHALL produce byte-identical `metrics-result.json`.

# 6. Reproducibility Guarantee

Reproducibility validation requirements:

- 3-run smoke validation is required for the same input artifacts.
- SHA-256 hash equality across all 3 produced artifacts is required.
- Raw byte-equality across all 3 produced artifacts is required.
- These checks are covered by CI and SHALL be enforced in continuous validation.

# 7. Cost/Slippage Baseline Rules

The deterministic baseline in this phase uses bounded assumptions:

- `slippage_bps` range: `[0, 250]`.
- `commission_per_order` range: `[0, 25]`.

Cost model:

- Slippage is side-aware and adverse (`BUY` increases fill price, `SELL` decreases fill price).
- Commission is fixed per filled order.
- Total transaction cost is `total_commission + total_slippage_cost`.

Cost-aware vs cost-free comparison:

- `cost_free` uses reference snapshot fill price (`open` or fallback `price`) and zero costs.
- `cost_aware` uses executed fill price plus commission.
- Closed-trade PnL in `trades` and `metrics_baseline.trades` is commission-aware on the cost-aware path.
- Open positions do not produce synthetic closed trades; they remain visible through `positions`, `equity_curve`, and ending-equity state.
- For identical fills with non-zero assumptions, `ending_equity_cost_aware` SHALL be less than `ending_equity_cost_free`.

# 8. Test Execution Evidence

Command used for the targeted backtest execution validation:

```powershell
python -m pytest tests\cilly_trading\engine\test_order_execution_model.py tests\cilly_trading\engine\test_backtest_execution_contract.py tests\cilly_trading\engine\test_backtest_runner.py
```

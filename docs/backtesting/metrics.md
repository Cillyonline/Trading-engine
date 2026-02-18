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

## 4.5 Win Rate

\[
\mathrm{win\_rate} = \frac{\#(\mathrm{pnl} > 0)}{\mathrm{total\_trades}}
\]

where `total_trades = |T|`.

Edge case:

- If `total_trades = 0`, `win_rate = null`.

## 4.6 Profit Factor

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
  "win_rate": number|null,
  "profit_factor": number|null
}
```

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

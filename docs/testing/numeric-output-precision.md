# Numeric Output Precision Rules

## Rule Summary

All floating-point values emitted in analysis output payloads must be stable under a fixed precision
rule:

- **Precision:** values must round to **4 decimal places** using standard half-up rounding.
- **Tolerance:** the absolute delta between the stored float and its 4-decimal rounded value must be
  less than or equal to `1e-9`.
- **Serialization:** deterministic JSON serialization is required (sorted keys, no NaN/Infinity, and
  compact separators) to keep payloads byte-stable across runs.

These rules prevent floating-point drift from causing silent regressions while preserving the
current runtime behavior.

## Entry Zone Precision

Signal `entry_zone` values (`from_` and `to`) are computed in strategy code using floating-point
price multipliers (e.g. `last_close * 0.97`). To prevent float drift from producing
non-deterministic signal IDs, strategies **must** round all entry-zone values to exactly 4 decimal
places using `Decimal.quantize(Decimal("0.0001"), ROUND_HALF_UP)` before converting back to
`float`. The resulting values satisfy the standard 4dp / `1e-9` tolerance rule above.

Pattern used in all strategy implementations:

```python
from decimal import Decimal, ROUND_HALF_UP

_scale = Decimal("0.0001")
entry_zone = {
    "from_": float(Decimal(str(raw_from)).quantize(_scale, ROUND_HALF_UP)),
    "to":    float(Decimal(str(raw_to)).quantize(_scale, ROUND_HALF_UP)),
}
```

## Tests

The numeric precision guard is enforced in `tests/numeric/test_numeric_precision_guard.py`, and
serialization stability is validated by comparing stable JSON outputs across repeated runs.

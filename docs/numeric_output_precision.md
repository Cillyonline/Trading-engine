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

## Tests

The numeric precision guard is enforced in `tests/numeric/test_numeric_precision_guard.py`, and
serialization stability is validated by comparing stable JSON outputs across repeated runs.

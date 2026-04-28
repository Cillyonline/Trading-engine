# Bounded Paper Runtime Evidence Series Summarizer

## Purpose

`scripts/validation/summarize_bounded_paper_runtime_evidence.py` summarizes a
directory of saved bounded paper-runtime JSON outputs for later review.

This tool is analysis-only. It reads existing JSON files from disk and writes an
aggregate JSON or Markdown report. It is not part of runtime execution and must
not be deployed into the VPS runtime path.

## Scope Boundary

In scope:

- offline parsing of saved bounded paper-runtime JSON outputs
- deterministic aggregation across matching run files
- run-quality distribution
- eligible, skipped, and rejected totals
- skip-reason counts
- reconciliation status counts and mismatch totals
- summary-file references where present

Out of scope:

- modifying `scripts/run_daily_bounded_paper_runtime.py`
- paper execution behavior
- signal generation
- risk logic
- score thresholds
- data ingestion behavior
- Docker or VPS deployment behavior
- live trading
- broker integration
- readiness or profitability claims

## Usage

### Default JSON Summary

Summarize files named like `run-*.json` under an operator-provided directory and
write deterministic JSON to stdout:

```bash
python scripts/validation/summarize_bounded_paper_runtime_evidence.py \
  --input-dir runs/daily-runtime \
  --pattern "run-*.json"
```

### Daily Runtime Summary Artifact Pattern

Summarize existing daily runtime summary artifacts:

```bash
python scripts/validation/summarize_bounded_paper_runtime_evidence.py \
  --input-dir runs/daily-runtime \
  --pattern "daily-runtime-summary-*.json"
```

### Markdown Output

Write deterministic Markdown output to a file:

```bash
python scripts/validation/summarize_bounded_paper_runtime_evidence.py \
  --input-dir runs/daily-runtime \
  --pattern "run-*.json" \
  --format markdown \
  --output runs/daily-runtime/evidence-series-summary.md
```

## Determinism

The summarizer sorts matched file paths, counter keys, run-file references, and
summary-file references before rendering output. Repeated runs over the same
input files produce the same aggregate content.

## Test Execution Evidence

Canonical command attempted:

```bash
uv run -- python -m pytest --import-mode=importlib
```

Fallback repository test command:

```bash
python -m pytest -q
```

## Claim Boundary

The summary is evidence review material only:

- it does not place live orders
- it does not call broker APIs
- it does not execute the daily paper runtime runner
- it does not change paper execution, signal generation, risk logic, or thresholds
- it does not establish live-trading, broker-readiness, production-readiness,
  trader-validation, or profitability claims

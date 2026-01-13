# I-029a Implicit Time Usage Inventory

Scope scanned: `api/`, `src/` (engine/data/strategies/persistence equivalents), `strategy/`.

## Findings

### 1) src/cilly_trading/engine/data.py:40-41
**Snippet:**
```
def _utc_now() -> datetime:
    return datetime.now(timezone.utc)
```
**Classification:** BLOCKS determinism (used to derive analysis data windows).

**Neutralization note:** Replace helper with an explicitly provided timestamp or inject a run-time reference from the caller/ingestion context.

### 2) src/cilly_trading/engine/data.py:178-179
**Snippet:**
```
end = _utc_now()
start = end - timedelta(days=lookback_days * 2)
```
**Classification:** BLOCKS determinism (data range depends on system time).

**Neutralization note:** Require `end`/`start` parameters (or a run timestamp) so the window is explicit for deterministic runs.

### 3) src/cilly_trading/engine/data.py:279
**Snippet:**
```
since = int((_utc_now() - timedelta(days=lookback_days * 2)).timestamp() * 1000)
```
**Classification:** BLOCKS determinism (Binance data range depends on system time).

**Neutralization note:** Provide an explicit end time or snapshot reference to compute `since` deterministically.

### 4) src/cilly_trading/engine/core.py:72-73
**Snippet:**
```
def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
```
**Classification:** BLOCKS determinism (used to supply signal timestamps when missing).

**Neutralization note:** Require a run timestamp to be passed in or remove automatic timestamping in favor of explicit strategy-provided timestamps.

### 5) src/cilly_trading/engine/core.py:219-224
**Snippet:**
```
s.setdefault("symbol", symbol)
s.setdefault("strategy", strat_name)
s.setdefault("timestamp", _now_iso())
```
**Classification:** BLOCKS determinism (signals get current time if timestamp missing).

**Neutralization note:** Require signals to include explicit timestamps (e.g., derived from data) or supply a deterministic run timestamp.

### 6) src/cilly_trading/repositories/analysis_runs_sqlite.py:118-124
**Snippet:**
```
json.dumps(request_payload, sort_keys=True),
json.dumps(result_payload, sort_keys=True),
datetime.now(timezone.utc).isoformat(),
```
**Classification:** ALLOWED metadata only (created_at persisted as metadata, not used in signal generation).

**Neutralization note:** Accept a provided `created_at` timestamp from the caller for deterministic metadata if needed.

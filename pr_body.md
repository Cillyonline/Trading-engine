Closes #592

## Summary
- remove helper-level guard telemetry reconstruction from the observability integration test
- keep integrated coverage limited to runtime surfaces that are actually emitted end-to-end
- verify deterministic structured logs, provider failover telemetry, runtime metrics, and health endpoints across healthy and failure scenarios

## Testing
- .\.venv\Scripts\python.exe -m pytest

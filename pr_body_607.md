Closes #607

## Summary
- enforce role checks on covered operator-facing API routes using a minimal header-based role dependency
- require owner for /execution/pause and /execution/resume
- require operator for /analysis/run
- require ead_only for /system/state and /compliance/guards/status
- add focused API tests for allowed, forbidden, and unauthorized behavior on covered routes only

## Testing
- .\.venv\Scripts\python.exe -m pytest src/api/test_execution_control_api.py src/api/test_operator_analysis_trigger_api.py src/api/test_system_state_api.py src/api/test_guard_compliance_status_api.py

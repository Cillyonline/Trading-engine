# Owner Runbook: Start / Stop / Logs / Reset Cheatsheet

## Purpose & Safety Notes
This runbook gives owners a short, safe checklist to run, stop, monitor, and reset the local system.

- Use this checklist exactly as written.
- Perform these steps only in your local environment.
- Keep commands and outputs visible while you operate.

## Start
Action:
```bash
<<START_COMMAND>>
```

What happens: The local service starts and becomes available for owner use.

Expected success signal: `<<HEALTH_CHECK_COMMAND>>` shows the service is available.

## Stop
Action:
```bash
<<STOP_COMMAND>>
```

What happens: The running local service shuts down cleanly.

Expected success signal: `<<STOP_SIGNAL>>` confirms the service is no longer running.

## Logs
Action:
```bash
<<LOG_ACCESS_COMMAND>>
```

What happens: Recent runtime output is displayed so you can verify current behavior.

Expected success signal: New log output appears and includes recent activity timestamps.

## Reset / Cleanup
> ⚠ WARNING — LOCAL DEVELOPMENT ONLY
>
> NEVER run this on production or shared systems.

Action:
```bash
<<RESET_COMMAND>>
```

What happens: Local runtime state is cleared for a fresh local start.

Expected success signal: `<<LOCAL_DATA_FILE>>` is removed or re-created cleanly after the next start.

## Troubleshooting
- If start fails, re-run `<<START_COMMAND>>` exactly and check the returned error line.
- If stop fails, run `<<STOP_COMMAND>>` again and verify `<<STOP_SIGNAL>>`.
- If logs are empty, re-run `<<LOG_ACCESS_COMMAND>>` and confirm you are targeting the active log source.
- If reset fails, stop first, run `<<RESET_COMMAND>>`, then start again with `<<START_COMMAND>>`.

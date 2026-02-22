# Owner Dashboard

## Overview
The Owner Dashboard is an operator interface for manually triggering and reviewing single-symbol analysis runs from the UI.

## Current Features
- Manual single-symbol analysis trigger from the Owner Dashboard UI.
- Display of returned signals for the requested symbol.
- Display of the analysis generation timestamp (`generated_at`).
- Tabular display of signal data fields returned by the analysis response.

## UI Behavior
- **Symbol input default:** `BTCUSDT`
- **Loading state:** the trigger button is disabled and shows `Loading...` while the request is in progress.
- **Error state:** an alert is shown when the request fails; fallback message is `Analysis request failed.`
- **Empty state:** `No signals returned.` is shown when no signals are returned.

## Scope & Limitations
This Owner Dashboard documentation only covers the current manual, single-symbol operator flow.

The following are explicitly **not included** in this scope:
- Batch analysis flows
- Scheduling workflows
- Optimization workflows
- Deployment workflows

## Local Development Setup
### Prerequisites
- Node.js and npm installed for frontend development.
- Python with a virtual environment available if backend services are run locally.

### Frontend
From the repository root, run:

```bash
cd frontend
npm install
npm run dev
```

Then open the Owner Dashboard at:

- `/owner`

### Backend requirement for analysis endpoint
The Owner Dashboard triggers `POST /analysis/run`, so the backend must be running for successful analysis responses.

Use the following uvicorn command pattern (replace `MODULE_PATH` with your app module path):

```bash
uvicorn MODULE_PATH:app --reload --port 8000
```

How to find the module path:
- Search the backend codebase for `app = FastAPI()`.
- Use the containing Python module path as `MODULE_PATH`.

### Same-origin and backend port note
If the frontend and backend are not configured for the same origin (or a development proxy is not configured), requests to `/analysis/run` may fail due to origin/port mismatch.

## Manual Test Checklist
1. Start frontend (`npm run dev`) and open `/owner`.
2. Confirm the symbol input defaults to `BTCUSDT`.
3. With backend **down**, trigger analysis and verify:
   - The button enters loading state (`Loading...`) and is disabled during the request.
   - An alert appears with an error, including fallback text `Analysis request failed.` when no detailed message is available.
4. Start backend so `POST /analysis/run` is reachable.
5. Trigger analysis again and verify with backend **up**:
   - Request completes without error alert.
   - `generated_at` is displayed.
   - Signal rows appear in the table when signals are returned.
6. Verify empty-result handling by using a case that returns no signals, and confirm `No signals returned.` is shown.

## Related Issues
- #419 – feature implementation described by this document.

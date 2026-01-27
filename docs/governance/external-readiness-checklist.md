# External Readiness Checklist (Binary)

Instructions:
1) Answer every item with YES or NO.
2) If any item is NO, External Ready = NO.
3) Only if all items are YES, External Ready = YES.

## Checklist

| # | Item | Answer (YES/NO) |
| --- | --- | --- |
| 1 | `docs/local_run.md` includes a command to start the API server with `uvicorn`. | |
| 2 | `docs/local_run.md` includes a `/health` request example for verifying the API is up. | |
| 3 | `README.md` links to at least one run/start guide in `docs/`. | |
| 4 | `docs/api/usage_contract.md` exists and is titled "API Usage Contract". | |
| 5 | `docs/api/usage_contract.md` documents snapshot-only behavior under "Common Conventions". | |
| 6 | `docs/api/usage_contract.md` includes a section titled "Error semantics". | |
| 7 | `docs/api/usage_contract.md` lists snapshot readiness/validation errors with status codes. | |
| 8 | `docs/api/external_api_happy_path.md` exists. | |

## Final decision rule

External Ready = YES only if every item above is YES; otherwise External Ready = NO.

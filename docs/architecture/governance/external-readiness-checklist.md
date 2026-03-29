# External Readiness Checklist (Binary)

Instructions:
1) Answer every item with YES or NO.
2) If any item is NO, External Ready = NO.
3) Only if all items are YES, External Ready = YES.

## Checklist

| # | Item | Answer (YES/NO) |
| --- | --- | --- |
| 1 | `docs/getting-started/local-run.md` includes a command to start the API server with `uvicorn`. | |
| 2 | `docs/getting-started/local-run.md` includes a `/health` request example for verifying the API is up. | |
| 3 | `README.md` links to at least one run/start guide in `docs/`. | |
| 4 | `docs/operations/api/usage_contract.md` exists and is titled "API Usage Contract". | |
| 5 | `docs/operations/api/usage_contract.md` documents snapshot-only behavior under "Common Conventions". | |
| 6 | `docs/operations/api/usage_contract.md` includes a section titled "Error semantics". | |
| 7 | `docs/operations/api/usage_contract.md` lists snapshot readiness/validation errors with status codes. | |
| 8 | `docs/operations/api/external_api_happy_path.md` exists. | |
| 9 | `docs/operations/runtime/staging-server-deployment.md` states localhost-only staging paper default. | |
| 10 | Deployment, API usage, and paper acceptance docs consistently state that `X-Cilly-Role` headers are not a public authentication model. | |
| 11 | Public exposure without an external trust boundary is explicitly disallowed in staging paper docs. | |

## Final decision rule

External Ready = YES only if every item above is YES; otherwise External Ready = NO.

# API Guarantees vs Non-Guarantees (MVP v1.1)

This document separates what the API guarantees from what it explicitly does not guarantee. It is limited to the currently implemented behavior documented in `docs/api/usage_contract.md` plus the operator access contract documented in `docs/access-policy.md`.

## Guaranteed

- The API guarantees that analysis requests are snapshot-only and require an `ingestion_run_id`.
- The API guarantees no implicit live data in analysis requests.
- The API guarantees that the request and response shapes documented in `docs/api/usage_contract.md` define the MVP v1.1 contract.
- The API guarantees that the documented field requirements, enums, and ranges in `docs/api/usage_contract.md` define the MVP v1.1 contract.
- The API guarantees that `docs/access-policy.md` is the authoritative role-to-endpoint contract for the current operator-facing routes in `src/api/main.py`.
- The API guarantees that every operator-facing endpoint covered by that contract is classified as either `read_only` or `mutating`.
- The API guarantees that the documented operator roles for the covered control-plane endpoints are limited to `owner`, `operator`, and `read_only`.
- The API guarantees deterministic denial semantics for protected operator-facing endpoints: unauthenticated requests map to `401 Unauthorized`, and authenticated requests without the required role map to `403 Forbidden` as documented in `docs/external/error_semantics.md`.

## Not guaranteed

- The API does not guarantee deterministic results for execution paths outside the snapshot-only analysis contract.
- The API does not guarantee deterministic results when live data sources are used outside the snapshot-only analysis contract.
- The API does not guarantee compatibility with request or response shapes not documented in `docs/api/usage_contract.md`.
- The API does not guarantee schema stability outside the MVP v1.1 contract documented in `docs/api/usage_contract.md`.
- The API does not guarantee an operator access contract for routes that are not listed in `docs/access-policy.md`.
- The API does not guarantee anonymous access to any operator-facing route covered by `docs/access-policy.md`.
- The API does not guarantee any role model other than the documented `owner`, `operator`, and `read_only` contract for the currently covered control-plane endpoints.
- The API does not guarantee profitability.
- The API does not guarantee signal completeness.
- The API does not guarantee complete snapshot coverage or more than one row per symbol and timeframe.
- The API does not guarantee snapshot ingestion or population of snapshot tables.

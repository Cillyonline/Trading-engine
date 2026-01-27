# API Guarantees vs Non-Guarantees (MVP v1.1)

This document separates what the API guarantees from what it explicitly does not guarantee. It is limited to the currently implemented behavior documented in `docs/api/usage_contract.md`.

## Guaranteed

- The API guarantees that analysis requests are snapshot-only and require an `ingestion_run_id`.
- The API guarantees no implicit live data in analysis requests.
- The API guarantees that the request and response shapes documented in `docs/api/usage_contract.md` define the MVP v1.1 contract.
- The API guarantees that the documented field requirements, enums, and ranges in `docs/api/usage_contract.md` define the MVP v1.1 contract.

## Not guaranteed

- The API does not guarantee deterministic results for execution paths outside the snapshot-only analysis contract.
- The API does not guarantee deterministic results when live data sources are used outside the snapshot-only analysis contract.
- The API does not guarantee compatibility with request or response shapes not documented in `docs/api/usage_contract.md`.
- The API does not guarantee schema stability outside the MVP v1.1 contract documented in `docs/api/usage_contract.md`.
- The API does not guarantee profitability.
- The API does not guarantee signal completeness.
- The API does not guarantee complete snapshot coverage or more than one row per symbol and timeframe.
- The API does not guarantee snapshot ingestion or population of snapshot tables.

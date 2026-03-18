# Phase 37 Watchlist Engine Planning Package

## Purpose

This file is the local planning index for the Phase 37 Watchlist Engine work package.

It prepares GitHub-ready milestone and issue content without pushing anything to GitHub yet.

## Scope Summary

Phase 37 remains bounded to:

- watchlist CRUD
- watchlist persistence
- persisted watchlist execution
- deterministic ranking results
- dedicated runtime-served `/ui` watchlist workflow
- evidence-based Phase 37 documentation alignment

Phase 37 remains explicitly out of scope for:

- market data provider expansion
- charting and visual analysis
- trading-desk heatmaps or leaderboards
- alerts and notifications
- strategy lab workflows
- paper-trading product workflows
- live-trading workflows

## Labels

Reuse existing repository labels if they already exist in GitHub:

- `api`
- `ui`
- `docs`
- `testing`
- `governance`

Add this new phase label when the GitHub objects are created:

- `phase:37`

## Milestones

- [Phase 37 milestones](phase-37-watchlist-engine-milestones.md)

## Issue Drafts

1. [Issue 1 - Watchlist persistence contract and repository](phase-37-issue-01-watchlist-persistence.md)
2. [Issue 2 - Watchlist CRUD API surface](phase-37-issue-02-watchlist-crud-api.md)
3. [Issue 3 - Watchlist execution and ranking workflow](phase-37-issue-03-watchlist-execution-ranking.md)
4. [Issue 4 - Runtime /ui watchlist management and execution flow](phase-37-issue-04-runtime-ui-watchlists.md)
5. [Issue 5 - Phase 37 status and contract alignment](phase-37-issue-05-phase-37-doc-alignment.md)

## Recommended Sequencing

1. Issue 1 in Milestone `Phase 37A - Watchlist Foundation`
2. Issue 2 in Milestone `Phase 37A - Watchlist Foundation`
3. Issue 3 in Milestone `Phase 37A - Watchlist Foundation`
4. Issue 4 in Milestone `Phase 37B - Watchlist Product Surface`
5. Issue 5 in Milestone `Phase 37B - Watchlist Product Surface`

## Notes

- The issue drafts follow the repository issue template structure from `.github/ISSUE_TEMPLATE/issue.md`.
- The package is intentionally local-only and can be copied into GitHub later without reformatting.
- The issue set keeps implementation and documentation scope separated so later PRs can stay narrow and reviewable.

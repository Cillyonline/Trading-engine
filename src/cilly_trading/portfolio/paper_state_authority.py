"""Canonical bounded paper portfolio state-authority contract.

This module defines the single authoritative source of truth for paper portfolio
and account state used during bounded paper evaluation.  Every paper inspection
surface MUST derive its state from the canonical execution repository described
here.  No alternative or competing state authority is permitted.

Source of truth
---------------
``SqliteCanonicalExecutionRepository`` (persisted in ``core_orders``,
``core_execution_events``, and ``core_trades`` tables) is the sole authoritative
store for paper execution state.  All derived views — account balance, positions,
portfolio aggregation, and reconciliation — are computed deterministically from
these canonical entities on every read request.

Restart-safe persistence
------------------------
Because the canonical repository is backed by SQLite, all execution state
survives process restarts and reloads without loss.  On restart the repository
re-opens the existing database file and deterministic derivation functions
reproduce identical views from the persisted entities.

Reconciliation semantics
------------------------
``build_paper_reconciliation_mismatches`` cross-validates every entity
relationship (order ↔ event ↔ trade ↔ position) and every account equation
(cash, equity, PnL) against the canonical entities.  Any inconsistency is
surfaced as a deterministic mismatch item with ``code``, ``entity_type``, and
``entity_id``.  The reconciliation endpoint fails closed: ``ok`` is ``True``
only when zero mismatches exist.

Competing-authority prohibition
-------------------------------
No runtime code path may use an alternative state source (e.g. in-memory
caches, legacy ``trades`` table payloads, or environment-variable overrides for
execution state) as authoritative for paper portfolio or account inspection.
The only permitted environment-variable input is
``CILLY_PAPER_ACCOUNT_STARTING_CASH`` which supplies the initial cash constant
and does not override any execution-derived value.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from cilly_trading.models import ExecutionEvent, Order, Trade


# ---------------------------------------------------------------------------
# State-authority contract constants
# ---------------------------------------------------------------------------

#: Identifier for the single bounded paper-state authority.
PAPER_STATE_AUTHORITY_ID: str = "canonical_execution_repository"

#: Human-readable label used in documentation and inspection surfaces.
PAPER_STATE_AUTHORITY_LABEL: str = (
    "SqliteCanonicalExecutionRepository (core_orders, core_execution_events, core_trades)"
)

#: Tables that together form the authoritative paper execution state.
CANONICAL_TABLES: tuple[str, ...] = (
    "core_orders",
    "core_execution_events",
    "core_trades",
)

#: Derived views that MUST be computed from canonical entities on each read.
DERIVED_VIEWS: tuple[str, ...] = (
    "account",
    "positions",
    "portfolio_positions",
    "reconciliation",
)

#: The single permitted environment-variable constant input (not execution state).
PERMITTED_ENV_CONSTANTS: tuple[str, ...] = (
    "CILLY_PAPER_ACCOUNT_STARTING_CASH",
)


# ---------------------------------------------------------------------------
# Contract validation helpers
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class StateAuthorityAssertion:
    """Result of a state-authority validation check."""

    canonical_orders: int
    canonical_execution_events: int
    canonical_trades: int
    authority_id: str
    restart_safe: bool


def assert_state_authority(
    *,
    orders: Sequence[Order],
    execution_events: Sequence[ExecutionEvent],
    trades: Sequence[Trade],
) -> StateAuthorityAssertion:
    """Return a snapshot of canonical entity counts for authority validation.

    This function does not mutate state.  It exists so that integration tests
    can assert that all paper-derived views originate from the same canonical
    entity set and that the authority identifier is singular and explicit.
    """
    return StateAuthorityAssertion(
        canonical_orders=len(orders),
        canonical_execution_events=len(execution_events),
        canonical_trades=len(trades),
        authority_id=PAPER_STATE_AUTHORITY_ID,
        restart_safe=True,
    )

"""Bounded paper execution worker (OPS-P52).

Converts eligible analysis signals into canonical paper execution state using
the policy defined in:

    docs/operations/runtime/signal_to_paper_execution_policy.md

State authority:
    All paper state is read from and written to
    ``SqliteCanonicalExecutionRepository`` as defined in
    ``src/cilly_trading/portfolio/paper_state_authority.py``.  No competing
    state source is used.

Non-live boundary:
    This worker operates exclusively within the bounded paper simulation:
    - No live orders are placed.
    - No broker APIs are called.
    - No real capital is at risk.
    - Passing all policy checks does not imply live-trading readiness.

Restart safety:
    All entity IDs are computed deterministically from the signal identity.
    The same signal always produces the same IDs and payloads.  Persisting
    twice is idempotent; the duplicate-entry check prevents double execution
    under normal operating conditions.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Literal, Optional, Sequence

from cilly_trading.engine.paper_execution_risk_profile import (
    DEFAULT_PAPER_EXECUTION_RISK_PROFILE,
    PaperExecutionRiskProfile,
)
from cilly_trading.engine.risk import evaluate_risk_framework_execution_decision
from cilly_trading.non_live_evaluation_contract import (
    CanonicalRiskRejectionReasonCode,
    normalize_risk_rejection_reason_code,
)
from cilly_trading.models import (
    ExecutionEvent,
    Order,
    Signal,
    Trade,
    canonical_json,
    compute_execution_event_id,
    compute_signal_id,
    sha256_hex,
)
from cilly_trading.portfolio_framework.capital_allocation_policy import (
    DeterministicTradeSizingInput,
    compute_deterministic_trade_notional,
)
from cilly_trading.repositories import CanonicalExecutionRepository
from cilly_trading.risk_framework.allocation_rules import RiskLimits


# ---------------------------------------------------------------------------
# Policy constants (bounded paper simulation parameters — static defaults)
# ---------------------------------------------------------------------------

#: Minimum signal score required for paper entry (inclusive) on a 0..100 scale.
MIN_SCORE_THRESHOLD: float = DEFAULT_PAPER_EXECUTION_RISK_PROFILE.min_score_threshold

#: Maximum fraction of account equity for a single paper position.
MAX_POSITION_PCT: Decimal = DEFAULT_PAPER_EXECUTION_RISK_PROFILE.max_position_pct

#: Maximum trade-level risk budget fraction of account equity.
MAX_RISK_PER_TRADE_PCT: Decimal = (
    DEFAULT_PAPER_EXECUTION_RISK_PROFILE.max_risk_per_trade_pct
)

#: Minimum bounded trade-risk input used for deterministic sizing.
MIN_TRADE_RISK_PCT: Decimal = DEFAULT_PAPER_EXECUTION_RISK_PROFILE.min_trade_risk_pct

#: Maximum bounded trade-risk input used for deterministic sizing.
MAX_TRADE_RISK_PCT: Decimal = DEFAULT_PAPER_EXECUTION_RISK_PROFILE.max_trade_risk_pct

#: Notional rounding quantum for deterministic sizing.
NOTIONAL_ROUNDING_QUANTUM: Decimal = (
    DEFAULT_PAPER_EXECUTION_RISK_PROFILE.notional_rounding_quantum
)

#: Maximum fraction of account equity across all open paper positions.
MAX_TOTAL_EXPOSURE_PCT: Decimal = (
    DEFAULT_PAPER_EXECUTION_RISK_PROFILE.max_total_exposure_pct
)

#: Maximum number of concurrent open paper positions.
MAX_CONCURRENT_POSITIONS: int = (
    DEFAULT_PAPER_EXECUTION_RISK_PROFILE.max_concurrent_positions
)

#: Maximum fraction of account equity for a strategy aggregate.
MAX_STRATEGY_EXPOSURE_PCT: Decimal = (
    DEFAULT_PAPER_EXECUTION_RISK_PROFILE.max_strategy_exposure_pct
)

#: Maximum fraction of account equity for a symbol aggregate.
MAX_SYMBOL_EXPOSURE_PCT: Decimal = (
    DEFAULT_PAPER_EXECUTION_RISK_PROFILE.max_symbol_exposure_pct
)

#: Minimum cooldown in hours between accepted entries for the same
#: ``(symbol, strategy)`` pair.
COOLDOWN_HOURS: int = DEFAULT_PAPER_EXECUTION_RISK_PROFILE.cooldown_hours

#: Default paper quantity (one unit per entry).
DEFAULT_PAPER_QUANTITY: Decimal = (
    DEFAULT_PAPER_EXECUTION_RISK_PROFILE.default_paper_quantity
)

#: Fallback entry price used when the signal provides no price or entry_zone.
DEFAULT_PAPER_ENTRY_PRICE: Decimal = (
    DEFAULT_PAPER_EXECUTION_RISK_PROFILE.default_paper_entry_price
)

_PRICE_SCALE: Decimal = Decimal("0.0001")


# ---------------------------------------------------------------------------
# Outcome codes
# ---------------------------------------------------------------------------

OutcomeCode = Literal[
    "eligible",
    "skip:score_below_threshold",
    "skip:duplicate_entry",
    "skip:cooldown_active",
    "reject:invalid_signal_fields",
    "reject:missing_trade_risk_input",
    "reject:invalid_trade_risk_input",
    "reject:max_risk_per_trade_exceeded",
    "reject:position_size_exceeds_limit",
    "reject:total_exposure_exceeds_limit",
    "reject:strategy_exposure_exceeds_limit",
    "reject:symbol_exposure_exceeds_limit",
    "reject:concurrent_position_limit_exceeded",
    "reject:risk_kill_switch_enabled",
]

_RISK_REASON_TO_OUTCOME: dict[CanonicalRiskRejectionReasonCode, OutcomeCode] = {
    "rejected:risk_framework_max_position_size_exceeded": (
        "reject:position_size_exceeds_limit"
    ),
    "rejected:risk_framework_max_account_exposure_pct_exceeded": (
        "reject:total_exposure_exceeds_limit"
    ),
    "rejected:risk_framework_max_strategy_exposure_pct_exceeded": (
        "reject:strategy_exposure_exceeds_limit"
    ),
    "rejected:risk_framework_max_symbol_exposure_pct_exceeded": (
        "reject:symbol_exposure_exceeds_limit"
    ),
    "rejected:risk_framework_kill_switch_enabled": "reject:risk_kill_switch_enabled",
}


@dataclass(frozen=True)
class SignalEvaluationResult:
    """Result returned by the bounded paper execution worker for every signal.

    ``outcome`` is always set to an explicit code as defined in the policy.
    ``order_id`` and ``trade_id`` are populated only when ``outcome == "eligible"``
    and the canonical entities have been persisted.
    ``reason`` is populated for skip and reject outcomes.
    """

    outcome: OutcomeCode
    signal_id: Optional[str] = None
    order_id: Optional[str] = None
    trade_id: Optional[str] = None
    reason: Optional[str] = None
    decision_inputs: Optional[dict[str, str]] = None


# ---------------------------------------------------------------------------
# Deterministic ID computation
# ---------------------------------------------------------------------------


def _resolve_signal_id(signal: Signal) -> str:
    """Return the canonical signal ID, computing it if not already present."""
    if signal.get("signal_id"):
        return str(signal["signal_id"])
    return compute_signal_id(signal)


def _compute_paper_order_id(signal_id: str) -> str:
    """Compute a deterministic paper order ID from a signal ID."""
    return f"ord_{sha256_hex(canonical_json({'scope': 'paper_entry', 'signal_id': signal_id}))}"


def _compute_paper_trade_id(signal_id: str) -> str:
    """Compute a deterministic paper trade ID from a signal ID."""
    return f"trd_{sha256_hex(canonical_json({'scope': 'paper_entry', 'signal_id': signal_id}))}"


def _compute_paper_position_id(signal_id: str) -> str:
    """Compute a deterministic paper position ID from a signal ID."""
    return f"pos_{sha256_hex(canonical_json({'scope': 'paper_entry', 'signal_id': signal_id}))}"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_timestamp(ts: str) -> datetime.datetime:
    """Parse an ISO-8601 timestamp string, handling the trailing ``Z``."""
    return datetime.datetime.fromisoformat(ts.replace("Z", "+00:00"))


def _extract_entry_price(
    signal: Signal,
    *,
    fallback_entry_price: Decimal,
) -> Decimal:
    """Extract a representative entry price from the signal.

    Uses the entry_zone midpoint when available; falls back to
    ``fallback_entry_price`` otherwise.
    """
    entry_zone = signal.get("entry_zone")
    if entry_zone is not None:
        mid = Decimal(str(entry_zone["from_"] + entry_zone["to"])) / Decimal("2")
        return mid.quantize(_PRICE_SCALE, rounding=ROUND_HALF_UP)
    return fallback_entry_price


_DIRECTION_TO_SIDE: dict[str, str] = {
    "long": "BUY",
    "short": "SELL",
}


def _direction_to_order_side(direction: str) -> str:
    """Map a canonical signal direction to an order side.

    ``"long"`` → ``"BUY"``, ``"short"`` → ``"SELL"``.
    Raises ``ValueError`` for unrecognised directions.
    """
    side = _DIRECTION_TO_SIDE.get(direction)
    if side is None:
        raise ValueError(f"unknown direction: {direction!r}")
    return side


def _validate_signal_fields(signal: Signal) -> Optional[str]:
    """Return a human-readable error if required fields are absent or invalid.

    Returns ``None`` when all required fields are valid.
    """
    required = ("symbol", "strategy", "direction", "score", "timestamp", "stage")
    missing = [f for f in required if not signal.get(f)]
    if missing:
        return f"missing required fields: {', '.join(missing)}"

    try:
        score = float(signal["score"])  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return "score must be numeric"

    if not (0.0 <= score <= 100.0):
        return f"score={score} out of range [0.0, 100.0]"

    try:
        _parse_timestamp(signal["timestamp"])  # type: ignore[arg-type]
    except (ValueError, TypeError, AttributeError):
        return f"timestamp is not a parseable ISO-8601 string: {signal.get('timestamp')!r}"

    return None


def _risk_rejection_outcome(reason: str) -> OutcomeCode:
    normalized_reason = normalize_risk_rejection_reason_code(reason)
    outcome = _RISK_REASON_TO_OUTCOME.get(normalized_reason)
    if outcome is None:
        raise ValueError(f"unsupported risk rejection reason: {normalized_reason}")
    return outcome


def _resolve_trade_risk_pct(signal: Signal) -> tuple[OutcomeCode | None, Decimal | None, str | None]:
    raw_trade_risk_pct = signal.get("trade_risk_pct")
    if raw_trade_risk_pct is None:
        return (
            "reject:missing_trade_risk_input",
            None,
            "trade_risk_pct is required for deterministic sizing",
        )
    try:
        trade_risk_pct = Decimal(str(raw_trade_risk_pct))
    except Exception:
        return (
            "reject:invalid_trade_risk_input",
            None,
            f"trade_risk_pct is not numeric: {raw_trade_risk_pct!r}",
        )
    if not trade_risk_pct.is_finite():
        return (
            "reject:invalid_trade_risk_input",
            None,
            "trade_risk_pct must be finite",
        )
    if trade_risk_pct <= Decimal("0"):
        return (
            "reject:invalid_trade_risk_input",
            None,
            f"trade_risk_pct must be > 0, got {trade_risk_pct}",
        )
    return None, trade_risk_pct, None


def _build_decision_inputs_payload(
    *,
    trade_risk_pct: Decimal,
    bounded_trade_risk_pct: Decimal,
    risk_budget_notional: Decimal,
    proposed_notional: Decimal,
    account_equity: Decimal,
    profile: PaperExecutionRiskProfile,
    entry_price: Decimal,
) -> dict[str, str]:
    return {
        "account_equity": str(account_equity),
        "max_risk_per_trade_pct": str(profile.max_risk_per_trade_pct),
        "trade_risk_pct": str(trade_risk_pct),
        "bounded_trade_risk_pct": str(bounded_trade_risk_pct),
        "risk_budget_notional": str(risk_budget_notional),
        "proposed_position_notional": str(proposed_notional),
        "entry_price": str(entry_price),
        "max_total_exposure_pct": str(profile.max_total_exposure_pct),
        "max_strategy_exposure_pct": str(profile.max_strategy_exposure_pct),
        "max_symbol_exposure_pct": str(profile.max_symbol_exposure_pct),
        "max_concurrent_positions": str(profile.max_concurrent_positions),
    }


# ---------------------------------------------------------------------------
# Worker
# ---------------------------------------------------------------------------


class BoundedPaperExecutionWorker:
    """Deterministic worker: converts eligible signals into bounded paper execution state.

    Each call to ``process_signal`` applies the ordered 5-step evaluation
    policy defined in ``signal_to_paper_execution_policy.md`` and returns an
    explicit ``SignalEvaluationResult``.

    When a signal is eligible all canonical paper entities (Order,
    ExecutionEvents, Trade) are created deterministically and persisted to the
    canonical execution repository.  The same signal always produces the same
    entity IDs; persistence is therefore idempotent and restart-safe.

    Non-live boundary:
        No broker calls, no live orders, no real capital.
    """

    def __init__(
        self,
        repository: CanonicalExecutionRepository,
        *,
        risk_profile: PaperExecutionRiskProfile = DEFAULT_PAPER_EXECUTION_RISK_PROFILE,
    ) -> None:
        self._repo = repository
        self._risk_profile = risk_profile
        self._risk_limits = self._build_risk_limits()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def process_signal(self, signal: Signal) -> SignalEvaluationResult:
        """Evaluate and process a single signal against the bounded policy.

        Returns a ``SignalEvaluationResult`` with an explicit outcome code.
        When the outcome is ``"eligible"``, canonical paper entities are
        created and persisted before returning.
        """
        result = self._evaluate(signal)
        if result.outcome == "eligible":
            result = self._persist_paper_entry(
                signal,
                decision_inputs=result.decision_inputs,
            )
        return result

    def process_batch(self, signals: Sequence[Signal]) -> list[SignalEvaluationResult]:
        """Process a batch of signals sequentially.

        Returns one ``SignalEvaluationResult`` per signal in input order.
        """
        return [self.process_signal(signal) for signal in signals]

    @property
    def risk_profile(self) -> PaperExecutionRiskProfile:
        """Return the canonical validated risk profile used by this worker."""
        return self._risk_profile

    def _build_risk_limits(self) -> RiskLimits:
        """Build deterministic risk-framework limits for paper execution."""
        max_notional_from_risk_budget = (
            self._risk_profile.account_equity
            * self._risk_profile.max_risk_per_trade_pct
            / self._risk_profile.min_trade_risk_pct
        )
        return RiskLimits(
            max_account_exposure_pct=float(self._risk_profile.max_total_exposure_pct),
            max_position_size=float(max_notional_from_risk_budget),
            max_strategy_exposure_pct=float(
                self._risk_profile.max_strategy_exposure_pct
            ),
            max_symbol_exposure_pct=float(self._risk_profile.max_symbol_exposure_pct),
        )

    def _compute_trade_sizing_for_signal(
        self,
        signal: Signal,
        *,
        entry_price: Decimal,
    ) -> tuple[SignalEvaluationResult | None, Decimal | None, dict[str, str] | None]:
        rejection_outcome, trade_risk_pct, rejection_reason = _resolve_trade_risk_pct(signal)
        if rejection_outcome is not None or trade_risk_pct is None:
            return (
                SignalEvaluationResult(
                    outcome=rejection_outcome or "reject:invalid_trade_risk_input",
                    reason=rejection_reason,
                ),
                None,
                None,
            )

        sizing_decision = compute_deterministic_trade_notional(
            DeterministicTradeSizingInput(
                account_equity=self._risk_profile.account_equity,
                max_risk_per_trade_pct=self._risk_profile.max_risk_per_trade_pct,
                trade_risk_pct=trade_risk_pct,
                min_trade_risk_pct=self._risk_profile.min_trade_risk_pct,
                max_trade_risk_pct=self._risk_profile.max_trade_risk_pct,
                notional_rounding_quantum=self._risk_profile.notional_rounding_quantum,
            )
        )
        decision_inputs = _build_decision_inputs_payload(
            trade_risk_pct=sizing_decision.trade_risk_pct,
            bounded_trade_risk_pct=sizing_decision.bounded_trade_risk_pct,
            risk_budget_notional=sizing_decision.risk_budget_notional,
            proposed_notional=sizing_decision.rounded_position_notional,
            account_equity=self._risk_profile.account_equity,
            profile=self._risk_profile,
            entry_price=entry_price,
        )
        if not sizing_decision.accepted:
            rejection_outcome_code: OutcomeCode = "reject:invalid_trade_risk_input"
            if sizing_decision.reason_code == "sizing_rejected:max_risk_per_trade_exceeded":
                rejection_outcome_code = "reject:max_risk_per_trade_exceeded"
            return (
                SignalEvaluationResult(
                    outcome=rejection_outcome_code,
                    reason=sizing_decision.reason_code,
                    decision_inputs=decision_inputs,
                ),
                None,
                decision_inputs,
            )
        return None, sizing_decision.rounded_position_notional, decision_inputs

    # ------------------------------------------------------------------
    # Policy evaluation (read-only)
    # ------------------------------------------------------------------

    def _evaluate(self, signal: Signal) -> SignalEvaluationResult:
        """Apply the 5-step ordered policy evaluation.

        Steps:
            1. Eligibility check (required fields)
            2. Score threshold check
            3. Duplicate-entry check
            4. Cooldown check
            5. Exposure and position-limit checks
        """
        # Step 1: eligibility — required signal fields
        field_error = _validate_signal_fields(signal)
        if field_error is not None:
            return SignalEvaluationResult(
                outcome="reject:invalid_signal_fields",
                reason=field_error,
            )

        symbol: str = signal["symbol"]  # type: ignore[assignment]
        strategy: str = signal["strategy"]  # type: ignore[assignment]
        direction: str = signal["direction"]  # type: ignore[assignment]
        score = float(signal["score"])  # type: ignore[arg-type]

        # Step 2: score threshold
        if score < self._risk_profile.min_score_threshold:
            return SignalEvaluationResult(
                outcome="skip:score_below_threshold",
                reason=(
                    f"score={score} < min_score_threshold={self._risk_profile.min_score_threshold}"
                ),
            )

        # Load canonical state for this (symbol, strategy) pair.
        # The limit of 1000 is sufficient for bounded paper simulation;
        # a paper session with more than 1000 trades per pair is outside
        # the supported bounded scope.
        symbol_strategy_trades = self._repo.list_trades(
            strategy_id=strategy,
            symbol=symbol,
            limit=1000,
        )
        open_pair_trades = [t for t in symbol_strategy_trades if t.status == "open"]

        # Step 3: duplicate-entry — no open position for (symbol, strategy, direction)
        for trade in open_pair_trades:
            if trade.direction == direction:
                return SignalEvaluationResult(
                    outcome="skip:duplicate_entry",
                    reason=(
                        f"open trade exists for ({symbol}, {strategy}, {direction})"
                    ),
                )

        # Step 4: cooldown — min 24h since last accepted entry for (symbol, strategy)
        if symbol_strategy_trades:
            most_recent_opened_at = max(t.opened_at for t in symbol_strategy_trades)
            signal_ts = _parse_timestamp(signal["timestamp"])  # type: ignore[arg-type]
            last_entry_ts = _parse_timestamp(most_recent_opened_at)
            elapsed = signal_ts - last_entry_ts
            cooldown_window = datetime.timedelta(hours=self._risk_profile.cooldown_hours)
            if elapsed < cooldown_window:
                return SignalEvaluationResult(
                    outcome="skip:cooldown_active",
                    reason=(
                        f"cooldown active: elapsed={elapsed} < cooldown={cooldown_window} "
                        f"since last entry at {most_recent_opened_at}"
                    ),
                )

        # Step 5: exposure and position-limit checks
        entry_price = _extract_entry_price(
            signal,
            fallback_entry_price=self._risk_profile.default_paper_entry_price,
        )
        sizing_rejection, proposed_notional, decision_inputs = self._compute_trade_sizing_for_signal(
            signal,
            entry_price=entry_price,
        )
        if sizing_rejection is not None or proposed_notional is None:
            return sizing_rejection or SignalEvaluationResult(
                outcome="reject:invalid_trade_risk_input",
                reason="trade sizing failed",
            )

        # Load all open trades for canonical exposure/concurrent-position checks.
        # The limit of 1000 reflects the bounded paper simulation scope
        # (max_concurrent_positions=10 by default; even large sessions remain
        # well within this bound).
        all_trades = self._repo.list_trades(limit=1000)
        all_open_trades = [t for t in all_trades if t.status == "open"]

        # Concurrent position limit
        if len(all_open_trades) >= self._risk_profile.max_concurrent_positions:
            return SignalEvaluationResult(
                outcome="reject:concurrent_position_limit_exceeded",
                reason=(
                    f"concurrent_positions={len(all_open_trades)} >= "
                    f"limit={self._risk_profile.max_concurrent_positions}"
                ),
                decision_inputs=decision_inputs,
            )

        current_exposure = sum(
            (t.exposure_notional or Decimal("0")) for t in all_open_trades
        )
        strategy_exposure = sum(
            (t.exposure_notional or Decimal("0"))
            for t in all_open_trades
            if t.strategy_id == strategy
        )
        symbol_exposure = sum(
            (t.exposure_notional or Decimal("0"))
            for t in all_open_trades
            if t.symbol == symbol
        )
        signal_id = _resolve_signal_id(signal)
        risk_decision = evaluate_risk_framework_execution_decision(
            request_id=f"paper:{signal_id}:risk",
            strategy_id=strategy,
            symbol=symbol,
            proposed_position_size=float(proposed_notional),
            account_equity=float(self._risk_profile.account_equity),
            current_exposure=float(current_exposure),
            strategy_exposure=float(strategy_exposure),
            symbol_exposure=float(symbol_exposure),
            limits=self._risk_limits,
            rule_version="paper-risk-framework-v1",
        )

        if risk_decision.decision == "REJECTED":
            normalized_reason = normalize_risk_rejection_reason_code(risk_decision.reason)
            return SignalEvaluationResult(
                outcome=_risk_rejection_outcome(normalized_reason),
                reason=normalized_reason,
                decision_inputs=decision_inputs,
            )

        return SignalEvaluationResult(outcome="eligible", decision_inputs=decision_inputs)

    # ------------------------------------------------------------------
    # Paper entity creation and persistence
    # ------------------------------------------------------------------

    def _persist_paper_entry(
        self,
        signal: Signal,
        *,
        decision_inputs: dict[str, str] | None,
    ) -> SignalEvaluationResult:
        """Create and persist canonical paper entities for an eligible signal.

        Deterministic: the same signal always produces the same entity IDs
        and payloads.  Safe to call on restart; idempotent against the
        canonical repository.
        """
        signal_id = _resolve_signal_id(signal)
        order_id = _compute_paper_order_id(signal_id)
        trade_id = _compute_paper_trade_id(signal_id)
        position_id = _compute_paper_position_id(signal_id)

        symbol: str = signal["symbol"]  # type: ignore[assignment]
        strategy: str = signal["strategy"]  # type: ignore[assignment]
        direction: str = signal["direction"]  # type: ignore[assignment]
        occurred_at: str = signal["timestamp"]  # type: ignore[assignment]
        entry_price = _extract_entry_price(
            signal,
            fallback_entry_price=self._risk_profile.default_paper_entry_price,
        )
        proposed_notional = (
            Decimal(decision_inputs["proposed_position_notional"])
            if decision_inputs is not None
            else self._risk_profile.default_paper_quantity * entry_price
        )
        quantity = (proposed_notional / entry_price).quantize(
            Decimal("0.00000001"),
            rounding=ROUND_HALF_UP,
        )
        side = _direction_to_order_side(direction)

        # --- Execution events ------------------------------------------
        created_event_id = compute_execution_event_id(
            order_id=order_id,
            event_type="created",
            occurred_at=occurred_at,
            sequence=1,
        )
        submitted_event_id = compute_execution_event_id(
            order_id=order_id,
            event_type="submitted",
            occurred_at=occurred_at,
            sequence=2,
        )
        filled_event_id = compute_execution_event_id(
            order_id=order_id,
            event_type="filled",
            occurred_at=occurred_at,
            sequence=3,
        )

        created_event = ExecutionEvent.model_validate(
            {
                "event_id": created_event_id,
                "order_id": order_id,
                "strategy_id": strategy,
                "symbol": symbol,
                "side": side,
                "event_type": "created",
                "occurred_at": occurred_at,
                "sequence": 1,
                "position_id": position_id,
                "trade_id": trade_id,
            }
        )
        submitted_event = ExecutionEvent.model_validate(
            {
                "event_id": submitted_event_id,
                "order_id": order_id,
                "strategy_id": strategy,
                "symbol": symbol,
                "side": side,
                "event_type": "submitted",
                "occurred_at": occurred_at,
                "sequence": 2,
                "position_id": position_id,
                "trade_id": trade_id,
            }
        )
        filled_event = ExecutionEvent.model_validate(
            {
                "event_id": filled_event_id,
                "order_id": order_id,
                "strategy_id": strategy,
                "symbol": symbol,
                "side": side,
                "event_type": "filled",
                "occurred_at": occurred_at,
                "sequence": 3,
                "execution_quantity": quantity,
                "execution_price": entry_price,
                "commission": Decimal("0"),
                "position_id": position_id,
                "trade_id": trade_id,
            }
        )

        # --- Filled order -----------------------------------------------
        order = Order.model_validate(
            {
                "order_id": order_id,
                "strategy_id": strategy,
                "symbol": symbol,
                "sequence": 1,
                "side": side,
                "order_type": "market",
                "time_in_force": "day",
                "status": "filled",
                "quantity": quantity,
                "filled_quantity": quantity,
                "created_at": occurred_at,
                "submitted_at": occurred_at,
                "average_fill_price": entry_price,
                "last_execution_event_id": filled_event_id,
                "position_id": position_id,
                "trade_id": trade_id,
            }
        )

        # --- Open trade -------------------------------------------------
        exposure_notional = quantity * entry_price
        trade = Trade.model_validate(
            {
                "trade_id": trade_id,
                "position_id": position_id,
                "strategy_id": strategy,
                "symbol": symbol,
                "direction": direction,
                "status": "open",
                "opened_at": occurred_at,
                "quantity_opened": quantity,
                "quantity_closed": Decimal("0"),
                "average_entry_price": entry_price,
                "exposure_notional": exposure_notional,
                "opening_order_ids": [order_id],
                "execution_event_ids": [filled_event_id],
            }
        )

        # --- Persist (idempotent, restart-safe) -------------------------
        self._repo.save_order(order)
        self._repo.save_execution_events([created_event, submitted_event, filled_event])
        self._repo.save_trade(trade)

        return SignalEvaluationResult(
            outcome="eligible",
            signal_id=signal_id,
            order_id=order_id,
            trade_id=trade_id,
            decision_inputs=decision_inputs,
        )


__all__ = [
    "BoundedPaperExecutionWorker",
    "DEFAULT_PAPER_EXECUTION_RISK_PROFILE",
    "SignalEvaluationResult",
    "MIN_SCORE_THRESHOLD",
    "MAX_POSITION_PCT",
    "MAX_RISK_PER_TRADE_PCT",
    "MIN_TRADE_RISK_PCT",
    "MAX_TRADE_RISK_PCT",
    "NOTIONAL_ROUNDING_QUANTUM",
    "MAX_STRATEGY_EXPOSURE_PCT",
    "MAX_SYMBOL_EXPOSURE_PCT",
    "MAX_TOTAL_EXPOSURE_PCT",
    "MAX_CONCURRENT_POSITIONS",
    "COOLDOWN_HOURS",
    "DEFAULT_PAPER_QUANTITY",
    "DEFAULT_PAPER_ENTRY_PRICE",
    "PaperExecutionRiskProfile",
    "_direction_to_order_side",
]

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
from decimal import ROUND_HALF_UP, Decimal, localcontext
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
from cilly_trading.engine.paper_performance import (
    PaperPerformanceAttribution,
    PaperPerformanceSummary,
    compute_paper_performance_attribution,
    compute_paper_performance_summary,
)
from cilly_trading.engine.regime_classifier import RegimeState
from cilly_trading.risk_framework.correlation_risk import (
    PriceHistory,
    evaluate_correlation_risk,
)


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
    "eligible:partial_exit",
    "eligible:full_exit",
    "skip:score_below_threshold",
    "skip:exit_signal_not_entry_candidate",
    "skip:duplicate_entry",
    "skip:cooldown_active",
    "skip:entry_zone_not_reached",
    "skip:correlation_risk_blocked",
    "skip:drawdown_guard_active",
    "skip:regime_filtered",
    "skip:no_open_position_to_exit",
    "skip:exit_quantity_zero",
    "reject:invalid_signal_fields",
    "reject:missing_trade_risk_input",
    "reject:invalid_trade_risk_input",
    "reject:atr_not_provided",
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
class EntryBar:
    """Minimal OHLCV snapshot used to validate paper-execution fills.

    Carries only the high/low needed to verify entry-zone intersection. A
    consumer of the worker can construct one from any bar source (replay
    feed, live data adapter, backtest dataframe).
    """

    high: Decimal
    low: Decimal


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
    decision_inputs: Optional[dict[str, object]] = None


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


def _compute_paper_exit_order_id(signal_id: str) -> str:
    """Compute a deterministic paper exit order ID from a signal ID."""
    return f"ord_{sha256_hex(canonical_json({'scope': 'paper_exit', 'signal_id': signal_id}))}"


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
        with localcontext() as ctx:
            ctx.prec = 28
            ctx.rounding = ROUND_HALF_UP
            mid = (Decimal(str(entry_zone["from_"])) + Decimal(str(entry_zone["to"]))) / Decimal("2")
            return mid.quantize(_PRICE_SCALE)
    return fallback_entry_price


_DIRECTION_TO_SIDE: dict[str, str] = {
    "long": "BUY",
    "short": "SELL",
}


def _apply_slippage(
    *,
    reference_price: Decimal,
    direction: str,
    slippage_rate: Decimal,
) -> Decimal:
    """Adjust the reference price for slippage in the direction of the trade.

    Long entries pay slightly more; short entries receive slightly less.
    """
    with localcontext() as ctx:
        ctx.prec = 28
        ctx.rounding = ROUND_HALF_UP
        if direction == "long":
            adjusted = reference_price * (Decimal("1") + slippage_rate)
        elif direction == "short":
            adjusted = reference_price * (Decimal("1") - slippage_rate)
        else:
            raise ValueError(f"unknown direction: {direction!r}")
        return adjusted.quantize(_PRICE_SCALE)


def _compute_commission(
    *,
    quantity: Decimal,
    fill_price: Decimal,
    commission_rate: Decimal,
) -> Decimal:
    """Compute a flat-rate commission against the realized notional."""
    with localcontext() as ctx:
        ctx.prec = 28
        ctx.rounding = ROUND_HALF_UP
        notional = quantity * fill_price
        return (notional * commission_rate).quantize(Decimal("0.0001"))


def bar_intersects_entry_zone(
    *,
    bar_low: Decimal,
    bar_high: Decimal,
    zone_low: Decimal,
    zone_high: Decimal,
) -> bool:
    """Return True when the bar's [low, high] range overlaps the entry zone.

    The classic "did we get filled?" check: a market-on-open or limit order
    inside the zone executes only if the next bar's price range traverses it.
    Bars that gap past the zone produce no fill.
    """
    if bar_low > bar_high:
        raise ValueError(f"bar_low ({bar_low}) must be <= bar_high ({bar_high})")
    if zone_low > zone_high:
        raise ValueError(f"zone_low ({zone_low}) must be <= zone_high ({zone_high})")
    return bar_low <= zone_high and bar_high >= zone_low


def stop_loss_breached(
    *,
    direction: str,
    stop_loss: Decimal,
    bar_low: Decimal,
    bar_high: Decimal,
) -> bool:
    """Return True when the bar's range crosses the stop-loss level.

    For long positions a stop is breached when the bar's low touches or
    falls below it; for short positions the bar's high crossing the stop
    triggers exit.
    """
    if bar_low > bar_high:
        raise ValueError(f"bar_low ({bar_low}) must be <= bar_high ({bar_high})")
    if direction == "long":
        return bar_low <= stop_loss
    if direction == "short":
        return bar_high >= stop_loss
    raise ValueError(f"unknown direction: {direction!r}")


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


def _derive_trade_risk_pct_from_stop_loss(
    signal: Signal,
    *,
    entry_price: Decimal,
) -> tuple[OutcomeCode | None, Decimal | None, str | None]:
    """Derive trade_risk_pct from the signal's stop_loss and entry_price.

    Returns the canonical |entry - stop| / entry fractional risk, suitable for
    consumption by ``compute_deterministic_trade_notional``.
    """
    raw_stop_loss = signal.get("stop_loss")
    if raw_stop_loss is None:
        return None, None, None
    try:
        stop_loss = Decimal(str(raw_stop_loss))
    except Exception:
        return (
            "reject:invalid_trade_risk_input",
            None,
            f"stop_loss is not numeric: {raw_stop_loss!r}",
        )
    if not stop_loss.is_finite() or stop_loss <= Decimal("0"):
        return (
            "reject:invalid_trade_risk_input",
            None,
            f"stop_loss must be finite and > 0, got {stop_loss}",
        )
    if entry_price <= Decimal("0"):
        return (
            "reject:invalid_trade_risk_input",
            None,
            f"entry_price must be > 0 to derive trade_risk_pct, got {entry_price}",
        )
    with localcontext() as ctx:
        ctx.prec = 28
        ctx.rounding = ROUND_HALF_UP
        derived = abs(entry_price - stop_loss) / entry_price
    if derived <= Decimal("0"):
        return (
            "reject:invalid_trade_risk_input",
            None,
            f"derived trade_risk_pct must be > 0, got {derived}",
        )
    return None, derived, None


def _derive_trade_risk_pct_from_atr(
    signal: Signal,
    *,
    entry_price: Decimal,
    atr_multiple: Decimal,
) -> tuple[OutcomeCode | None, Decimal | None, str | None]:
    """Derive trade_risk_pct from the signal's ATR field.

    Converts ATR * multiple to a fractional risk-per-unit relative to entry:
    ``trade_risk_pct = (atr * atr_multiple) / entry_price``

    This is equivalent to using ATR-scaled stop distance as the risk denominator,
    which normalises position sizes across symbols with different volatility.
    """
    raw_atr = signal.get("atr")
    if raw_atr is None:
        return (
            "reject:atr_not_provided",
            None,
            "sizing_method='atr' requires signal.atr to be set",
        )
    try:
        atr = Decimal(str(raw_atr))
    except Exception:
        return (
            "reject:invalid_trade_risk_input",
            None,
            f"atr is not numeric: {raw_atr!r}",
        )
    if not atr.is_finite() or atr <= Decimal("0"):
        return (
            "reject:invalid_trade_risk_input",
            None,
            f"atr must be finite and > 0, got {atr}",
        )
    if entry_price <= Decimal("0"):
        return (
            "reject:invalid_trade_risk_input",
            None,
            f"entry_price must be > 0, got {entry_price}",
        )
    with localcontext() as ctx:
        ctx.prec = 28
        ctx.rounding = ROUND_HALF_UP
        risk_per_unit = atr * atr_multiple
        derived = risk_per_unit / entry_price
    if derived <= Decimal("0"):
        return (
            "reject:invalid_trade_risk_input",
            None,
            f"atr-derived trade_risk_pct must be > 0, got {derived}",
        )
    return None, derived, None


def _resolve_trade_risk_pct(
    signal: Signal,
    *,
    entry_price: Decimal,
    sizing_method: str = "stop_distance",
    atr_multiple: Decimal = Decimal("2.0"),
) -> tuple[OutcomeCode | None, Decimal | None, str | None]:
    if sizing_method == "atr":
        return _derive_trade_risk_pct_from_atr(
            signal, entry_price=entry_price, atr_multiple=atr_multiple
        )

    if sizing_method == "fixed":
        # Use trade_risk_pct directly from the signal — no derivation.
        raw_trade_risk_pct = signal.get("trade_risk_pct")
        if raw_trade_risk_pct is None:
            return (
                "reject:missing_trade_risk_input",
                None,
                "sizing_method='fixed' requires signal.trade_risk_pct to be set",
            )
        try:
            trade_risk_pct = Decimal(str(raw_trade_risk_pct))
        except Exception:
            return (
                "reject:invalid_trade_risk_input",
                None,
                f"trade_risk_pct is not numeric: {raw_trade_risk_pct!r}",
            )
        if not trade_risk_pct.is_finite() or trade_risk_pct <= Decimal("0"):
            return (
                "reject:invalid_trade_risk_input",
                None,
                f"trade_risk_pct must be finite and > 0, got {trade_risk_pct}",
            )
        return None, trade_risk_pct, None

    # Default: "stop_distance" — prefer explicit trade_risk_pct, fall back to stop_loss.
    raw_trade_risk_pct = signal.get("trade_risk_pct")
    if raw_trade_risk_pct is None:
        derived_outcome, derived_pct, derived_reason = (
            _derive_trade_risk_pct_from_stop_loss(signal, entry_price=entry_price)
        )
        if derived_outcome is not None:
            return derived_outcome, None, derived_reason
        if derived_pct is not None:
            return None, derived_pct, None
        return (
            "reject:missing_trade_risk_input",
            None,
            "trade_risk_pct or stop_loss is required for deterministic sizing",
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


def _build_signal_contract_evidence(
    signal: Signal,
    *,
    outcome: OutcomeCode,
    reason: str,
    profile: PaperExecutionRiskProfile,
    missing_fields: list[str] | None = None,
    required_any_of: list[str] | None = None,
) -> dict[str, object]:
    evidence: dict[str, object] = {
        "outcome": outcome,
        "reason": reason,
        "symbol": str(signal.get("symbol")),
        "strategy": str(signal.get("strategy")),
        "stage": str(signal.get("stage")),
        "direction": str(signal.get("direction")),
        "sizing_method": profile.sizing_method,
        "risk_profile_contract_id": profile.contract_id,
    }
    if signal.get("signal_id"):
        evidence["signal_id"] = str(signal["signal_id"])
    if missing_fields is not None:
        evidence["missing_fields"] = missing_fields
    if required_any_of is not None:
        evidence["required_any_of"] = required_any_of
    return evidence


def _compute_drawdown_state(
    closed_trades: list[Trade],
    *,
    initial_equity: Decimal,
) -> tuple[int, Decimal]:
    """Return (consecutive_losses, current_drawdown_pct) from closed trade history.

    consecutive_losses: how many of the most recent closed trades are losses
    current_drawdown_pct: (equity_peak - current_equity) / equity_peak
    """
    if not closed_trades:
        return 0, Decimal("0")

    sorted_trades = sorted(closed_trades, key=lambda t: t.closed_at or "")

    running_pnl = Decimal("0")
    peak_equity = initial_equity
    for t in sorted_trades:
        pnl = t.realized_pnl or Decimal("0")
        running_pnl += pnl
        current = initial_equity + running_pnl
        if current > peak_equity:
            peak_equity = current

    current_equity = initial_equity + running_pnl
    if peak_equity <= Decimal("0"):
        drawdown_pct = Decimal("0")
    else:
        with localcontext() as ctx:
            ctx.prec = 28
            ctx.rounding = ROUND_HALF_UP
            drawdown_pct = (peak_equity - current_equity) / peak_equity

    consecutive_losses = 0
    for t in reversed(sorted_trades):
        pnl = t.realized_pnl or Decimal("0")
        if pnl < Decimal("0"):
            consecutive_losses += 1
        else:
            break

    return consecutive_losses, drawdown_pct


# ---------------------------------------------------------------------------
# Worker
# ---------------------------------------------------------------------------


class BoundedPaperExecutionWorker:
    """Deterministic worker: converts eligible signals into bounded paper execution state.

    Each call to ``process_signal`` applies the ordered evaluation policy
    defined in ``signal_to_paper_execution_policy.md`` and returns an explicit
    ``SignalEvaluationResult``.

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

    def process_signal(
        self,
        signal: Signal,
        *,
        entry_bar: EntryBar | None = None,
        price_history: PriceHistory | None = None,
        regime_state: RegimeState | None = None,
    ) -> SignalEvaluationResult:
        """Evaluate and process a single signal against the bounded policy.

        Returns a ``SignalEvaluationResult`` with an explicit outcome code.
        When the outcome is ``"eligible"``, canonical paper entities are
        created and persisted before returning.

        ``entry_bar`` is optional. When provided alongside an ``entry_zone``
        on the signal, the worker rejects fills whose next bar gapped past
        the zone (``skip:entry_zone_not_reached``). Callers without bar
        context behave as before.

        ``price_history`` is optional. When provided and
        ``risk_profile.correlation_check_enabled`` is True, the worker
        evaluates pairwise correlation against open positions and blocks
        entries that would exceed ``max_correlated_pairs``.

        ``regime_state`` is optional. When provided and
        ``risk_profile.allowed_regimes`` is non-empty, the worker skips
        entries whose regime label is not in the allowed set.
        """
        result = self._evaluate(signal, entry_bar=entry_bar, price_history=price_history, regime_state=regime_state)
        if result.outcome == "eligible":
            result = self._persist_paper_entry(
                signal,
                decision_inputs=result.decision_inputs,
            )
        return result

    def process_exit_signal(
        self,
        signal: Signal,
    ) -> SignalEvaluationResult:
        """Execute a full or partial position exit for a matching open trade.

        Uses ``signal.exit_pct`` (fraction of remaining quantity to close,
        default 1.0 = full exit). The exit fill price has slippage applied
        inverse to the entry direction (long exits receive slightly below
        reference; short exits pay slightly above).

        Returns ``"eligible:partial_exit"`` when the position remains open
        after the exit, or ``"eligible:full_exit"`` when fully closed.
        """
        field_error = _validate_signal_fields(signal)
        if field_error is not None:
            return SignalEvaluationResult(
                outcome="reject:invalid_signal_fields",
                reason=field_error,
            )

        symbol: str = signal["symbol"]  # type: ignore[assignment]
        strategy: str = signal["strategy"]  # type: ignore[assignment]
        direction: str = signal["direction"]  # type: ignore[assignment]
        occurred_at: str = signal["timestamp"]  # type: ignore[assignment]
        signal_id = _resolve_signal_id(signal)
        exit_order_id = _compute_paper_exit_order_id(signal_id)

        existing_exit_order = self._repo.get_order(exit_order_id)
        if existing_exit_order is not None:
            existing_trade = (
                self._repo.get_trade(existing_exit_order.trade_id)
                if existing_exit_order.trade_id is not None
                else None
            )
            return SignalEvaluationResult(
                outcome=(
                    "eligible:full_exit"
                    if existing_trade is not None and existing_trade.status == "closed"
                    else "eligible:partial_exit"
                ),
                signal_id=signal_id,
                order_id=exit_order_id,
                trade_id=existing_exit_order.trade_id,
            )

        trades = self._repo.list_trades(strategy_id=strategy, symbol=symbol, limit=100)
        open_trades = [t for t in trades if t.status == "open" and t.direction == direction]

        if not open_trades:
            return SignalEvaluationResult(
                outcome="skip:no_open_position_to_exit",
                reason=f"no open position for ({symbol}, {strategy}, {direction})",
            )

        trade = open_trades[0]
        remaining_qty = trade.quantity_opened - trade.quantity_closed

        raw_exit_pct = signal.get("exit_pct")
        if raw_exit_pct is not None:
            with localcontext() as ctx:
                ctx.prec = 28
                ctx.rounding = ROUND_HALF_UP
                exit_pct = Decimal(str(raw_exit_pct))
                exit_qty = (remaining_qty * exit_pct).quantize(Decimal("0.00000001"))
        else:
            exit_qty = remaining_qty

        exit_qty = min(exit_qty, remaining_qty)
        if exit_qty <= Decimal("0"):
            return SignalEvaluationResult(
                outcome="skip:exit_quantity_zero",
                reason=f"exit_qty={exit_qty} after applying exit_pct={raw_exit_pct}",
            )

        # Exit fill: inverse slippage direction (long exit = short side slippage)
        ref_price = _extract_entry_price(
            signal,
            fallback_entry_price=trade.average_entry_price or self._risk_profile.default_paper_entry_price,
        )
        exit_slippage_direction = "short" if direction == "long" else "long"
        fill_price = _apply_slippage(
            reference_price=ref_price,
            direction=exit_slippage_direction,
            slippage_rate=self._risk_profile.slippage_rate,
        )
        commission = _compute_commission(
            quantity=exit_qty,
            fill_price=fill_price,
            commission_rate=self._risk_profile.commission_rate,
        )

        entry_price = trade.average_entry_price or Decimal("0")
        with localcontext() as ctx:
            ctx.prec = 28
            ctx.rounding = ROUND_HALF_UP
            if direction == "long":
                partial_pnl = exit_qty * (fill_price - entry_price) - commission
            else:
                partial_pnl = exit_qty * (entry_price - fill_price) - commission

            new_qty_closed = trade.quantity_closed + exit_qty

            prior_exit_notional = (trade.average_exit_price or Decimal("0")) * trade.quantity_closed
            new_exit_notional = prior_exit_notional + fill_price * exit_qty
            new_avg_exit_price = new_exit_notional / new_qty_closed

        new_realized_pnl = (trade.realized_pnl or Decimal("0")) + partial_pnl
        is_full_exit = new_qty_closed >= trade.quantity_opened

        remaining_qty = trade.quantity_opened - new_qty_closed
        entry_px = trade.average_entry_price or Decimal("0")
        new_exposure = remaining_qty * entry_px
        exit_event_id = compute_execution_event_id(
            order_id=exit_order_id,
            event_type="filled",
            occurred_at=occurred_at,
            sequence=1,
        )

        trade_data: dict = {
            **trade.model_dump(mode="python"),
            "quantity_closed": new_qty_closed,
            "average_exit_price": new_avg_exit_price,
            "realized_pnl": new_realized_pnl,
            "exposure_notional": new_exposure,
            "closing_order_ids": [*trade.closing_order_ids, exit_order_id],
            "execution_event_ids": [*trade.execution_event_ids, exit_event_id],
        }
        if is_full_exit:
            trade_data["status"] = "closed"
            trade_data["closed_at"] = occurred_at

        updated_trade = Trade.model_validate(trade_data)

        # Exit order and execution event
        exit_side = "SELL" if direction == "long" else "BUY"
        exit_order = Order.model_validate(
            {
                "order_id": exit_order_id,
                "strategy_id": strategy,
                "symbol": symbol,
                "sequence": 1,
                "side": exit_side,
                "order_type": "market",
                "time_in_force": "day",
                "status": "filled",
                "quantity": exit_qty,
                "filled_quantity": exit_qty,
                "created_at": occurred_at,
                "submitted_at": occurred_at,
                "average_fill_price": fill_price,
                "last_execution_event_id": exit_event_id,
                "position_id": trade.position_id,
                "trade_id": trade.trade_id,
            }
        )
        exit_event = ExecutionEvent.model_validate(
            {
                "event_id": exit_event_id,
                "order_id": exit_order_id,
                "strategy_id": strategy,
                "symbol": symbol,
                "side": exit_side,
                "event_type": "filled",
                "occurred_at": occurred_at,
                "sequence": 1,
                "execution_quantity": exit_qty,
                "execution_price": fill_price,
                "commission": commission,
                "position_id": trade.position_id,
                "trade_id": trade.trade_id,
            }
        )

        self._repo.save_order(exit_order)
        self._repo.save_execution_events([exit_event])
        self._repo.save_trade(updated_trade)

        return SignalEvaluationResult(
            outcome="eligible:full_exit" if is_full_exit else "eligible:partial_exit",
            signal_id=signal_id,
            order_id=exit_order_id,
            trade_id=trade.trade_id,
        )

    def process_batch(
        self,
        signals: Sequence[Signal],
    ) -> list[SignalEvaluationResult]:
        """Process a batch of signals sequentially.

        Returns one ``SignalEvaluationResult`` per signal in input order.
        """
        return [
            self.process_exit_signal(signal)
            if signal.get("stage") == "exit"
            else self.process_signal(signal)
            for signal in signals
        ]

    @property
    def risk_profile(self) -> PaperExecutionRiskProfile:
        """Return the canonical validated risk profile used by this worker."""
        return self._risk_profile

    def get_performance_summary(self) -> PaperPerformanceSummary:
        """Compute performance metrics from all closed trades in the repository."""
        trades = self._repo.list_trades(limit=10000)
        return compute_paper_performance_summary(
            trades, initial_equity=self._risk_profile.account_equity
        )

    def get_performance_attribution(self) -> PaperPerformanceAttribution:
        """Compute per-strategy and per-symbol attribution from all closed trades."""
        trades = self._repo.list_trades(limit=10000)
        return compute_paper_performance_attribution(trades)

    def _build_risk_limits(self) -> RiskLimits:
        """Build deterministic risk-framework limits for paper execution."""
        with localcontext() as ctx:
            ctx.prec = 28
            ctx.rounding = ROUND_HALF_UP
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
            correlation_threshold=self._risk_profile.correlation_threshold,
            max_correlated_pairs=self._risk_profile.max_correlated_pairs,
            correlation_check_enabled=self._risk_profile.correlation_check_enabled,
            correlation_window=self._risk_profile.correlation_window,
        )

    def _compute_trade_sizing_for_signal(
        self,
        signal: Signal,
        *,
        entry_price: Decimal,
    ) -> tuple[SignalEvaluationResult | None, Decimal | None, dict[str, object] | None]:
        rejection_outcome, trade_risk_pct, rejection_reason = _resolve_trade_risk_pct(
            signal,
            entry_price=entry_price,
            sizing_method=self._risk_profile.sizing_method,
            atr_multiple=self._risk_profile.atr_multiple,
        )
        if rejection_outcome is not None or trade_risk_pct is None:
            evidence = None
            if (
                rejection_outcome == "reject:missing_trade_risk_input"
                and self._risk_profile.sizing_method == "stop_distance"
            ):
                reason = (
                    rejection_reason
                    or "trade_risk_pct or stop_loss is required for deterministic sizing"
                )
                evidence = _build_signal_contract_evidence(
                    signal,
                    outcome="reject:missing_trade_risk_input",
                    reason=reason,
                    profile=self._risk_profile,
                    missing_fields=["stop_loss", "trade_risk_pct"],
                    required_any_of=["stop_loss", "trade_risk_pct"],
                )
            return (
                SignalEvaluationResult(
                    outcome=rejection_outcome or "reject:invalid_trade_risk_input",
                    reason=rejection_reason,
                    decision_inputs=evidence,
                ),
                None,
                evidence,
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

    def _evaluate(
        self,
        signal: Signal,
        *,
        entry_bar: EntryBar | None = None,
        price_history: PriceHistory | None = None,
        regime_state: RegimeState | None = None,
    ) -> SignalEvaluationResult:
        """Apply the ordered policy evaluation.

        Steps:
            1. Eligibility check (required fields)
            2. Score threshold check
            3. Duplicate-entry check
            4. Cooldown check
            5. Entry-bar fill check (if entry_bar provided)
            6. Regime filter (if regime_state provided and allowed_regimes non-empty)
            7. Drawdown guard (if drawdown_guard_enabled)
            8. Trade sizing
            9. Exposure and position-limit checks
            10. Correlation risk check (if price_history provided and correlation_check_enabled)
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
        stage: str = signal["stage"]  # type: ignore[assignment]
        score = float(signal["score"])  # type: ignore[arg-type]

        if stage == "exit":
            reason = "exit signal is not an entry-sizing candidate"
            return SignalEvaluationResult(
                outcome="skip:exit_signal_not_entry_candidate",
                reason=reason,
                decision_inputs=_build_signal_contract_evidence(
                    signal,
                    outcome="skip:exit_signal_not_entry_candidate",
                    reason=reason,
                    profile=self._risk_profile,
                ),
            )

        # Step 2: score threshold
        if score < self._risk_profile.min_score_threshold:
            return SignalEvaluationResult(
                outcome="skip:score_below_threshold",
                reason=(
                    f"score={score} < min_score_threshold={self._risk_profile.min_score_threshold}"
                ),
            )

        # Load canonical state for this (symbol, strategy) pair.
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

        # Step 4: cooldown — min N hours since last accepted entry for (symbol, strategy)
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

        # Step 5: entry-bar fill check — only when bar context is supplied.
        entry_zone = signal.get("entry_zone")
        if entry_bar is not None and entry_zone is not None:
            zone_low = Decimal(str(entry_zone["from_"]))
            zone_high = Decimal(str(entry_zone["to"]))
            if zone_low > zone_high:
                zone_low, zone_high = zone_high, zone_low
            if not bar_intersects_entry_zone(
                bar_low=entry_bar.low,
                bar_high=entry_bar.high,
                zone_low=zone_low,
                zone_high=zone_high,
            ):
                return SignalEvaluationResult(
                    outcome="skip:entry_zone_not_reached",
                    reason=(
                        f"bar [{entry_bar.low}, {entry_bar.high}] did not intersect "
                        f"entry_zone [{zone_low}, {zone_high}]"
                    ),
                )

        # Step 6: regime filter — skip entries in disallowed market regimes.
        if regime_state is not None and self._risk_profile.allowed_regimes:
            if regime_state.label not in self._risk_profile.allowed_regimes:
                return SignalEvaluationResult(
                    outcome="skip:regime_filtered",
                    reason=(
                        f"regime={regime_state.label!r} not in "
                        f"allowed_regimes={sorted(self._risk_profile.allowed_regimes)}"
                    ),
                )

        # Step 7: drawdown guard — block new entries during losing streaks / drawdown periods.
        if self._risk_profile.drawdown_guard_enabled:
            all_closed = [t for t in self._repo.list_trades(limit=5000) if t.status == "closed"]
            consecutive_losses, drawdown_pct = _compute_drawdown_state(
                all_closed, initial_equity=self._risk_profile.account_equity
            )
            if consecutive_losses >= self._risk_profile.max_consecutive_losses:
                return SignalEvaluationResult(
                    outcome="skip:drawdown_guard_active",
                    reason=(
                        f"drawdown_guard: consecutive_losses={consecutive_losses} >= "
                        f"max_consecutive_losses={self._risk_profile.max_consecutive_losses}"
                    ),
                )
            if drawdown_pct >= self._risk_profile.max_drawdown_pct:
                return SignalEvaluationResult(
                    outcome="skip:drawdown_guard_active",
                    reason=(
                        f"drawdown_guard: drawdown_pct={drawdown_pct:.4f} >= "
                        f"max_drawdown_pct={self._risk_profile.max_drawdown_pct}"
                    ),
                )

        # Step 7: trade sizing
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

        # Step 8: exposure and position-limit checks.
        all_trades = self._repo.list_trades(limit=1000)
        all_open_trades = [t for t in all_trades if t.status == "open"]

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

        # Step 9: correlation risk — only when price history is supplied and the gate is enabled.
        if price_history is not None and self._risk_profile.correlation_check_enabled:
            open_symbols = [t.symbol for t in all_open_trades]
            corr_check = evaluate_correlation_risk(
                proposed_symbol=symbol,
                open_position_symbols=open_symbols,
                price_history=price_history,
                limits=self._risk_limits,
            )
            if corr_check.rejection_reason is not None:
                return SignalEvaluationResult(
                    outcome="skip:correlation_risk_blocked",
                    reason=corr_check.rejection_reason,
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
        decision_inputs: dict[str, object] | None,
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
        fill_price = _apply_slippage(
            reference_price=entry_price,
            direction=direction,
            slippage_rate=self._risk_profile.slippage_rate,
        )
        with localcontext() as ctx:
            ctx.prec = 28
            ctx.rounding = ROUND_HALF_UP
            proposed_notional = (
                Decimal(str(decision_inputs["proposed_position_notional"]))
                if decision_inputs is not None
                else self._risk_profile.default_paper_quantity * entry_price
            )
            quantity = (proposed_notional / fill_price).quantize(
                Decimal("0.00000001"),
            )
        commission = _compute_commission(
            quantity=quantity,
            fill_price=fill_price,
            commission_rate=self._risk_profile.commission_rate,
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
                "execution_price": fill_price,
                "commission": commission,
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
                "average_fill_price": fill_price,
                "last_execution_event_id": filled_event_id,
                "position_id": position_id,
                "trade_id": trade_id,
            }
        )

        # --- Open trade -------------------------------------------------
        exposure_notional = quantity * fill_price
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
                "average_entry_price": fill_price,
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
    "EntryBar",
    "PaperExecutionRiskProfile",
    "PriceHistory",
    "RegimeState",
    "PaperPerformanceSummary",
    "PaperPerformanceAttribution",
    "bar_intersects_entry_zone",
    "stop_loss_breached",
    "_direction_to_order_side",
    "_compute_drawdown_state",
]

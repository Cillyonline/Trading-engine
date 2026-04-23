"""Docs contract test for the bounded alert delivery channel documentation.

Locks the bounded, non-live, non-readiness wording for the new bounded
alert delivery channels doc so it cannot silently drift into live trading,
broker integration, or readiness/profitability claims.
"""

from __future__ import annotations

from tests.utils.consumer_contract_helpers import (
    assert_contains_all,
    assert_starts_with,
    read_repo_text,
)

CONTRACT_DOC = "docs/operations/runtime/bounded-alert-delivery-channels.md"


def test_bounded_alert_delivery_channels_doc_preserves_bounded_wording() -> None:
    content = read_repo_text(CONTRACT_DOC)

    assert_starts_with(content, "# Bounded Alert Delivery Channels")
    assert_contains_all(
        content,
        "Non-live and Non-readiness Boundary",
        "explicitly not",
        "broker integration",
        "live trading",
        "uncontrolled notification",
        "delivery_mode=\"bounded_non_live\"",
        "live_routing: false",
        "bounded_non_live",
        "file_sink",
        "CILLY_ALERT_FILE_SINK_PATH",
        "Append-only JSONL",
        "No network I/O",
        "Backwards Compatibility",
    )


def test_bounded_alert_delivery_channels_doc_excludes_live_or_readiness_claims() -> None:
    content = read_repo_text(CONTRACT_DOC).lower()

    forbidden_phrases = [
        "production-ready",
        "production ready",
        "broker execution ready",
        "guaranteed delivery",
        "ready for live trading",
    ]
    for phrase in forbidden_phrases:
        assert phrase not in content, f"Forbidden phrase present in doc: {phrase!r}"

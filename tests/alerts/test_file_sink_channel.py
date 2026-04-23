from __future__ import annotations

import json
from pathlib import Path

import pytest

from cilly_trading.alerts.alert_delivery_service import AlertDeliveryService
from cilly_trading.alerts.alert_models import create_alert_event
from cilly_trading.alerts.alert_persistence_sqlite import (
    BOUNDED_DELIVERY_MODE,
    SqliteAlertDeliveryHistoryRepository,
)
from cilly_trading.alerts.channels.file_sink_channel import FileSinkChannel


def _event():
    return create_alert_event(
        event_type="runtime.guard_triggered",
        source_type="runtime",
        source_id="guard-file-sink-1",
        severity="warning",
        occurred_at="2026-04-12T10:00:00Z",
        payload={"guard": "drawdown", "value": 3.8},
    )


def test_file_sink_channel_appends_jsonl_line(tmp_path: Path) -> None:
    sink_path = tmp_path / "sink" / "alerts.jsonl"
    channel = FileSinkChannel(sink_path)
    event = _event()

    channel.deliver(event)
    channel.deliver(event)

    contents = sink_path.read_text(encoding="utf-8").splitlines()
    assert len(contents) == 2
    decoded = json.loads(contents[0])
    assert decoded["event_id"] == event.event_id
    assert decoded["event_type"] == "runtime.guard_triggered"
    assert decoded["payload"] == {"guard": "drawdown", "value": 3.8}


def test_file_sink_channel_rejects_empty_path() -> None:
    with pytest.raises(ValueError):
        FileSinkChannel("")


def test_file_sink_channel_raises_when_parent_missing_and_creation_disabled(
    tmp_path: Path,
) -> None:
    sink_path = tmp_path / "missing-dir" / "alerts.jsonl"
    channel = FileSinkChannel(sink_path, create_parents=False)

    with pytest.raises(FileNotFoundError):
        channel.deliver(_event())


def test_delivery_service_with_file_sink_persists_success(tmp_path: Path) -> None:
    db_path = tmp_path / "alerts.db"
    sink_path = tmp_path / "alerts.jsonl"
    history_store = SqliteAlertDeliveryHistoryRepository(db_path=db_path)
    service = AlertDeliveryService(history_store=history_store, file_sink_path=sink_path)
    event = _event()

    result = service.dispatch_event(event)
    rows, total = history_store.list_delivery_results(limit=10, offset=0)

    assert service.channel_names == ("bounded_non_live", "file_sink")
    assert result.delivered_channels == ("bounded_non_live", "file_sink")
    assert result.failed_channels == ()
    assert total == 2

    channel_results = {row["channel_name"]: row for row in rows}
    assert channel_results["file_sink"]["delivered"] is True
    assert channel_results["file_sink"]["error"] is None
    assert channel_results["file_sink"]["delivery_mode"] == BOUNDED_DELIVERY_MODE
    assert channel_results["bounded_non_live"]["delivered"] is True

    on_disk = sink_path.read_text(encoding="utf-8").splitlines()
    assert len(on_disk) == 1
    assert json.loads(on_disk[0])["event_id"] == event.event_id


def test_delivery_service_records_file_sink_failure_without_breaking_other_channels(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "alerts.db"
    # Point the sink at a path whose parent we explicitly do not create. Then
    # disable parent creation in the channel by registering it manually via the
    # service, and pre-create a regular file at the parent slot so mkdir cannot
    # turn it into a directory. This produces a deterministic failure when the
    # channel tries to open the file for append.
    blocking_file = tmp_path / "blocked"
    blocking_file.write_text("not-a-directory")
    sink_path = blocking_file / "alerts.jsonl"

    history_store = SqliteAlertDeliveryHistoryRepository(db_path=db_path)
    service = AlertDeliveryService(history_store=history_store, file_sink_path=sink_path)
    event = _event()

    result = service.dispatch_event(event)
    rows, total = history_store.list_delivery_results(limit=10, offset=0)

    assert "file_sink" in result.failed_channels
    assert "bounded_non_live" in result.delivered_channels
    assert total == 2

    failures = {row["channel_name"]: row for row in rows if not row["delivered"]}
    assert "file_sink" in failures
    assert failures["file_sink"]["error"] is not None
    assert failures["file_sink"]["error"].startswith(
        ("NotADirectoryError:", "FileExistsError:", "FileNotFoundError:")
    )


def test_delivery_service_default_excludes_file_sink(tmp_path: Path) -> None:
    db_path = tmp_path / "alerts.db"
    history_store = SqliteAlertDeliveryHistoryRepository(db_path=db_path)
    service = AlertDeliveryService(history_store=history_store)

    assert service.channel_names == ("bounded_non_live",)

"""Bounded, non-live, file-based external alert delivery channel.

This channel appends a deterministic JSON line per delivered alert event to a
configured file path. It is an explicitly bounded external sink: it writes to
the local filesystem only, performs no network I/O, and does not participate
in any live trading or broker execution path.

Failure modes are explicit:
- a missing or empty path is rejected at construction time
- write failures (for example permission errors or non-existent parent
  directories when ``create_parents`` is ``False``) are raised so the
  dispatcher can record them as failed deliveries.
"""

from __future__ import annotations

from pathlib import Path

from cilly_trading.alerts.alert_models import AlertEvent


class FileSinkChannel:
    """Append AlertEvent records as deterministic JSONL to a local file."""

    channel_name = "file_sink"

    def __init__(self, sink_path: str | Path, *, create_parents: bool = True) -> None:
        if sink_path is None or str(sink_path).strip() == "":
            raise ValueError("file sink path must be a non-empty filesystem path")
        self._sink_path = Path(sink_path)
        self._create_parents = create_parents

    @property
    def sink_path(self) -> Path:
        return self._sink_path

    def deliver(self, event: AlertEvent) -> None:
        if not event.event_id:
            raise ValueError("alert event_id is required")

        if self._create_parents:
            self._sink_path.parent.mkdir(parents=True, exist_ok=True)

        serialized = event.model_dump_json()
        with self._sink_path.open("a", encoding="utf-8") as sink_file:
            sink_file.write(serialized)
            sink_file.write("\n")


__all__ = ["FileSinkChannel"]

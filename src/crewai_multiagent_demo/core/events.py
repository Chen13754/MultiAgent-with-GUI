from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

from crewai_multiagent_demo.utils.files import atomic_write_json

EventCallback = Callable[[dict[str, Any]], None]
LOGGER = logging.getLogger(__name__)


class EventEmitter:
    def __init__(self, callback: EventCallback | None = None) -> None:
        self.events: list[dict[str, Any]] = []
        self.callback = callback

    def emit(self, event_type: str, **payload: Any) -> None:
        event = {
            "type": event_type,
            "time": datetime.now().isoformat(timespec="seconds"),
            **payload,
        }
        self.events.append(event)
        if self.callback is not None:
            try:
                self.callback(event)
            except Exception:
                # UI/observer failures must never convert a successful model run
                # into a failed workflow.
                LOGGER.exception("Run event callback failed")


def write_event_log(run_dir: Path, events: list[dict[str, Any]]) -> None:
    atomic_write_json(run_dir / "events.json", events)

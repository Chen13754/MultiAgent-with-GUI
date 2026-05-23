from __future__ import annotations

import json
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any


EventCallback = Callable[[dict[str, Any]], None]


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
            self.callback(event)


def write_event_log(run_dir: Path, events: list[dict[str, Any]]) -> None:
    (run_dir / "events.json").write_text(
        json.dumps(events, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

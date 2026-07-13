from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class RunResult:
    topic: str
    model_alias: str
    model_name: str
    crewai_model: str
    elapsed_seconds: float
    token_usage: dict[str, int]
    run_dir: Path
    full_report: str
    concise_report: str
    task_outputs: list[dict[str, str]]
    run_id: str = ""
    status: str = "succeeded"
    events: list[dict[str, Any]] = field(default_factory=list)

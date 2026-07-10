from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class TaskConfig:
    id: str
    name: str
    description: str
    expected_output: str
    agent_id: str
    context_task_ids: list[str] = field(default_factory=list)
    artifact_role: str = "none"
    enabled: bool = True

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AgentConfig:
    id: str
    role: str
    goal: str
    backstory: str
    enabled: bool = True

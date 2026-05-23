from __future__ import annotations

from dataclasses import asdict
from typing import Any

from crewai_multiagent_demo.domain.agents import AgentConfig
from crewai_multiagent_demo.domain.tasks import TaskConfig


def _required_str(item: dict[str, Any], field: str, *, kind: str, index: int) -> str:
    if field not in item:
        raise ValueError(f"{kind}[{index}] 缺少必填字段: {field}")
    value = str(item[field]).strip()
    if not value:
        raise ValueError(f"{kind}[{index}] 字段不能为空: {field}")
    return value


def parse_agent_config(item: dict[str, Any], index: int) -> AgentConfig:
    return AgentConfig(
        id=_required_str(item, "id", kind="agent", index=index),
        role=_required_str(item, "role", kind="agent", index=index),
        goal=_required_str(item, "goal", kind="agent", index=index),
        backstory=_required_str(item, "backstory", kind="agent", index=index),
        enabled=bool(item.get("enabled", True)),
    )


def parse_task_config(item: dict[str, Any], index: int) -> TaskConfig:
    raw_context = item.get("context_task_ids", [])
    if raw_context is None:
        context_task_ids: list[str] = []
    elif isinstance(raw_context, list):
        context_task_ids = [str(task_id).strip() for task_id in raw_context if str(task_id).strip()]
    elif isinstance(raw_context, str):
        context_task_ids = [part.strip() for part in raw_context.split(",") if part.strip()]
    else:
        raise ValueError(f"task[{index}] context_task_ids 必须是列表或逗号分隔字符串")

    task_id = _required_str(item, "id", kind="task", index=index)
    return TaskConfig(
        id=task_id,
        name=str(item.get("name") or task_id).strip(),
        description=_required_str(item, "description", kind="task", index=index),
        expected_output=_required_str(item, "expected_output", kind="task", index=index),
        agent_id=_required_str(item, "agent_id", kind="task", index=index),
        context_task_ids=context_task_ids,
        enabled=bool(item.get("enabled", True)),
    )


def config_to_dicts(configs: list[AgentConfig] | list[TaskConfig]) -> list[dict[str, Any]]:
    return [asdict(config) for config in configs]

from __future__ import annotations

from collections import Counter

from crewai_multiagent_demo.domain.agents import AgentConfig
from crewai_multiagent_demo.domain.tasks import TaskConfig


def _find_duplicates(values: list[str]) -> list[str]:
    counts = Counter(values)
    return sorted(value for value, count in counts.items() if count > 1)


def validate_configs(agents: list[AgentConfig], tasks: list[TaskConfig]) -> None:
    allowed_artifact_roles = {"none", "full_report", "summary"}
    for agent in agents:
        for field_name in ("id", "role", "goal", "backstory"):
            if not getattr(agent, field_name).strip():
                raise ValueError(f"agent '{agent.id or '<empty>'}' 字段不能为空: {field_name}")
    for task in tasks:
        for field_name in ("id", "name", "description", "expected_output", "agent_id"):
            if not getattr(task, field_name).strip():
                raise ValueError(f"task '{task.id or '<empty>'}' 字段不能为空: {field_name}")
        if task.artifact_role not in allowed_artifact_roles:
            raise ValueError(
                f"task '{task.id}' artifact_role 无效: {task.artifact_role}。"
                "可用值: none, full_report, summary"
            )

    duplicate_agents = _find_duplicates([agent.id for agent in agents])
    if duplicate_agents:
        raise ValueError(f"重复的 agent id: {', '.join(duplicate_agents)}")

    duplicate_tasks = _find_duplicates([task.id for task in tasks])
    if duplicate_tasks:
        raise ValueError(f"重复的 task id: {', '.join(duplicate_tasks)}")

    for role in ("full_report", "summary"):
        owners = [task.id for task in tasks if task.enabled and task.artifact_role == role]
        if len(owners) > 1:
            raise ValueError(f"artifact_role '{role}' 只能分配给一个启用 task: {', '.join(owners)}")

    enabled_agents = {agent.id for agent in agents if agent.enabled}
    all_task_ids = {task.id for task in tasks}
    enabled_tasks = {task.id for task in tasks if task.enabled}
    disabled_tasks = {task.id for task in tasks if not task.enabled}

    if not enabled_agents:
        raise ValueError("至少需要启用一个 agent")
    if not enabled_tasks:
        raise ValueError("至少需要启用一个 task")

    for task in tasks:
        if not task.enabled:
            continue
        if task.agent_id not in enabled_agents:
            raise ValueError(f"task '{task.id}' 引用了不存在或未启用的 agent: {task.agent_id}")
        missing_context = [task_id for task_id in task.context_task_ids if task_id not in all_task_ids]
        if missing_context:
            raise ValueError(f"task '{task.id}' 依赖不存在的 task: {', '.join(missing_context)}")
        disabled_context = [task_id for task_id in task.context_task_ids if task_id in disabled_tasks]
        if disabled_context:
            raise ValueError(f"task '{task.id}' 依赖了已禁用的 task: {', '.join(disabled_context)}")
        duplicate_context = _find_duplicates(task.context_task_ids)
        if duplicate_context:
            raise ValueError(f"task '{task.id}' 存在重复依赖: {', '.join(duplicate_context)}")

    _validate_no_cycles(tasks)


def _validate_no_cycles(tasks: list[TaskConfig]) -> None:
    enabled_task_ids = {task.id for task in tasks if task.enabled}
    graph = {
        task.id: [dep for dep in task.context_task_ids if dep in enabled_task_ids]
        for task in tasks
        if task.enabled
    }
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(task_id: str, trail: list[str]) -> None:
        if task_id in visited:
            return
        if task_id in visiting:
            cycle = trail[trail.index(task_id):] + [task_id]
            raise ValueError(f"task 存在循环依赖: {' -> '.join(cycle)}")
        visiting.add(task_id)
        for dependency in graph.get(task_id, []):
            visit(dependency, trail + [dependency])
        visiting.remove(task_id)
        visited.add(task_id)

    for task_id in graph:
        visit(task_id, [task_id])

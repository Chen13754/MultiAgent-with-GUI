from __future__ import annotations

import pytest

from crewai_multiagent_demo.config.validation import validate_configs
from crewai_multiagent_demo.domain.agents import AgentConfig
from crewai_multiagent_demo.domain.tasks import TaskConfig


def agent(agent_id: str = "agent") -> AgentConfig:
    return AgentConfig(id=agent_id, role="Role", goal="Goal", backstory="Backstory")


def task(task_id: str, agent_id: str = "agent", deps: list[str] | None = None, enabled: bool = True) -> TaskConfig:
    return TaskConfig(
        id=task_id,
        name=task_id,
        description="Description",
        expected_output="Output",
        agent_id=agent_id,
        context_task_ids=deps or [],
        enabled=enabled,
    )


def test_validation_accepts_valid_dependency_graph() -> None:
    validate_configs([agent()], [task("a"), task("b", deps=["a"])])


def test_validation_rejects_duplicate_ids() -> None:
    with pytest.raises(ValueError, match="重复的 task id"):
        validate_configs([agent()], [task("a"), task("a")])


def test_validation_rejects_empty_fields() -> None:
    bad_agent = AgentConfig(id="", role="Role", goal="Goal", backstory="Backstory")
    with pytest.raises(ValueError, match="字段不能为空"):
        validate_configs([bad_agent], [task("a")])


def test_validation_rejects_missing_agent() -> None:
    with pytest.raises(ValueError, match="missing"):
        validate_configs([agent()], [task("a", agent_id="missing")])


def test_validation_rejects_disabled_dependency() -> None:
    with pytest.raises(ValueError, match="已禁用"):
        validate_configs([agent()], [task("a", enabled=False), task("b", deps=["a"])])


def test_validation_rejects_cycles() -> None:
    with pytest.raises(ValueError, match="循环依赖"):
        validate_configs([agent()], [task("a", deps=["b"]), task("b", deps=["a"])])


def test_validation_rejects_duplicate_dependencies() -> None:
    with pytest.raises(ValueError, match="重复依赖"):
        validate_configs([agent()], [task("a"), task("b", deps=["a", "a"])])

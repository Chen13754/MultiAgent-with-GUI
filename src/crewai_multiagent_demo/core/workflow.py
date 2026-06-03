from __future__ import annotations

from crewai_multiagent_demo.config.loader import AppConfig, ConfigLoader
from crewai_multiagent_demo.config.validation import validate_configs
from crewai_multiagent_demo.domain.tasks import TaskConfig


def ordered_enabled_tasks(tasks_config: list[TaskConfig]) -> list[TaskConfig]:
    by_id = {task.id: task for task in tasks_config if task.enabled}
    ordered: list[TaskConfig] = []
    added: set[str] = set()

    def add_with_dependencies(task: TaskConfig) -> None:
        if task.id in added:
            return
        for dependency_id in task.context_task_ids:
            dependency = by_id.get(dependency_id)
            if dependency is not None:
                add_with_dependencies(dependency)
        ordered.append(task)
        added.add(task.id)

    for task in tasks_config:
        if task.enabled:
            add_with_dependencies(task)
    return ordered


def load_and_validate_workflow(config_dir: str | None = None) -> AppConfig:
    loader = ConfigLoader(config_dir) if config_dir else ConfigLoader()
    return loader.load(validate=True)


def validate_workflow(config: AppConfig) -> None:
    validate_configs(config.agents, config.tasks)

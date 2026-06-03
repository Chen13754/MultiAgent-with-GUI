from __future__ import annotations

from crewai_multiagent_demo.config.validation import validate_configs
from crewai_multiagent_demo.core.events import EventCallback
from crewai_multiagent_demo.core.outputs import task_output_text
from crewai_multiagent_demo.core.workflow import ordered_enabled_tasks
from crewai_multiagent_demo.domain.agents import AgentConfig
from crewai_multiagent_demo.domain.tasks import TaskConfig
from crewai_multiagent_demo.utils.environment import configure_runtime_environment


def build_crew(
    *,
    crewai_model: str,
    agents_config: list[AgentConfig],
    tasks_config: list[TaskConfig],
    on_event: EventCallback | None = None,
):
    configure_runtime_environment()
    from crewai import Agent, Crew, Process, Task

    validate_configs(agents_config, tasks_config)

    agent_by_id: dict[str, Agent] = {}
    for config in agents_config:
        if not config.enabled:
            continue
        agent_by_id[config.id] = Agent(
            role=config.role,
            goal=config.goal,
            backstory=config.backstory,
            llm=crewai_model,
            verbose=True,
        )

    task_by_id: dict[str, Task] = {}
    tasks: list[Task] = []
    for config in ordered_enabled_tasks(tasks_config):
        task = Task(
            description=config.description,
            expected_output=config.expected_output,
            agent=agent_by_id[config.agent_id],
            context=[task_by_id[task_id] for task_id in config.context_task_ids],
        )
        task_by_id[config.id] = task
        tasks.append(task)

    def task_callback(task_output: object) -> None:
        if on_event is None:
            return
        on_event(
            {
                "type": "task_completed",
                "agent": getattr(task_output, "agent", ""),
                "output": task_output_text(task_output),
            }
        )

    return Crew(
        agents=list(agent_by_id.values()),
        tasks=tasks,
        process=Process.sequential,
        verbose=True,
        task_callback=task_callback,
    )

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
    request_timeout_seconds: float = 180.0,
    max_retries: int = 2,
):
    configure_runtime_environment()
    from crewai import LLM, Agent, Crew, Process, Task

    validate_configs(agents_config, tasks_config)

    # CrewAI forwards provider-specific kwargs although its public type stub
    # does not yet declare max_retries for OpenAI-compatible providers.
    llm = LLM(
        model=crewai_model,
        timeout=request_timeout_seconds,
        max_retries=max_retries,
    )
    agent_by_id: dict[str, Agent] = {}
    for agent_config in agents_config:
        if not agent_config.enabled:
            continue
        agent_by_id[agent_config.id] = Agent(
            role=agent_config.role,
            goal=agent_config.goal,
            backstory=agent_config.backstory,
            llm=llm,
            verbose=True,
            max_retry_limit=max_retries,
        )

    task_by_id: dict[str, Task] = {}
    tasks: list[Task] = []
    ordered_configs = ordered_enabled_tasks(tasks_config)
    for task_config in ordered_configs:
        task = Task(
            description=task_config.description,
            expected_output=task_config.expected_output,
            agent=agent_by_id[task_config.agent_id],
            context=[task_by_id[task_id] for task_id in task_config.context_task_ids],
        )
        task_by_id[task_config.id] = task
        tasks.append(task)

    completed_index = 0

    def task_callback(task_output: object) -> None:
        nonlocal completed_index
        if on_event is None:
            return
        config = ordered_configs[completed_index] if completed_index < len(ordered_configs) else None
        completed_index += 1
        on_event(
            {
                "type": "task_completed",
                "task_id": config.id if config else "",
                "task_name": config.name if config else "",
                "agent": getattr(task_output, "agent", ""),
                "output": task_output_text(task_output),
            }
        )

    return Crew(
        agents=list(agent_by_id.values()),
        tasks=tasks,
        process=Process.sequential,
        # This application does not use CrewAI memory/knowledge. Keep the
        # ChromaDB-backed feature explicitly disabled at the product boundary.
        memory=False,
        verbose=True,
        task_callback=task_callback,
    )

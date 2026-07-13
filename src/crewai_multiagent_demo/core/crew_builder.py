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
    from crewai.events import TaskCompletedEvent, TaskFailedEvent, TaskStartedEvent, crewai_event_bus

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

    handlers: list[tuple[type[object], object]] = []

    def config_for_event(event: object) -> TaskConfig | None:
        task_object = getattr(event, "task", None)
        if task_object is not None and id(task_object) in {id(task): task_id for task_id, task in task_by_id.items()}:
            task_object_id = id(task_object)
            for task_id, candidate in task_by_id.items():
                if id(candidate) == task_object_id:
                    return next((item for item in ordered_configs if item.id == task_id), None)
        name = str(getattr(event, "task_name", "") or "")
        return next((item for item in ordered_configs if item.name == name), None)

    def register(event_type: type[object], event_handler: object) -> None:
        crewai_event_bus.on(event_type)(event_handler)
        handlers.append((event_type, event_handler))

    if on_event is not None:
        def emit_task_event(event: object, *, event_type: str, output: str = "", error: str = "") -> None:
            config = config_for_event(event)
            on_event(
                {
                    "type": event_type,
                    "task_id": config.id if config else str(getattr(event, "task_id", "") or ""),
                    "task_name": config.name if config else str(getattr(event, "task_name", "") or ""),
                    "agent": str(getattr(event, "agent_role", "") or getattr(event, "agent_id", "") or ""),
                    **({"output": output} if output else {}),
                    **({"error": error} if error else {}),
                }
            )

        def started(_source: object, event: TaskStartedEvent) -> None:
            emit_task_event(event, event_type="task_started")

        def completed(_source: object, event: TaskCompletedEvent) -> None:
            emit_task_event(event, event_type="task_completed", output=task_output_text(event.output))

        def failed(_source: object, event: TaskFailedEvent) -> None:
            emit_task_event(event, event_type="task_failed", error=str(event.error))

        register(TaskStartedEvent, started)
        register(TaskCompletedEvent, completed)
        register(TaskFailedEvent, failed)

    crew = Crew(
        agents=list(agent_by_id.values()),
        tasks=tasks,
        process=Process.sequential,
        # This application does not use CrewAI memory/knowledge. Keep the
        # ChromaDB-backed feature explicitly disabled at the product boundary.
        memory=False,
        verbose=True,
    )
    def cleanup() -> None:
        for event_type, handler in handlers:
            crewai_event_bus.off(event_type, handler)

    crew._studio_event_cleanup = cleanup
    return crew

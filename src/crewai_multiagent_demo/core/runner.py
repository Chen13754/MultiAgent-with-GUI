from __future__ import annotations

from pathlib import Path
from time import perf_counter
from typing import Any

from crewai_multiagent_demo.config.loader import AppConfig, ConfigLoader
from crewai_multiagent_demo.core.crew_builder import build_crew
from crewai_multiagent_demo.core.events import EventCallback, EventEmitter, write_event_log
from crewai_multiagent_demo.core.outputs import task_output_text, write_failed_run_outputs, write_run_outputs
from crewai_multiagent_demo.core.workflow import ordered_enabled_tasks
from crewai_multiagent_demo.domain.run_result import RunResult
from crewai_multiagent_demo.domain.tasks import TaskConfig
from crewai_multiagent_demo.llm.model_registry import MODEL_REGISTRY, ModelRegistry
from crewai_multiagent_demo.utils.environment import require_api_key
from crewai_multiagent_demo.utils.paths import DEFAULT_CONFIG_DIR, DEFAULT_OUTPUT_DIR


DEFAULT_TOPIC = "分析并解决一个需要多方权衡的复杂问题"


def usage_to_dict(usage: object | None) -> dict[str, int]:
    if usage is None:
        return {}

    if hasattr(usage, "model_dump"):
        dumped = usage.model_dump()
        return {key: int(value) for key, value in dumped.items() if isinstance(value, int)}

    if isinstance(usage, dict):
        return {key: int(value) for key, value in usage.items() if isinstance(value, int)}

    fields = (
        "total_tokens",
        "prompt_tokens",
        "cached_prompt_tokens",
        "completion_tokens",
        "reasoning_tokens",
        "cache_creation_tokens",
        "successful_requests",
    )
    return {
        field: int(value)
        for field in fields
        if isinstance((value := getattr(usage, field, None)), int)
    }


def extract_token_usage(result: object, crew: object) -> dict[str, int]:
    for usage in (
        getattr(result, "token_usage", None),
        getattr(result, "usage_metrics", None),
        getattr(crew, "usage_metrics", None),
        getattr(crew, "token_usage", None),
    ):
        usage_dict = usage_to_dict(usage)
        if usage_dict.get("total_tokens", 0) > 0:
            return usage_dict
    return {}


def collect_task_outputs(result: object, tasks_config: list[TaskConfig] | None = None) -> list[dict[str, str]]:
    task_outputs_raw = getattr(result, "tasks_output", None) or []
    ordered_tasks = ordered_enabled_tasks(tasks_config or [])
    task_outputs: list[dict[str, str]] = []
    for index, task_output in enumerate(task_outputs_raw):
        config = ordered_tasks[index] if index < len(ordered_tasks) else None
        row = {
            "agent": str(getattr(task_output, "agent", "")),
            "description": str(getattr(task_output, "description", "")),
            "output": task_output_text(task_output),
        }
        if config is not None:
            row["task_id"] = config.id
            row["task_name"] = config.name
        task_outputs.append(row)
    return task_outputs


def select_reports(result: object, task_outputs: list[dict[str, str]]) -> tuple[str, str]:
    by_id = {task_output.get("task_id", ""): task_output.get("output", "") for task_output in task_outputs}
    full_report = by_id.get("review") or by_id.get("full_report")
    concise_report = by_id.get("summary") or by_id.get("concise_report")
    if full_report and concise_report:
        return full_report, concise_report
    if full_report:
        return full_report, full_report
    if concise_report:
        return concise_report, concise_report
    if len(task_outputs) >= 2:
        return task_outputs[-2]["output"], task_outputs[-1]["output"]
    if task_outputs:
        return task_outputs[-1]["output"], task_outputs[-1]["output"]
    text = str(result)
    return text, text


def run_workflow(
    *,
    topic: str,
    model_alias: str | None = None,
    config_dir: str | Path = DEFAULT_CONFIG_DIR,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    on_event: EventCallback | None = None,
    app_config: AppConfig | None = None,
    registry: ModelRegistry = MODEL_REGISTRY,
) -> RunResult:
    config = app_config or ConfigLoader(config_dir).load(validate=True)
    model = registry.resolve(model_alias)
    require_api_key(model.crewai_model)
    resolved_topic = topic.strip() or DEFAULT_TOPIC
    emitter = EventEmitter(on_event)

    def emit_event(event: dict[str, Any]) -> None:
        event_type = str(event.pop("type", "event"))
        emitter.emit(event_type, **event)

    started_at = perf_counter()
    try:
        emitter.emit("run_started", model=model.alias, topic=resolved_topic)
        crew = build_crew(
            crewai_model=model.crewai_model,
            agents_config=config.agents,
            tasks_config=config.tasks,
            on_event=emit_event,
        )
        result = crew.kickoff(inputs={"topic": resolved_topic})
    except Exception as exc:
        elapsed_seconds = perf_counter() - started_at
        run_dir = write_failed_run_outputs(
            output_dir=output_dir,
            error=str(exc),
            metadata={
                "topic": resolved_topic,
                "model_alias": model.alias,
                "model_name": model.model_name,
                "crewai_model": model.crewai_model,
                "elapsed_seconds": elapsed_seconds,
                "token_usage": {},
            },
        )
        emitter.emit("run_failed", error=str(exc), elapsed_seconds=elapsed_seconds, run_dir=str(run_dir))
        write_event_log(run_dir, emitter.events)
        raise

    elapsed_seconds = perf_counter() - started_at
    token_usage = extract_token_usage(result, crew)
    task_outputs = collect_task_outputs(result, config.tasks)
    full_report, concise_report = select_reports(result, task_outputs)

    run_dir = write_run_outputs(
        output_dir=output_dir,
        full_report=full_report,
        concise_report=concise_report,
        task_outputs=task_outputs,
        metadata={
            "topic": resolved_topic,
            "model_alias": model.alias,
            "model_name": model.model_name,
            "crewai_model": model.crewai_model,
            "elapsed_seconds": elapsed_seconds,
            "token_usage": token_usage,
        },
    )
    emitter.emit("run_completed", elapsed_seconds=elapsed_seconds, run_dir=str(run_dir))
    write_event_log(run_dir, emitter.events)

    return RunResult(
        topic=resolved_topic,
        model_alias=model.alias,
        model_name=model.model_name,
        crewai_model=model.crewai_model,
        elapsed_seconds=elapsed_seconds,
        token_usage=token_usage,
        run_dir=run_dir,
        full_report=full_report,
        concise_report=concise_report,
        task_outputs=task_outputs,
        events=emitter.events,
    )

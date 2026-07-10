from __future__ import annotations

import logging
from pathlib import Path
from time import perf_counter
from typing import Any
from uuid import uuid4

from crewai_multiagent_demo.config.loader import AppConfig, ConfigLoader
from crewai_multiagent_demo.core.crew_builder import build_crew
from crewai_multiagent_demo.core.events import EventCallback, EventEmitter, write_event_log
from crewai_multiagent_demo.core.outputs import (
    create_output_run_dir,
    task_output_text,
    write_failed_run_outputs,
    write_run_manifest,
    write_run_outputs,
)
from crewai_multiagent_demo.core.workflow import ordered_enabled_tasks
from crewai_multiagent_demo.domain.run_result import RunResult
from crewai_multiagent_demo.domain.tasks import TaskConfig
from crewai_multiagent_demo.llm.model_registry import MODEL_REGISTRY, ModelRegistry
from crewai_multiagent_demo.utils.environment import require_api_key
from crewai_multiagent_demo.utils.paths import DEFAULT_CONFIG_DIR, DEFAULT_OUTPUT_DIR

DEFAULT_TOPIC = "分析并解决一个需要多方权衡的复杂问题"
LOGGER = logging.getLogger(__name__)


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
            row["artifact_role"] = config.artifact_role
        task_outputs.append(row)
    return task_outputs


def select_reports(result: object, task_outputs: list[dict[str, str]]) -> tuple[str, str]:
    by_role = {item.get("artifact_role", "none"): item.get("output", "") for item in task_outputs}
    by_id = {item.get("task_id", ""): item.get("output", "") for item in task_outputs}
    full_report = by_role.get("full_report") or by_id.get("review") or by_id.get("full_report")
    concise_report = by_role.get("summary") or by_id.get("summary") or by_id.get("concise_report")
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
    run_id: str | None = None,
    request_timeout_seconds: float = 180.0,
    max_retries: int = 2,
) -> RunResult:
    resolved_topic = topic.strip() or DEFAULT_TOPIC
    resolved_run_id = run_id or uuid4().hex
    run_dir = create_output_run_dir(output_dir, run_id=resolved_run_id)
    manifest: dict[str, Any] = {
        "run_id": resolved_run_id,
        "status": "created",
        "topic": resolved_topic,
        "model_alias": model_alias or "",
        "elapsed_seconds": 0.0,
        "error": None,
        "artifacts": {},
    }
    write_run_manifest(run_dir, manifest)

    emitter: EventEmitter

    def dispatch(event: dict[str, Any]) -> None:
        write_event_log(run_dir, emitter.events)
        if on_event is not None:
            on_event(event)

    emitter = EventEmitter(dispatch)

    def transition(status: str, **values: Any) -> None:
        manifest.update(values)
        manifest["status"] = status
        write_run_manifest(run_dir, manifest)

    started_at = perf_counter()
    model: Any = None
    try:
        config = app_config or ConfigLoader(config_dir).load(validate=True)
        model = registry.resolve(model_alias)
        require_api_key(model.crewai_model)
        transition("preflight", model_alias=model.alias, model_name=model.model_name, crewai_model=model.crewai_model)
        emitter.emit(
            "run_started",
            run_id=resolved_run_id,
            run_dir=str(run_dir),
            model=model.alias,
            topic=resolved_topic,
        )
        transition("running")
        crew = build_crew(
            crewai_model=model.crewai_model,
            agents_config=config.agents,
            tasks_config=config.tasks,
            on_event=lambda event: emitter.emit(str(event.pop("type", "event")), **event),
            request_timeout_seconds=request_timeout_seconds,
            max_retries=max_retries,
        )
        result = crew.kickoff(inputs={"topic": resolved_topic})
        elapsed_seconds = perf_counter() - started_at
        token_usage = extract_token_usage(result, crew)
        task_outputs = collect_task_outputs(result, config.tasks)
        full_report, concise_report = select_reports(result, task_outputs)
        transition("persisting", elapsed_seconds=elapsed_seconds)
        write_run_outputs(
            output_dir=output_dir,
            run_dir=run_dir,
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
                "status": "succeeded",
            },
        )
        artifacts = {
            "full_report": "full_report.md",
            "summary_report": "summary_report.md",
            "metadata": "run_metadata.md",
            "events": "events.json",
            "tasks": "tasks",
        }
        emitter.emit("run_completed", run_id=resolved_run_id, elapsed_seconds=elapsed_seconds, run_dir=str(run_dir))
        transition("succeeded", elapsed_seconds=elapsed_seconds, artifacts=artifacts)
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
            run_id=resolved_run_id,
            events=emitter.events,
        )
    except Exception as exc:
        elapsed_seconds = perf_counter() - started_at
        error = str(exc)
        model_alias_value = getattr(model, "alias", model_alias or "unknown")
        model_name_value = getattr(model, "model_name", "unknown")
        crewai_model_value = getattr(model, "crewai_model", "unknown")
        try:
            emitter.emit(
                "run_failed",
                run_id=resolved_run_id,
                error=error,
                elapsed_seconds=elapsed_seconds,
                run_dir=str(run_dir),
            )
            write_failed_run_outputs(
                output_dir=output_dir,
                run_dir=run_dir,
                error=error,
                metadata={
                    "topic": resolved_topic,
                    "model_alias": model_alias_value,
                    "model_name": model_name_value,
                    "crewai_model": crewai_model_value,
                    "elapsed_seconds": elapsed_seconds,
                    "token_usage": {},
                },
            )
            transition("failed", elapsed_seconds=elapsed_seconds, error=error)
        except Exception:
            LOGGER.exception("Failed to persist workflow failure for run %s", resolved_run_id)
        LOGGER.exception("Workflow %s failed", resolved_run_id)
        raise

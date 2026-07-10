from __future__ import annotations

from types import SimpleNamespace

import pytest

from crewai_multiagent_demo.config.loader import AppConfig
from crewai_multiagent_demo.core import runner
from crewai_multiagent_demo.domain.agents import AgentConfig
from crewai_multiagent_demo.domain.tasks import TaskConfig


def task(task_id: str, deps: list[str] | None = None) -> TaskConfig:
    return TaskConfig(
        id=task_id,
        name=task_id.title(),
        description=f"{task_id} description",
        expected_output=f"{task_id} output",
        agent_id="agent",
        context_task_ids=deps or [],
    )


def test_collect_task_outputs_keeps_config_task_identity() -> None:
    result = SimpleNamespace(
        tasks_output=[
            SimpleNamespace(agent="Analyst", description="one", raw="analysis text"),
            SimpleNamespace(agent="Reviewer", description="two", raw="review text"),
        ]
    )

    outputs = runner.collect_task_outputs(result, [task("analysis"), task("review", ["analysis"])])

    assert outputs[0]["task_id"] == "analysis"
    assert outputs[0]["task_name"] == "Analysis"
    assert outputs[1]["task_id"] == "review"


def test_select_reports_prefers_semantic_task_ids_over_position() -> None:
    outputs = [
        {"task_id": "analysis", "output": "analysis text"},
        {"task_id": "summary", "output": "summary text"},
        {"task_id": "review", "output": "review text"},
    ]

    full_report, concise_report = runner.select_reports(object(), outputs)

    assert full_report == "review text"
    assert concise_report == "summary text"


def test_run_workflow_emits_failure_when_crew_build_fails(tmp_path, monkeypatch) -> None:
    events = []
    config = AppConfig(
        agents=[AgentConfig(id="agent", role="Role", goal="Goal", backstory="Backstory")],
        tasks=[task("analysis")],
    )
    registry = SimpleNamespace(
        resolve=lambda alias: SimpleNamespace(
            alias="flash",
            model_name="deepseek-v4-flash",
            crewai_model="deepseek/deepseek-v4-flash",
        )
    )

    monkeypatch.setattr(runner, "require_api_key", lambda crewai_model=None: None)

    def fail_build(**kwargs):
        raise RuntimeError("crew unavailable")

    monkeypatch.setattr(runner, "build_crew", fail_build)

    with pytest.raises(RuntimeError, match="crew unavailable"):
        runner.run_workflow(
            topic="topic",
            output_dir=tmp_path,
            app_config=config,
            registry=registry,
            on_event=events.append,
        )

    assert [event["type"] for event in events] == ["run_started", "run_failed"]
    failed_run_dirs = list(tmp_path.iterdir())
    assert len(failed_run_dirs) == 1
    run_dir = failed_run_dirs[0]
    assert "crew unavailable" in (run_dir / "summary_report.md").read_text(encoding="utf-8")
    assert '"type": "run_failed"' in (run_dir / "events.json").read_text(encoding="utf-8")
    manifest = __import__("json").loads((run_dir / "run.json").read_text(encoding="utf-8"))
    assert manifest["status"] == "failed"
    assert manifest["run_id"]
    assert "crew unavailable" in manifest["error"]


def test_select_reports_uses_explicit_artifact_roles() -> None:
    outputs = [
        {"task_id": "custom-a", "artifact_role": "summary", "output": "short"},
        {"task_id": "custom-b", "artifact_role": "full_report", "output": "long"},
    ]

    assert runner.select_reports(object(), outputs) == ("long", "short")

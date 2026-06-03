from __future__ import annotations

import json

import pytest

from crewai_multiagent_demo.gui.services import ConfigEditorService, HistoryService


def write_config(config_dir, agents, tasks) -> None:
    config_dir.mkdir(exist_ok=True)
    (config_dir / "agents.json").write_text(json.dumps(agents), encoding="utf-8")
    (config_dir / "tasks.json").write_text(json.dumps(tasks), encoding="utf-8")


def valid_agents() -> list[dict[str, object]]:
    return [
        {
            "id": "agent",
            "role": "Analyst",
            "goal": "Analyze",
            "backstory": "Careful analyst",
            "enabled": True,
        }
    ]


def valid_tasks() -> list[dict[str, object]]:
    return [
        {
            "id": "analysis",
            "name": "Analysis",
            "description": "Analyze {topic}",
            "expected_output": "Report",
            "agent_id": "agent",
            "context_task_ids": [],
            "enabled": True,
        }
    ]


def test_config_editor_service_loads_snapshot(tmp_path) -> None:
    write_config(tmp_path, valid_agents(), valid_tasks())

    snapshot = ConfigEditorService(tmp_path).load_snapshot()

    assert snapshot.agents[0]["id"] == "agent"
    assert snapshot.task_rows[0]["context_task_ids"] == ""
    assert snapshot.enabled_task_count == 1
    assert "配置检查通过" in snapshot.validation_text


def test_config_editor_service_validates_before_saving(tmp_path) -> None:
    write_config(tmp_path, valid_agents(), valid_tasks())
    service = ConfigEditorService(tmp_path)

    with pytest.raises(ValueError, match="agent"):
        service.save_tasks_payload([{**valid_tasks()[0], "agent_id": "missing"}])

    saved = json.loads((tmp_path / "tasks.json").read_text(encoding="utf-8"))
    assert saved[0]["agent_id"] == "agent"


def test_config_editor_service_parses_json_errors() -> None:
    with pytest.raises(ValueError, match="Agents JSON"):
        ConfigEditorService.parse_json_payload("[", "Agents")


def test_history_service_lists_runs_and_reads_missing_files(tmp_path) -> None:
    old = tmp_path / "20260101_120000"
    new = tmp_path / "20260102_120000"
    old.mkdir()
    new.mkdir()
    (new / "summary_report.md").write_text("summary", encoding="utf-8")

    service = HistoryService(tmp_path)

    assert [path.name for path in service.list_run_dirs()] == [new.name, old.name]
    selection = service.load_selection(new)
    assert selection.summary == "summary"
    assert selection.full_report == "无"

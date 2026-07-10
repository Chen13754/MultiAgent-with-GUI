from __future__ import annotations

import json

import pytest

from crewai_multiagent_demo.config.loader import ConfigLoader


def write_config(config_dir, agents, tasks) -> None:
    config_dir.mkdir(exist_ok=True)
    (config_dir / "agents.json").write_text(json.dumps(agents), encoding="utf-8")
    (config_dir / "tasks.json").write_text(json.dumps(tasks), encoding="utf-8")


def test_loader_reads_compatible_json(tmp_path) -> None:
    write_config(
        tmp_path,
        [
            {
                "id": "analyst",
                "role": "Analyst",
                "goal": "Analyze",
                "backstory": "Careful analyst",
            }
        ],
        [
            {
                "id": "analysis",
                "description": "Analyze {topic}",
                "expected_output": "Report",
                "agent_id": "analyst",
                "context_task_ids": [],
            }
        ],
    )

    config = ConfigLoader(tmp_path).load()

    assert config.agents[0].id == "analyst"
    assert config.tasks[0].name == "analysis"


def test_loader_parses_string_enabled_flags(tmp_path) -> None:
    write_config(
        tmp_path,
        [
            {
                "id": "analyst",
                "role": "Analyst",
                "goal": "Analyze",
                "backstory": "Careful analyst",
                "enabled": "false",
            },
            {
                "id": "writer",
                "role": "Writer",
                "goal": "Write",
                "backstory": "Careful writer",
                "enabled": "true",
            },
        ],
        [
            {
                "id": "summary",
                "description": "Summarize {topic}",
                "expected_output": "Summary",
                "agent_id": "writer",
                "enabled": "0",
            },
            {
                "id": "review",
                "description": "Review {topic}",
                "expected_output": "Review",
                "agent_id": "writer",
                "enabled": "1",
            },
        ],
    )

    config = ConfigLoader(tmp_path).load()

    assert [agent.enabled for agent in config.agents] == [False, True]
    assert [task.enabled for task in config.tasks] == [False, True]


def test_loader_reports_json_error(tmp_path) -> None:
    tmp_path.mkdir(exist_ok=True)
    (tmp_path / "agents.json").write_text("[", encoding="utf-8")
    (tmp_path / "tasks.json").write_text("[]", encoding="utf-8")

    with pytest.raises(ValueError, match="JSON 格式错误"):
        ConfigLoader(tmp_path).load_agents()


def test_loader_migrates_legacy_files_to_versioned_workflow(tmp_path) -> None:
    write_config(
        tmp_path,
        [{"id": "agent", "role": "Role", "goal": "Goal", "backstory": "Backstory"}],
        [{"id": "review", "description": "Review", "expected_output": "Report", "agent_id": "agent"}],
    )
    loader = ConfigLoader(tmp_path)

    loader.migrate_legacy_config()

    document = json.loads((tmp_path / "workflow.json").read_text(encoding="utf-8"))
    assert document["schema_version"] == 1
    assert document["tasks"][0]["artifact_role"] == "full_report"
    assert (tmp_path / "agents.json.legacy.bak").exists()
    assert (tmp_path / "tasks.json.legacy.bak").exists()

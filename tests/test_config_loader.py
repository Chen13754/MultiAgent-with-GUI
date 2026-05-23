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


def test_loader_reports_json_error(tmp_path) -> None:
    tmp_path.mkdir(exist_ok=True)
    (tmp_path / "agents.json").write_text("[", encoding="utf-8")
    (tmp_path / "tasks.json").write_text("[]", encoding="utf-8")

    with pytest.raises(ValueError, match="JSON 格式错误"):
        ConfigLoader(tmp_path).load_agents()

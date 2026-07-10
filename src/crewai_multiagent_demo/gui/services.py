from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from crewai_multiagent_demo.config.loader import AppConfig, ConfigLoader
from crewai_multiagent_demo.config.schema import config_to_dicts, parse_agent_config, parse_task_config
from crewai_multiagent_demo.config.validation import validate_configs
from crewai_multiagent_demo.gui.state import task_rows_for_editor
from crewai_multiagent_demo.utils.paths import DEFAULT_CONFIG_DIR, DEFAULT_OUTPUT_DIR


@dataclass(frozen=True)
class ConfigEditorSnapshot:
    agents: list[dict[str, Any]]
    tasks: list[dict[str, Any]]
    task_rows: list[dict[str, Any]]
    agents_json: str
    tasks_json: str
    enabled_task_count: int
    validation_text: str


@dataclass(frozen=True)
class HistorySelection:
    summary: str
    full_report: str
    metadata: str


def read_text_or_empty(path: Path) -> str:
    if not path.exists():
        return "无"
    return path.read_text(encoding="utf-8")


class ConfigEditorService:
    def __init__(self, config_dir: str | Path = DEFAULT_CONFIG_DIR) -> None:
        self.config_dir = Path(config_dir)
        self.loader = ConfigLoader(self.config_dir)
        self.agents_file = self.config_dir / "agents.json"
        self.tasks_file = self.config_dir / "tasks.json"

    def load_snapshot(self) -> ConfigEditorSnapshot:
        agents = ConfigLoader.load_json_file(self.agents_file)
        tasks = ConfigLoader.load_json_file(self.tasks_file)
        return ConfigEditorSnapshot(
            agents=agents,
            tasks=tasks,
            task_rows=task_rows_for_editor(tasks),
            agents_json=json.dumps(agents, ensure_ascii=False, indent=2),
            tasks_json=json.dumps(tasks, ensure_ascii=False, indent=2),
            enabled_task_count=self.enabled_task_count(),
            validation_text=self.validation_text(),
        )

    def enabled_task_count(self) -> int:
        try:
            tasks = self.loader.load_tasks()
        except Exception:
            return 4
        return max(1, sum(1 for task in tasks if task.enabled))

    def validation_text(self) -> str:
        config = self.loader.load(validate=True)
        return (
            "配置检查通过。\n\nAgents:\n"
            + json.dumps(config_to_dicts(config.agents), ensure_ascii=False, indent=2)
            + "\n\nTasks:\n"
            + json.dumps(config_to_dicts(config.tasks), ensure_ascii=False, indent=2)
        )

    def validate_current_config(self) -> AppConfig:
        return self.loader.load(validate=True)

    def save_agents_payload(self, payload: Any) -> None:
        if not isinstance(payload, list):
            raise ValueError("agents 顶层必须是数组")
        agents = [parse_agent_config(item, index) for index, item in enumerate(payload)]
        tasks = self.loader.load_tasks()
        validate_configs(agents, tasks)
        ConfigLoader.save_json_file(self.agents_file, payload)

    def save_tasks_payload(self, payload: Any) -> None:
        if not isinstance(payload, list):
            raise ValueError("tasks 顶层必须是数组")
        agents = self.loader.load_agents()
        tasks = [parse_task_config(item, index) for index, item in enumerate(payload)]
        validate_configs(agents, tasks)
        ConfigLoader.save_json_file(self.tasks_file, payload)

    def save_config_payloads(self, agents_payload: Any, tasks_payload: Any) -> None:
        """Validate both editable documents together before either is written."""

        if not isinstance(agents_payload, list):
            raise ValueError("agents 顶层必须是数组")
        if not isinstance(tasks_payload, list):
            raise ValueError("tasks 顶层必须是数组")
        agents = [parse_agent_config(item, index) for index, item in enumerate(agents_payload)]
        tasks = [parse_task_config(item, index) for index, item in enumerate(tasks_payload)]
        validate_configs(agents, tasks)
        ConfigLoader.save_json_file(self.agents_file, agents_payload)
        ConfigLoader.save_json_file(self.tasks_file, tasks_payload)

    @staticmethod
    def parse_json_payload(text: str, label: str) -> Any:
        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{label} JSON 格式错误：{exc}") from exc


class HistoryService:
    def __init__(self, output_dir: str | Path = DEFAULT_OUTPUT_DIR) -> None:
        self.output_dir = Path(output_dir)

    def list_run_dirs(self) -> list[Path]:
        if not self.output_dir.exists():
            return []
        return sorted(
            [path for path in self.output_dir.iterdir() if path.is_dir()],
            key=lambda path: path.name,
            reverse=True,
        )

    def load_selection(self, run_dir: Path | None) -> HistorySelection:
        if run_dir is None:
            return HistorySelection(summary="无", full_report="无", metadata="无")
        return HistorySelection(
            summary=read_text_or_empty(run_dir / "summary_report.md"),
            full_report=read_text_or_empty(run_dir / "full_report.md"),
            metadata=read_text_or_empty(run_dir / "run_metadata.md"),
        )

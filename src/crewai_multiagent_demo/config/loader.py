from __future__ import annotations

import json
from dataclasses import dataclass
from json import JSONDecodeError
from pathlib import Path
from typing import Any

from crewai_multiagent_demo.config.schema import parse_agent_config, parse_task_config
from crewai_multiagent_demo.config.validation import validate_configs
from crewai_multiagent_demo.domain.agents import AgentConfig
from crewai_multiagent_demo.domain.tasks import TaskConfig
from crewai_multiagent_demo.utils.paths import DEFAULT_CONFIG_DIR


@dataclass(frozen=True)
class AppConfig:
    agents: list[AgentConfig]
    tasks: list[TaskConfig]


class ConfigLoader:
    def __init__(self, config_dir: str | Path = DEFAULT_CONFIG_DIR) -> None:
        self.config_dir = Path(config_dir)
        self.agents_file = self.config_dir / "agents.json"
        self.tasks_file = self.config_dir / "tasks.json"

    def load(self, *, validate: bool = True) -> AppConfig:
        agents = self.load_agents()
        tasks = self.load_tasks()
        if validate:
            validate_configs(agents, tasks)
        return AppConfig(agents=agents, tasks=tasks)

    def load_agents(self) -> list[AgentConfig]:
        data = self.load_json_file(self.agents_file)
        if not isinstance(data, list):
            raise ValueError(f"{self.agents_file} 顶层必须是数组")
        return [parse_agent_config(item, index) for index, item in enumerate(data)]

    def load_tasks(self) -> list[TaskConfig]:
        data = self.load_json_file(self.tasks_file)
        if not isinstance(data, list):
            raise ValueError(f"{self.tasks_file} 顶层必须是数组")
        return [parse_task_config(item, index) for index, item in enumerate(data)]

    @staticmethod
    def load_json_file(path: Path) -> Any:
        if not path.exists():
            raise FileNotFoundError(f"配置文件不存在: {path}")
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except JSONDecodeError as exc:
            raise ValueError(f"配置文件 JSON 格式错误: {path} ({exc})") from exc

    @staticmethod
    def save_json_file(path: Path, data: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

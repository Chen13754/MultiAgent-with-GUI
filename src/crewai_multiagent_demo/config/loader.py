from __future__ import annotations

import hashlib
import json
import math
import shutil
from dataclasses import dataclass
from json import JSONDecodeError
from pathlib import Path
from typing import Any

from crewai_multiagent_demo.config.schema import config_to_dicts, parse_agent_config, parse_task_config
from crewai_multiagent_demo.config.validation import validate_configs
from crewai_multiagent_demo.domain.agents import AgentConfig
from crewai_multiagent_demo.domain.tasks import TaskConfig
from crewai_multiagent_demo.utils.files import atomic_write_json
from crewai_multiagent_demo.utils.paths import DEFAULT_CONFIG_DIR

WORKFLOW_SCHEMA_VERSION = 2


@dataclass(frozen=True)
class AppConfig:
    agents: list[AgentConfig]
    tasks: list[TaskConfig]
    schema_version: int = WORKFLOW_SCHEMA_VERSION
    graph: dict[str, Any] | None = None


class ConfigLoader:
    def __init__(self, config_dir: str | Path = DEFAULT_CONFIG_DIR) -> None:
        self.config_dir = Path(config_dir)
        self.workflow_file = self.config_dir / "workflow.json"
        self.agents_file = self.config_dir / "agents.json"
        self.tasks_file = self.config_dir / "tasks.json"

    def load(self, *, validate: bool = True) -> AppConfig:
        document = self._load_document()
        agents_payload = document.get("agents")
        tasks_payload = document.get("tasks")
        if not isinstance(agents_payload, list):
            raise ValueError("workflow.json agents 必须是数组")
        if not isinstance(tasks_payload, list):
            raise ValueError("workflow.json tasks 必须是数组")
        agents = [parse_agent_config(item, index) for index, item in enumerate(agents_payload)]
        tasks = [parse_task_config(item, index) for index, item in enumerate(tasks_payload)]
        if validate:
            validate_configs(agents, tasks)
        return AppConfig(
            agents=agents,
            tasks=tasks,
            schema_version=int(document.get("schema_version", WORKFLOW_SCHEMA_VERSION)),
            graph=_normalise_graph(document.get("graph")),
        )

    def load_agents(self) -> list[AgentConfig]:
        return self.load(validate=False).agents

    def load_tasks(self) -> list[TaskConfig]:
        return self.load(validate=False).tasks

    def migrate_legacy_config(self) -> Path:
        if self.workflow_file.exists():
            return self.workflow_file
        config = self.load(validate=True)
        self.config_dir.mkdir(parents=True, exist_ok=True)
        for path in (self.agents_file, self.tasks_file):
            if path.exists():
                backup = path.with_suffix(path.suffix + ".legacy.bak")
                if not backup.exists():
                    shutil.copy2(path, backup)
        self.save_workflow(config.agents, config.tasks)
        return self.workflow_file

    def save_workflow(self, agents: list[AgentConfig], tasks: list[TaskConfig]) -> None:
        validate_configs(agents, tasks)
        graph = self.load(validate=False).graph if self.workflow_file.exists() else None
        self.save_workflow_payloads(config_to_dicts(agents), config_to_dicts(tasks), graph=graph)

    def save_workflow_payloads(
        self,
        agents_payload: list[dict[str, Any]],
        tasks_payload: list[dict[str, Any]],
        *,
        graph: dict[str, Any] | None = None,
    ) -> None:
        document = {
            "schema_version": 2 if graph else WORKFLOW_SCHEMA_VERSION,
            "agents": agents_payload,
            "tasks": tasks_payload,
        }
        if graph:
            document["graph"] = _normalise_graph(graph)
        atomic_write_json(self.workflow_file, document)

    def revision(self) -> str:
        """Return a stable revision for optimistic UI saves and run snapshots."""
        document = self._load_document()
        canonical = json.dumps(document, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]

    def _load_document(self) -> dict[str, Any]:
        if self.workflow_file.exists():
            data = self.load_json_file(self.workflow_file)
            if not isinstance(data, dict):
                raise ValueError(f"{self.workflow_file} 顶层必须是对象")
            version = data.get("schema_version", WORKFLOW_SCHEMA_VERSION)
            if version not in {1, 2}:
                raise ValueError(f"不支持的 workflow schema_version: {version}")
            return data

        agents = self.load_json_file(self.agents_file)
        tasks = self.load_json_file(self.tasks_file)
        return {"schema_version": WORKFLOW_SCHEMA_VERSION, "agents": agents, "tasks": tasks}

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
        atomic_write_json(path, data)


def _normalise_graph(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {"positions": {}, "viewport": {"x": 0, "y": 0, "zoom": 1}}
    raw_positions = value.get("positions", {})
    positions: dict[str, dict[str, float]] = {}
    if isinstance(raw_positions, dict):
        for task_id, raw_position in raw_positions.items():
            if not isinstance(raw_position, dict):
                continue
            try:
                x = float(raw_position.get("x", 0))
                y = float(raw_position.get("y", 0))
                if not math.isfinite(x) or not math.isfinite(y):
                    continue
                positions[str(task_id)] = {"x": x, "y": y}
            except (TypeError, ValueError):
                continue
    raw_viewport = value.get("viewport", {})
    viewport = raw_viewport if isinstance(raw_viewport, dict) else {}
    try:
        zoom = min(2.0, max(0.25, float(viewport.get("zoom", 1))))
        if not math.isfinite(zoom):
            raise ValueError
    except (TypeError, ValueError):
        zoom = 1.0
    try:
        x = float(viewport.get("x", 0))
        if not math.isfinite(x):
            raise ValueError
    except (TypeError, ValueError):
        x = 0.0
    try:
        y = float(viewport.get("y", 0))
        if not math.isfinite(y):
            raise ValueError
    except (TypeError, ValueError):
        y = 0.0
    return {"positions": positions, "viewport": {"x": x, "y": y, "zoom": zoom}}

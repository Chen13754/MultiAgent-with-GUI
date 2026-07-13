from __future__ import annotations

import json
import re
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
    graph: dict[str, Any]
    revision: str


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
        self.workflow_file = self.loader.workflow_file

    def load_snapshot(self) -> ConfigEditorSnapshot:
        if not self.workflow_file.exists():
            self.loader.migrate_legacy_config()
        config = self.loader.load(validate=True)
        agents = config_to_dicts(config.agents)
        tasks = config_to_dicts(config.tasks)
        return ConfigEditorSnapshot(
            agents=agents,
            tasks=tasks,
            task_rows=task_rows_for_editor(tasks),
            agents_json=json.dumps(agents, ensure_ascii=False, indent=2),
            tasks_json=json.dumps(tasks, ensure_ascii=False, indent=2),
            enabled_task_count=max(1, sum(1 for task in config.tasks if task.enabled)),
            validation_text=self._validation_text(config),
            graph=config.graph or {"positions": {}, "viewport": {"x": 0, "y": 0, "zoom": 1}},
            revision=self.loader.revision(),
        )

    def enabled_task_count(self) -> int:
        return max(1, sum(1 for task in self.loader.load_tasks() if task.enabled))

    def revision(self) -> str:
        return self.loader.revision()

    def validation_text(self) -> str:
        return self._validation_text(self.loader.load(validate=True))

    @staticmethod
    def _validation_text(config: AppConfig) -> str:
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
        self.loader.save_workflow(agents, tasks)

    def save_tasks_payload(self, payload: Any) -> None:
        if not isinstance(payload, list):
            raise ValueError("tasks 顶层必须是数组")
        agents = self.loader.load_agents()
        tasks = [parse_task_config(item, index) for index, item in enumerate(payload)]
        validate_configs(agents, tasks)
        self.loader.save_workflow(agents, tasks)

    def save_config_payloads(self, agents_payload: Any, tasks_payload: Any) -> None:
        if not isinstance(agents_payload, list):
            raise ValueError("agents 顶层必须是数组")
        if not isinstance(tasks_payload, list):
            raise ValueError("tasks 顶层必须是数组")
        agents = [parse_agent_config(item, index) for index, item in enumerate(agents_payload)]
        tasks = [parse_task_config(item, index) for index, item in enumerate(tasks_payload)]
        validate_configs(agents, tasks)
        self.loader.save_workflow(agents, tasks)

    def save_graph_payload(self, payload: Any) -> None:
        if not isinstance(payload, dict):
            raise ValueError("graph 顶层必须是对象")
        config = self.loader.load(validate=True)
        self.loader.save_workflow_payloads(
            config_to_dicts(config.agents),
            config_to_dicts(config.tasks),
            graph=payload,
        )

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

    def item_for_path(self, record_id: str, path: Path) -> dict[str, Any]:
        manifest_file = path / "run.json"
        if manifest_file.exists():
            try:
                manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
                return {
                    "id": record_id,
                    "runId": str(manifest.get("run_id", "")),
                    "createdAt": path.name,
                    "modelAlias": str(manifest.get("model_alias") or "-"),
                    "elapsedSeconds": _optional_float(manifest.get("elapsed_seconds")),
                    "status": _history_status(str(manifest.get("status", "failed"))),
                }
            except (OSError, ValueError, TypeError):
                pass

        model_alias = "-"
        elapsed_seconds: float | None = None
        status = "succeeded"
        events_file = path / "events.json"
        if events_file.exists():
            try:
                events = json.loads(events_file.read_text(encoding="utf-8"))
                for event in events:
                    if event.get("type") == "run_started":
                        model_alias = str(event.get("model", model_alias))
                    if event.get("type") in {"run_completed", "run_failed", "run_cancelled"}:
                        status = _history_status(event.get("type", ""))
                        elapsed_seconds = _optional_float(event.get("elapsed_seconds"))
            except (OSError, ValueError, TypeError):
                pass
        metadata = path / "run_metadata.md"
        if metadata.exists() and (model_alias == "-" or elapsed_seconds is None):
            text = metadata.read_text(encoding="utf-8", errors="ignore")
            model_match = re.search(r"模型档位[：:]\s*([^\n]+)", text)
            elapsed_match = re.search(r"总用时[：:]\s*([0-9.]+)", text)
            if model_match:
                model_alias = model_match.group(1).strip()
            if elapsed_match:
                elapsed_seconds = float(elapsed_match.group(1))
            if re.search(r"(?:状态|status)[：:]\s*(?:failed|失败)", text, flags=re.IGNORECASE):
                status = "failed"
        return {
            "id": record_id,
            "runId": "",
            "createdAt": path.name,
            "modelAlias": model_alias,
            "elapsedSeconds": elapsed_seconds,
            "status": status,
        }


def _optional_float(value: Any) -> float | None:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _history_status(value: str) -> str:
    if value in {"succeeded", "run_completed"}:
        return "succeeded"
    if value in {"cancelled", "run_cancelled"}:
        return "cancelled"
    if value in {"created", "preflight", "running", "persisting"}:
        return "interrupted"
    return "failed"

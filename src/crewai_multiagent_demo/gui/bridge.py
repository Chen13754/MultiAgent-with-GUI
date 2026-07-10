from __future__ import annotations

import json
import re
from collections.abc import Callable
from pathlib import Path
from typing import Any

from PySide6.QtCore import QObject, QThread, Signal, Slot
from PySide6.QtGui import QDesktopServices
from PySide6.QtCore import QUrl

from crewai_multiagent_demo.core.runner import run_workflow
from crewai_multiagent_demo.gui.services import ConfigEditorService, HistoryService
from crewai_multiagent_demo.gui.state import RunStatus, event_label, progress_from_events, status_label
from crewai_multiagent_demo.llm.model_registry import MODEL_REGISTRY, ModelRegistry
from crewai_multiagent_demo.utils.environment import has_api_key_for_model
from crewai_multiagent_demo.utils.paths import DEFAULT_CONFIG_DIR, DEFAULT_OUTPUT_DIR

WorkflowRunner = Callable[..., object]
ApiKeyChecker = Callable[[str], bool]


class WorkflowWorker(QThread):
    eventReceived = Signal(dict)
    completed = Signal(object)
    failed = Signal(str)

    def __init__(self, runner: WorkflowRunner, *, topic: str, model_alias: str) -> None:
        super().__init__()
        self._runner = runner
        self._topic = topic
        self._model_alias = model_alias

    def run(self) -> None:
        try:
            result = self._runner(
                topic=self._topic,
                model_alias=self._model_alias,
                on_event=self.eventReceived.emit,
            )
        except Exception as exc:  # pragma: no cover - surfaced through the bridge.
            self.failed.emit(str(exc))
            return
        self.completed.emit(result)


class StudioBridge(QObject):
    """The deliberately small, path-safe boundary between Qt and React."""

    runStateChanged = Signal(str)
    eventReceived = Signal(str)
    historyChanged = Signal(str)
    noticeRaised = Signal(str)

    def __init__(
        self,
        *,
        config_dir: Path = DEFAULT_CONFIG_DIR,
        output_dir: Path = DEFAULT_OUTPUT_DIR,
        legacy_output_dir: Path | None = None,
        runner: WorkflowRunner = run_workflow,
        registry: ModelRegistry = MODEL_REGISTRY,
        api_key_checker: ApiKeyChecker = has_api_key_for_model,
    ) -> None:
        super().__init__()
        self.config_service = ConfigEditorService(config_dir)
        self.output_dir = Path(output_dir)
        self.legacy_output_dir = Path(legacy_output_dir) if legacy_output_dir else None
        self._runner = runner
        self._registry = registry
        self._api_key_checker = api_key_checker
        self._worker: WorkflowWorker | None = None
        self._events: list[dict[str, Any]] = []
        self._last_result: object | None = None
        self._history_paths: dict[str, Path] = {}
        self._state: dict[str, Any] = self._empty_state()

    def is_running(self) -> bool:
        return self._state["status"] == RunStatus.RUNNING.value

    @Slot(result=str)
    def bootstrap(self) -> str:
        return self._json(self._response(data=self._snapshot()))

    @Slot(str, str, result=str)
    def startRun(self, topic: str, model_alias: str) -> str:  # noqa: N802 - QWebChannel API.
        if self.is_running():
            return self._json(self._response(ok=False, code="run_active", message="工作流正在运行。"))

        try:
            model = self._registry.resolve(model_alias)
            self.config_service.validate_current_config()
        except Exception as exc:
            return self._json(self._response(ok=False, code="invalid_config", message=str(exc)))

        if not self._api_key_checker(model.crewai_model):
            message = "未检测到当前模型所需的 API key。请在本地 .env 中配置后重试。"
            self._state = {**self._empty_state(), "status": RunStatus.FAILED.value, "error": message}
            self._emit_state()
            return self._json(self._response(ok=False, code="missing_api_key", message=message))

        self._events = []
        self._last_result = None
        self._state = {
            **self._empty_state(),
            "status": RunStatus.RUNNING.value,
            "modelAlias": model.alias,
            "topic": topic.strip(),
            "taskCount": self.config_service.enabled_task_count(),
            "progress": 5,
            "activeAgent": "等待启动",
        }
        self._emit_state()

        self._worker = WorkflowWorker(self._runner, topic=topic, model_alias=model.alias)
        self._worker.eventReceived.connect(self._handle_event)
        self._worker.completed.connect(self._handle_completed)
        self._worker.failed.connect(self._handle_failed)
        self._worker.finished.connect(self._release_worker)
        self._worker.start()
        return self._json(self._response(data={"accepted": True}))

    @Slot(result=str)
    def resetRun(self) -> str:  # noqa: N802 - QWebChannel API.
        if self.is_running():
            return self._json(self._response(ok=False, code="run_active", message="运行结束前不能重置。"))
        self._events = []
        self._last_result = None
        self._state = self._empty_state()
        self._emit_state()
        return self._json(self._response(data=self._state))

    @Slot(result=str)
    def validateConfig(self) -> str:  # noqa: N802 - QWebChannel API.
        try:
            return self._json(self._response(data={"text": self.config_service.validation_text()}))
        except Exception as exc:
            return self._json(self._response(ok=False, code="invalid_config", message=str(exc)))

    @Slot(str, str, result=str)
    def saveConfig(self, kind: str, payload_json: str) -> str:  # noqa: N802 - QWebChannel API.
        if self.is_running():
            return self._json(self._response(ok=False, code="run_active", message="运行中不能修改配置。"))
        try:
            payload = json.loads(payload_json)
            if kind == "agents":
                self.config_service.save_agents_payload(payload)
            elif kind == "tasks":
                self.config_service.save_tasks_payload(payload)
            else:
                raise ValueError("未知配置类型")
        except Exception as exc:
            return self._json(self._response(ok=False, code="save_failed", message=str(exc)))
        return self._json(self._response(data=self._config_snapshot()))

    @Slot(str, str, result=str)
    def saveConfigBundle(self, agents_json: str, tasks_json: str) -> str:  # noqa: N802 - QWebChannel API.
        if self.is_running():
            return self._json(self._response(ok=False, code="run_active", message="运行中不能修改配置。"))
        try:
            self.config_service.save_config_payloads(json.loads(agents_json), json.loads(tasks_json))
        except Exception as exc:
            return self._json(self._response(ok=False, code="save_failed", message=str(exc)))
        return self._json(self._response(data=self._config_snapshot()))

    @Slot(str, result=str)
    def loadHistory(self, record_id: str) -> str:  # noqa: N802 - QWebChannel API.
        self._refresh_history_paths()
        path = self._history_paths.get(record_id)
        if path is None:
            return self._json(self._response(ok=False, code="history_missing", message="找不到该历史记录。"))
        selection = HistoryService(path.parent).load_selection(path)
        return self._json(
            self._response(
                data={
                    "id": record_id,
                    "summary": selection.summary,
                    "fullReport": selection.full_report,
                    "metadata": selection.metadata,
                }
            )
        )

    @Slot(str, str, result=str)
    def openLocation(self, target: str, record_id: str = "") -> str:  # noqa: N802 - QWebChannel API.
        path: Path | None
        if target == "outputs":
            path = self.output_dir
        elif target == "history":
            self._refresh_history_paths()
            path = self._history_paths.get(record_id)
        else:
            path = None
        if path is None or not path.exists():
            return self._json(self._response(ok=False, code="location_missing", message="没有可打开的位置。"))
        opened = QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))
        return self._json(self._response(ok=opened, code="open_failed" if not opened else None))

    def _handle_event(self, event: dict[str, Any]) -> None:
        self._events.append(dict(event))
        event_type = str(event.get("type", ""))
        self._state["progress"] = progress_from_events(self._events, self._state["taskCount"])
        self._state["activeAgent"] = str(event.get("agent") or event_label(event_type))
        self._state["events"] = self._events[-50:]
        self.eventReceived.emit(self._json(event))
        self._emit_state()

    def _handle_completed(self, result: object) -> None:
        self._last_result = result
        run_dir = Path(str(getattr(result, "run_dir", "")))
        self._state = {
            **self._state,
            "status": RunStatus.SUCCEEDED.value,
            "progress": 100,
            "result": {
                "historyId": self._id_for_path(run_dir),
                "modelAlias": str(getattr(result, "model_alias", self._state["modelAlias"])),
                "elapsedSeconds": float(getattr(result, "elapsed_seconds", 0.0)),
                "summary": str(getattr(result, "concise_report", "")),
                "fullReport": str(getattr(result, "full_report", "")),
                "taskOutputs": list(getattr(result, "task_outputs", []) or []),
            },
        }
        self._emit_state()
        self.historyChanged.emit(self._json(self._history_items()))
        self.noticeRaised.emit(self._json({"kind": "success", "message": "工作流已完成，报告已生成。"}))

    def _handle_failed(self, error: str) -> None:
        self._state = {**self._state, "status": RunStatus.FAILED.value, "progress": 0, "error": error}
        self._emit_state()
        self.historyChanged.emit(self._json(self._history_items()))
        self.noticeRaised.emit(self._json({"kind": "error", "message": error}))

    def _release_worker(self) -> None:
        if self._worker is not None:
            self._worker.deleteLater()
        self._worker = None

    def _snapshot(self) -> dict[str, Any]:
        return {
            "models": list(self._registry.aliases),
            "defaultModel": self._registry.default_alias(),
            "apiKeyConfigured": {
                alias: self._api_key_checker(self._registry.resolve(alias).crewai_model)
                for alias in self._registry.aliases
            },
            "config": self._config_snapshot(),
            "history": self._history_items(),
            "runState": self._state,
        }

    def _config_snapshot(self) -> dict[str, Any]:
        snapshot = self.config_service.load_snapshot()
        return {
            "agents": snapshot.agents,
            "tasks": snapshot.tasks,
            "agentsJson": snapshot.agents_json,
            "tasksJson": snapshot.tasks_json,
            "enabledTaskCount": snapshot.enabled_task_count,
            "validationText": snapshot.validation_text,
        }

    def _history_items(self) -> list[dict[str, Any]]:
        self._refresh_history_paths()
        return [self._history_item(record_id, path) for record_id, path in self._history_paths.items()]

    def _refresh_history_paths(self) -> None:
        paths: dict[str, Path] = {}
        sources = (("current", self.output_dir), ("legacy", self.legacy_output_dir))
        for prefix, root in sources:
            if root is None:
                continue
            for path in HistoryService(root).list_run_dirs():
                paths[f"{prefix}:{path.name}"] = path
        self._history_paths = dict(
            sorted(paths.items(), key=lambda item: item[1].name, reverse=True)
        )

    def _history_item(self, record_id: str, path: Path) -> dict[str, Any]:
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
                    if event.get("type") in {"run_completed", "run_failed"}:
                        status = "failed" if event.get("type") == "run_failed" else "succeeded"
                        if event.get("elapsed_seconds") is not None:
                            elapsed_seconds = float(event["elapsed_seconds"])
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
            if re.search(r"status[：:]\s*failed", text, flags=re.IGNORECASE):
                status = "failed"
        return {
            "id": record_id,
            "createdAt": path.name,
            "modelAlias": model_alias,
            "elapsedSeconds": elapsed_seconds,
            "status": status,
        }

    def _id_for_path(self, path: Path) -> str:
        self._refresh_history_paths()
        for record_id, candidate in self._history_paths.items():
            if candidate == path:
                return record_id
        return f"current:{path.name}"

    @staticmethod
    def _empty_state() -> dict[str, Any]:
        return {
            "status": RunStatus.IDLE.value,
            "progress": 0,
            "modelAlias": MODEL_REGISTRY.default_alias(),
            "topic": "",
            "taskCount": 0,
            "activeAgent": "等待启动",
            "events": [],
            "result": None,
            "error": None,
        }

    def _emit_state(self) -> None:
        self.runStateChanged.emit(self._json(self._state))

    @staticmethod
    def _response(
        *, ok: bool = True, data: Any | None = None, code: str | None = None, message: str | None = None
    ) -> dict[str, Any]:
        response: dict[str, Any] = {"ok": ok}
        if data is not None:
            response["data"] = data
        if code:
            response["code"] = code
        if message:
            response["message"] = message
        return response

    @staticmethod
    def _json(value: Any) -> str:
        return json.dumps(value, ensure_ascii=False, default=str)

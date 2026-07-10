from __future__ import annotations

import json
import os
from collections.abc import Callable
from pathlib import Path
from typing import Any

from PySide6.QtCore import QObject, QThread, QUrl, Signal, Slot
from PySide6.QtGui import QDesktopServices

from crewai_multiagent_demo.config.loader import ConfigLoader
from crewai_multiagent_demo.core.runner import run_workflow
from crewai_multiagent_demo.domain.run_request import RunRequest
from crewai_multiagent_demo.gui.run_process import WorkflowProcessWorker
from crewai_multiagent_demo.gui.services import ConfigEditorService, HistoryService
from crewai_multiagent_demo.gui.state import RunStatus, event_label, progress_from_events
from crewai_multiagent_demo.llm.model_registry import MODEL_REGISTRY, ModelRegistry
from crewai_multiagent_demo.utils.diagnostics import create_diagnostics_archive
from crewai_multiagent_demo.utils.environment import has_api_key_for_model
from crewai_multiagent_demo.utils.files import atomic_write_json, atomic_write_text
from crewai_multiagent_demo.utils.paths import (
    BUNDLED_CONFIG_DIR,
    DEFAULT_CACHE_DIR,
    DEFAULT_CONFIG_DIR,
    DEFAULT_ENV_FILE,
    DEFAULT_OUTPUT_DIR,
)

PROTOCOL_VERSION = 1
WorkflowRunner = Callable[..., object]
ApiKeyChecker = Callable[[str], bool]


class InlineWorkflowWorker(QThread):
    """Test/development adapter; production runs use WorkflowProcessWorker."""

    eventReceived = Signal(dict)
    completed = Signal(object)
    failed = Signal(str)
    cancelled = Signal(str)

    def __init__(self, runner: WorkflowRunner, request: RunRequest) -> None:
        super().__init__()
        self._runner = runner
        self.request = request

    def request_cancel(self) -> None:
        # Injected test runners are deliberately in-process and cannot be
        # forcefully interrupted. The production path never uses this adapter.
        return

    def run(self) -> None:
        try:
            result = self._runner(
                topic=self.request.topic,
                model_alias=self.request.model_alias,
                config_dir=self.request.config_dir,
                output_dir=self.request.output_dir,
                run_id=self.request.run_id,
                request_timeout_seconds=self.request.request_timeout_seconds,
                max_retries=self.request.max_retries,
                on_event=self.eventReceived.emit,
            )
        except Exception as exc:  # pragma: no cover - surfaced through the bridge.
            self.failed.emit(str(exc))
            return
        self.completed.emit(result)


class StudioBridge(QObject):
    """Path-safe QWebChannel protocol adapter for the desktop UI."""

    runStateChanged = Signal(str)
    eventReceived = Signal(str)
    historyChanged = Signal(str)
    noticeRaised = Signal(str)

    def __init__(
        self,
        *,
        config_dir: Path = DEFAULT_CONFIG_DIR,
        output_dir: Path = DEFAULT_OUTPUT_DIR,
        env_file: Path = DEFAULT_ENV_FILE,
        cache_dir: Path = DEFAULT_CACHE_DIR,
        legacy_output_dir: Path | None = None,
        runner: WorkflowRunner = run_workflow,
        registry: ModelRegistry = MODEL_REGISTRY,
        api_key_checker: ApiKeyChecker = has_api_key_for_model,
    ) -> None:
        super().__init__()
        self.config_service = ConfigEditorService(config_dir)
        self.output_dir = Path(output_dir)
        self.env_file = Path(env_file)
        self.cache_dir = Path(cache_dir)
        self.legacy_output_dir = Path(legacy_output_dir) if legacy_output_dir else None
        self._runner = runner
        self._registry = registry
        self._api_key_checker = api_key_checker
        self._worker: WorkflowProcessWorker | InlineWorkflowWorker | None = None
        self._events: list[dict[str, Any]] = []
        self._last_result: object | None = None
        self._history_paths: dict[str, Path] = {}
        self._state: dict[str, Any] = self._empty_state()

    def is_running(self) -> bool:
        return self._state["status"] == RunStatus.RUNNING.value

    @Slot(result=str)
    def bootstrap(self) -> str:
        try:
            return self._json(self._response(data=self._snapshot()))
        except Exception as exc:
            return self._json(
                self._response(
                    ok=False,
                    code="bootstrap_failed",
                    message=str(exc),
                    data={
                        "protocolVersion": PROTOCOL_VERSION,
                        "configPath": str(self.config_service.config_dir),
                        "recoverable": True,
                    },
                )
            )

    @Slot(str, str, result=str)
    def startRun(self, topic: str, model_alias: str) -> str:  # noqa: N802
        if self.is_running():
            return self._json(self._response(ok=False, code="run_active", message="工作流正在运行。"))
        try:
            model = self._registry.resolve(model_alias)
            self.config_service.validate_current_config()
        except Exception as exc:
            return self._json(self._response(ok=False, code="invalid_config", message=str(exc)))
        if not self._api_key_checker(model.crewai_model):
            message = f"未检测到当前模型所需的 API key。请在设置中配置。配置文件：{self.env_file}"
            self._state = {**self._empty_state(), "status": RunStatus.FAILED.value, "error": message}
            self._emit_state()
            return self._json(self._response(ok=False, code="missing_api_key", message=message))

        request = RunRequest.create(
            topic=topic,
            model_alias=model.alias,
            config_dir=self.config_service.config_dir,
            output_dir=self.output_dir,
            env_file=self.env_file,
        )
        self._events = []
        self._last_result = None
        self._state = {
            **self._empty_state(),
            "status": RunStatus.RUNNING.value,
            "runId": request.run_id,
            "modelAlias": model.alias,
            "topic": topic.strip(),
            "taskCount": self.config_service.enabled_task_count(),
            "progress": 5,
            "activeAgent": "等待启动",
        }
        self._emit_state()

        if self._runner is run_workflow:
            worker: WorkflowProcessWorker | InlineWorkflowWorker = WorkflowProcessWorker(request)
        else:
            worker = InlineWorkflowWorker(self._runner, request)
        self._worker = worker
        worker.eventReceived.connect(self._handle_event)
        worker.completed.connect(self._handle_completed)
        worker.failed.connect(self._handle_failed)
        worker.cancelled.connect(self._handle_cancelled)
        worker.finished.connect(self._release_worker)
        worker.start()
        return self._json(self._response(data={"accepted": True, "runId": request.run_id}))

    @Slot(result=str)
    def cancelRun(self) -> str:  # noqa: N802
        if not self.is_running() or self._worker is None:
            return self._json(self._response(ok=False, code="run_inactive", message="当前没有正在运行的工作流。"))
        self._worker.request_cancel()
        self._state["activeAgent"] = "正在取消"
        self._emit_state()
        return self._json(self._response(data={"accepted": True}))

    def shutdown(self, wait_ms: int = 5500) -> None:
        if self._worker is None:
            return
        self._worker.request_cancel()
        self._worker.wait(wait_ms)

    @Slot(result=str)
    def resetRun(self) -> str:  # noqa: N802
        if self.is_running():
            return self._json(self._response(ok=False, code="run_active", message="运行结束前不能重置。"))
        self._events = []
        self._last_result = None
        self._state = self._empty_state()
        self._emit_state()
        return self._json(self._response(data=self._state))

    @Slot(result=str)
    def validateConfig(self) -> str:  # noqa: N802
        try:
            return self._json(self._response(data={"text": self.config_service.validation_text()}))
        except Exception as exc:
            return self._json(self._response(ok=False, code="invalid_config", message=str(exc)))

    @Slot(str, str, result=str)
    def saveConfig(self, kind: str, payload_json: str) -> str:  # noqa: N802
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
    def saveConfigBundle(self, agents_json: str, tasks_json: str) -> str:  # noqa: N802
        if self.is_running():
            return self._json(self._response(ok=False, code="run_active", message="运行中不能修改配置。"))
        try:
            self.config_service.save_config_payloads(json.loads(agents_json), json.loads(tasks_json))
        except Exception as exc:
            return self._json(self._response(ok=False, code="save_failed", message=str(exc)))
        return self._json(self._response(data=self._config_snapshot()))

    @Slot(result=str)
    def resetConfig(self) -> str:  # noqa: N802
        if self.is_running():
            return self._json(self._response(ok=False, code="run_active", message="运行中不能重置配置。"))
        try:
            document = ConfigLoader.load_json_file(BUNDLED_CONFIG_DIR / "workflow.json")
            atomic_write_json(self.config_service.workflow_file, document)
            return self._json(self._response(data=self._snapshot()))
        except Exception as exc:
            return self._json(self._response(ok=False, code="reset_failed", message=str(exc)))

    @Slot(str, result=str)
    def saveApiKey(self, key: str) -> str:  # noqa: N802
        cleaned = key.strip()
        if len(cleaned) < 8 or "\n" in cleaned or "\r" in cleaned:
            return self._json(self._response(ok=False, code="invalid_api_key", message="API key 格式无效。"))
        try:
            lines = self.env_file.read_text(encoding="utf-8").splitlines() if self.env_file.exists() else []
            updated: list[str] = []
            replaced = False
            for line in lines:
                if line.startswith("DEEPSEEK_API_KEY="):
                    updated.append(f"DEEPSEEK_API_KEY={cleaned}")
                    replaced = True
                else:
                    updated.append(line)
            if not replaced:
                updated.append(f"DEEPSEEK_API_KEY={cleaned}")
            atomic_write_text(self.env_file, "\n".join(updated) + "\n")
            os.environ["DEEPSEEK_API_KEY"] = cleaned
            return self._json(self._response(data={"configured": True, "envFile": str(self.env_file)}))
        except Exception as exc:
            return self._json(self._response(ok=False, code="save_key_failed", message=str(exc)))

    @Slot(result=str)
    def exportDiagnostics(self) -> str:  # noqa: N802
        try:
            archive = create_diagnostics_archive(self.cache_dir, self.output_dir)
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(archive.parent)))
            return self._json(self._response(data={"path": str(archive)}))
        except Exception as exc:
            return self._json(self._response(ok=False, code="diagnostics_failed", message=str(exc)))

    @Slot(str, result=str)
    def loadHistory(self, record_id: str) -> str:  # noqa: N802
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
    def openLocation(self, target: str, record_id: str = "") -> str:  # noqa: N802
        path: Path | None
        if target == "outputs":
            path = self.output_dir
        elif target == "config":
            path = self.config_service.config_dir
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
        public_event = dict(event)
        output = str(public_event.pop("output", ""))
        if output:
            public_event["outputPreview"] = output[:240]
        self._events.append(public_event)
        event_type = str(public_event.get("type", ""))
        self._state["progress"] = progress_from_events(self._events, self._state["taskCount"])
        self._state["activeAgent"] = str(
            public_event.get("task_name") or public_event.get("agent") or event_label(event_type)
        )
        self._state["events"] = self._events[-50:]
        self.eventReceived.emit(self._json(public_event))
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

    def _handle_cancelled(self, message: str) -> None:
        self._state = {
            **self._state,
            "status": RunStatus.CANCELLED.value,
            "progress": 0,
            "activeAgent": "已取消",
            "error": message,
        }
        self._emit_state()
        self.historyChanged.emit(self._json(self._history_items()))
        self.noticeRaised.emit(self._json({"kind": "warning", "message": message}))

    def _release_worker(self) -> None:
        if self._worker is not None:
            self._worker.deleteLater()
        self._worker = None

    def _snapshot(self) -> dict[str, Any]:
        return {
            "protocolVersion": PROTOCOL_VERSION,
            "models": list(self._registry.aliases),
            "defaultModel": self._registry.default_alias(),
            "apiKeyConfigured": {
                alias: self._api_key_checker(self._registry.resolve(alias).crewai_model)
                for alias in self._registry.aliases
            },
            "configPath": str(self.config_service.config_dir),
            "envFile": str(self.env_file),
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
        return [
            HistoryService(path.parent).item_for_path(record_id, path)
            for record_id, path in self._history_paths.items()
        ]

    def _refresh_history_paths(self) -> None:
        paths: dict[str, Path] = {}
        for prefix, root in (("current", self.output_dir), ("legacy", self.legacy_output_dir)):
            if root is None:
                continue
            for path in HistoryService(root).list_run_dirs():
                paths[f"{prefix}:{path.name}"] = path
        self._history_paths = dict(sorted(paths.items(), key=lambda item: item[1].name, reverse=True))

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
            "runId": "",
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

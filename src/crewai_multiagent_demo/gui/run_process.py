from __future__ import annotations

import json
import multiprocessing
import queue
import traceback
from pathlib import Path
from threading import Event
from time import monotonic
from typing import Any

from PySide6.QtCore import QThread, Signal

from crewai_multiagent_demo.core.outputs import write_run_manifest
from crewai_multiagent_demo.core.runner import run_workflow
from crewai_multiagent_demo.domain.run_request import RunRequest
from crewai_multiagent_demo.utils.environment import load_project_env


def _workflow_process_entry(request: RunRequest, event_queue: Any, result_queue: Any) -> None:
    try:
        load_project_env(request.env_file)
        result = run_workflow(
            topic=request.topic,
            model_alias=request.model_alias,
            config_dir=request.config_dir,
            output_dir=request.output_dir,
            run_id=request.run_id,
            request_timeout_seconds=request.request_timeout_seconds,
            max_retries=request.max_retries,
            on_event=event_queue.put,
        )
        result_queue.put(("completed", result))
    except BaseException as exc:
        result_queue.put(
            (
                "failed",
                {
                    "message": str(exc),
                    "traceback": "".join(traceback.format_exception(type(exc), exc, exc.__traceback__)),
                },
            )
        )


class WorkflowProcessWorker(QThread):
    eventReceived = Signal(dict)
    completed = Signal(object)
    failed = Signal(str)
    cancelled = Signal(str)

    def __init__(self, request: RunRequest) -> None:
        super().__init__()
        self.request = request
        self._cancel_requested = Event()
        self._process: multiprocessing.Process | None = None

    def request_cancel(self) -> None:
        self._cancel_requested.set()

    def run(self) -> None:
        context = multiprocessing.get_context("spawn")
        event_queue = context.Queue()
        result_queue = context.Queue()
        process = context.Process(
            target=_workflow_process_entry,
            args=(self.request, event_queue, result_queue),
            name=f"multiagent-run-{self.request.run_id[:8]}",
        )
        self._process = process
        process.start()
        deadline = monotonic() + self.request.total_timeout_seconds
        terminal: tuple[str, Any] | None = None
        try:
            while process.is_alive() or terminal is None:
                self._drain_events(event_queue)
                try:
                    terminal = result_queue.get_nowait()
                    break
                except queue.Empty:
                    pass
                if self._cancel_requested.is_set():
                    self._stop_process(process)
                    mark_interrupted_run(self.request, "cancelled", "用户取消了运行。")
                    self.cancelled.emit("用户取消了运行。")
                    return
                if monotonic() >= deadline:
                    self._stop_process(process)
                    message = f"工作流超过 {int(self.request.total_timeout_seconds)} 秒，已终止。"
                    mark_interrupted_run(self.request, "failed", message)
                    self.failed.emit(message)
                    return
                if not process.is_alive() and terminal is None:
                    try:
                        terminal = result_queue.get(timeout=0.2)
                    except queue.Empty:
                        terminal = ("failed", {"message": f"工作流子进程异常退出（code={process.exitcode}）。"})
                    break
                self.msleep(50)
            self._drain_events(event_queue)
            if terminal and terminal[0] == "completed":
                self.completed.emit(terminal[1])
            else:
                payload = terminal[1] if terminal else {}
                self.failed.emit(str(payload.get("message", "工作流运行失败。")))
        finally:
            if process.is_alive():
                self._stop_process(process)
            process.join(timeout=1)
            event_queue.close()
            result_queue.close()
            self._process = None

    def _drain_events(self, event_queue: Any) -> None:
        while True:
            try:
                self.eventReceived.emit(event_queue.get_nowait())
            except queue.Empty:
                return

    @staticmethod
    def _stop_process(process: multiprocessing.Process) -> None:
        if not process.is_alive():
            return
        process.terminate()
        process.join(timeout=5)
        if process.is_alive() and hasattr(process, "kill"):
            process.kill()
            process.join(timeout=1)


def mark_interrupted_run(request: RunRequest, status: str, error: str) -> None:
    candidates = sorted(Path(request.output_dir).glob(f"*_{request.run_id}"), reverse=True)
    if not candidates:
        return
    run_dir = candidates[0]
    manifest_file = run_dir / "run.json"
    manifest: dict[str, Any] = {}
    if manifest_file.exists():
        try:
            manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError):
            manifest = {}
    manifest.update({"run_id": request.run_id, "status": status, "error": error})
    write_run_manifest(run_dir, manifest)

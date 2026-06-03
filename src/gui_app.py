from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Any

from PySide6.QtCore import QThread, QTimer, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QMainWindow,
    QMessageBox,
    QStackedWidget,
    QTextBrowser,
    QWidget,
)

sys.path.insert(0, str(Path(__file__).resolve().parent))

from crewai_multiagent_demo.core.runner import run_workflow
from crewai_multiagent_demo.gui.pages import (
    build_config_page,
    build_history_page,
    build_run_page,
    build_sidebar,
    populate_table,
    table_rows,
)
from crewai_multiagent_demo.gui.services import ConfigEditorService, HistoryService
from crewai_multiagent_demo.gui.state import (
    RUN_LOCK_REASON,
    RunStatus,
    event_label,
    normalize_status,
    normalize_task_rows,
    progress_from_events,
    status_label,
)
from crewai_multiagent_demo.gui.styles import APP_QSS
from crewai_multiagent_demo.gui.widgets import fade_in
from crewai_multiagent_demo.llm.model_registry import MODEL_REGISTRY
from crewai_multiagent_demo.utils.environment import (
    api_key_env_names_for_model,
    has_api_key_for_model,
    load_project_env,
    loaded_env_file,
)
from crewai_multiagent_demo.utils.paths import DEFAULT_CONFIG_DIR, DEFAULT_OUTPUT_DIR, PROJECT_ROOT


class RunWorker(QThread):
    event_received = Signal(dict)
    completed = Signal(object)
    failed = Signal(str)

    def __init__(self, *, topic: str, model_alias: str) -> None:
        super().__init__()
        self.topic = topic
        self.model_alias = model_alias

    def run(self) -> None:
        try:
            result = run_workflow(
                topic=self.topic,
                model_alias=self.model_alias,
                on_event=self.event_received.emit,
            )
        except Exception as exc:  # pragma: no cover - exercised through GUI smoke/manual use.
            self.failed.emit(str(exc))
            return
        self.completed.emit(result)


class MultiagentStudio(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.run_status = RunStatus.IDLE
        self.events: list[dict[str, Any]] = []
        self.last_result: Any = None
        self.worker: RunWorker | None = None
        self.expected_task_count = 4
        self.config_service = ConfigEditorService(DEFAULT_CONFIG_DIR)
        self.history_service = HistoryService(DEFAULT_OUTPUT_DIR)

        self.setWindowTitle("Multiagent Studio")
        self.resize(1220, 780)
        self.setMinimumSize(960, 640)

        root = QWidget()
        root.setObjectName("Root")
        self.setCentralWidget(root)
        shell = QHBoxLayout(root)
        shell.setContentsMargins(0, 0, 0, 0)
        shell.setSpacing(0)

        shell.addWidget(build_sidebar(self))

        self.pages = QStackedWidget()
        self.run_page = build_run_page(self)
        self.config_page = build_config_page(self)
        self.history_page = build_history_page(self)
        self.pages.addWidget(self.run_page)
        self.pages.addWidget(self.config_page)
        self.pages.addWidget(self.history_page)
        shell.addWidget(self.pages, 1)

        self.setStyleSheet(APP_QSS)
        self.refresh_status_cards()
        self.refresh_history()

    def switch_page(self, index: int) -> None:
        if self.is_running():
            self.lock_hint.setText(RUN_LOCK_REASON)
            return
        self.pages.setCurrentIndex(index)
        fade_in(self.pages.currentWidget(), 150)
        for button_index, button in enumerate(self.nav_buttons):
            button.setChecked(button_index == index)
        if index == 2:
            self.refresh_history()

    def is_running(self) -> bool:
        return self.run_status == RunStatus.RUNNING

    def refresh_expected_task_count(self) -> None:
        self.expected_task_count = self.config_service.enabled_task_count()

    def set_running_locked(self, locked: bool) -> None:
        for button in self.nav_buttons:
            button.setEnabled(not locked)
        self.config_tabs.setEnabled(not locked)
        self.run_button.setEnabled(True)
        self.run_button.set_pulsing(locked)
        self.model_combo.setEnabled(not locked)
        self.topic_edit.setEnabled(not locked)
        self.lock_hint.setText(RUN_LOCK_REASON if locked else "")
        self.run_button.setText("工作流运行中" if locked else "运行工作流")
        self.agent_graph.set_running(locked)

    def start_run(self) -> None:
        if self.is_running():
            return
        model = MODEL_REGISTRY.resolve(self.model_combo.currentText())
        required_keys = ", ".join(api_key_env_names_for_model(model.crewai_model))
        if not has_api_key_for_model(model.crewai_model):
            self.run_status = RunStatus.FAILED
            self.api_warning.setText(f"未检测到 API key。请先在 .env 中配置 {required_keys}。")
            self.refresh_status_cards()
            QMessageBox.warning(self, "缺少 API key", f"缺少 {required_keys}，无法运行。")
            return

        self.events = []
        self.last_result = None
        self.refresh_expected_task_count()
        self.reset_events()
        self.clear_result_views()
        self.progress.setValue(5)
        self.agent_graph.set_progress(5)
        self.run_status = RunStatus.RUNNING
        self.set_running_locked(True)
        self.refresh_status_cards()

        self.worker = RunWorker(
            topic=self.topic_edit.toPlainText(),
            model_alias=self.model_combo.currentText(),
        )
        self.worker.event_received.connect(self.handle_event)
        self.worker.completed.connect(self.handle_completed)
        self.worker.failed.connect(self.handle_failed)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker.start()

    def handle_event(self, event: dict[str, Any]) -> None:
        self.events.append(event)
        progress = progress_from_events(self.events, self.expected_task_count)
        self.progress.setValue(progress)
        self.agent_graph.set_progress(progress)
        self.agent_graph.handle_event(event)
        self.add_event_item(event)

    def handle_completed(self, result: object) -> None:
        self.last_result = result
        self.run_status = RunStatus.SUCCEEDED
        self.progress.setValue(100)
        self.set_running_locked(False)
        self.agent_graph.set_completed()
        self.refresh_status_cards()
        self.render_result(result)
        self.refresh_history()
        QMessageBox.information(self, "运行完成", f"运行完成，输出目录：{getattr(result, 'run_dir', '')}")

    def handle_failed(self, error: str) -> None:
        self.run_status = RunStatus.FAILED
        self.progress.setValue(0)
        self.set_running_locked(False)
        self.agent_graph.set_failed()
        self.refresh_status_cards()
        QMessageBox.critical(self, "运行失败", error)

    def refresh_status_cards(self) -> None:
        model = self.model_combo.currentText() if hasattr(self, "model_combo") else MODEL_REGISTRY.default_alias()
        if self.last_result is not None:
            model = getattr(self.last_result, "model_alias", model)
        tasks = len(getattr(self.last_result, "task_outputs", []) or [])
        elapsed = getattr(self.last_result, "elapsed_seconds", None)
        current_status = normalize_status(self.run_status.value)
        self.status_widgets["status"].set_value(status_label(current_status.value))
        self.status_widgets["status"].set_status(current_status.value)
        self.status_widgets["model"].set_value(str(model))
        self.status_widgets["tasks"].set_value(str(tasks))
        self.status_widgets["elapsed"].set_value(f"{elapsed:.1f}s" if elapsed is not None else "-")
        env_hint = loaded_env_file() or Path(os.getenv("MULTIAGENT_ENV_FILE") or PROJECT_ROOT / ".env")
        model_spec = MODEL_REGISTRY.resolve(str(model))
        required_keys = ", ".join(api_key_env_names_for_model(model_spec.crewai_model))
        self.api_warning.setText(
            ""
            if has_api_key_for_model(model_spec.crewai_model)
            else f"未检测到 API key。请检查 {env_hint} 中的 {required_keys}。"
        )

    def reset_events(self) -> None:
        self.event_list.clear()
        self.agent_graph.reset()
        self.event_list.add_motion_item("运行后这里会显示公开事件、任务完成状态和输出节点。", "idle")

    def add_event_item(self, event: dict[str, Any]) -> None:
        if self.event_list.count() == 1 and "运行后" in self.event_list.item(0).text():
            self.event_list.clear()
        details = []
        if event.get("agent"):
            details.append(f"Agent: {event['agent']}")
        if event.get("model"):
            details.append(f"Model: {event['model']}")
        if event.get("elapsed_seconds") is not None:
            details.append(f"{float(event['elapsed_seconds']):.2f}s")
        if event.get("run_dir"):
            details.append(str(event["run_dir"]))
        if event.get("error"):
            details.append(str(event["error"]))
        text = f"{event_label(str(event.get('type', '')))}  {event.get('time', '')}"
        if details:
            text += "\n" + " · ".join(details)
        self.event_list.add_motion_item(text, str(event.get("type", "")))

    def clear_result_views(self) -> None:
        self.summary_view.setMarkdown("暂无运行结果。")
        self.full_view.setMarkdown("暂无运行结果。")
        self.task_outputs.clear()
        empty = QTextBrowser()
        empty.setMarkdown("暂无任务输出。")
        self.task_outputs.addTab(empty, "任务输出")
        self.files_view.setPlainText("暂无文件。")

    def render_result(self, result: object) -> None:
        self.summary_view.setMarkdown(str(getattr(result, "concise_report", "")))
        self.full_view.setMarkdown(str(getattr(result, "full_report", "")))
        self.task_outputs.clear()
        for index, task_output in enumerate(getattr(result, "task_outputs", []) or [], start=1):
            title = task_output.get("agent") or f"Task {index}"
            view = QTextBrowser()
            view.setMarkdown(task_output.get("output", ""))
            self.task_outputs.addTab(view, f"{index}. {title}")
        run_dir = getattr(result, "run_dir", "")
        files = ["full_report.md", "summary_report.md", "run_metadata.md", "events.json"]
        self.files_view.setPlainText(str(run_dir) + "\n\n" + "\n".join(files))

    def load_config_editors(self) -> None:
        snapshot = self.config_service.load_snapshot()
        populate_table(self.agents_table, snapshot.agents)
        populate_table(self.tasks_table, snapshot.task_rows)
        self.agents_json.setPlainText(snapshot.agents_json)
        self.tasks_json.setPlainText(snapshot.tasks_json)
        self.expected_task_count = snapshot.enabled_task_count
        self.validation_view.setPlainText(snapshot.validation_text)

    def save_agents_table(self) -> None:
        self.save_agents_payload(table_rows(self.agents_table))

    def save_tasks_table(self) -> None:
        self.save_tasks_payload(normalize_task_rows(table_rows(self.tasks_table)))

    def save_agents_json(self) -> None:
        try:
            payload = self.config_service.parse_json_payload(self.agents_json.toPlainText(), "Agents")
        except ValueError as exc:
            QMessageBox.critical(self, "保存失败", str(exc))
            return
        self.save_agents_payload(payload)

    def save_tasks_json(self) -> None:
        try:
            payload = self.config_service.parse_json_payload(self.tasks_json.toPlainText(), "Tasks")
        except ValueError as exc:
            QMessageBox.critical(self, "保存失败", str(exc))
            return
        self.save_tasks_payload(payload)

    def save_agents_payload(self, payload: Any) -> None:
        try:
            self.config_service.save_agents_payload(payload)
            self.load_config_editors()
        except Exception as exc:
            QMessageBox.critical(self, "保存失败", str(exc))
            return
        QMessageBox.information(self, "已保存", "Agents 已保存。")

    def save_tasks_payload(self, payload: Any) -> None:
        try:
            self.config_service.save_tasks_payload(payload)
            self.load_config_editors()
        except Exception as exc:
            QMessageBox.critical(self, "保存失败", str(exc))
            return
        QMessageBox.information(self, "已保存", "Tasks 已保存。")

    def validate_current_config(self, *, show_message: bool = True) -> None:
        try:
            validation_text = self.config_service.validation_text()
        except Exception as exc:
            self.validation_view.setPlainText(f"配置有问题：{exc}")
            if show_message:
                QMessageBox.critical(self, "配置有问题", str(exc))
            return
        self.validation_view.setPlainText(validation_text)
        if show_message:
            QMessageBox.information(self, "配置检查", "配置检查通过。")

    def refresh_history(self) -> None:
        current = self.history_combo.currentData()
        self.history_combo.blockSignals(True)
        self.history_combo.clear()
        run_dirs = self.history_service.list_run_dirs()
        if not DEFAULT_OUTPUT_DIR.exists():
            self.history_combo.addItem("还没有输出目录", None)
        elif not run_dirs:
            self.history_combo.addItem("还没有历史运行", None)
        else:
            for path in run_dirs:
                self.history_combo.addItem(path.name, path)
            if current:
                index = self.history_combo.findData(current)
                if index >= 0:
                    self.history_combo.setCurrentIndex(index)
        self.history_combo.blockSignals(False)
        self.load_history_selection()

    def load_history_selection(self) -> None:
        selected = self.history_combo.currentData()
        history = self.history_service.load_selection(selected)
        self.history_summary.setMarkdown(history.summary)
        self.history_full.setMarkdown(history.full_report)
        self.history_metadata.setMarkdown(history.metadata)

    def closeEvent(self, event: Any) -> None:
        if self.worker and self.worker.isRunning():
            QMessageBox.warning(self, "工作流运行中", "请等待当前工作流完成后再关闭窗口。")
            event.ignore()
            return
        event.accept()


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Launch Multiagent Studio desktop GUI.")
    parser.add_argument("--smoke-test", action="store_true", help="Create the main window and exit automatically.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    if args.smoke_test:
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    load_project_env()
    app = QApplication(sys.argv[:1])
    app.setFont(QFont("Microsoft YaHei UI", 10))
    window = MultiagentStudio()
    window.show()
    if args.smoke_test:
        QTimer.singleShot(250, app.quit)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())

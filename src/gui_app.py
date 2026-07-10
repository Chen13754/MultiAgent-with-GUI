from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt, QThread, QTimer, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QStackedWidget,
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
from crewai_multiagent_demo.gui.widgets import fade_in, show_success_sheet
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
        except Exception as exc:  # pragma: no cover - exercised through GUI/manual use.
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
        self.load_config_editors()
        self.refresh_status_cards()
        self.refresh_history()

    def switch_page(self, index: int) -> None:
        if self.is_running():
            self.lock_hint.setText(RUN_LOCK_REASON)
            return
        self.pages.setCurrentIndex(index)
        fade_in(self.pages.currentWidget(), 170)
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
        if hasattr(self, "model_button_group"):
            for button in self.model_button_group.buttons():
                button.setEnabled(not locked)
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
            self.api_warning.setText(f"未检测到 API key。请先在根目录 .env 中配置 {required_keys}。")
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
        self.refresh_status_cards()

    def handle_completed(self, result: object) -> None:
        self.last_result = result
        self.run_status = RunStatus.SUCCEEDED
        self.progress.setValue(100)
        self.set_running_locked(False)
        self.agent_graph.set_completed()
        self.refresh_status_cards()
        self.render_result(result)
        self.refresh_history()
        self.output_tabs.setCurrentIndex(0)
        show_success_sheet(
            self,
            "运行成功",
            f"输出目录：{getattr(result, 'run_dir', '')}",
            "查看报告",
        )

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
        if hasattr(self, "status_widgets"):
            self.status_widgets["status"].set_value(status_label(current_status.value))
            self.status_widgets["status"].set_status(current_status.value)
            self.status_widgets["model"].set_value(str(model))
            self.status_widgets["tasks"].set_value(str(tasks))
            self.status_widgets["elapsed"].set_value(f"{elapsed:.1f}s" if elapsed is not None else "-")

        progress_value = self.progress.value() if hasattr(self, "progress") else 0
        active_agent = "等待启动"
        if self.events:
            active_agent = str(self.events[-1].get("agent") or event_label(str(self.events[-1].get("type", ""))))
        if hasattr(self, "workflow_card"):
            self.workflow_card.set_metrics(
                model=str(model),
                status=status_label(current_status.value),
                tasks=str(tasks or self.expected_task_count),
                elapsed=f"{elapsed:.1f}s" if elapsed is not None else "-",
                progress=progress_value,
                active_agent=active_agent,
            )
        if hasattr(self, "orchestration_badge"):
            badge_status = {
                RunStatus.RUNNING.value: "warning",
                RunStatus.SUCCEEDED.value: "success",
                RunStatus.FAILED.value: "danger",
            }.get(current_status.value, "neutral")
            self.orchestration_badge.setText(status_label(current_status.value))
            self.orchestration_badge.set_status(badge_status)

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
            text += "\n" + " / ".join(details)
        self.event_list.add_motion_item(text, str(event.get("type", "")))

    def clear_result_views(self) -> None:
        self.summary_view.setMarkdown("暂无运行结果。")
        self.full_view.setMarkdown("暂无运行结果。")
        self.task_outputs_view.setMarkdown("暂无任务输出。")
        self.files_view.setPlainText("暂无文件。")

    def render_result(self, result: object) -> None:
        self.summary_view.setMarkdown(str(getattr(result, "concise_report", "")))
        self.full_view.setMarkdown(str(getattr(result, "full_report", "")))
        task_sections = []
        for index, task_output in enumerate(getattr(result, "task_outputs", []) or [], start=1):
            title = task_output.get("agent") or f"Task {index}"
            task_sections.append(f"## {index}. {title}\n\n{task_output.get('output', '')}")
        self.task_outputs_view.setMarkdown("\n\n---\n\n".join(task_sections) if task_sections else "暂无任务输出。")
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
        self.validation_text.setPlainText(snapshot.validation_text)
        self.agents_summary_value.setText(str(len(snapshot.agents)))
        self.tasks_summary_value.setText(str(len(snapshot.task_rows)))
        self.config_validation_badge.setText("待检查")
        self.config_validation_badge.set_status("neutral")

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
        show_success_sheet(self, "已保存", "Agents 配置已保存。", "完成")

    def save_tasks_payload(self, payload: Any) -> None:
        try:
            self.config_service.save_tasks_payload(payload)
            self.load_config_editors()
        except Exception as exc:
            QMessageBox.critical(self, "保存失败", str(exc))
            return
        show_success_sheet(self, "已保存", "Tasks 配置已保存。", "完成")

    def validate_current_config(self, *, show_message: bool = True) -> None:
        try:
            validation_text = self.config_service.validation_text()
        except Exception as exc:
            self.validation_text.setPlainText(f"配置有问题：{exc}")
            self.config_validation_badge.setText("检查失败")
            self.config_validation_badge.set_status("danger")
            if show_message:
                QMessageBox.critical(self, "配置有问题", str(exc))
            return
        self.validation_text.setPlainText(validation_text)
        self.config_validation_badge.setText("检查通过")
        self.config_validation_badge.set_status("success")
        if show_message:
            show_success_sheet(self, "配置检查通过", "Agents 和 Tasks 可以正常运行。", "完成")

    def refresh_history(self) -> None:
        current = self.selected_history_dir()
        self.history_list.blockSignals(True)
        self.history_list.clear()
        run_dirs = self.history_service.list_run_dirs()
        if not DEFAULT_OUTPUT_DIR.exists():
            item = QListWidgetItem("还没有输出目录")
            item.setData(Qt.ItemDataRole.UserRole, None)
            self.history_list.addItem(item)
        elif not run_dirs:
            item = QListWidgetItem("还没有历史运行")
            item.setData(Qt.ItemDataRole.UserRole, None)
            self.history_list.addItem(item)
        else:
            for path in run_dirs:
                item = QListWidgetItem(self.history_item_label(path))
                item.setData(Qt.ItemDataRole.UserRole, path)
                self.history_list.addItem(item)
            selected_row = 0
            if current:
                for index in range(self.history_list.count()):
                    if self.history_list.item(index).data(Qt.ItemDataRole.UserRole) == current:
                        selected_row = index
                        break
            self.history_list.setCurrentRow(selected_row)
        self.history_list.blockSignals(False)
        self.load_history_selection()

    def load_history_selection(self, *_args: object) -> None:
        selected = self.selected_history_dir()
        history = self.history_service.load_selection(selected)
        self.history_summary.setMarkdown(history.summary)
        self.history_full.setMarkdown(history.full_report)
        self.history_metadata.setMarkdown(history.metadata)

    def selected_history_dir(self) -> Path | None:
        item = self.history_list.currentItem() if hasattr(self, "history_list") else None
        selected = item.data(Qt.ItemDataRole.UserRole) if item else None
        return selected if isinstance(selected, Path) else None

    def history_item_label(self, path: Path) -> str:
        metadata = path / "run_metadata.md"
        model = "-"
        elapsed = "-"
        if metadata.exists():
            text = metadata.read_text(encoding="utf-8", errors="ignore")
            for line in text.splitlines():
                lowered = line.lower()
                if "model" in lowered and model == "-":
                    model = line.split(":", 1)[-1].strip() if ":" in line else line.strip()
                if "elapsed" in lowered and elapsed == "-":
                    elapsed = line.split(":", 1)[-1].strip() if ":" in line else line.strip()
        return f"{path.name}\n模型 {model} · 耗时 {elapsed}"

    def reset_workspace(self) -> None:
        self.events = []
        self.last_result = None
        self.progress.setValue(0)
        self.run_status = RunStatus.IDLE
        self.reset_events()
        self.clear_result_views()
        self.refresh_status_cards()

    def open_current_output_dir(self) -> None:
        run_dir = getattr(self.last_result, "run_dir", None)
        if run_dir and Path(run_dir).exists():
            os.startfile(str(run_dir))
            return
        if DEFAULT_OUTPUT_DIR.exists():
            os.startfile(str(DEFAULT_OUTPUT_DIR))
            return
        QMessageBox.information(self, "输出目录", "还没有可打开的输出目录。")

    def open_selected_history_dir(self) -> None:
        selected = self.selected_history_dir()
        if selected and selected.exists():
            os.startfile(str(selected))
            return
        QMessageBox.information(self, "历史输出", "请先选择一条历史记录。")

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
    if args.smoke_test or os.getenv("MULTIAGENT_GUI_SMOKE") == "1":
        QTimer.singleShot(250, app.quit)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())

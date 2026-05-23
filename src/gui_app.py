from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from PySide6.QtCore import QThread, QTimer, Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextBrowser,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

sys.path.insert(0, str(Path(__file__).resolve().parent))

from crewai_multiagent_demo.config.loader import ConfigLoader
from crewai_multiagent_demo.config.schema import (
    config_to_dicts,
    parse_agent_config,
    parse_task_config,
)
from crewai_multiagent_demo.config.validation import validate_configs
from crewai_multiagent_demo.core.runner import DEFAULT_TOPIC, run_workflow
from crewai_multiagent_demo.gui.state import (
    RUN_LOCK_REASON,
    RunStatus,
    event_label,
    normalize_status,
    normalize_task_rows,
    progress_from_events,
    status_label,
    task_rows_for_editor,
)
from crewai_multiagent_demo.gui.styles import APP_QSS
from crewai_multiagent_demo.llm.model_registry import MODEL_REGISTRY
from crewai_multiagent_demo.utils.environment import has_api_key, load_project_env, loaded_env_file
from crewai_multiagent_demo.utils.paths import DEFAULT_CONFIG_DIR, DEFAULT_OUTPUT_DIR, PROJECT_ROOT


AGENTS_FILE = DEFAULT_CONFIG_DIR / "agents.json"
TASKS_FILE = DEFAULT_CONFIG_DIR / "tasks.json"


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


def make_card(object_name: str = "Card") -> QFrame:
    frame = QFrame()
    frame.setObjectName(object_name)
    frame.setFrameShape(QFrame.Shape.StyledPanel)
    return frame


def label(text: str, object_name: str | None = None) -> QLabel:
    widget = QLabel(text)
    widget.setWordWrap(True)
    if object_name:
        widget.setObjectName(object_name)
    return widget


def read_text_or_empty(path: Path) -> str:
    if not path.exists():
        return "无"
    return path.read_text(encoding="utf-8")


class MultiagentStudio(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.run_status = RunStatus.IDLE
        self.events: list[dict[str, Any]] = []
        self.last_result: Any = None
        self.worker: RunWorker | None = None

        self.setWindowTitle("Multiagent Studio")
        self.resize(1220, 780)
        self.setMinimumSize(960, 640)

        root = QWidget()
        root.setObjectName("Root")
        self.setCentralWidget(root)
        shell = QHBoxLayout(root)
        shell.setContentsMargins(0, 0, 0, 0)
        shell.setSpacing(0)

        shell.addWidget(self.build_sidebar())

        self.pages = QStackedWidget()
        self.run_page = self.build_run_page()
        self.config_page = self.build_config_page()
        self.history_page = self.build_history_page()
        self.pages.addWidget(self.run_page)
        self.pages.addWidget(self.config_page)
        self.pages.addWidget(self.history_page)
        shell.addWidget(self.pages, 1)

        self.setStyleSheet(APP_QSS)
        self.refresh_status_cards()
        self.refresh_history()

    def build_sidebar(self) -> QFrame:
        sidebar = make_card("Sidebar")
        sidebar.setFixedWidth(220)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        layout.addWidget(label("Multiagent Studio", "AppTitle"))
        layout.addWidget(label("桌面工作台", "Muted"))

        self.nav_buttons: list[QPushButton] = []
        for index, name in enumerate(("运行", "配置", "历史")):
            button = QPushButton(name)
            button.setObjectName("NavButton")
            button.setCheckable(True)
            button.clicked.connect(lambda checked=False, page=index: self.switch_page(page))
            layout.addWidget(button)
            self.nav_buttons.append(button)
        self.nav_buttons[0].setChecked(True)

        layout.addStretch(1)
        self.lock_hint = label("", "Muted")
        layout.addWidget(self.lock_hint)
        return sidebar

    def switch_page(self, index: int) -> None:
        if self.is_running():
            self.lock_hint.setText(RUN_LOCK_REASON)
            return
        self.pages.setCurrentIndex(index)
        for button_index, button in enumerate(self.nav_buttons):
            button.setChecked(button_index == index)
        if index == 2:
            self.refresh_history()

    def build_run_page(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        page = QWidget()
        scroll.setWidget(page)
        layout = QVBoxLayout(page)
        layout.setContentsMargins(24, 20, 24, 24)
        layout.setSpacing(14)

        hero = make_card("Hero")
        hero_layout = QVBoxLayout(hero)
        hero_layout.setContentsMargins(18, 16, 18, 16)
        hero_layout.addWidget(label("MULTIAGENT STUDIO", "HeroKicker"))
        hero_layout.addWidget(label("多 Agent 工作台", "HeroTitle"))
        hero_layout.addWidget(label("用桌面 GUI 启动工作流，实时查看任务进度、事件流和结构化输出。", "Muted"))
        layout.addWidget(hero)

        self.status_grid = QGridLayout()
        self.status_grid.setSpacing(10)
        self.status_widgets: dict[str, QLabel] = {}
        for col, (key, title) in enumerate((("status", "状态"), ("model", "模型"), ("tasks", "任务数"), ("elapsed", "耗时"))):
            card = make_card("StatusCard")
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(14, 12, 14, 12)
            card_layout.addWidget(label(title, "StatusLabel"))
            value = label("-", "StatusValue")
            if key == "status":
                value.setObjectName("StatusBadge")
            self.status_widgets[key] = value
            card_layout.addWidget(value)
            self.status_grid.addWidget(card, 0, col)
        layout.addLayout(self.status_grid)

        body_widget = QWidget()
        body_widget.setMinimumHeight(390)
        body = QHBoxLayout(body_widget)
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(14)
        body.addWidget(self.build_run_controls(), 1)
        body.addWidget(self.build_event_panel(), 2)
        layout.addWidget(body_widget)

        output_card = make_card()
        output_layout = QVBoxLayout(output_card)
        output_layout.setContentsMargins(16, 14, 16, 16)
        output_layout.addWidget(label("OUTPUTS", "Kicker"))
        output_layout.addWidget(label("输出", "AppTitle"))

        self.output_tabs = QTabWidget()
        self.summary_view = QTextBrowser()
        self.full_view = QTextBrowser()
        self.task_outputs = QTabWidget()
        self.files_view = QTextBrowser()
        for browser in (self.summary_view, self.full_view, self.files_view):
            browser.setOpenExternalLinks(True)
        self.output_tabs.addTab(self.summary_view, "精简报告")
        self.output_tabs.addTab(self.full_view, "完整报告")
        self.output_tabs.addTab(self.task_outputs, "任务输出")
        self.output_tabs.addTab(self.files_view, "文件")
        output_layout.addWidget(self.output_tabs)
        layout.addWidget(output_card)
        layout.addStretch(1)
        self.clear_result_views()
        return scroll

    def build_run_controls(self) -> QFrame:
        card = make_card()
        card.setMinimumWidth(310)
        card.setMinimumHeight(390)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 18)
        layout.setSpacing(9)
        layout.addWidget(label("CONTROL", "Kicker"))
        layout.addWidget(label("运行设置", "AppTitle"))

        layout.addWidget(label("模型档位", "StatusLabel"))
        self.model_combo = QComboBox()
        self.model_combo.addItems(list(MODEL_REGISTRY.aliases))
        self.model_combo.setCurrentText(MODEL_REGISTRY.default_alias())
        self.model_combo.setMinimumHeight(34)
        layout.addWidget(self.model_combo)

        layout.addWidget(label("任务主题", "StatusLabel"))
        self.topic_edit = QTextEdit()
        self.topic_edit.setMinimumHeight(118)
        self.topic_edit.setMaximumHeight(138)
        self.topic_edit.setPlainText(DEFAULT_TOPIC)
        layout.addWidget(self.topic_edit)

        self.api_warning = label("", "WarningLabel")
        self.api_warning.setMinimumHeight(38)
        self.api_warning.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self.api_warning)

        self.run_button = QPushButton("运行工作流")
        self.run_button.setObjectName("PrimaryButton")
        self.run_button.setMinimumHeight(38)
        self.run_button.clicked.connect(self.start_run)
        layout.addWidget(self.run_button)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setMinimumHeight(22)
        self.progress.setMaximumHeight(22)
        layout.addSpacing(2)
        layout.addWidget(self.progress)
        layout.addStretch(1)
        return card

    def build_event_panel(self) -> QFrame:
        card = make_card()
        card.setMinimumHeight(390)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 14, 16, 16)
        layout.setSpacing(10)
        layout.addWidget(label("LIVE TIMELINE", "Kicker"))
        layout.addWidget(label("运行过程", "AppTitle"))
        self.event_list = QListWidget()
        layout.addWidget(self.event_list)
        self.reset_events()
        return card

    def build_config_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(24, 20, 24, 24)
        layout.setSpacing(14)
        layout.addWidget(label("配置中心", "HeroTitle"))
        layout.addWidget(label("编辑 agents/tasks，保存前自动校验配置。", "Muted"))

        self.config_tabs = QTabWidget()
        self.agents_table = self.build_table(("id", "role", "goal", "backstory", "enabled"))
        self.tasks_table = self.build_table(("id", "name", "description", "expected_output", "agent_id", "context_task_ids", "enabled"))
        self.agents_json = QPlainTextEdit()
        self.tasks_json = QPlainTextEdit()
        self.validation_view = QTextBrowser()

        self.config_tabs.addTab(self.wrap_editor(self.agents_table, self.save_agents_table), "Agents")
        self.config_tabs.addTab(self.wrap_editor(self.tasks_table, self.save_tasks_table), "Tasks")
        self.config_tabs.addTab(self.build_json_tab(), "JSON 高级编辑")
        self.config_tabs.addTab(self.build_validation_tab(), "配置检查")
        layout.addWidget(self.config_tabs, 1)
        self.load_config_editors()
        return page

    def build_table(self, columns: tuple[str, ...]) -> QTableWidget:
        table = QTableWidget()
        table.setColumnCount(len(columns))
        table.setHorizontalHeaderLabels(columns)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        table.verticalHeader().setVisible(False)
        table.setAlternatingRowColors(True)
        return table

    def wrap_editor(self, table: QTableWidget, save_callback: Any) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.addWidget(table)
        controls = QHBoxLayout()
        add_button = QPushButton("新增行")
        remove_button = QPushButton("删除选中行")
        save_button = QPushButton("保存")
        save_button.setObjectName("PrimaryButton")
        add_button.clicked.connect(lambda: table.insertRow(table.rowCount()))
        remove_button.clicked.connect(lambda: self.remove_selected_rows(table))
        save_button.clicked.connect(save_callback)
        controls.addWidget(add_button)
        controls.addWidget(remove_button)
        controls.addStretch(1)
        controls.addWidget(save_button)
        layout.addLayout(controls)
        return page

    def build_json_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(8, 8, 8, 8)
        editors = QHBoxLayout()
        editors.addWidget(self.wrap_json_editor("Agents JSON", self.agents_json, self.save_agents_json))
        editors.addWidget(self.wrap_json_editor("Tasks JSON", self.tasks_json, self.save_tasks_json))
        layout.addLayout(editors)
        reload_button = QPushButton("重新读取配置")
        reload_button.clicked.connect(self.load_config_editors)
        layout.addWidget(reload_button, alignment=Qt.AlignmentFlag.AlignRight)
        return page

    def wrap_json_editor(self, title: str, editor: QPlainTextEdit, save_callback: Any) -> QFrame:
        card = make_card()
        layout = QVBoxLayout(card)
        layout.addWidget(label(title, "AppTitle"))
        layout.addWidget(editor)
        save_button = QPushButton(f"保存 {title.split()[0]}")
        save_button.setObjectName("PrimaryButton")
        save_button.clicked.connect(save_callback)
        layout.addWidget(save_button)
        return card

    def build_validation_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(8, 8, 8, 8)
        check_button = QPushButton("检查配置")
        check_button.setObjectName("PrimaryButton")
        check_button.clicked.connect(self.validate_current_config)
        layout.addWidget(check_button, alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self.validation_view, 1)
        return page

    def build_history_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(24, 20, 24, 24)
        layout.setSpacing(14)
        layout.addWidget(label("历史输出", "HeroTitle"))
        layout.addWidget(label("浏览 outputs 下已有运行记录。", "Muted"))
        self.history_combo = QComboBox()
        self.history_combo.currentIndexChanged.connect(self.load_history_selection)
        layout.addWidget(self.history_combo)

        self.history_tabs = QTabWidget()
        self.history_summary = QTextBrowser()
        self.history_full = QTextBrowser()
        self.history_metadata = QTextBrowser()
        self.history_tabs.addTab(self.history_summary, "精简报告")
        self.history_tabs.addTab(self.history_full, "完整报告")
        self.history_tabs.addTab(self.history_metadata, "元数据")
        layout.addWidget(self.history_tabs, 1)
        return page

    def is_running(self) -> bool:
        return self.run_status == RunStatus.RUNNING

    def set_running_locked(self, locked: bool) -> None:
        for button in self.nav_buttons:
            button.setEnabled(not locked)
        self.config_tabs.setEnabled(not locked)
        self.run_button.setEnabled(not locked)
        self.model_combo.setEnabled(not locked)
        self.topic_edit.setEnabled(not locked)
        self.lock_hint.setText(RUN_LOCK_REASON if locked else "")
        self.run_button.setText("工作流运行中" if locked else "运行工作流")

    def start_run(self) -> None:
        if self.is_running():
            return
        if not has_api_key():
            self.run_status = RunStatus.FAILED
            self.api_warning.setText("未检测到 API key。请先在 .env 中配置 DEEPSEEK_API_KEY。")
            self.refresh_status_cards()
            QMessageBox.warning(self, "缺少 API key", "缺少 API key，无法运行。")
            return

        self.events = []
        self.last_result = None
        self.reset_events()
        self.clear_result_views()
        self.progress.setValue(5)
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
        self.progress.setValue(progress_from_events(self.events))
        self.add_event_item(event)

    def handle_completed(self, result: object) -> None:
        self.last_result = result
        self.run_status = RunStatus.SUCCEEDED
        self.progress.setValue(100)
        self.set_running_locked(False)
        self.refresh_status_cards()
        self.render_result(result)
        self.refresh_history()
        QMessageBox.information(self, "运行完成", f"运行完成，输出目录：{getattr(result, 'run_dir', '')}")

    def handle_failed(self, error: str) -> None:
        self.run_status = RunStatus.FAILED
        self.progress.setValue(0)
        self.set_running_locked(False)
        self.refresh_status_cards()
        QMessageBox.critical(self, "运行失败", error)

    def refresh_status_cards(self) -> None:
        model = self.model_combo.currentText() if hasattr(self, "model_combo") else MODEL_REGISTRY.default_alias()
        if self.last_result is not None:
            model = getattr(self.last_result, "model_alias", model)
        tasks = len(getattr(self.last_result, "task_outputs", []) or [])
        elapsed = getattr(self.last_result, "elapsed_seconds", None)
        self.status_widgets["status"].setText(status_label(self.run_status))
        self.status_widgets["model"].setText(str(model))
        self.status_widgets["tasks"].setText(str(tasks))
        self.status_widgets["elapsed"].setText(f"{elapsed:.1f}s" if elapsed is not None else "-")
        env_hint = loaded_env_file() or Path(os.getenv("MULTIAGENT_ENV_FILE") or PROJECT_ROOT / ".env")
        self.api_warning.setText(
            ""
            if has_api_key()
            else f"未检测到 API key。请检查 {env_hint} 中的 DEEPSEEK_API_KEY。"
        )

    def reset_events(self) -> None:
        self.event_list.clear()
        self.event_list.addItem("运行后这里会显示公开事件、任务完成状态和输出节点。")

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
        self.event_list.addItem(QListWidgetItem(text))
        self.event_list.scrollToBottom()

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
        agents = ConfigLoader.load_json_file(AGENTS_FILE)
        tasks = ConfigLoader.load_json_file(TASKS_FILE)
        self.populate_table(self.agents_table, agents)
        self.populate_table(self.tasks_table, task_rows_for_editor(tasks))
        self.agents_json.setPlainText(json.dumps(agents, ensure_ascii=False, indent=2))
        self.tasks_json.setPlainText(json.dumps(tasks, ensure_ascii=False, indent=2))
        self.validate_current_config(show_message=False)

    def populate_table(self, table: QTableWidget, rows: list[dict[str, Any]]) -> None:
        table.setRowCount(len(rows))
        columns = [table.horizontalHeaderItem(col).text() for col in range(table.columnCount())]
        for row_index, row in enumerate(rows):
            for col_index, key in enumerate(columns):
                value = row.get(key, "")
                item = QTableWidgetItem("true" if value is True else "false" if value is False else str(value))
                table.setItem(row_index, col_index, item)

    def table_rows(self, table: QTableWidget) -> list[dict[str, Any]]:
        columns = [table.horizontalHeaderItem(col).text() for col in range(table.columnCount())]
        rows: list[dict[str, Any]] = []
        for row_index in range(table.rowCount()):
            row: dict[str, Any] = {}
            if all(not (table.item(row_index, col) and table.item(row_index, col).text().strip()) for col in range(table.columnCount())):
                continue
            for col_index, key in enumerate(columns):
                item = table.item(row_index, col_index)
                value = item.text().strip() if item else ""
                if key == "enabled":
                    row[key] = value.lower() not in {"false", "0", "no", "否"}
                else:
                    row[key] = value
            rows.append(row)
        return rows

    def remove_selected_rows(self, table: QTableWidget) -> None:
        rows = sorted({index.row() for index in table.selectedIndexes()}, reverse=True)
        for row in rows:
            table.removeRow(row)

    def save_agents_table(self) -> None:
        self.save_agents_payload(self.table_rows(self.agents_table))

    def save_tasks_table(self) -> None:
        self.save_tasks_payload(normalize_task_rows(self.table_rows(self.tasks_table)))

    def save_agents_json(self) -> None:
        try:
            payload = json.loads(self.agents_json.toPlainText())
        except json.JSONDecodeError as exc:
            QMessageBox.critical(self, "保存失败", f"Agents JSON 格式错误：{exc}")
            return
        self.save_agents_payload(payload)

    def save_tasks_json(self) -> None:
        try:
            payload = json.loads(self.tasks_json.toPlainText())
        except json.JSONDecodeError as exc:
            QMessageBox.critical(self, "保存失败", f"Tasks JSON 格式错误：{exc}")
            return
        self.save_tasks_payload(payload)

    def save_agents_payload(self, payload: Any) -> None:
        try:
            if not isinstance(payload, list):
                raise ValueError("agents 顶层必须是数组")
            agents = [parse_agent_config(item, index) for index, item in enumerate(payload)]
            tasks = ConfigLoader(DEFAULT_CONFIG_DIR).load_tasks()
            validate_configs(agents, tasks)
            ConfigLoader.save_json_file(AGENTS_FILE, payload)
            self.load_config_editors()
        except Exception as exc:
            QMessageBox.critical(self, "保存失败", str(exc))
            return
        QMessageBox.information(self, "已保存", "Agents 已保存。")

    def save_tasks_payload(self, payload: Any) -> None:
        try:
            if not isinstance(payload, list):
                raise ValueError("tasks 顶层必须是数组")
            agents = ConfigLoader(DEFAULT_CONFIG_DIR).load_agents()
            tasks = [parse_task_config(item, index) for index, item in enumerate(payload)]
            validate_configs(agents, tasks)
            ConfigLoader.save_json_file(TASKS_FILE, payload)
            self.load_config_editors()
        except Exception as exc:
            QMessageBox.critical(self, "保存失败", str(exc))
            return
        QMessageBox.information(self, "已保存", "Tasks 已保存。")

    def validate_current_config(self, *, show_message: bool = True) -> None:
        try:
            config = ConfigLoader(DEFAULT_CONFIG_DIR).load(validate=True)
        except Exception as exc:
            self.validation_view.setPlainText(f"配置有问题：{exc}")
            if show_message:
                QMessageBox.critical(self, "配置有问题", str(exc))
            return
        self.validation_view.setPlainText(
            "配置检查通过。\n\nAgents:\n"
            + json.dumps(config_to_dicts(config.agents), ensure_ascii=False, indent=2)
            + "\n\nTasks:\n"
            + json.dumps(config_to_dicts(config.tasks), ensure_ascii=False, indent=2)
        )
        if show_message:
            QMessageBox.information(self, "配置检查", "配置检查通过。")

    def refresh_history(self) -> None:
        current = self.history_combo.currentData()
        self.history_combo.blockSignals(True)
        self.history_combo.clear()
        if not DEFAULT_OUTPUT_DIR.exists():
            self.history_combo.addItem("还没有输出目录", None)
        else:
            run_dirs = sorted(
                [path for path in DEFAULT_OUTPUT_DIR.iterdir() if path.is_dir()],
                key=lambda path: path.name,
                reverse=True,
            )
            if not run_dirs:
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
        if not selected:
            self.history_summary.setPlainText("无")
            self.history_full.setPlainText("无")
            self.history_metadata.setPlainText("无")
            return
        self.history_summary.setMarkdown(read_text_or_empty(selected / "summary_report.md"))
        self.history_full.setMarkdown(read_text_or_empty(selected / "full_report.md"))
        self.history_metadata.setMarkdown(read_text_or_empty(selected / "run_metadata.md"))

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

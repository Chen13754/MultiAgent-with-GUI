from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextBrowser,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from crewai_multiagent_demo.core.runner import DEFAULT_TOPIC
from crewai_multiagent_demo.gui.widgets import (
    AnimatedAgentGraph,
    GlassPanel,
    MetricCard,
    MotionEventList,
    PulseButton,
)
from crewai_multiagent_demo.llm.model_registry import MODEL_REGISTRY


def make_card(object_name: str = "GlassPanel") -> QFrame:
    return GlassPanel(object_name)


def label(text: str, object_name: str | None = None) -> QLabel:
    widget = QLabel(text)
    widget.setWordWrap(True)
    if object_name:
        widget.setObjectName(object_name)
    return widget


def build_sidebar(controller: Any) -> QFrame:
    sidebar = make_card("Sidebar")
    sidebar.setFixedWidth(232)
    layout = QVBoxLayout(sidebar)
    layout.setContentsMargins(18, 20, 18, 18)
    layout.setSpacing(10)

    layout.addWidget(label("Multiagent Studio", "BrandTitle"))
    layout.addWidget(label("多 Agent 工作流控制台", "Muted"))
    layout.addSpacing(8)

    controller.nav_buttons = []
    for index, name in enumerate(("运行", "配置", "历史")):
        button = QPushButton(name)
        button.setObjectName("NavButton")
        button.setCheckable(True)
        button.clicked.connect(lambda checked=False, page=index: controller.switch_page(page))
        layout.addWidget(button)
        controller.nav_buttons.append(button)
    controller.nav_buttons[0].setChecked(True)

    layout.addStretch(1)
    controller.lock_hint = label("", "Muted")
    layout.addWidget(controller.lock_hint)
    return sidebar


def build_run_page(controller: Any) -> QWidget:
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QFrame.Shape.NoFrame)
    page = QWidget()
    scroll.setWidget(page)
    layout = QVBoxLayout(page)
    layout.setContentsMargins(24, 20, 24, 24)
    layout.setSpacing(14)

    header = make_card("CommandHeader")
    header_layout = QHBoxLayout(header)
    header_layout.setContentsMargins(18, 14, 18, 14)
    header_layout.setSpacing(16)
    title_box = QVBoxLayout()
    title_box.setSpacing(3)
    title_box.addWidget(label("MULTIAGENT STUDIO", "Kicker"))
    title_box.addWidget(label("工作流控制台", "PageTitle"))
    title_box.addWidget(label("输入主题，启动多 Agent 协作，并在实时编排视图中观察任务流转。", "Muted"))
    header_layout.addLayout(title_box, 1)

    controller.status_widgets = {}
    for key, title in (("status", "状态"), ("model", "模型"), ("tasks", "任务"), ("elapsed", "耗时")):
        card = MetricCard(title)
        controller.status_widgets[key] = card
        header_layout.addWidget(card)
    layout.addWidget(header)

    body_widget = QWidget()
    body_widget.setMinimumHeight(380)
    body = QHBoxLayout(body_widget)
    body.setContentsMargins(0, 0, 0, 0)
    body.setSpacing(14)
    body.addWidget(build_run_controls(controller), 1)
    body.addWidget(build_event_panel(controller), 2)
    layout.addWidget(body_widget)

    output_card = make_card("OutputPanel")
    output_layout = QVBoxLayout(output_card)
    output_layout.setContentsMargins(16, 14, 16, 16)
    output_layout.setSpacing(10)
    output_layout.addWidget(label("OUTPUTS", "Kicker"))
    output_layout.addWidget(label("输出报告", "SectionTitle"))

    controller.output_tabs = QTabWidget()
    controller.summary_view = QTextBrowser()
    controller.full_view = QTextBrowser()
    controller.task_outputs = QTabWidget()
    controller.files_view = QTextBrowser()
    for browser in (controller.summary_view, controller.full_view, controller.files_view):
        browser.setOpenExternalLinks(True)
    controller.output_tabs.addTab(controller.summary_view, "精简报告")
    controller.output_tabs.addTab(controller.full_view, "完整报告")
    controller.output_tabs.addTab(controller.task_outputs, "任务输出")
    controller.output_tabs.addTab(controller.files_view, "文件")
    output_layout.addWidget(controller.output_tabs)
    layout.addWidget(output_card)
    layout.addStretch(1)
    controller.clear_result_views()
    return scroll


def build_run_controls(controller: Any) -> QFrame:
    card = make_card("ControlPanel")
    card.setMinimumWidth(310)
    card.setMinimumHeight(380)
    layout = QVBoxLayout(card)
    layout.setContentsMargins(18, 16, 18, 18)
    layout.setSpacing(10)
    layout.addWidget(label("CONTROL", "Kicker"))
    layout.addWidget(label("运行设置", "SectionTitle"))

    layout.addWidget(label("模型档位", "StatusLabel"))
    controller.model_combo = QComboBox()
    controller.model_combo.addItems(list(MODEL_REGISTRY.aliases))
    controller.model_combo.setCurrentText(MODEL_REGISTRY.default_alias())
    controller.model_combo.setMinimumHeight(34)
    layout.addWidget(controller.model_combo)

    layout.addWidget(label("任务主题", "StatusLabel"))
    controller.topic_edit = QTextEdit()
    controller.topic_edit.setMinimumHeight(118)
    controller.topic_edit.setMaximumHeight(138)
    controller.topic_edit.setPlainText(DEFAULT_TOPIC)
    layout.addWidget(controller.topic_edit)

    controller.api_warning = label("", "WarningLabel")
    controller.api_warning.setMinimumHeight(38)
    controller.api_warning.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
    layout.addWidget(controller.api_warning)

    controller.run_button = PulseButton("运行工作流")
    controller.run_button.setObjectName("PrimaryButton")
    controller.run_button.setMinimumHeight(38)
    controller.run_button.clicked.connect(controller.start_run)
    layout.addWidget(controller.run_button)

    controller.progress = QProgressBar()
    controller.progress.setRange(0, 100)
    controller.progress.setValue(0)
    controller.progress.setMinimumHeight(22)
    controller.progress.setMaximumHeight(22)
    layout.addSpacing(2)
    layout.addWidget(controller.progress)
    layout.addStretch(1)
    return card


def build_event_panel(controller: Any) -> QFrame:
    card = make_card("GlassPanel")
    card.setMinimumHeight(380)
    layout = QVBoxLayout(card)
    layout.setContentsMargins(16, 14, 16, 16)
    layout.setSpacing(10)
    layout.addWidget(label("LIVE ORCHESTRATION", "Kicker"))
    layout.addWidget(label("实时编排", "SectionTitle"))
    controller.agent_graph = AnimatedAgentGraph()
    layout.addWidget(controller.agent_graph, 2)
    layout.addWidget(label("事件流", "Kicker"))
    controller.event_list = MotionEventList()
    controller.event_list.setMinimumHeight(104)
    controller.event_list.setMaximumHeight(130)
    layout.addWidget(controller.event_list, 1)
    controller.reset_events()
    return card


def build_config_page(controller: Any) -> QWidget:
    page = QWidget()
    layout = QVBoxLayout(page)
    layout.setContentsMargins(24, 20, 24, 24)
    layout.setSpacing(14)
    header = make_card("ConfigHeader")
    header_layout = QVBoxLayout(header)
    header_layout.setContentsMargins(18, 14, 18, 14)
    header_layout.setSpacing(3)
    header_layout.addWidget(label("CONFIGURATION", "Kicker"))
    header_layout.addWidget(label("配置中心", "PageTitle"))
    header_layout.addWidget(label("编辑 agents/tasks，保存前自动校验配置。", "Muted"))
    layout.addWidget(header)

    controller.config_tabs = QTabWidget()
    controller.agents_table = build_table(("id", "role", "goal", "backstory", "enabled"))
    controller.tasks_table = build_table(("id", "name", "description", "expected_output", "agent_id", "context_task_ids", "enabled"))
    controller.agents_json = QPlainTextEdit()
    controller.tasks_json = QPlainTextEdit()
    controller.validation_view = QTextBrowser()

    controller.config_tabs.addTab(wrap_editor(controller.agents_table, controller.save_agents_table), "Agents")
    controller.config_tabs.addTab(wrap_editor(controller.tasks_table, controller.save_tasks_table), "Tasks")
    controller.config_tabs.addTab(build_json_tab(controller), "JSON 高级编辑")
    controller.config_tabs.addTab(build_validation_tab(controller), "配置检查")
    layout.addWidget(controller.config_tabs, 1)
    controller.load_config_editors()
    return page


def build_table(columns: tuple[str, ...]) -> QTableWidget:
    table = QTableWidget()
    table.setColumnCount(len(columns))
    table.setHorizontalHeaderLabels(columns)
    table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
    table.verticalHeader().setVisible(False)
    table.setAlternatingRowColors(True)
    return table


def wrap_editor(table: QTableWidget, save_callback: Any) -> QWidget:
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
    remove_button.clicked.connect(lambda: remove_selected_rows(table))
    save_button.clicked.connect(save_callback)
    controls.addWidget(add_button)
    controls.addWidget(remove_button)
    controls.addStretch(1)
    controls.addWidget(save_button)
    layout.addLayout(controls)
    return page


def build_json_tab(controller: Any) -> QWidget:
    page = QWidget()
    layout = QVBoxLayout(page)
    layout.setContentsMargins(8, 8, 8, 8)
    editors = QHBoxLayout()
    editors.addWidget(wrap_json_editor("Agents JSON", controller.agents_json, controller.save_agents_json))
    editors.addWidget(wrap_json_editor("Tasks JSON", controller.tasks_json, controller.save_tasks_json))
    layout.addLayout(editors)
    reload_button = QPushButton("重新读取配置")
    reload_button.clicked.connect(controller.load_config_editors)
    layout.addWidget(reload_button, alignment=Qt.AlignmentFlag.AlignRight)
    return page


def wrap_json_editor(title: str, editor: QPlainTextEdit, save_callback: Any) -> QFrame:
    card = make_card("GlassPanel")
    layout = QVBoxLayout(card)
    layout.addWidget(label(title, "SectionTitle"))
    layout.addWidget(editor)
    save_button = QPushButton(f"保存 {title.split()[0]}")
    save_button.setObjectName("PrimaryButton")
    save_button.clicked.connect(save_callback)
    layout.addWidget(save_button)
    return card


def build_validation_tab(controller: Any) -> QWidget:
    page = QWidget()
    layout = QVBoxLayout(page)
    layout.setContentsMargins(8, 8, 8, 8)
    check_button = QPushButton("检查配置")
    check_button.setObjectName("PrimaryButton")
    check_button.clicked.connect(controller.validate_current_config)
    layout.addWidget(check_button, alignment=Qt.AlignmentFlag.AlignLeft)
    layout.addWidget(controller.validation_view, 1)
    return page


def build_history_page(controller: Any) -> QWidget:
    page = QWidget()
    layout = QVBoxLayout(page)
    layout.setContentsMargins(24, 20, 24, 24)
    layout.setSpacing(14)
    header = make_card("HistoryHeader")
    header_layout = QVBoxLayout(header)
    header_layout.setContentsMargins(18, 14, 18, 14)
    header_layout.setSpacing(3)
    header_layout.addWidget(label("RUN HISTORY", "Kicker"))
    header_layout.addWidget(label("历史输出", "PageTitle"))
    header_layout.addWidget(label("浏览 outputs 下已有运行记录，快速回看报告与元数据。", "Muted"))
    layout.addWidget(header)
    controller.history_combo = QComboBox()
    controller.history_combo.currentIndexChanged.connect(controller.load_history_selection)
    layout.addWidget(controller.history_combo)

    controller.history_tabs = QTabWidget()
    controller.history_summary = QTextBrowser()
    controller.history_full = QTextBrowser()
    controller.history_metadata = QTextBrowser()
    controller.history_tabs.addTab(controller.history_summary, "精简报告")
    controller.history_tabs.addTab(controller.history_full, "完整报告")
    controller.history_tabs.addTab(controller.history_metadata, "元数据")
    layout.addWidget(controller.history_tabs, 1)
    return page


def remove_selected_rows(table: QTableWidget) -> None:
    rows = sorted({index.row() for index in table.selectedIndexes()}, reverse=True)
    for row in rows:
        table.removeRow(row)


def populate_table(table: QTableWidget, rows: list[dict[str, Any]]) -> None:
    table.setRowCount(len(rows))
    columns = [table.horizontalHeaderItem(col).text() for col in range(table.columnCount())]
    for row_index, row in enumerate(rows):
        for col_index, key in enumerate(columns):
            value = row.get(key, "")
            item = QTableWidgetItem("true" if value is True else "false" if value is False else str(value))
            table.setItem(row_index, col_index, item)


def table_rows(table: QTableWidget) -> list[dict[str, Any]]:
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

"""Page builders for the PySide6 desktop application."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QListWidget,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSplitter,
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
    AgentCreditCard,
    AnimatedAgentGraph,
    GlassPanel,
    MetricCard,
    MotionEventList,
    PlataPanel,
    PlataStatusBadge,
    PulseButton,
)
from crewai_multiagent_demo.llm.model_registry import MODEL_REGISTRY


def build_sidebar(controller: Any) -> QWidget:
    sidebar = QFrame()
    sidebar.setObjectName("Sidebar")
    sidebar.setFixedWidth(210)
    layout = QVBoxLayout(sidebar)
    layout.setContentsMargins(24, 26, 24, 22)
    layout.setSpacing(18)

    brand = QLabel("MS")
    brand.setObjectName("BrandPill")
    brand.setFixedWidth(66)
    layout.addWidget(brand, 0, Qt.AlignmentFlag.AlignLeft)

    title = QLabel("Multiagent\nStudio")
    title.setObjectName("SidebarTitle")
    title.setWordWrap(True)
    layout.addWidget(title)

    subtitle = QLabel("多 Agent 工作流控制台")
    subtitle.setObjectName("SidebarSubtitle")
    subtitle.setWordWrap(True)
    layout.addWidget(subtitle)

    layout.addSpacing(20)
    nav_group = QButtonGroup(sidebar)
    nav_group.setExclusive(True)
    controller.nav_buttons = []
    nav_items = [
        ("⌂", "运行"),
        ("⚙", "配置"),
        ("◷", "历史"),
    ]
    for index, (icon, text) in enumerate(nav_items):
        button = QPushButton(f"{icon}  {text}")
        button.setObjectName("NavButton")
        button.setCheckable(True)
        button.clicked.connect(lambda checked=False, page=index: controller.switch_page(page))
        nav_group.addButton(button, index)
        controller.nav_buttons.append(button)
        layout.addWidget(button)
    controller.nav_buttons[0].setChecked(True)

    layout.addStretch()
    hint = PlataPanel()
    hint.setObjectName("SidebarHint")
    hint_layout = QVBoxLayout(hint)
    hint_layout.setContentsMargins(16, 14, 16, 14)
    hint_layout.setSpacing(6)
    hint_title = QLabel("本地入口")
    hint_title.setObjectName("SmallSectionTitle")
    hint_body = QLabel("MultiagentStudio.exe")
    hint_body.setObjectName("MutedText")
    hint_body.setWordWrap(True)
    controller.lock_hint = QLabel("")
    controller.lock_hint.setObjectName("MutedText")
    controller.lock_hint.setWordWrap(True)
    hint_layout.addWidget(hint_title)
    hint_layout.addWidget(hint_body)
    hint_layout.addWidget(controller.lock_hint)
    layout.addWidget(hint)
    return sidebar


def build_run_page(controller: Any) -> QWidget:
    page = _scroll_page()
    content = page.widget()
    layout = content.layout()

    layout.addWidget(_build_run_hero(controller))

    main = QWidget()
    main_layout = QVBoxLayout(main)
    main_layout.setContentsMargins(0, 0, 0, 0)
    main_layout.setSpacing(14)

    left = QWidget()
    left_layout = QVBoxLayout(left)
    left_layout.setContentsMargins(0, 0, 0, 0)
    left_layout.setSpacing(16)
    controller.workflow_card = AgentCreditCard()
    left_layout.addWidget(controller.workflow_card)
    left_layout.addWidget(_build_quick_actions(controller))
    left_layout.addWidget(_build_run_controls(controller), 1)

    right = QWidget()
    right_layout = QVBoxLayout(right)
    right_layout.setContentsMargins(0, 0, 0, 0)
    right_layout.setSpacing(16)
    right_layout.addWidget(_build_orchestration_panel(controller), 1)

    main_layout.addWidget(left)
    main_layout.addWidget(right, 1)
    layout.addWidget(main)
    layout.addWidget(_build_output_panel(controller))
    layout.addStretch()
    return page


def build_config_page(controller: Any) -> QWidget:
    page = _scroll_page()
    content = page.widget()
    layout = content.layout()

    layout.addWidget(_build_page_header("配置中心", "编辑 agents/tasks，保存前自动校验配置。", "CONFIGURATION"))

    summary = QWidget()
    summary_layout = QHBoxLayout(summary)
    summary_layout.setContentsMargins(0, 0, 0, 0)
    summary_layout.setSpacing(14)
    controller.agents_summary_value = QLabel("0")
    controller.tasks_summary_value = QLabel("0")
    controller.config_validation_badge = PlataStatusBadge("待检查", "neutral")
    summary_layout.addWidget(_config_summary_card("Agents", controller.agents_summary_value, "启用状态与角色目标"))
    summary_layout.addWidget(_config_summary_card("Tasks", controller.tasks_summary_value, "任务编排与上下文依赖"))
    summary_layout.addWidget(_validation_summary_card(controller.config_validation_badge))
    layout.addWidget(summary)

    tabs = QTabWidget()
    tabs.setObjectName("SegmentTabs")
    controller.config_tabs = tabs
    controller.agents_table = build_table(["id", "role", "goal", "backstory", "enabled"])
    controller.tasks_table = build_table(
        ["id", "description", "expected_output", "agent", "context", "enabled"]
    )
    tabs.addTab(_wrap_editor(controller.agents_table, controller, "agents"), "Agents")
    tabs.addTab(_wrap_editor(controller.tasks_table, controller, "tasks"), "Tasks")

    json_editor = QWidget()
    json_layout = QHBoxLayout(json_editor)
    json_layout.setContentsMargins(0, 0, 0, 0)
    json_layout.setSpacing(14)
    controller.agents_json = QPlainTextEdit()
    controller.agents_json.setObjectName("JsonEditor")
    controller.tasks_json = QPlainTextEdit()
    controller.tasks_json.setObjectName("JsonEditor")
    json_layout.addWidget(controller.agents_json)
    json_layout.addWidget(controller.tasks_json)
    tabs.addTab(json_editor, "JSON 高级编辑")

    validation = PlataPanel()
    validation.setObjectName("ValidationCard")
    validation_layout = QVBoxLayout(validation)
    validation_layout.setContentsMargins(20, 18, 20, 20)
    validation_layout.setSpacing(14)
    row = QHBoxLayout()
    title = QLabel("配置检查")
    title.setObjectName("SectionTitle")
    validate_button = QPushButton("立即检查")
    validate_button.setObjectName("LinkButton")
    validate_button.clicked.connect(controller.validate_current_config)
    row.addWidget(title)
    row.addStretch()
    row.addWidget(validate_button)
    controller.validation_text = QTextBrowser()
    controller.validation_text.setObjectName("ReportView")
    controller.validation_text.setPlainText("尚未执行检查。")
    validation_layout.addLayout(row)
    validation_layout.addWidget(controller.validation_text)
    tabs.addTab(validation, "配置检查")

    layout.addWidget(tabs, 1)
    layout.addStretch()
    return page


def build_history_page(controller: Any) -> QWidget:
    page = _scroll_page()
    content = page.widget()
    layout = content.layout()

    layout.addWidget(_build_page_header("历史输出", "按运行记录回看报告、元数据与输出文件。", "RUN HISTORY"))

    split = QSplitter(Qt.Orientation.Horizontal)
    split.setChildrenCollapsible(False)

    list_card = PlataPanel()
    list_card.setObjectName("HistoryListCard")
    list_layout = QVBoxLayout(list_card)
    list_layout.setContentsMargins(20, 18, 20, 20)
    list_layout.setSpacing(12)
    header = QLabel("Transactions")
    header.setObjectName("SectionTitle")
    controller.history_list = QListWidget()
    controller.history_list.setObjectName("HistoryList")
    controller.history_list.currentItemChanged.connect(controller.load_history_selection)
    list_layout.addWidget(header)
    list_layout.addWidget(controller.history_list, 1)

    detail = PlataPanel()
    detail.setObjectName("HistoryDetailCard")
    detail_layout = QVBoxLayout(detail)
    detail_layout.setContentsMargins(20, 18, 20, 20)
    detail_layout.setSpacing(14)
    detail_header = QHBoxLayout()
    detail_title = QLabel("报告详情")
    detail_title.setObjectName("SectionTitle")
    open_button = QPushButton("打开目录")
    open_button.setObjectName("LinkButton")
    open_button.clicked.connect(controller.open_selected_history_dir)
    detail_header.addWidget(detail_title)
    detail_header.addStretch()
    detail_header.addWidget(open_button)
    controller.history_tabs = QTabWidget()
    controller.history_tabs.setObjectName("SegmentTabs")
    controller.history_summary = QTextBrowser()
    controller.history_summary.setObjectName("ReportView")
    controller.history_full = QTextBrowser()
    controller.history_full.setObjectName("ReportView")
    controller.history_metadata = QTextBrowser()
    controller.history_metadata.setObjectName("ReportView")
    controller.history_tabs.addTab(controller.history_summary, "精简报告")
    controller.history_tabs.addTab(controller.history_full, "完整报告")
    controller.history_tabs.addTab(controller.history_metadata, "元数据")
    detail_layout.addLayout(detail_header)
    detail_layout.addWidget(controller.history_tabs, 1)

    split.addWidget(list_card)
    split.addWidget(detail)
    split.setSizes([330, 780])
    layout.addWidget(split, 1)
    layout.addStretch()
    return page


def populate_table(
    table: QTableWidget, rows: list[dict[str, Any]], columns: list[str] | None = None
) -> None:
    if columns is None:
        columns = [
            table.horizontalHeaderItem(index).text()
            for index in range(table.columnCount())
            if table.horizontalHeaderItem(index)
        ]
    table.setRowCount(len(rows))
    table.setColumnCount(len(columns))
    table.setHorizontalHeaderLabels(columns)
    for row_index, row_data in enumerate(rows):
        for col_index, col_name in enumerate(columns):
            value = row_data.get(col_name, "")
            if isinstance(value, (list, dict)):
                value = ", ".join(value) if isinstance(value, list) else str(value)
            item = QTableWidgetItem(str(value))
            table.setItem(row_index, col_index, item)
        table.setRowHeight(row_index, 48)


def table_rows(table: QTableWidget) -> list[dict[str, str]]:
    columns = [
        table.horizontalHeaderItem(index).text()
        for index in range(table.columnCount())
        if table.horizontalHeaderItem(index)
    ]
    rows: list[dict[str, str]] = []
    for row in range(table.rowCount()):
        payload: dict[str, str] = {}
        has_value = False
        for column, name in enumerate(columns):
            item = table.item(row, column)
            value = item.text().strip() if item else ""
            if value:
                has_value = True
            payload[name] = value
        if has_value:
            rows.append(payload)
    return rows


def _scroll_page() -> QScrollArea:
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setObjectName("PageScroll")
    content = QWidget()
    layout = QVBoxLayout(content)
    layout.setContentsMargins(20, 22, 20, 26)
    layout.setSpacing(16)
    scroll.setWidget(content)
    return scroll


def _build_run_hero(controller: Any) -> QFrame:
    header = PlataPanel()
    header.setObjectName("CommandHeader")
    layout = QVBoxLayout(header)
    layout.setContentsMargins(26, 24, 26, 24)
    layout.setSpacing(22)

    left = QWidget()
    left_layout = QVBoxLayout(left)
    left_layout.setContentsMargins(0, 0, 0, 0)
    left_layout.setSpacing(10)
    welcome = QHBoxLayout()
    avatar = QLabel("AI")
    avatar.setObjectName("AvatarBubble")
    avatar.setFixedSize(54, 54)
    welcome_text = QLabel("欢迎使用 Multiagent Studio")
    welcome_text.setObjectName("MutedText")
    welcome.addWidget(avatar)
    welcome.addWidget(welcome_text)
    welcome.addStretch()
    title = QLabel("用多 Agent 得到")
    title.setObjectName("HeroTitle")
    accent = QLabel("高质量方案")
    accent.setObjectName("HeroAccent")
    subtitle = QLabel("输入主题，启动协作流，在实时编排与报告区观察任务推进。")
    subtitle.setObjectName("HeroSubtitle")
    subtitle.setWordWrap(True)
    left_layout.addLayout(welcome)
    left_layout.addWidget(title)
    left_layout.addWidget(accent)
    left_layout.addWidget(subtitle)

    metrics = QWidget()
    metrics_layout = QGridLayout(metrics)
    metrics_layout.setContentsMargins(0, 0, 0, 0)
    metrics_layout.setHorizontalSpacing(12)
    metrics_layout.setVerticalSpacing(12)
    controller.status_widgets = {
        "status": MetricCard("状态", "待运行"),
        "model": MetricCard("模型", "flash"),
        "tasks": MetricCard("任务", "0"),
        "elapsed": MetricCard("耗时", "-"),
    }
    for index, card in enumerate(controller.status_widgets.values()):
        metrics_layout.addWidget(card, 0, index)

    layout.addWidget(left)
    layout.addWidget(metrics)
    return header


def _build_quick_actions(controller: Any) -> QFrame:
    card = QWidget()
    layout = QVBoxLayout(card)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(10)
    actions = [
        ("✓", "配置检查", "校验 agents/tasks", controller.validate_current_config),
        ("↺", "清空结果", "重置本次工作区", controller.reset_workspace),
        ("↗", "输出目录", "打开最新结果", controller.open_current_output_dir),
    ]
    for icon, title, subtitle, callback in actions:
        layout.addWidget(_quick_action_card(icon, title, subtitle, callback))
    return card


def _quick_action_card(icon: str, title: str, subtitle: str, callback: Callable[[], None]) -> QFrame:
    card = PlataPanel()
    card.setObjectName("QuickActionCard")
    layout = QVBoxLayout(card)
    layout.setContentsMargins(14, 14, 14, 14)
    layout.setSpacing(8)
    icon_label = QLabel(icon)
    icon_label.setObjectName("QuickIcon")
    title_label = QLabel(title)
    title_label.setObjectName("QuickTitle")
    subtitle_label = QLabel(subtitle)
    subtitle_label.setObjectName("QuickSubtitle")
    subtitle_label.setWordWrap(True)
    action = QPushButton("执行")
    action.setObjectName("LinkButton")
    action.clicked.connect(callback)
    layout.addWidget(icon_label)
    layout.addWidget(title_label)
    layout.addWidget(subtitle_label)
    layout.addStretch()
    layout.addWidget(action, 0, Qt.AlignmentFlag.AlignLeft)
    return card


def _build_run_controls(controller: Any) -> QFrame:
    panel = GlassPanel()
    panel.setObjectName("ControlPanel")
    layout = QVBoxLayout(panel)
    layout.setContentsMargins(20, 18, 20, 20)
    layout.setSpacing(15)
    heading = QLabel("工作流设置")
    heading.setObjectName("SectionTitle")
    layout.addWidget(heading)

    label = QLabel("模型档位")
    label.setObjectName("FieldLabel")
    layout.addWidget(label)
    controller.model_combo = QComboBox()
    controller.model_combo.setVisible(False)
    controller.model_button_group = QButtonGroup(panel)
    controller.model_button_group.setExclusive(True)
    pill_row = QHBoxLayout()
    for index, alias in enumerate(MODEL_REGISTRY.aliases):
        controller.model_combo.addItem(alias)
        button = QPushButton(alias)
        button.setObjectName("PillButton")
        button.setCheckable(True)
        if index == 0:
            button.setChecked(True)
        controller.model_button_group.addButton(button, index)
        button.clicked.connect(
            lambda checked=False, i=index: _select_model(controller, i)
        )
        pill_row.addWidget(button)
    pill_row.addStretch()
    layout.addLayout(pill_row)
    layout.addWidget(controller.model_combo)

    topic_label = QLabel("任务主题")
    topic_label.setObjectName("FieldLabel")
    layout.addWidget(topic_label)
    controller.topic_edit = QTextEdit()
    controller.topic_edit.setObjectName("TopicInput")
    controller.topic_edit.setPlainText(DEFAULT_TOPIC)
    controller.topic_edit.setMinimumHeight(132)
    layout.addWidget(controller.topic_edit)

    controller.api_warning = QLabel("")
    controller.api_warning.setObjectName("WarningCard")
    controller.api_warning.setWordWrap(True)
    layout.addWidget(controller.api_warning)

    controller.run_button = PulseButton("运行工作流")
    controller.run_button.clicked.connect(controller.start_run)
    layout.addWidget(controller.run_button)

    controller.progress = QProgressBar()
    controller.progress.setRange(0, 100)
    controller.progress.setValue(0)
    layout.addWidget(controller.progress)
    layout.addStretch()
    return panel


def _select_model(controller: Any, index: int) -> None:
    controller.model_combo.setCurrentIndex(index)
    controller.refresh_expected_task_count()
    controller.refresh_status_cards()


def _build_orchestration_panel(controller: Any) -> QFrame:
    panel = PlataPanel()
    panel.setObjectName("OrchestrationPanel")
    layout = QVBoxLayout(panel)
    layout.setContentsMargins(22, 20, 22, 22)
    layout.setSpacing(12)
    header = QHBoxLayout()
    title = QLabel("实时编排")
    title.setObjectName("SectionTitle")
    controller.orchestration_badge = PlataStatusBadge("等待事件", "neutral")
    header.addWidget(title)
    header.addStretch()
    header.addWidget(controller.orchestration_badge)
    controller.agent_graph = AnimatedAgentGraph()
    event_label = QLabel("事件流")
    event_label.setObjectName("SmallSectionTitle")
    controller.event_list = MotionEventList()
    layout.addLayout(header)
    layout.addWidget(controller.agent_graph, 3)
    layout.addWidget(event_label)
    layout.addWidget(controller.event_list, 2)
    return panel


def _build_output_panel(controller: Any) -> QFrame:
    panel = PlataPanel()
    panel.setObjectName("OutputPanel")
    layout = QVBoxLayout(panel)
    layout.setContentsMargins(22, 20, 22, 22)
    layout.setSpacing(12)
    header = QHBoxLayout()
    title = QLabel("Transactions")
    title.setObjectName("SectionTitle")
    subtitle = QLabel("输出报告")
    subtitle.setObjectName("MutedText")
    header.addWidget(title)
    header.addWidget(subtitle)
    header.addStretch()
    layout.addLayout(header)

    controller.output_tabs = QTabWidget()
    controller.output_tabs.setObjectName("SegmentTabs")
    controller.summary_view = QTextBrowser()
    controller.summary_view.setObjectName("ReportView")
    controller.full_view = QTextBrowser()
    controller.full_view.setObjectName("ReportView")
    controller.task_outputs_view = QTextBrowser()
    controller.task_outputs_view.setObjectName("ReportView")
    controller.files_view = QTextBrowser()
    controller.files_view.setObjectName("ReportView")
    controller.output_tabs.addTab(controller.summary_view, "精简报告")
    controller.output_tabs.addTab(controller.full_view, "完整报告")
    controller.output_tabs.addTab(controller.task_outputs_view, "任务输出")
    controller.output_tabs.addTab(controller.files_view, "文件")
    layout.addWidget(controller.output_tabs)
    return panel


def _build_page_header(title: str, subtitle: str, kicker: str) -> QFrame:
    header = PlataPanel()
    header.setObjectName("CommandHeader")
    layout = QVBoxLayout(header)
    layout.setContentsMargins(26, 24, 26, 24)
    layout.setSpacing(8)
    kicker_label = QLabel(kicker)
    kicker_label.setObjectName("Kicker")
    title_label = QLabel(title)
    title_label.setObjectName("PageTitle")
    subtitle_label = QLabel(subtitle)
    subtitle_label.setObjectName("HeroSubtitle")
    subtitle_label.setWordWrap(True)
    layout.addWidget(kicker_label)
    layout.addWidget(title_label)
    layout.addWidget(subtitle_label)
    return header


def _config_summary_card(title: str, value_label: QLabel, subtitle: str) -> QFrame:
    card = PlataPanel()
    card.setObjectName("ConfigSummaryCard")
    layout = QVBoxLayout(card)
    layout.setContentsMargins(18, 16, 18, 16)
    layout.setSpacing(7)
    title_label = QLabel(title)
    title_label.setObjectName("MetricLabel")
    value_label.setObjectName("MetricValue")
    subtitle_label = QLabel(subtitle)
    subtitle_label.setObjectName("MutedText")
    subtitle_label.setWordWrap(True)
    layout.addWidget(title_label)
    layout.addWidget(value_label)
    layout.addWidget(subtitle_label)
    return card


def _validation_summary_card(badge: PlataStatusBadge) -> QFrame:
    card = PlataPanel()
    card.setObjectName("ConfigSummaryCard")
    layout = QVBoxLayout(card)
    layout.setContentsMargins(18, 16, 18, 16)
    layout.setSpacing(12)
    title_label = QLabel("校验状态")
    title_label.setObjectName("MetricLabel")
    subtitle = QLabel("保存前建议检查一次配置完整性。")
    subtitle.setObjectName("MutedText")
    subtitle.setWordWrap(True)
    layout.addWidget(title_label)
    layout.addWidget(badge, 0, Qt.AlignmentFlag.AlignLeft)
    layout.addWidget(subtitle)
    return card


def build_table(columns: list[str]) -> QTableWidget:
    table = QTableWidget(0, len(columns))
    table.setObjectName("ConfigTable")
    table.setHorizontalHeaderLabels(columns)
    table.verticalHeader().setVisible(False)
    table.verticalHeader().setDefaultSectionSize(48)
    table.setAlternatingRowColors(True)
    table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
    table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
    table.setWordWrap(False)
    table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
    table.horizontalHeader().setMinimumSectionSize(110)
    return table


def _wrap_editor(table: QTableWidget, controller: Any, kind: str) -> QWidget:
    wrapper = PlataPanel()
    wrapper.setObjectName("TableWorkspace")
    layout = QVBoxLayout(wrapper)
    layout.setContentsMargins(16, 14, 16, 16)
    layout.setSpacing(12)
    layout.addWidget(table, 1)
    actions = QHBoxLayout()
    add_button = QPushButton("新增行")
    add_button.setObjectName("SecondaryButton")
    delete_button = QPushButton("删除选中行")
    delete_button.setObjectName("SecondaryButton")
    save_button = QPushButton("保存")
    save_button.setObjectName("PrimaryButton")
    if kind == "agents":
        add_button.clicked.connect(lambda: table.insertRow(table.rowCount()))
        delete_button.clicked.connect(lambda: _delete_selected_row(table))
        save_button.clicked.connect(controller.save_agents_payload)
    else:
        add_button.clicked.connect(lambda: table.insertRow(table.rowCount()))
        delete_button.clicked.connect(lambda: _delete_selected_row(table))
        save_button.clicked.connect(controller.save_tasks_payload)
    actions.addWidget(add_button)
    actions.addWidget(delete_button)
    actions.addStretch()
    actions.addWidget(save_button)
    layout.addLayout(actions)
    return wrapper


def _delete_selected_row(table: QTableWidget) -> None:
    row = table.currentRow()
    if row >= 0:
        table.removeRow(row)

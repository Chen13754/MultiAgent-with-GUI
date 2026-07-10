from __future__ import annotations


APP_QSS = """
QMainWindow, QWidget, QLabel, QPushButton, QComboBox, QTextEdit, QPlainTextEdit,
QTableWidget, QListWidget, QTabWidget, QTabBar, QTextBrowser, QMessageBox {
  font-family: "Microsoft YaHei UI", "Microsoft YaHei", "Segoe UI", Arial, sans-serif;
  font-size: 13px;
  letter-spacing: 0;
}

QMainWindow, QWidget#Root {
  background: #f3f4f8;
  color: #090a0d;
}

QFrame#Sidebar {
  background: #ffffff;
  border-right: 1px solid rgba(9, 10, 13, 0.06);
}

QScrollArea {
  background: transparent;
  border: 0;
}

QScrollArea > QWidget > QWidget {
  background: transparent;
}

QFrame#PlataPanel, QFrame#GlassPanel, QFrame#CommandHeader, QFrame#OutputPanel,
QFrame#ControlPanel, QFrame#ConfigHeader, QFrame#HistoryHeader, QFrame#MetricCard,
QFrame#Card, QFrame#WorkflowPanel, QFrame#OrchestrationPanel, QFrame#SummaryPanel,
QFrame#QuickActionCard, QFrame#ConfigSummaryCard, QFrame#HistoryDetailCard,
QFrame#HistoryListCard, QFrame#ValidationCard {
  background: #ffffff;
  border: 1px solid rgba(9, 10, 13, 0.08);
  border-radius: 24px;
}

QFrame#MetricCard {
  min-width: 92px;
  max-width: 132px;
}

QFrame#MetricCard[status="running"] {
  border-color: rgba(255, 90, 20, 0.34);
  background: #fff7f2;
}

QFrame#MetricCard[status="succeeded"] {
  border-color: rgba(21, 199, 111, 0.32);
  background: #effcf5;
}

QFrame#MetricCard[status="failed"] {
  border-color: rgba(255, 59, 48, 0.30);
  background: #fce9ec;
}

QFrame#WarningCard {
  background: #fce9ec;
  border: 1px solid rgba(255, 59, 48, 0.16);
  border-radius: 20px;
}

QLabel#BrandTitle {
  color: #090a0d;
  font-size: 22px;
  font-weight: 800;
}

QLabel#BrandPill {
  background: #ff5a14;
  color: #ffffff;
  border-radius: 14px;
  padding: 4px 12px;
  font-size: 11px;
  font-weight: 800;
}

QLabel#PageTitle {
  color: #090a0d;
  font-size: 36px;
  font-weight: 850;
}

QLabel#HeroTitle {
  color: #090a0d;
  font-size: 42px;
  font-weight: 850;
}

QLabel#HeroAccent {
  color: #ff5a14;
  font-size: 42px;
  font-weight: 850;
}

QLabel#SectionTitle {
  color: #090a0d;
  font-size: 22px;
  font-weight: 800;
}

QLabel#Kicker, QLabel#HeroKicker {
  color: #ff5a14;
  font-size: 12px;
  font-weight: 800;
}

QLabel#Muted, QLabel#StatusLabel, QLabel#MetricTitle, QLabel#CardSubtitle {
  color: #7b7f89;
}

QLabel#MetricTitle {
  font-size: 12px;
  font-weight: 700;
}

QLabel#MetricValue, QLabel#StatusValue {
  color: #090a0d;
  font-size: 20px;
  font-weight: 850;
}

QLabel#PlataStatusBadge {
  border-radius: 12px;
  padding: 5px 10px;
  font-size: 12px;
  font-weight: 800;
}

QLabel#PlataStatusBadge[status="success"] {
  background: rgba(21, 199, 111, 0.12);
  color: #087a42;
}

QLabel#PlataStatusBadge[status="warning"] {
  background: #fce9ec;
  color: #b42318;
}

QLabel#PlataStatusBadge[status="active"] {
  background: rgba(255, 90, 20, 0.12);
  color: #c64208;
}

QLabel#WarningLabel {
  color: #7b7f89;
  background: #f7f8fb;
  border: 1px solid rgba(9, 10, 13, 0.06);
  border-radius: 18px;
  padding: 9px 12px;
}

QPushButton {
  background: #ffffff;
  border: 1px solid rgba(9, 10, 13, 0.10);
  border-radius: 18px;
  padding: 10px 16px;
  color: #090a0d;
  font-weight: 750;
}

QPushButton:hover {
  background: #f7f8fb;
  border-color: rgba(36, 20, 232, 0.22);
}

QPushButton:pressed {
  background: #eef0f5;
}

QPushButton:disabled {
  color: rgba(9, 10, 13, 0.32);
  background: rgba(255, 255, 255, 0.58);
}

QPushButton#PrimaryButton {
  background: #ff5a14;
  border-color: #ff5a14;
  color: #ffffff;
  border-radius: 22px;
  min-height: 44px;
  font-size: 15px;
  font-weight: 800;
}

QPushButton#PrimaryButton:hover {
  background: #f04f0d;
  border-color: #f04f0d;
}

QPushButton#LinkButton {
  background: transparent;
  border: 0;
  color: #2414e8;
  font-weight: 800;
  padding: 6px 8px;
}

QPushButton#PillButton {
  background: #ffffff;
  border: 1px solid rgba(9, 10, 13, 0.08);
  border-radius: 18px;
  padding: 9px 14px;
  font-weight: 800;
}

QPushButton#PillButton:checked {
  color: #ffffff;
  background: #2414e8;
  border-color: #2414e8;
}

QPushButton#NavButton {
  text-align: left;
  padding: 12px 14px;
  border: 0;
  background: transparent;
  font-size: 15px;
  font-weight: 800;
  color: #7b7f89;
}

QPushButton#NavButton:hover {
  background: #f7f8fb;
}

QPushButton#NavButton:checked {
  background: rgba(255, 90, 20, 0.10);
  color: #ff5a14;
}

QComboBox, QLineEdit, QTextEdit, QPlainTextEdit, QTableWidget, QListWidget, QTextBrowser {
  background: #ffffff;
  border: 1px solid rgba(9, 10, 13, 0.10);
  border-radius: 18px;
  padding: 9px;
  selection-background-color: rgba(255, 90, 20, 0.18);
  selection-color: #090a0d;
}

QComboBox {
  min-height: 40px;
  padding-left: 14px;
}

QComboBox::drop-down {
  border: 0;
  width: 30px;
}

QTextEdit, QPlainTextEdit, QTextBrowser {
  line-height: 1.45;
}

QTextBrowser {
  background: #ffffff;
}

QListWidget {
  background: transparent;
  border: 0;
}

QListWidget::item {
  background: #ffffff;
  border: 1px solid rgba(9, 10, 13, 0.08);
  border-radius: 16px;
  margin: 5px 2px;
  padding: 11px;
}

QListWidget::item:selected {
  background: #fff2eb;
  color: #090a0d;
  border-left: 4px solid #ff5a14;
}

QTableWidget {
  background: #ffffff;
  border: 1px solid rgba(9, 10, 13, 0.08);
  border-radius: 18px;
  gridline-color: rgba(9, 10, 13, 0.07);
  alternate-background-color: #f8f9fb;
}

QTableWidget::item {
  padding: 8px;
}

QHeaderView::section {
  background: #f3f4f8;
  border: 0;
  border-bottom: 1px solid rgba(9, 10, 13, 0.10);
  padding: 10px;
  color: #343740;
  font-weight: 850;
}

QTabWidget::pane {
  border: 1px solid rgba(9, 10, 13, 0.08);
  border-radius: 22px;
  background: #ffffff;
  top: -1px;
}

QTabBar::tab {
  background: #ffffff;
  border: 1px solid rgba(9, 10, 13, 0.08);
  border-bottom: 0;
  border-top-left-radius: 18px;
  border-top-right-radius: 18px;
  padding: 10px 18px;
  margin-right: 6px;
  color: #7b7f89;
  font-weight: 750;
}

QTabBar::tab:selected {
  color: #ff5a14;
  font-weight: 850;
}

QProgressBar {
  background: #ebeef3;
  border: 0;
  border-radius: 5px;
  min-height: 10px;
  max-height: 10px;
  text-align: center;
  color: transparent;
}

QProgressBar::chunk {
  background: #ff5a14;
  border-radius: 5px;
}

QDialog#PlataBottomSheet {
  background: #ffffff;
  border-radius: 28px;
}

QLabel#SheetSuccessIcon {
  background: #15c76f;
  color: #ffffff;
  border-radius: 36px;
  min-width: 72px;
  min-height: 72px;
  max-width: 72px;
  max-height: 72px;
  font-size: 34px;
  font-weight: 900;
}

QLabel#SheetTitle {
  color: #090a0d;
  font-size: 24px;
  font-weight: 850;
}

QLabel#SheetMessage {
  color: #343740;
  font-size: 14px;
}
"""

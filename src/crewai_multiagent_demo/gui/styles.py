from __future__ import annotations


APP_QSS = """
QMainWindow, QWidget, QLabel, QPushButton, QComboBox, QTextEdit, QPlainTextEdit,
QTableWidget, QListWidget, QTabWidget, QTabBar, QTextBrowser, QMessageBox {
  font-family: "Microsoft YaHei UI", "Microsoft YaHei", "Segoe UI", Arial, sans-serif;
  font-size: 13px;
  letter-spacing: 0;
}

QMainWindow, QWidget#Root {
  background: #f4f8fb;
  color: #142033;
}

QFrame#Sidebar {
  background: rgba(255, 255, 255, 0.78);
  border-right: 1px solid rgba(35, 56, 82, 0.10);
}

QScrollArea {
  background: transparent;
  border: 0;
}

QScrollArea > QWidget > QWidget {
  background: transparent;
}

QFrame#GlassPanel, QFrame#Card, QFrame#OutputPanel, QFrame#ControlPanel,
QFrame#ConfigHeader, QFrame#HistoryHeader, QFrame#MetricCard {
  background: rgba(255, 255, 255, 0.84);
  border: 1px solid rgba(35, 56, 82, 0.10);
  border-radius: 8px;
}

QFrame#CommandHeader {
  background: rgba(255, 255, 255, 0.62);
  border: 1px solid rgba(35, 56, 82, 0.08);
  border-radius: 8px;
}

QFrame#MetricCard[status="running"] {
  border-color: rgba(25, 167, 200, 0.44);
  background: rgba(234, 249, 253, 0.86);
}

QFrame#MetricCard[status="succeeded"] {
  border-color: rgba(36, 166, 106, 0.40);
  background: rgba(238, 250, 244, 0.88);
}

QFrame#MetricCard[status="failed"] {
  border-color: rgba(227, 95, 111, 0.44);
  background: rgba(255, 242, 244, 0.90);
}

QLabel#AppTitle {
  color: #142033;
  font-size: 20px;
  font-weight: 650;
}

QLabel#BrandTitle {
  color: #142033;
  font-size: 18px;
  font-weight: 700;
}

QLabel#PageTitle {
  color: #142033;
  font-size: 27px;
  font-weight: 700;
}

QLabel#SectionTitle {
  color: #142033;
  font-size: 18px;
  font-weight: 700;
}

QLabel#Kicker, QLabel#HeroKicker {
  color: #1689a5;
  font-size: 11px;
  font-weight: 700;
}

QLabel#Muted, QLabel#StatusLabel, QLabel#MetricTitle {
  color: #667085;
}

QLabel#MetricTitle {
  font-size: 11px;
  font-weight: 650;
}

QLabel#MetricValue, QLabel#StatusValue {
  color: #142033;
  font-size: 18px;
  font-weight: 750;
}

QLabel#WarningLabel {
  color: #667085;
  background: rgba(244, 248, 251, 0.78);
  border: 1px solid rgba(35, 56, 82, 0.08);
  border-radius: 8px;
  padding: 7px 10px;
}

QPushButton {
  background: rgba(255, 255, 255, 0.88);
  border: 1px solid rgba(35, 56, 82, 0.14);
  border-radius: 8px;
  padding: 8px 13px;
  color: #142033;
  font-weight: 600;
}

QPushButton:hover {
  background: #ffffff;
  border-color: rgba(25, 167, 200, 0.42);
}

QPushButton:pressed {
  background: #eaf8fc;
  border-color: rgba(25, 167, 200, 0.58);
}

QPushButton:disabled {
  color: rgba(20, 32, 51, 0.36);
  background: rgba(255, 255, 255, 0.44);
  border-color: rgba(35, 56, 82, 0.07);
}

QPushButton#PrimaryButton {
  background: #19a7c8;
  border-color: #19a7c8;
  color: white;
  font-weight: 750;
}

QPushButton#PrimaryButton:hover {
  background: #1398b8;
  border-color: #1398b8;
}

QPushButton#NavButton {
  text-align: left;
  padding: 10px 12px;
  border: 1px solid transparent;
  background: transparent;
  font-weight: 650;
  color: #415064;
}

QPushButton#NavButton:hover {
  background: rgba(25, 167, 200, 0.07);
  border-color: rgba(25, 167, 200, 0.12);
}

QPushButton#NavButton:checked {
  background: rgba(25, 167, 200, 0.12);
  border-color: rgba(25, 167, 200, 0.24);
  color: #126f86;
}

QComboBox, QLineEdit, QTextEdit, QPlainTextEdit, QTableWidget, QListWidget, QTextBrowser {
  background: rgba(255, 255, 255, 0.90);
  border: 1px solid rgba(35, 56, 82, 0.12);
  border-radius: 8px;
  padding: 7px;
  selection-background-color: rgba(25, 167, 200, 0.20);
  selection-color: #142033;
}

QTextBrowser {
  background: rgba(255, 255, 255, 0.72);
}

QComboBox {
  min-height: 34px;
  padding-left: 10px;
}

QComboBox::drop-down {
  border: 0;
  width: 30px;
}

QTextEdit, QPlainTextEdit, QTextBrowser {
  line-height: 1.42;
}

QListWidget::item {
  border: 1px solid rgba(35, 56, 82, 0.08);
  border-radius: 8px;
  margin: 4px 2px;
  padding: 8px;
}

QListWidget::item:selected {
  background: rgba(25, 167, 200, 0.16);
  color: #142033;
}

QTableWidget {
  gridline-color: rgba(35, 56, 82, 0.08);
  alternate-background-color: rgba(244, 248, 251, 0.64);
}

QHeaderView::section {
  background: rgba(238, 246, 250, 0.95);
  border: 0;
  border-bottom: 1px solid rgba(35, 56, 82, 0.12);
  padding: 8px;
  color: #415064;
  font-weight: 700;
}

QTabWidget::pane {
  border: 1px solid rgba(35, 56, 82, 0.10);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.74);
  top: -1px;
}

QTabBar::tab {
  background: rgba(255, 255, 255, 0.54);
  border: 1px solid rgba(35, 56, 82, 0.10);
  border-bottom: 0;
  border-top-left-radius: 8px;
  border-top-right-radius: 8px;
  padding: 8px 14px;
  margin-right: 4px;
  color: #667085;
}

QTabBar::tab:selected {
  background: #ffffff;
  color: #126f86;
  font-weight: 700;
}

QProgressBar {
  background: rgba(213, 228, 237, 0.72);
  border: 0;
  border-radius: 4px;
  min-height: 8px;
  max-height: 8px;
  text-align: center;
  color: transparent;
}

QProgressBar::chunk {
  background: #19a7c8;
  border-radius: 4px;
}
"""

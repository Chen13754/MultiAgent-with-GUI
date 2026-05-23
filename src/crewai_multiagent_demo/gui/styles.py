from __future__ import annotations


APP_QSS = """
QMainWindow, QWidget, QLabel, QPushButton, QComboBox, QTextEdit, QPlainTextEdit,
QTableWidget, QListWidget, QTabWidget, QTabBar, QTextBrowser, QMessageBox {
  font-family: "Microsoft YaHei UI", "Microsoft YaHei", "Segoe UI", Arial, sans-serif;
  font-size: 13px;
}

QMainWindow, QWidget#Root {
  background: #eef4f8;
  color: #172033;
}

QFrame#Sidebar {
  background: rgba(255, 255, 255, 0.82);
  border-right: 1px solid rgba(23, 32, 51, 0.10);
}

QScrollArea {
  background: transparent;
  border: 0;
}

QScrollArea > QWidget > QWidget {
  background: transparent;
}

QFrame#Hero, QFrame#Card, QFrame#StatusCard {
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid rgba(23, 32, 51, 0.10);
  border-radius: 8px;
}

QLabel#AppTitle {
  color: #172033;
  font-size: 21px;
  font-weight: 650;
}

QLabel#HeroKicker, QLabel#Kicker {
  color: #2c7a7b;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 1px;
}

QLabel#HeroTitle {
  color: #172033;
  font-size: 26px;
  font-weight: 650;
}

QLabel#Muted, QLabel#StatusLabel {
  color: rgba(23, 32, 51, 0.64);
}

QLabel#WarningLabel {
  color: #6b7280;
  background: rgba(246, 248, 251, 0.76);
  border: 1px solid rgba(23, 32, 51, 0.08);
  border-radius: 8px;
  padding: 6px 9px;
}

QLabel#StatusValue {
  color: #172033;
  font-size: 16px;
  font-weight: 700;
}

QLabel#StatusBadge {
  background: rgba(23, 105, 170, 0.12);
  color: #0d5f97;
  border-radius: 8px;
  padding: 5px 10px;
  font-weight: 700;
}

QPushButton {
  background: #ffffff;
  border: 1px solid rgba(23, 32, 51, 0.14);
  border-radius: 8px;
  padding: 8px 12px;
  color: #172033;
}

QPushButton:hover {
  background: #f5fafc;
  border-color: rgba(23, 105, 170, 0.34);
}

QPushButton:pressed {
  background: #e9f3f7;
}

QPushButton:disabled {
  color: rgba(23, 32, 51, 0.38);
  background: rgba(255, 255, 255, 0.54);
}

QPushButton#PrimaryButton {
  background: #1769aa;
  border-color: #1769aa;
  color: white;
  font-weight: 700;
}

QPushButton#PrimaryButton:hover {
  background: #1c78bf;
}

QPushButton#NavButton {
  text-align: left;
  padding: 10px 12px;
  border: 0;
  background: transparent;
}

QPushButton#NavButton:checked {
  background: rgba(23, 105, 170, 0.12);
  color: #0d5f97;
  font-weight: 700;
}

QComboBox, QLineEdit, QTextEdit, QPlainTextEdit, QTableWidget, QListWidget {
  background: rgba(255, 255, 255, 0.96);
  border: 1px solid rgba(23, 32, 51, 0.12);
  border-radius: 8px;
  padding: 7px;
  selection-background-color: rgba(23, 105, 170, 0.24);
}

QComboBox {
  min-height: 34px;
  padding-left: 10px;
}

QComboBox::drop-down {
  border: 0;
  width: 28px;
}

QTextEdit, QPlainTextEdit, QTextBrowser {
  line-height: 1.35;
}

QHeaderView::section {
  background: #f6f8fb;
  border: 0;
  border-bottom: 1px solid rgba(23, 32, 51, 0.12);
  padding: 7px;
  font-weight: 700;
}

QTabWidget::pane {
  border: 1px solid rgba(23, 32, 51, 0.10);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.88);
  top: -1px;
}

QTabBar::tab {
  background: rgba(255, 255, 255, 0.66);
  border: 1px solid rgba(23, 32, 51, 0.10);
  border-bottom: 0;
  border-top-left-radius: 8px;
  border-top-right-radius: 8px;
  padding: 8px 14px;
  margin-right: 4px;
}

QTabBar::tab:selected {
  background: #ffffff;
  color: #0d5f97;
  font-weight: 700;
}

QProgressBar {
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid rgba(23, 32, 51, 0.10);
  border-radius: 8px;
  min-height: 22px;
  max-height: 22px;
  text-align: center;
}

QProgressBar::chunk {
  background: #2c7a7b;
  border-radius: 8px;
}
"""

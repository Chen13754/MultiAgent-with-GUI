from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineSettings
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QLabel, QMainWindow

from crewai_multiagent_demo.gui.bridge import StudioBridge


class StudioPage(QWebEnginePage):
    """Limit the embedded browser to bundled files and safe external links."""

    def __init__(self, ui_root: Path, parent: QWebEngineView) -> None:
        super().__init__(parent)
        self._ui_root = ui_root.resolve()

    def acceptNavigationRequest(self, url: QUrl, nav_type: Any, is_main_frame: bool) -> bool:  # noqa: N802
        if url.scheme() == "file":
            try:
                url.toLocalFile()
                Path(url.toLocalFile()).resolve().relative_to(self._ui_root)
                return True
            except (OSError, ValueError):
                return False
        if url.scheme() == "qrc":
            return True
        if is_main_frame and url.scheme() in {"http", "https"}:
            QDesktopServices.openUrl(url)
        return False


class StudioWebWindow(QMainWindow):
    def __init__(self, *, ui_index: Path, bridge: StudioBridge) -> None:
        super().__init__()
        self.bridge = bridge
        self._ui_index = ui_index.resolve()
        self.setWindowTitle("Multiagent Studio")
        self.resize(1220, 780)
        self.setMinimumSize(960, 640)

        if not self._ui_index.exists():
            missing = QLabel("界面资源尚未构建。请先运行前端构建命令。")
            missing.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.setCentralWidget(missing)
            return

        self.web_view = QWebEngineView(self)
        self.page = StudioPage(self._ui_index.parent, self.web_view)
        self.web_view.setPage(self.page)
        self.web_view.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
        settings = self.web_view.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, False)
        # The Vite bundle is loaded as sibling file:// assets. Navigation stays
        # constrained to this directory by StudioPage and reports are rendered
        # without raw HTML, so enabling same-package files does not broaden the
        # browser-facing API to arbitrary local paths.
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.ErrorPageEnabled, False)

        self.channel = QWebChannel(self.page)
        self.channel.registerObject("studio", self.bridge)
        self.page.setWebChannel(self.channel)
        self.web_view.load(QUrl.fromLocalFile(str(self._ui_index)))
        self.setCentralWidget(self.web_view)

    def closeEvent(self, event: Any) -> None:  # noqa: N802 - Qt override.
        if self.bridge.is_running():
            self.bridge.shutdown()
        event.accept()

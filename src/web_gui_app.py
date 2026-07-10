from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

sys.path.insert(0, str(Path(__file__).resolve().parent))

from crewai_multiagent_demo.gui.bridge import StudioBridge
from crewai_multiagent_demo.gui.web_host import StudioWebWindow
from crewai_multiagent_demo.utils.environment import load_project_env
from crewai_multiagent_demo.utils.paths import IS_FROZEN, PROJECT_ROOT, RESOURCE_ROOT, ensure_gui_workspace


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Launch the Multiagent Studio web desktop GUI.")
    parser.add_argument("--smoke-test", action="store_true", help="Load the bundled UI and exit automatically.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    if args.smoke_test:
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        os.environ.setdefault("QTWEBENGINE_CHROMIUM_FLAGS", "--no-sandbox --disable-gpu")

    workspace = ensure_gui_workspace()
    load_project_env()
    app = QApplication(sys.argv[:1])
    app.setFont(QFont("Microsoft YaHei UI", 10))
    bridge = StudioBridge(
        config_dir=workspace.config_dir,
        output_dir=workspace.output_dir,
        legacy_output_dir=workspace.legacy_output_dir,
    )
    ui_root = RESOURCE_ROOT / "webui" if IS_FROZEN else PROJECT_ROOT / "frontend" / "dist"
    window = StudioWebWindow(ui_index=ui_root / "index.html", bridge=bridge)
    window.show()
    smoke_test = args.smoke_test or os.getenv("MULTIAGENT_GUI_SMOKE") == "1"
    if smoke_test:
        completed = {"value": False}

        def finish(ready: object) -> None:
            if completed["value"]:
                return
            completed["value"] = True
            app.exit(0 if bool(ready) else 1)

        def verify_loaded_ui(ok: bool) -> None:
            if not ok:
                finish(False)
                return
            QTimer.singleShot(
                700,
                lambda: window.page.runJavaScript(
                    "Boolean(document.querySelector('#root')?.innerText.includes('Multiagent'))",
                    finish,
                ),
            )

        window.web_view.loadFinished.connect(verify_loaded_ui)
        QTimer.singleShot(8000, lambda: finish(False))
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())

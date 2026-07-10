from __future__ import annotations

import argparse
import multiprocessing
import os
import sys
from pathlib import Path
from urllib.parse import urlparse

from PySide6.QtCore import QTimer
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication, QMessageBox

sys.path.insert(0, str(Path(__file__).resolve().parent))

from crewai_multiagent_demo.gui.bridge import StudioBridge
from crewai_multiagent_demo.gui.web_host import StudioWebWindow
from crewai_multiagent_demo.utils.environment import load_project_env
from crewai_multiagent_demo.utils.logging import configure_file_logging
from crewai_multiagent_demo.utils.paths import (
    IS_FROZEN,
    PROJECT_ROOT,
    RESOURCE_ROOT,
    GuiWorkspace,
    ensure_gui_workspace,
)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Launch the Multiagent Studio web desktop GUI.")
    parser.add_argument("--smoke-test", action="store_true", help="Load the bundled UI and exit automatically.")
    parser.add_argument("--provider-e2e-test", action="store_true", help=argparse.SUPPRESS)
    return parser.parse_args(argv)


def run_provider_e2e(workspace: GuiWorkspace) -> int:
    base_url = os.getenv("DEEPSEEK_BASE_URL", "")
    if urlparse(base_url).hostname not in {"127.0.0.1", "localhost", "::1"}:
        print("Provider E2E is restricted to a loopback DEEPSEEK_BASE_URL.", file=sys.stderr)
        return 2
    from crewai_multiagent_demo.core.runner import run_workflow

    result = run_workflow(
        topic="Local packaged provider end-to-end test",
        model_alias="flash",
        config_dir=workspace.config_dir,
        output_dir=workspace.output_dir,
        request_timeout_seconds=15,
        max_retries=0,
    )
    print(f"Provider E2E passed: {result.run_id}")
    return 0


def main(argv: list[str] | None = None) -> int:
    multiprocessing.freeze_support()
    args = parse_args(argv or sys.argv[1:])
    if args.smoke_test or args.provider_e2e_test:
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        os.environ.setdefault("QTWEBENGINE_CHROMIUM_FLAGS", "--no-sandbox --disable-gpu")

    app = QApplication(sys.argv[:1])
    app.setFont(QFont("Microsoft YaHei UI", 10))
    try:
        workspace = ensure_gui_workspace()
        load_project_env(workspace.env_file)
        configure_file_logging(workspace.cache_dir)
    except Exception as exc:
        if args.smoke_test:
            print(f"Workspace initialization failed: {exc}", file=sys.stderr)
            return 1
        QMessageBox.critical(None, "Multiagent Studio 启动失败", str(exc))
        return 1
    if args.provider_e2e_test:
        return run_provider_e2e(workspace)
    bridge = StudioBridge(
        config_dir=workspace.config_dir,
        output_dir=workspace.output_dir,
        env_file=workspace.env_file,
        cache_dir=workspace.cache_dir,
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
                    "document.documentElement.dataset.studioProtocol === '1'",
                    finish,
                ),
            )

        window.web_view.loadFinished.connect(verify_loaded_ui)
        QTimer.singleShot(8000, lambda: finish(False))
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
